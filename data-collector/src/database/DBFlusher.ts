/**
 * 資料庫 Flusher
 * 從 Redis 佇列批次取出資料並寫入 TimescaleDB
 */
import { Pool, PoolClient } from 'pg';
import { log } from '../utils/logger';
import { createPool } from '../shared/database/pool';
import { RedisQueue } from '../queues/RedisQueue';
import {
  MessageType,
  Trade,
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

  constructor(private flushConfig: FlushConfig, private exchange: string = '') {
    // 建立 PostgreSQL 連接池
    this.pool = createPool();

    this.pool.on('error', (err: Error) => {
      log.error('PostgreSQL pool error', err);
    });

    this.queue = new RedisQueue(this.exchange);

    log.info('DBFlusher initialized', {
      batchSize: flushConfig.batchSize,
      intervalMs: flushConfig.intervalMs,
      exchange: this.exchange
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
        const liquidationsFlushed = await this.flushLiquidations();

        keepDraining =
          tradesFlushed >= batchSize || 
          orderbooksFlushed >= batchSize ||
          klinesFlushed >= batchSize ||
          liquidationsFlushed >= batchSize;
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
        number, number, number, string | null, string, number
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
          trade.price,
          trade.quantity,
          trade.side || null,
          trade.tradeId.toString(),
          trade.timestamp
        ]);
      }

      const values = rows
        .map(
          (_, i) =>
            `($${i * 6 + 1}, to_timestamp($${i * 6 + 6} / 1000.0), $${i * 6 + 2}, $${i * 6 + 3}, ` +
            `$${i * 6 + 4}, $${i * 6 + 5})`
        )
        .join(', ');

      await client.query(
        `
        INSERT INTO trades (
          market_id, time, price, amount, side, trade_id
        )
        VALUES ${values}
        ON CONFLICT (market_id, time, trade_id) DO NOTHING
        `,
        rows.flat()
      );

      await client.query('COMMIT');

      this.stats.totalFlushed += messages.length;
      log.debug(`Flushed ${messages.length} trades`);

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
    // V3 Schema 已移除 orderbook_snapshots 表以優化效能
    await this.queue.pop(
      MessageType.ORDERBOOK_SNAPSHOT,
      this.flushConfig.batchSize
    );
    return 0;
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
        number, string
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

        const metadata = {
          quote_volume: kline.quoteVolume || null,
          trade_count: kline.trades || null
        };

        rows.push([
          marketId,
          kline.interval,           // timeframe (1m, 5m, 1h, etc.)
          kline.openTime,           // time
          kline.open,
          kline.high,
          kline.low,
          kline.close,
          kline.volume,
          JSON.stringify(metadata)
        ]);
      }

      if (rows.length === 0) {
        await client.query('COMMIT');
        return 0;
      }

      const values = rows
        .map(
          (_, i) =>
            `($${i * 9 + 1}, $${i * 9 + 2}, to_timestamp($${i * 9 + 3} / 1000.0), ` +
            `$${i * 9 + 4}, $${i * 9 + 5}, $${i * 9 + 6}, $${i * 9 + 7}, ` +
            `$${i * 9 + 8}, $${i * 9 + 9})`
        )
        .join(', ');

      await client.query(
        `
        INSERT INTO ohlcv (
          market_id, timeframe, time,
          open, high, low, close, volume,
          metadata
        )
        VALUES ${values}
        ON CONFLICT (market_id, time, timeframe) 
        DO UPDATE SET
          open = EXCLUDED.open,
          high = EXCLUDED.high,
          low = EXCLUDED.low,
          close = EXCLUDED.close,
          volume = EXCLUDED.volume,
          metadata = EXCLUDED.metadata
        `,
        rows.flat()
      );

      await client.query('COMMIT');

      this.stats.totalFlushed += rows.length;
      log.debug(`Flushed ${rows.length} klines (${messages.length - rows.length} skipped as not closed)`);

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
   * Flush 爆倉數據
   */
  private async flushLiquidations(): Promise<number> {
    const messages = await this.queue.pop(
      MessageType.LIQUIDATION,
      this.flushConfig.batchSize
    );

    if (messages.length === 0) {
      return 0;
    }

    log.debug(`Flushing ${messages.length} liquidations`);

    const client = await this.pool.connect();

    try {
      await client.query('BEGIN');

      const rows: Array<[string, string, string, string, number, number, number]> = [];

      for (const msg of messages) {
        const liq = msg.data as any; // Using any to avoid TS mismatch if Liquidation type is not yet recognized globally
        
        const valueUsd = liq.price * liq.quantity;
        
        rows.push([
          msg.exchange,
          liq.symbol,
          liq.side,
          liq.price,
          liq.quantity,
          valueUsd,
          liq.timestamp
        ]);
      }

      const values = rows
        .map(
          (_, i) => {
            const base = i * 7;
            // $1: exchange, $2: symbol, $3: side, $4: price, $5: quantity, $6: value_usd, $7: timestamp
            return `(to_timestamp($${base + 7} / 1000.0), $${base + 1}, $${base + 2}, $${base + 3}, $${base + 4}, $${base + 5}, $${base + 6})`;
          }
        )
        .join(', ');

      await client.query(
        `
        INSERT INTO liquidations (
          time, exchange, symbol, side, price, quantity, value_usd
        )
        VALUES ${values}
        ON CONFLICT (time, exchange, symbol, side, price) DO NOTHING
        `,
        rows.flat()
      );

      await client.query('COMMIT');
      this.stats.totalFlushed += messages.length;
      return messages.length;

    } catch (error) {
      await client.query('ROLLBACK');
      log.error('Failed to flush liquidations', error);
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
        `INSERT INTO exchanges (name, is_active)
         VALUES ($1, TRUE)
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

    // 決定市場類型 (啟發式判斷)
    let marketType = 'spot';
    if (exchangeName === 'bybit') {
      marketType = 'linear_perpetual';
    }

    result = await client.query(
      `INSERT INTO markets (exchange_id, symbol, base_asset, quote_asset, market_type)
       VALUES ($1, $2, $3, $4, $5)
       ON CONFLICT (exchange_id, symbol) DO UPDATE SET 
         base_asset = EXCLUDED.base_asset,
         quote_asset = EXCLUDED.quote_asset,
         market_type = EXCLUDED.market_type
       RETURNING id`,
      [exchangeId, normalizedSymbol, base, quote, marketType]
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
