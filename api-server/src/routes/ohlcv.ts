import { Router, Request, Response } from 'express';
import { query } from '../database/pool';
import { CacheService } from '../database/cache';
import { logger } from '../utils/logger';

const router = Router();
const cache = new CacheService(5); // 5 seconds cache for OHLCV

// GET /api/ohlcv/:exchange/:symbol - 取得 OHLCV 資料
router.get('/:exchange/:symbol', async (req: Request, res: Response) => {
  try {
    const exchange = String(req.params.exchange);
    const symbol = String(req.params.symbol);
    const timeframe = String(req.query.timeframe || '1m');
    const limit = parseInt(String(req.query.limit || '500')) || 500;

    const cacheKey = cache.makeKey('ohlcv', exchange, symbol, timeframe, limit);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    let result;

    if (timeframe === '1m') {
      // 原有邏輯：直接查詢 1m 資料
      result = await query(
        `
        SELECT
          o.open_time as timestamp,
          o.open,
          o.high,
          o.low,
          o.close,
          o.volume
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = $1
          AND m.symbol = $2
          AND o.timeframe = '1m'
        ORDER BY o.open_time DESC
        LIMIT $3
        `,
        [exchange, symbol, limit]
      );
    } else {
      // 動態聚合：Resample from 1m data
      // Map timeframe string to interval (e.g. '5m' -> '5 minutes')
      let interval = '1 minute';
      switch (timeframe) {
        case '5m': interval = '5 minutes'; break;
        case '15m': interval = '15 minutes'; break;
        case '30m': interval = '30 minutes'; break;
        case '1h': interval = '1 hour'; break;
        case '4h': interval = '4 hours'; break;
        case '12h': interval = '12 hours'; break;
        case '1d': interval = '1 day'; break;
        default: interval = '1 minute'; // Fallback
      }

      result = await query(
        `
        SELECT
          time_bucket($3::interval, o.open_time)::text as timestamp,
          FIRST(o.open, o.open_time) as open,
          MAX(o.high) as high,
          MIN(o.low) as low,
          LAST(o.close, o.open_time) as close,
          SUM(o.volume) as volume
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = $1
          AND m.symbol = $2
          AND o.timeframe = '1m'
        GROUP BY timestamp
        ORDER BY timestamp DESC
        LIMIT $4
        `,
        [exchange, symbol, interval, limit]
      );
    }

    const ohlcv = result.rows.reverse(); // 返回時間順序
    await cache.set(cacheKey, ohlcv);

    res.json({ data: ohlcv, cached: false });
  } catch (err) {
    logger.error('Error fetching OHLCV', err);
    res.status(500).json({ error: 'Failed to fetch OHLCV data' });
  }
});

// GET /api/ohlcv/:exchange/:symbol/summary - 取得市場摘要
router.get('/:exchange/:symbol/summary', async (req: Request, res: Response) => {
  try {
    const exchange = String(req.params.exchange);
    const symbol = String(req.params.symbol);

    const cacheKey = cache.makeKey('summary', exchange, symbol);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    // 取得最新資料與 24h 統計
    const result = await query(
      `
      WITH latest_data AS (
        SELECT DISTINCT ON (m.id)
          o.close as latest_price,
          o.open_time
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = $1 AND m.symbol = $2 AND o.timeframe = '1m'
        ORDER BY m.id, o.open_time DESC
        LIMIT 1
      ),
      price_24h_ago AS (
        SELECT o.close as price_24h_ago
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = $1 AND m.symbol = $2 AND o.timeframe = '1m'
          AND o.open_time >= NOW() - INTERVAL '24 hours'
        ORDER BY o.open_time ASC
        LIMIT 1
      ),
      stats_24h AS (
        SELECT
          MAX(o.high) as high_24h,
          MIN(o.low) as low_24h,
          SUM(o.volume) as volume_24h
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = $1 AND m.symbol = $2 AND o.timeframe = '1m'
          AND o.open_time >= NOW() - INTERVAL '24 hours'
      )
      SELECT
        ld.latest_price,
        CASE
          WHEN p24.price_24h_ago IS NOT NULL
          THEN ((ld.latest_price - p24.price_24h_ago) / p24.price_24h_ago * 100)
          ELSE 0
        END as change_24h,
        s24.high_24h,
        s24.low_24h,
        s24.volume_24h
      FROM latest_data ld
      CROSS JOIN price_24h_ago p24
      CROSS JOIN stats_24h s24
      `,
      [exchange, symbol]
    );

    const summary = result.rows[0] || {};
    await cache.set(cacheKey, summary, 5);

    res.json({ data: summary, cached: false });
  } catch (err) {
    logger.error('Error fetching market summary', err);
    res.status(500).json({ error: 'Failed to fetch market summary' });
  }
});

export { router as ohlcvRoutes };
