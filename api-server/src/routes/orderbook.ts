import { Router, Request, Response } from 'express';
import { query } from '../database/pool';
import { CacheService } from '../database/cache';
import { logger } from '../utils/logger';
import { RedisKeys } from '../shared/utils/RedisKeys';
import { sendError } from '../shared/utils/sendError';
import { ErrorType } from '../shared/errors/ErrorClassifier';
import { clampLimit } from '../shared/utils/limits';

const router = Router();
const cache = new CacheService(2); // 2 seconds cache for orderbook

// GET /api/orderbook/:exchange/:symbol - 取得訂單簿快照
router.get('/:exchange/:symbol', async (req: Request, res: Response) => {
  try {
    const exchange = String(req.params.exchange);
    const symbol = String(req.params.symbol);
    const limit = clampLimit(req.query.limit, { defaultValue: 100, max: 200 });

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
      return sendError(res, null, 'Market not found', {
        statusCode: 404,
        errorType: ErrorType.NOT_FOUND,
        errorCode: 'NOT_FOUND'
      });
    }

    const marketId = marketResult.rows[0].id;

    // 取得歷史快照與 OBI (極致容錯版)
    let snapshots: any[] = [];
    try {
      // 先查詢 raw data，不使用可能不存在的欄位別名
      const result = await query(
        `SELECT * FROM orderbook_snapshots WHERE market_id = $1 ORDER BY time DESC LIMIT $2`,
        [marketId, limit]
      );

      snapshots = result.rows.map(r => {
        return {
          time: r.time,
          obi: r.obi !== undefined && r.obi !== null ? parseFloat(r.obi) : 0,
          spread: r.spread !== undefined && r.spread !== null ? parseFloat(r.spread) : 0,
          mid_price: r.mid_price !== undefined && r.mid_price !== null ? parseFloat(r.mid_price) : 0
        };
      }).reverse();
    } catch (dbErr: any) {
      logger.warn('Orderbook historical query failed, returning empty', { error: dbErr.message });
      snapshots = [];
    }

    await cache.set(cacheKey, snapshots);
    res.json({ data: snapshots, cached: false });
  } catch (err) {
    logger.error('Error fetching orderbook', err);
    return sendError(res, err, 'Failed to fetch orderbook data');
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

    // 3. 從 DB 嘗試讀取最新的一筆作為備份 (Restore DB Fallback)
    let snapshot: any = null;
    try {
      const marketResult = await query(
        'SELECT id FROM markets m JOIN exchanges e ON m.exchange_id = e.id WHERE e.name = $1 AND m.symbol = $2 LIMIT 1',
        [exchange, symbol]
      );
      
      if (marketResult.rows.length > 0) {
        const result = await query(
          'SELECT bids, asks, time as timestamp FROM orderbook_snapshots WHERE market_id = $1 ORDER BY time DESC LIMIT 1',
          [marketResult.rows[0].id]
        );
        if (result.rows.length > 0) {
          snapshot = {
            symbol,
            timestamp: result.rows[0].timestamp.getTime(),
            bids: result.rows[0].bids,
            asks: result.rows[0].asks
          };
        }
      }
    } catch (e: any) {
      logger.warn('Failed to fetch latest orderbook from DB fallback', { error: e.message });
    }

    await cache.set(cacheKey, snapshot, 1); // 1 second cache
    res.json({ data: snapshot, cached: false });
  } catch (err) {
    logger.error('Error fetching latest orderbook', err);
    return sendError(res, err, 'Failed to fetch latest orderbook');
  }
});

export { router as orderbookRoutes };
