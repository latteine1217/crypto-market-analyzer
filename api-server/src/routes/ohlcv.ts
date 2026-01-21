import { Router, Request, Response } from 'express';
import { query } from '../database/pool';
import { CacheService } from '../database/cache';
import { logger } from '../utils/logger';
import { asyncHandler } from '../shared/utils/asyncHandler';
import { Errors } from '../shared/errors/ErrorClassifier';

const router = Router();
const cache = new CacheService(5); // 5 seconds cache for OHLCV

// GET /api/ohlcv/:exchange/:symbol - 取得 OHLCV 資料
router.get('/:exchange/:symbol', asyncHandler(async (req: Request, res: Response) => {
  const exchange = String(req.params.exchange);
  const symbol = String(req.params.symbol);
  const timeframe = String(req.query.timeframe || '1m');
  const limit = parseInt(String(req.query.limit || '500')) || 500;

  const cacheKey = cache.makeKey('ohlcv', exchange, symbol, timeframe, limit);
  const cached = await cache.get(cacheKey);
  
  if (cached) {
    return res.json({ data: cached, cached: true });
  }

  // 1. 先嘗試直接查詢該 timeframe 的現成資料
  const directResult = await query(
    `
    SELECT
      time as timestamp,
      open, high, low, close, volume
    FROM ohlcv o
    JOIN markets m ON o.market_id = m.id
    JOIN exchanges e ON m.exchange_id = e.id
    WHERE e.name = $1
      AND m.symbol = $2
      AND o.timeframe = $3
    ORDER BY o.time DESC
    LIMIT $4
    `,
    [exchange, symbol, timeframe, limit]
  );

  let ohlcv: any[] = [];
  
  // 決定聚合區間
  let interval = '1 minute';
  if (timeframe !== '1m') {
    switch (timeframe) {
      case '5m': interval = '5 minutes'; break;
      case '15m': interval = '15 minutes'; break;
      case '30m': interval = '30 minutes'; break;
      case '1h': interval = '1 hour'; break;
      case '4h': interval = '4 hours'; break;
      case '12h': interval = '12 hours'; break;
      case '1d': interval = '1 day'; break;
      default: interval = '1 minute';
    }
  }

  if (directResult.rows.length > 0) {
    // 如果有直接儲存的該時框資料，直接使用
    ohlcv = directResult.rows.reverse();

    // [Hybrid Strategy] 如果是非 1m 資料，檢查是否需要從 1m 補齊最新數據（包含未完成 K 線）
    if (timeframe !== '1m') {
      const lastCandle = ohlcv[ohlcv.length - 1];
      const lastTimestamp = new Date(lastCandle.timestamp).toISOString();

      // 查詢比最後一根 K 線更新的 1m 數據並聚合
      const pendingData = await query(
        `
        SELECT
          time_bucket($3::interval, o.time) as timestamp,
          FIRST(o.open, o.time) as open,
          MAX(o.high) as high,
          MIN(o.low) as low,
          LAST(o.close, o.time) as close,
          SUM(o.volume) as volume
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = $1
          AND m.symbol = $2
          AND o.timeframe = '1m'
          AND o.time >= ($4::timestamptz + $3::interval)
        GROUP BY timestamp
        ORDER BY timestamp ASC
        `,
        [exchange, symbol, interval, lastTimestamp]
      );

      if (pendingData.rows.length > 0) {
        ohlcv = ohlcv.concat(pendingData.rows);
      }
    }

  } else if (timeframe !== '1m') {
    // 2. 如果沒有直接資料且不是 1m，嘗試從 1m 進行動態聚合 (Full Aggregation)
    const resampleResult = await query(
      `
      SELECT
        time_bucket($3::interval, o.time) as timestamp,
        FIRST(o.open, o.time) as open,
        MAX(o.high) as high,
        MIN(o.low) as low,
        LAST(o.close, o.time) as close,
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
    ohlcv = resampleResult.rows.reverse();
  } else {
    ohlcv = [];
  }

  if (ohlcv.length === 0) {
    // Optional: could throw NotFound if expected, but for OHLCV empty is sometimes normal
  }

  await cache.set(cacheKey, ohlcv);
  res.json({ data: ohlcv, cached: false });
}));

// GET /api/ohlcv/:exchange/:symbol/summary - 取得市場摘要
router.get('/:exchange/:symbol/summary', asyncHandler(async (req: Request, res: Response) => {
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
        o.time
      FROM ohlcv o
      JOIN markets m ON o.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1 AND m.symbol = $2 AND o.timeframe = '1m'
      ORDER BY m.id, o.time DESC
      LIMIT 1
    ),
    price_24h_ago AS (
      SELECT o.close as price_24h_ago
      FROM ohlcv o
      JOIN markets m ON o.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1 AND m.symbol = $2 AND o.timeframe = '1m'
        AND o.time >= NOW() - INTERVAL '24 hours'
      ORDER BY o.time ASC
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
        AND o.time >= NOW() - INTERVAL '24 hours'
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
    LEFT JOIN price_24h_ago p24 ON TRUE
    LEFT JOIN stats_24h s24 ON TRUE
    `,
    [exchange, symbol]
  );

  if (result.rows.length === 0 || !result.rows[0].latest_price) {
    throw Errors.NotFound(`Market summary for ${exchange}:${symbol}`);
  }

  const summary = result.rows[0];
  await cache.set(cacheKey, summary, 5);

  res.json({ data: summary, cached: false });
}));

export { router as ohlcvRoutes };
