import { Router } from 'express';
import { query } from '../database/pool';
import { cacheableQuery } from '../utils/apiUtils';

const router = Router();

// GET /api/markets - 取得所有市場列表
router.get('/', cacheableQuery(
  () => 'markets:all',
  async () => {
    const result = await query(`
      SELECT 
        m.id,
        m.symbol,
        m.base_asset,
        m.quote_asset,
        e.name as exchange,
        m.is_active,
        m.created_at
      FROM markets m
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE m.is_active = true
      ORDER BY e.name, m.symbol
    `);
    return result.rows;
  },
  { ttl: 60 }
));

// GET /api/markets/prices - 取得最新價格 (優化為前十大報表格式)
router.get('/prices', cacheableQuery(
  () => 'markets:prices',
  async () => {
    const result = await query(`
      WITH latest_prices AS (
        SELECT DISTINCT ON (m.id)
          e.name as exchange,
          m.symbol,
          m.id as market_id,
          o.close as price,
          o.volume,
          o.time
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE o.timeframe = '1m'
          AND o.time >= NOW() - INTERVAL '25 hours'
        ORDER BY m.id, o.time DESC
      ),
      stats_24h AS (
        SELECT
          m.id as market_id,
          MAX(o.high) as high_24h,
          MIN(o.low) as low_24h,
          SUM(o.volume) as volume_24h
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        WHERE o.timeframe = '1m'
          AND o.time >= NOW() - INTERVAL '24 hours'
        GROUP BY m.id
      ),
      first_prices_24h AS (
        SELECT DISTINCT ON (m.id)
          m.id as market_id,
          o.open as first_price
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        WHERE o.timeframe = '1m'
          AND o.time >= NOW() - INTERVAL '24 hours'
        ORDER BY m.id, o.time ASC
      ),
      latest_funding AS (
        SELECT DISTINCT ON (market_id)
          market_id,
          value as funding_rate,
          time as funding_time
        FROM market_metrics
        WHERE name = 'funding_rate'
          AND time >= NOW() - INTERVAL '24 hours'
        ORDER BY market_id, time DESC
      )
      SELECT
        lp.exchange,
        lp.symbol,
        lp.price,
        lp.volume,
        CASE
          WHEN fp.first_price IS NOT NULL AND fp.first_price > 0
          THEN ((lp.price - fp.first_price) / fp.first_price * 100)
          ELSE 0
        END as change_24h,
        s24.high_24h,
        s24.low_24h,
        s24.volume_24h,
        lf.funding_rate
      FROM latest_prices lp
      LEFT JOIN first_prices_24h fp ON lp.market_id = fp.market_id
      LEFT JOIN stats_24h s24 ON lp.market_id = s24.market_id
      LEFT JOIN latest_funding lf ON lp.market_id = lf.market_id
      ORDER BY s24.volume_24h DESC NULLS LAST
      LIMIT 10
    `);
    return result.rows;
  },
  { ttl: 5 }
));

// GET /api/markets/quality - 取得最新資料品質指標
router.get('/quality', cacheableQuery(
  () => 'markets:quality',
  async () => {
    const result = await query(`
      SELECT DISTINCT ON (metadata->>'market_id', metadata->>'timeframe')
        sl.time as check_time,
        m.symbol,
        e.name as exchange,
        metadata->>'timeframe' as timeframe,
        (metadata->>'missing_rate')::numeric as missing_rate,
        sl.value as quality_score,
        metadata->>'status' as status
      FROM system_logs sl
      JOIN markets m ON (sl.metadata->>'market_id')::int = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE sl.level = 'QUALITY'
        AND sl.module = 'collector'
      ORDER BY metadata->>'market_id', metadata->>'timeframe', sl.time DESC
    `);
    return result.rows;
  },
  { ttl: 60 }
));

export { router as marketRoutes };
