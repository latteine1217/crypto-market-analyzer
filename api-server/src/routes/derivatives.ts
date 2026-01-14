import { Router, Request, Response } from 'express';
import { query } from '../database/pool';
import { CacheService } from '../database/cache';
import { logger } from '../utils/logger';

const router = Router();
const cache = new CacheService(10); // 10 seconds cache

// GET /api/derivatives/:exchange/:symbol/funding-rate - 取得資金費率歷史
router.get('/:exchange/:symbol/funding-rate', async (req: Request, res: Response) => {
  try {
    const exchange = String(req.params.exchange);
    const symbol = String(req.params.symbol);
    const limit = parseInt(String(req.query.limit || '100')) || 100;

    const cacheKey = cache.makeKey('funding-rate', exchange, symbol, limit);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    const result = await query(
      `
      SELECT
        fr.funding_time as timestamp,
        fr.funding_rate,
        fr.funding_rate_daily,
        fr.mark_price,
        fr.index_price,
        fr.next_funding_time
      FROM funding_rates fr
      JOIN markets m ON fr.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1
        AND m.symbol = $2
      ORDER BY fr.funding_time DESC
      LIMIT $3
      `,
      [exchange, symbol, limit]
    );

    const fundingRates = result.rows.reverse(); // 返回時間順序
    await cache.set(cacheKey, fundingRates);

    res.json({ data: fundingRates, cached: false });
  } catch (err) {
    logger.error('Error fetching funding rates', err);
    res.status(500).json({ error: 'Failed to fetch funding rates' });
  }
});

// GET /api/derivatives/:exchange/:symbol/funding-rate/latest - 取得最新資金費率
router.get('/:exchange/:symbol/funding-rate/latest', async (req: Request, res: Response) => {
  try {
    const exchange = String(req.params.exchange);
    const symbol = String(req.params.symbol);

    const cacheKey = cache.makeKey('funding-rate-latest', exchange, symbol);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    const result = await query(
      `
      SELECT
        fr.funding_time as timestamp,
        fr.funding_rate,
        fr.funding_rate_daily,
        fr.mark_price,
        fr.index_price,
        fr.next_funding_time
      FROM funding_rates fr
      JOIN markets m ON fr.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1
        AND m.symbol = $2
      ORDER BY fr.funding_time DESC
      LIMIT 1
      `,
      [exchange, symbol]
    );

    const latest = result.rows[0] || null;
    await cache.set(cacheKey, latest, 5);

    res.json({ data: latest, cached: false });
  } catch (err) {
    logger.error('Error fetching latest funding rate', err);
    res.status(500).json({ error: 'Failed to fetch latest funding rate' });
  }
});

// GET /api/derivatives/:exchange/:symbol/open-interest - 取得持倉量歷史
router.get('/:exchange/:symbol/open-interest', async (req: Request, res: Response) => {
  try {
    const exchange = String(req.params.exchange);
    const symbol = String(req.params.symbol);
    const limit = parseInt(String(req.query.limit || '100')) || 100;

    const cacheKey = cache.makeKey('open-interest', exchange, symbol, limit);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    const result = await query(
      `
      SELECT
        oi.timestamp,
        oi.open_interest,
        oi.open_interest_usd,
        oi.open_interest_change_24h,
        oi.open_interest_change_pct,
        oi.price,
        oi.volume_24h
      FROM open_interest oi
      JOIN markets m ON oi.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1
        AND m.symbol = $2
      ORDER BY oi.timestamp DESC
      LIMIT $3
      `,
      [exchange, symbol, limit]
    );

    const openInterest = result.rows.reverse(); // 返回時間順序
    await cache.set(cacheKey, openInterest);

    res.json({ data: openInterest, cached: false });
  } catch (err) {
    logger.error('Error fetching open interest', err);
    res.status(500).json({ error: 'Failed to fetch open interest' });
  }
});

// GET /api/derivatives/:exchange/:symbol/open-interest/latest - 取得最新持倉量
router.get('/:exchange/:symbol/open-interest/latest', async (req: Request, res: Response) => {
  try {
    const exchange = String(req.params.exchange);
    const symbol = String(req.params.symbol);

    const cacheKey = cache.makeKey('open-interest-latest', exchange, symbol);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    const result = await query(
      `
      SELECT
        oi.timestamp,
        oi.open_interest,
        oi.open_interest_usd,
        oi.open_interest_change_24h,
        oi.open_interest_change_pct,
        oi.price,
        oi.volume_24h
      FROM open_interest oi
      JOIN markets m ON oi.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1
        AND m.symbol = $2
      ORDER BY oi.timestamp DESC
      LIMIT 1
      `,
      [exchange, symbol]
    );

    const latest = result.rows[0] || null;
    await cache.set(cacheKey, latest, 5);

    res.json({ data: latest, cached: false });
  } catch (err) {
    logger.error('Error fetching latest open interest', err);
    res.status(500).json({ error: 'Failed to fetch latest open interest' });
  }
});

export { router as derivativesRoutes };
