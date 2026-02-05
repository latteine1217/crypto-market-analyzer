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

  // [Optimized Strategy] 優先使用原生 Timeframe (1m, 1h, 4h, 1d)
  // 只有當請求非原生 Timeframe (e.g. 15m) 時，才從 1m 數據動態聚合
  // 同時修正 interval 字串，避免 '15m' 被當成 15 months
  const intervalMap: Record<string, string> = {
    '1m': '1 minute',
    '5m': '5 minutes',
    '15m': '15 minutes',
    '1h': '1 hour',
    '4h': '4 hours',
    '1d': '1 day',
  };
  const intervalLiteral = intervalMap[timeframe];
  if (!intervalLiteral) {
    return res.status(400).json({ error: `Unsupported timeframe: ${timeframe}` });
  }

  const nativeTimeframes = ['1m', '1h', '4h', '1d'];
  const useNative = nativeTimeframes.includes(timeframe);

  const querySqlNative = `
      SELECT
        time as timestamp,
        open, high, low, close, volume
      FROM ohlcv o
      JOIN markets m ON o.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1 AND m.symbol = $2 AND o.timeframe = $4
      ORDER BY o.time DESC
      LIMIT $3
    `;

  const querySqlAgg = `
      SELECT
        time_bucket($4::interval, o.time) as timestamp,
        FIRST(o.open, o.time) as open,
        MAX(o.high) as high,
        MIN(o.low) as low,
        LAST(o.close, o.time) as close,
        SUM(o.volume) as volume
      FROM ohlcv o
      JOIN markets m ON o.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1 AND m.symbol = $2 AND o.timeframe = '1m'
      GROUP BY timestamp
      ORDER BY timestamp DESC
      LIMIT $3
    `;

  const nativeParams = [exchange, symbol, limit, timeframe];
  const aggParams = [exchange, symbol, limit, intervalLiteral];

  const result = await query(useNative ? querySqlNative : querySqlAgg, useNative ? nativeParams : aggParams);
  let ohlcv = result.rows.reverse();

  // 如果數據量太少且不是 1m，嘗試回溯更遠的 1m 數據
  if (timeframe !== '1m' && ohlcv.length < Math.min(50, Math.floor(limit / 2))) {
    // fallback: 使用 1m 重新聚合，避免原生 timeframe 缺漏
    const fallback = await query(querySqlAgg, aggParams);
    ohlcv = fallback.rows.reverse();
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
