/**
 * 資料庫 Flusher
 * 從 Redis 佇列批次取出資料並寫入 TimescaleDB
 */
import { Pool, PoolClient } from 'pg';
import { log } from '../utils/logger';
import { config } from '../config';
import { RedisQueue } from '../queues/RedisQueue';
import {
  MessageType,
  Trade,
  OrderBookSnapshot,
  Kline,
  FlushConfig
} from '../types';
import { parseSymbol, normalizeSymbol } from '../utils/symbolUtils';

export class DBFlusher {
  private pool: Pool;
  private queue: RedisQueue;
  private flushing: boolean = false;
  private flushTimer: NodeJS.Timeout | null = null;
  private marketIdCache: Map<string, number> = new Map();
  private stats = {
    totalFlushed: 0,
    lastFlushTime: 0,
    errorCount: 0
  };

  constructor(private flushConfig: FlushConfig) {
    // 建立 PostgreSQL 連接池
    this.pool = new Pool({
      host: config.database.host,
      port: config.database.port,
      database: config.database.database,
      user: config.database.user,
      password: config.database.password,
      max: 20,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000
    });

    this.pool.on('error', (err: Error) => {
      log.error('PostgreSQL pool error', err);
    });

    this.queue = new RedisQueue();

    log.info('DBFlusher initialized', {
      batchSize: flushConfig.batchSize,
      intervalMs: flushConfig.intervalMs
    });
  }

  /**
   * 啟動定期 flush
   */
  public start(): void {
    log.info('Starting periodic flush');

    this.flushTimer = setInterval(async () => {
      await this.flushAll();
    }, this.flushConfig.intervalMs);
  }

  /**
   * 停止 flush
   */
  public stop(): void {
    log.info('Stopping periodic flush');

    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
  }

  /**
   * Flush 所有類型的數據
   */
  public async flushAll(): Promise<void> {
    if (this.flushing) {
      log.debug('Flush already in progress, skipping');
      return;
    }

    this.flushing = true;

    try {
      let batches = 0;
      let keepDraining = true;
      const { batchSize, maxBatchesPerFlush } = this.flushConfig;

      while (keepDraining && batches < maxBatchesPerFlush) {
        const tradesFlushed = await this.flushTrades();
        const orderbooksFlushed = await this.flushOrderBookSnapshots();
        const klinesFlushed = await this.flushKlines();

        keepDraining =
          tradesFlushed >= batchSize || 
          orderbooksFlushed >= batchSize ||
          klinesFlushed >= batchSize;
        batches += 1;
      }

      this.stats.lastFlushTime = Date.now();

    } catch (error) {
      log.error('Flush failed', error);
      this.stats.errorCount++;
    } finally {
      this.flushing = false;
    }
  }

  /**
   * Flush 交易數據
   */
  private async flushTrades(): Promise<number> {
    const messages = await this.queue.pop(
      MessageType.TRADE,
      this.flushConfig.batchSize
    );

    if (messages.length === 0) {
      return 0;
    }

    log.debug(`Flushing ${messages.length} trades`);

    const client = await this.pool.connect();

    try {
      await client.query('BEGIN');

      const rows: Array<[
        number, string, number, number, number | null, string | null, boolean,
        number
      ]> = [];

      for (const msg of messages) {
        const trade = msg.data as Trade;

        // 先取得或建立 market_id
        const marketId = await this.getOrCreateMarketId(
          client,
          msg.exchange,
          trade.symbol
        );

        rows.push([
          marketId,
          trade.tradeId.toString(),
          trade.price,
          trade.quantity,
          trade.quoteQuantity || null,
          trade.side || null,
          trade.isBuyerMaker,
          trade.timestamp
        ]);
      }

      const values = rows
        .map(
          (_, i) =>
            `($${i * 8 + 1}, $${i * 8 + 2}, $${i * 8 + 3}, $${i * 8 + 4}, ` +
            `$${i * 8 + 5}, $${i * 8 + 6}, $${i * 8 + 7}, ` +
            `to_timestamp($${i * 8 + 8} / 1000.0))`
        )
        .join(', ');

      await client.query(
        `
        INSERT INTO trades (
          market_id, trade_id, price, quantity, quote_qty,
          side, is_buyer_maker, timestamp
        )
        VALUES ${values}
        ON CONFLICT (market_id, timestamp, trade_id) DO NOTHING
        `,
        rows.flat()
      );

      await client.query('COMMIT');

      this.stats.totalFlushed += messages.length;
      log.info(`Flushed ${messages.length} trades`);

      return messages.length;

    } catch (error) {
      await client.query('ROLLBACK');
      log.error('Failed to flush trades', error);

      // 重新推回佇列
      await this.queue.pushBatch(messages);
      throw error;

    } finally {
      client.release();
    }
  }

