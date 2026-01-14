import { Router, Request, Response } from 'express';
import { query } from '../database/pool';
import { CacheService } from '../database/cache';
import { logger } from '../utils/logger';

const router = Router();
const cache = new CacheService(60); // 1 minute cache for markets

// GET /api/markets - 取得所有市場列表
router.get('/', async (req: Request, res: Response) => {
  try {
    const cacheKey = cache.makeKey('markets', 'all');
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

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

    const markets = result.rows;
    await cache.set(cacheKey, markets);

    res.json({ data: markets, cached: false });
  } catch (err) {
    logger.error('Error fetching markets', err);
    res.status(500).json({ error: 'Failed to fetch markets' });
  }
});

// GET /api/markets/prices - 取得最新價格
router.get('/prices', async (req: Request, res: Response) => {
  try {
    const cacheKey = cache.makeKey('markets', 'prices');
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    const result = await query(`
      WITH latest_prices AS (
        SELECT DISTINCT ON (m.id)
          e.name as exchange,
          m.symbol,
          m.id as market_id,
          o.close as price,
          o.volume,
          o.open_time
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE o.timeframe = '1m'
          AND o.open_time >= NOW() - INTERVAL '25 hours'
        ORDER BY m.id, o.open_time DESC
      ),
      first_prices_24h AS (
        SELECT DISTINCT ON (m.id)
          m.id as market_id,
          o.open as first_price
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        WHERE o.timeframe = '1m'
          AND o.open_time >= NOW() - INTERVAL '24 hours'
        ORDER BY m.id, o.open_time ASC
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
          AND o.open_time >= NOW() - INTERVAL '24 hours'
        GROUP BY m.id
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
        s24.volume_24h
      FROM latest_prices lp
      LEFT JOIN first_prices_24h fp ON lp.market_id = fp.market_id
      LEFT JOIN stats_24h s24 ON lp.market_id = s24.market_id
      ORDER BY lp.exchange, lp.symbol
    `);

    const prices = result.rows;
    await cache.set(cacheKey, prices, 5); // 5 seconds cache

    res.json({ data: prices, cached: false });
  } catch (err) {
    logger.error('Error fetching market prices', err);
    res.status(500).json({ error: 'Failed to fetch market prices' });
  }
});

// GET /api/markets/quality - 取得最新資料品質指標
router.get('/quality', async (req: Request, res: Response) => {
  try {
    const cacheKey = cache.makeKey('markets', 'quality');
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    const result = await query(`
      SELECT 
        id,
        symbol,
        exchange,
        timeframe,
        check_time,
        missing_rate,
        duplicate_rate,
        quality_score,
        status,
        missing_count,
        expected_count,
        backfill_task_created
      FROM latest_data_quality
      ORDER BY exchange, symbol, timeframe
    `);

    const quality = result.rows;
    await cache.set(cacheKey, quality, 60); // 1 minute cache

    res.json({ data: quality, cached: false });
  } catch (err) {
    logger.error('Error fetching market quality', err);
    res.status(500).json({ error: 'Failed to fetch market quality' });
  }
});

export { router as marketRoutes };
