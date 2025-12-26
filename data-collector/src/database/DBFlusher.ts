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
  FlushConfig
} from '../types';

export class DBFlusher {
  private pool: Pool;
  private queue: RedisQueue;
  private flushing: boolean = false;
  private flushTimer: NodeJS.Timeout | null = null;
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
      // Flush 交易數據
      await this.flushTrades();

      // Flush 訂單簿快照
      await this.flushOrderBookSnapshots();

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
  private async flushTrades(): Promise<void> {
    const messages = await this.queue.pop(
      MessageType.TRADE,
      this.flushConfig.batchSize
    );

    if (messages.length === 0) {
      return;
    }

    log.debug(`Flushing ${messages.length} trades`);

    const client = await this.pool.connect();

    try {
      await client.query('BEGIN');

      for (const msg of messages) {
        const trade = msg.data as Trade;

        // 先取得或建立 market_id
        const marketId = await this.getOrCreateMarketId(
          client,
          msg.exchange,
          trade.symbol
        );

        // 插入交易記錄
        await client.query(
          `
          INSERT INTO trades (
            market_id, trade_id, price, quantity, quote_qty,
            side, is_buyer_maker, timestamp
          )
          VALUES ($1, $2, $3, $4, $5, $6, $7, to_timestamp($8 / 1000.0))
          ON CONFLICT (market_id, timestamp, trade_id) DO NOTHING
          `,
          [
            marketId,
            trade.tradeId.toString(),
            trade.price,
            trade.quantity,
            trade.quoteQuantity || null,
            trade.side || null,
            trade.isBuyerMaker,
            trade.timestamp
          ]
        );
      }

      await client.query('COMMIT');

      this.stats.totalFlushed += messages.length;
      log.info(`Flushed ${messages.length} trades`);

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
  private async flushOrderBookSnapshots(): Promise<void> {
    const messages = await this.queue.pop(
      MessageType.ORDERBOOK_SNAPSHOT,
      this.flushConfig.batchSize
    );

    if (messages.length === 0) {
      return;
    }

    log.debug(`Flushing ${messages.length} orderbook snapshots`);

    const client = await this.pool.connect();

    try {
      await client.query('BEGIN');

      for (const msg of messages) {
        const snapshot = msg.data as OrderBookSnapshot;

        const marketId = await this.getOrCreateMarketId(
          client,
          msg.exchange,
          snapshot.symbol
        );

        // 插入訂單簿快照
        await client.query(
          `
          INSERT INTO orderbook_snapshots (
            market_id, timestamp, bids, asks
          )
          VALUES ($1, to_timestamp($2 / 1000.0), $3, $4)
          ON CONFLICT (market_id, timestamp)
          DO UPDATE SET bids = EXCLUDED.bids, asks = EXCLUDED.asks
          `,
          [
            marketId,
            snapshot.timestamp,
            JSON.stringify(snapshot.bids),
            JSON.stringify(snapshot.asks)
          ]
        );
      }

      await client.query('COMMIT');

      this.stats.totalFlushed += messages.length;
      log.info(`Flushed ${messages.length} orderbook snapshots`);

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
   * 取得或建立 market_id
   */
  private async getOrCreateMarketId(
    client: PoolClient,
    exchangeName: string,
    symbol: string
  ): Promise<number> {
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
    const [base, quote] = symbol.replace('/', '').match(/.{1,4}/g) || ['', ''];

    result = await client.query(
      `INSERT INTO markets (exchange_id, symbol, base_asset, quote_asset)
       VALUES ($1, $2, $3, $4)
       ON CONFLICT (exchange_id, symbol) DO UPDATE SET symbol = EXCLUDED.symbol
       RETURNING id`,
      [exchangeId, symbol, base || symbol.slice(0, -4), quote || 'USDT']
    );

    return result.rows[0].id;
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
