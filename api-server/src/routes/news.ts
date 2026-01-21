import { Router, Request, Response } from 'express';
import { query } from '../database/pool';
import { CacheService } from '../database/cache';
import { logger } from '../utils/logger';

const router = Router();
const cache = new CacheService(60); // 60 seconds cache for news

// GET /api/news - 取得最新新聞
router.get('/', async (req: Request, res: Response) => {
  try {
    const currency = req.query.currency as string;
    const limit = parseInt(req.query.limit as string) || 50;
    
    const cacheKey = cache.makeKey('news', currency || 'all', limit);
    const cached = await cache.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached, cached: true });
    }

    let sql = `
      SELECT 
        time as published_at, title, url, source_domain, 
        votes_positive, votes_negative, votes_important,
        currencies, kind
      FROM news
    `;
    
    const params: any[] = [];
    
    if (currency) {
      sql += ` WHERE currencies @> $1::jsonb`;
      params.push(JSON.stringify([{ code: currency.toUpperCase() }]));
    }
    
    sql += ` ORDER BY time DESC LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await query(sql, params);
    const news = result.rows;
    
    await cache.set(cacheKey, news);

    res.json({ data: news, cached: false });
  } catch (err) {
    logger.error('Error fetching news', err);
    res.status(500).json({ error: 'Failed to fetch news' });
  }
});

export { router as newsRoutes };