  /**
   * Flush 訂單簿快照
   */
  private async flushOrderBookSnapshots(): Promise<number> {
    const messages = await this.queue.pop(
      MessageType.ORDERBOOK_SNAPSHOT,
      this.flushConfig.batchSize
    );

    if (messages.length === 0) {
      return 0;
    }

    log.debug(`Flushing ${messages.length} orderbook snapshots`);

    const client = await this.pool.connect();

    try {
      await client.query('BEGIN');

      const rows: Array<[number, number, string, string]> = [];

      for (const msg of messages) {
        const snapshot = msg.data as OrderBookSnapshot;

        const marketId = await this.getOrCreateMarketId(
          client,
          msg.exchange,
          snapshot.symbol
        );

        rows.push([
          marketId,
          snapshot.timestamp,
          JSON.stringify(snapshot.bids),
          JSON.stringify(snapshot.asks)
        ]);
      }

      const values = rows
        .map(
          (_, i) =>
            `($${i * 4 + 1}, to_timestamp($${i * 4 + 2} / 1000.0), ` +
            `$${i * 4 + 3}, $${i * 4 + 4})`
        )
        .join(', ');

      await client.query(
        `
        INSERT INTO orderbook_snapshots (
          market_id, timestamp, bids, asks
        )
        VALUES ${values}
        ON CONFLICT (market_id, timestamp)
        DO UPDATE SET bids = EXCLUDED.bids, asks = EXCLUDED.asks
        `,
        rows.flat()
      );

      await client.query('COMMIT');

      this.stats.totalFlushed += messages.length;
      log.info(`Flushed ${messages.length} orderbook snapshots`);

      return messages.length;

    } catch (error) {
      await client.query('ROLLBACK');
      log.error('Failed to flush orderbook snapshots', error);

      await this.queue.pushBatch(messages);
      throw error;

    } finally {
      client.release();
    }
  }

