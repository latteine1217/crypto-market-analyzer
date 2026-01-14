import { Router, Request, Response } from 'express';
import { query } from '../database/pool';
import { CacheService } from '../database/cache';
import { logger } from '../utils/logger';
import { RedisKeys } from '../../shared/utils/RedisKeys';

const router = Router();
const cache = new CacheService(2); // 2 seconds cache for orderbook

// GET /api/orderbook/:exchange/:symbol - 取得訂單簿快照
router.get('/:exchange/:symbol', async (req: Request, res: Response) => {
  try {
    const exchange = String(req.params.exchange);
    const symbol = String(req.params.symbol);
    const limit = parseInt(String(req.query.limit || '100')) || 100;

    const cacheKey = cache.makeKey('orderbook', exchange, symbol, limit);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    // 取得 market_id
    const marketResult = await query(
      `
      SELECT m.id
      FROM markets m
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1 AND m.symbol = $2
      LIMIT 1
      `,
      [exchange, symbol]
    );

    if (marketResult.rows.length === 0) {
      return res.status(404).json({ error: 'Market not found' });
    }

    const marketId = marketResult.rows[0].id;

    // 取得訂單簿快照
    const result = await query(
      `
      SELECT
        timestamp,
        bids,
        asks
      FROM orderbook_snapshots
      WHERE market_id = $1
      ORDER BY timestamp DESC
      LIMIT $2
      `,
      [marketId, limit]
    );

    const snapshots = result.rows;
    await cache.set(cacheKey, snapshots);

    res.json({ data: snapshots, cached: false });
  } catch (err) {
    logger.error('Error fetching orderbook', err);
    res.status(500).json({ error: 'Failed to fetch orderbook data' });
  }
});

// GET /api/orderbook/:exchange/:symbol/latest - 取得最新訂單簿
router.get('/:exchange/:symbol/latest', async (req: Request, res: Response) => {
  try {
    const exchange = String(req.params.exchange);
    const symbol = String(req.params.symbol);

    // 1. 優先從 Redis 獲取即時快照 (Data Collector 寫入的)
    const redisKey = RedisKeys.getOrderBookKey(exchange, symbol);
    const redisData = await cache.hget(redisKey, 'data');
    
    if (redisData) {
      try {
        const snapshot = JSON.parse(redisData);
        return res.json({ 
          data: snapshot, 
          source: 'redis_live',
          cached: true 
        });
      } catch (e) {
        logger.warn('Failed to parse redis orderbook data', { exchange, symbol });
      }
    }

    // 2. 如果 Redis 沒有，檢查 API Server 自己的 Cache
    const cacheKey = cache.makeKey('orderbook', exchange, symbol, 'latest');
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, source: 'api_cache', cached: true });
    }

    // 3. 從資料庫讀取 (Fallback)
    const result = await query(
      `
      SELECT
        obs.timestamp,
        obs.bids,
        obs.asks
      FROM orderbook_snapshots obs
      JOIN markets m ON obs.market_id = m.id
      JOIN exchanges e ON m.exchange_id = e.id
      WHERE e.name = $1 AND m.symbol = $2
      ORDER BY obs.timestamp DESC
      LIMIT 1
      `,
      [exchange, symbol]
    );

    const snapshot = result.rows[0] || null;
    await cache.set(cacheKey, snapshot, 1); // 1 second cache

    res.json({ data: snapshot, cached: false });
  } catch (err) {
    logger.error('Error fetching latest orderbook', err);
    res.status(500).json({ error: 'Failed to fetch latest orderbook' });
  }
});

export { router as orderbookRoutes };
