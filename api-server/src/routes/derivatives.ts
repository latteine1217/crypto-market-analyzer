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
        mm.time as timestamp,
        mm.value as funding_rate,
        (mm.metadata->>'funding_rate_daily')::numeric as funding_rate_daily,
        (mm.metadata->>'mark_price')::numeric as mark_price,
        (mm.metadata->>'index_price')::numeric as index_price,
        (mm.metadata->>'next_funding_time')::timestamptz as next_funding_time
      FROM market_metrics mm
      JOIN markets m ON mm.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1
        AND m.symbol = $2
        AND mm.name = 'funding_rate'
      ORDER BY mm.time DESC
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
        mm.time as timestamp,
        mm.value as funding_rate,
        (mm.metadata->>'funding_rate_daily')::numeric as funding_rate_daily,
        (mm.metadata->>'mark_price')::numeric as mark_price,
        (mm.metadata->>'index_price')::numeric as index_price,
        (mm.metadata->>'next_funding_time')::timestamptz as next_funding_time
      FROM market_metrics mm
      JOIN markets m ON mm.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1
        AND m.symbol = $2
        AND mm.name = 'funding_rate'
      ORDER BY mm.time DESC
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
        mm.time as timestamp,
        mm.value::numeric as open_interest,
        (mm.metadata->>'open_interest_usd')::numeric as open_interest_usd,
        (mm.metadata->>'open_interest_change_24h')::numeric as open_interest_change_24h,
        (mm.metadata->>'open_interest_change_pct')::numeric as open_interest_change_pct,
        (mm.metadata->>'price')::numeric as price,
        (mm.metadata->>'volume_24h')::numeric as volume_24h
      FROM market_metrics mm
      JOIN markets m ON mm.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1
        AND m.symbol = $2
        AND mm.name = 'open_interest'
      ORDER BY mm.time DESC
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
        mm.time as timestamp,
        mm.value::numeric as open_interest,
        (mm.metadata->>'open_interest_usd')::numeric as open_interest_usd,
        (mm.metadata->>'open_interest_change_24h')::numeric as open_interest_change_24h,
        (mm.metadata->>'open_interest_change_pct')::numeric as open_interest_change_pct,
        (mm.metadata->>'price')::numeric as price,
        (mm.metadata->>'volume_24h')::numeric as volume_24h
      FROM market_metrics mm
      JOIN markets m ON mm.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1
        AND m.symbol = $2
        AND mm.name = 'open_interest'
      ORDER BY mm.time DESC
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

// GET /api/derivatives/aggregated/open-interest - 取得全網聚合持倉量
router.get('/aggregated/open-interest', async (req: Request, res: Response) => {
  try {
    const symbol = String(req.query.symbol || 'BTCUSDT');
    const limit = parseInt(String(req.query.limit || '100')) || 100;

    const cacheKey = cache.makeKey('aggregated-open-interest', symbol, limit);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    const result = await query(
      `
      SELECT
        time as timestamp,
        symbol,
        total_oi_usd,
        exchange_count,
        exchange_breakdown
      FROM aggregated_oi
      WHERE symbol = $1
      ORDER BY time DESC
      LIMIT $2
      `,
      [symbol, limit]
    );

    const aggregatedOI = result.rows.reverse();
    await cache.set(cacheKey, aggregatedOI, 30); // Cache for 30s

    res.json({ data: aggregatedOI, cached: false });
  } catch (err) {
    logger.error('Error fetching aggregated open interest', err);
    res.status(500).json({ error: 'Failed to fetch aggregated open interest' });
  }
});

// GET /api/derivatives/aggregated/open-interest/latest - 取得最新全網聚合持倉量
router.get('/aggregated/open-interest/latest', async (req: Request, res: Response) => {
  try {
    const symbol = String(req.query.symbol || 'BTCUSDT');

    const cacheKey = cache.makeKey('aggregated-open-interest-latest', symbol);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    const result = await query(
      `
      SELECT
        time as timestamp,
        symbol,
        total_oi_usd,
        exchange_count,
        exchange_breakdown
      FROM aggregated_oi
      WHERE symbol = $1
      ORDER BY time DESC
      LIMIT 1
      `,
      [symbol]
    );

    const latest = result.rows[0] || null;
    await cache.set(cacheKey, latest, 10); // Cache for 10s

    res.json({ data: latest, cached: false });
  } catch (err) {
    logger.error('Error fetching latest aggregated open interest', err);
    res.status(500).json({ error: 'Failed to fetch latest aggregated open interest' });
  }
});

// GET /api/derivatives/funding-rate/heatmap - 取得資金費率熱力圖數據
router.get('/funding-rate/heatmap', async (req: Request, res: Response) => {
  try {
    const hours = parseInt(String(req.query.hours || '72')) || 72;
    const cacheKey = cache.makeKey('funding-heatmap', hours);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    // 取得熱門交易對最近 N 小時的費率
    // 對齊到 8 小時 (標準結算時間)
    const result = await query(
      `
      SELECT
        time_bucket('8 hours', mm.time) as bucket,
        m.symbol,
        AVG(mm.value) as avg_rate
      FROM market_metrics mm
      JOIN markets m ON mm.market_id = m.id
      WHERE mm.name = 'funding_rate'
        AND mm.time >= NOW() - ($1 || ' hours')::INTERVAL
      GROUP BY bucket, m.symbol
      ORDER BY bucket ASC, m.symbol ASC
      `,
      [hours]
    );

    // 格式化為 Heatmap 所需的矩陣
    const times = [...new Set(result.rows.map(r => r.bucket.toISOString()))].sort();
    const symbols = [...new Set(result.rows.map(r => r.symbol))].sort();
    
    const matrix = symbols.map(s => {
      return times.map(t => {
        const found = result.rows.find(r => r.symbol === s && r.bucket.toISOString() === t);
        return found ? parseFloat(found.avg_rate) : null;
      });
    });

    const heatmapData = { times, symbols, matrix };
    await cache.set(cacheKey, heatmapData, 60); // Cache for 1 min

    res.json({ data: heatmapData, cached: false });
  } catch (err) {
    logger.error('Error fetching funding heatmap', err);
    res.status(500).json({ error: 'Failed to fetch funding heatmap' });
  }
});

// GET /api/derivatives/:exchange/:symbol/liquidations - 取得爆倉歷史
router.get('/:exchange/:symbol/liquidations', async (req: Request, res: Response) => {
  try {
    const exchange = String(req.params.exchange);
    const symbol = String(req.params.symbol);
    const limit = parseInt(String(req.query.limit || '200')) || 200;

    const cacheKey = cache.makeKey('liquidations', exchange, symbol, limit);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    const result = await query(
      `
      SELECT
        time as timestamp,
        side,
        price,
        quantity,
        value_usd
      FROM liquidations
      WHERE exchange = $1
        AND symbol = $2
        AND time > NOW() - INTERVAL '7 days'
      ORDER BY time DESC
      LIMIT $3
      `,
      [exchange, symbol, limit]
    );

    const liquidations = result.rows;
    await cache.set(cacheKey, liquidations, 5); // 爆倉頻率高，快取設短一點

    res.json({ data: liquidations, cached: false });
  } catch (err) {
    logger.error('Error fetching liquidations', err);
    res.status(500).json({ error: 'Failed to fetch liquidation data' });
  }
});

export { router as derivativesRoutes };