  /**
   * Flush K線資料
   */
  private async flushKlines(): Promise<number> {
    const messages = await this.queue.pop(
      MessageType.KLINE,
      this.flushConfig.batchSize
    );

    if (messages.length === 0) {
      return 0;
    }

    log.debug(`Flushing ${messages.length} klines`);

    const client = await this.pool.connect();

    try {
      await client.query('BEGIN');

      const rows: Array<[
        number, string, number, number, number, number, number, 
        number, number | null, number | null
      ]> = [];

      for (const msg of messages) {
        const kline = msg.data as Kline;

        // 只寫入已完結的 K線（避免重複更新）
        if (!kline.isClosed) {
          continue;
        }

        const marketId = await this.getOrCreateMarketId(
          client,
          msg.exchange,
          kline.symbol
        );

        rows.push([
          marketId,
          kline.interval,           // timeframe (1m, 5m, 1h, etc.)
          kline.openTime,           // open_time
          kline.open,
          kline.high,
          kline.low,
          kline.close,
          kline.volume,
          kline.quoteVolume || null,
          kline.trades || null
        ]);
      }

      if (rows.length === 0) {
        await client.query('COMMIT');
        return 0;
      }

      const values = rows
        .map(
          (_, i) =>
            `($${i * 10 + 1}, $${i * 10 + 2}, to_timestamp($${i * 10 + 3} / 1000.0), ` +
            `$${i * 10 + 4}, $${i * 10 + 5}, $${i * 10 + 6}, $${i * 10 + 7}, ` +
            `$${i * 10 + 8}, $${i * 10 + 9}, $${i * 10 + 10})`
        )
        .join(', ');

      await client.query(
        `
        INSERT INTO ohlcv (
          market_id, timeframe, open_time,
          open, high, low, close, volume,
          quote_volume, trade_count
        )
        VALUES ${values}
        ON CONFLICT (market_id, timeframe, open_time) 
        DO UPDATE SET
          open = EXCLUDED.open,
          high = EXCLUDED.high,
          low = EXCLUDED.low,
          close = EXCLUDED.close,
          volume = EXCLUDED.volume,
          quote_volume = EXCLUDED.quote_volume,
          trade_count = EXCLUDED.trade_count
        `,
        rows.flat()
      );

      await client.query('COMMIT');

      this.stats.totalFlushed += rows.length;
      log.info(`Flushed ${rows.length} klines (${messages.length - rows.length} skipped as not closed)`);

      return rows.length;

    } catch (error) {
      await client.query('ROLLBACK');
      log.error('Failed to flush klines', error);

      await this.queue.pushBatch(messages);
      throw error;

    } finally {
      client.release();
    }
  }

  /**
   * 取得或建立 market_id
   */
  private async getOrCreateMarketId(
    client: PoolClient,
    exchangeName: string,
    symbol: string
  ): Promise<number> {
    const cacheKey = `${exchangeName}:${symbol}`;
    const cached = this.marketIdCache.get(cacheKey);
    if (cached) {
      return cached;
    }

    // 取得 exchange_id
    let result = await client.query(
      'SELECT id FROM exchanges WHERE name = $1',
      [exchangeName]
    );

    let exchangeId: number;

    if (result.rows.length === 0) {
      // 建立 exchange
      result = await client.query(
        `INSERT INTO exchanges (name, api_type, is_active)
         VALUES ($1, 'websocket', TRUE)
         RETURNING id`,
        [exchangeName]
      );
      exchangeId = result.rows[0].id;
    } else {
      exchangeId = result.rows[0].id;
    }

    // 取得或建立 market
    let base: string, quote: string;
    try {
      [base, quote] = parseSymbol(symbol);
    } catch (error) {
      log.error(`Failed to parse symbol: ${symbol}`, error);
      throw error;
    }

    // 標準化 symbol 為交易所原生格式 (無斜線)
    const normalizedSymbol = normalizeSymbol(symbol);

    result = await client.query(
      `INSERT INTO markets (exchange_id, symbol, base_asset, quote_asset)
       VALUES ($1, $2, $3, $4)
       ON CONFLICT (exchange_id, symbol) DO UPDATE SET symbol = EXCLUDED.symbol
       RETURNING id`,
      [exchangeId, normalizedSymbol, base, quote]
    );

    const marketId = result.rows[0].id;
    this.marketIdCache.set(cacheKey, marketId);
    return marketId;
  }

  /**
   * 獲取統計資訊
   */
  public getStats(): any {
    return {
      ...this.stats,
      isFlushing: this.flushing
    };
  }

  /**
   * 測試資料庫連接
   */
  public async testConnection(): Promise<boolean> {
    try {
      const client = await this.pool.connect();
      await client.query('SELECT 1');
      client.release();
      log.info('Database connection test successful');
      return true;
    } catch (error) {
      log.error('Database connection test failed', error);
      return false;
    }
  }

  /**
   * 關閉連接
   */
  public async shutdown(): Promise<void> {
    this.stop();
    await this.pool.end();
    await this.queue.disconnect();
    log.info('DBFlusher shutdown complete');
  }
}
