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
  OrderBookSnapshot,
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
      // 分別處理各種類型的數據，互不干擾
      try { await this.flushTrades(); } catch (e) { log.error('Trade flush failed', e); }
      try { await this.flushOrderBookSnapshots(); } catch (e) { log.error('Orderbook flush failed', e); }
      try { await this.flushKlines(); } catch (e) { log.error('Kline flush failed', e); }
      try { await this.flushLiquidations(); } catch (e) { log.error('Liquidation flush failed', e); }

      this.stats.lastFlushTime = Date.now();

    } catch (error) {
      log.error('Global flush failed', error);
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

      const rows: Array<[
        number, number, string, string, number | null, number | null, number | null
      ]> = [];

      for (const msg of messages) {
        const snap = msg.data as OrderBookSnapshot;
        
        const marketId = await this.getOrCreateMarketId(
          client,
          msg.exchange,
          snap.symbol
        );

        const bestBid = snap.bids.length > 0 ? snap.bids[0].price : null;
        const bestAsk = snap.asks.length > 0 ? snap.asks[0].price : null;
        const spread = (bestBid && bestAsk) ? (bestAsk - bestBid) : null;
        const midPrice = (bestBid && bestAsk) ? (bestAsk + bestBid) / 2 : null;

        rows.push([
          marketId,
          snap.timestamp,
          JSON.stringify(snap.bids.slice(0, 20)), // 限制存儲 Top 20 檔位
          JSON.stringify(snap.asks.slice(0, 20)),
          spread,
          midPrice,
          snap.obi || null
        ]);
      }

      const values = rows
        .map(
          (_, i) =>
            `($${i * 7 + 1}, to_timestamp($${i * 7 + 2} / 1000.0), $${i * 7 + 3}, $${i * 7 + 4}, $${i * 7 + 5}, $${i * 7 + 6}, $${i * 7 + 7})`
        )
        .join(', ');

      await client.query(
        `
        INSERT INTO orderbook_snapshots (
          market_id, time, bids, asks, spread, mid_price, obi
        )
        VALUES ${values}
        ON CONFLICT (market_id, time) DO NOTHING
        `,
        rows.flat()
      );

      await client.query('COMMIT');

      this.stats.totalFlushed += messages.length;
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

    log.info(`💾 Flushing ${messages.length} liquidations to DB`);

    const client = await this.pool.connect();

    try {
      await client.query('BEGIN');

      let successCount = 0;
      for (const msg of messages) {
        const liq = msg.data as any;
        const valueUsd = liq.price * liq.quantity;
        
        try {
          await client.query(
            `INSERT INTO liquidations (time, exchange, symbol, side, price, quantity, value_usd)
             VALUES (to_timestamp($1 / 1000.0), $2, $3, $4, $5, $6, $7)
             ON CONFLICT DO NOTHING`,
            [liq.timestamp, msg.exchange, liq.symbol, liq.side, liq.price, liq.quantity, valueUsd]
          );
          successCount++;
        } catch (e) {
          log.error(`Failed to insert single liquidation: ${liq.symbol}`, e);
        }
      }

      await client.query('COMMIT');
      this.stats.totalFlushed += successCount;
      log.info(`✅ Successfully flushed ${successCount} liquidations`);
      return successCount;

    } catch (error) {
      await client.query('ROLLBACK');
      log.error('❌ Failed to flush liquidations batch', error);
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

    // ✅ 優先從 symbol_registry 尋找匹配
    const registryResult = await client.query(
      'SELECT internal_symbol, market_type, base_asset, quote_asset FROM symbol_registry WHERE exchange_id = $1 AND native_symbol = $2',
      [exchangeId, normalizedSymbol]
    );

    let marketType = 'spot';

    if (registryResult.rows.length > 0) {
      const reg = registryResult.rows[0];
      marketType = reg.market_type;
      base = reg.base_asset;
      quote = reg.quote_asset;
      // 我們在 markets 表仍存 native_symbol，但屬性由 registry 決定
    } else {
      // 降級邏輯 (Heuristic)
      if (exchangeName === 'bybit') {
        marketType = 'linear_perpetual';
      }
      log.warn(`Symbol ${normalizedSymbol} not found in registry for ${exchangeName}, using heuristics.`);
    }

    result = await client.query(
      `INSERT INTO markets (exchange_id, symbol, base_asset, quote_asset, market_type, is_active)
       VALUES ($1, $2, $3, $4, $5, FALSE)
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
