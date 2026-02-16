import { Router, Request, Response } from 'express';
import { query } from '../database/pool';
import { logger } from '../utils/logger';
import { CacheService } from '../database/cache';
import { sendError } from '../shared/utils/sendError';
import { clampLimit } from '../shared/utils/limits';

const router = Router();
const cache = new CacheService(600); // 10 minutes cache for events

/**
 * GET /api/events/upcoming
 * 獲取即將到來的事件（經濟與加密貨幣）
 */
router.get('/upcoming', async (req: Request, res: Response) => {
  const { 
    days = 7,  // 預設查詢未來 7 天
    source,    // 'finnhub' or 'coinmarketcal' or undefined (all)
    impact,    // 'high', 'medium', 'low'
    limit = 50 
  } = req.query;

  const cacheKey = `events:upcoming:${days}:${source || 'all'}:${impact || 'all'}:${limit}`;

  try {
    // 檢查快取
    const cached = await cache.get(cacheKey);
    if (cached) {
      return res.json(cached);
    }

    // 建立查詢條件
    const conditions: string[] = ['time >= NOW()', 'time <= NOW() + $1::interval'];
    const params: any[] = [`${days} days`];
    let paramIndex = 2;

    if (source) {
      conditions.push(`source = $${paramIndex}`);
      params.push(source);
      paramIndex++;
    }

    if (impact) {
      conditions.push(`impact = $${paramIndex}`);
      params.push(impact);
      paramIndex++;
    }

    const limitParam = clampLimit(limit, { defaultValue: 50, max: 100 });

    const result = await query(`
      SELECT 
        id,
        source,
        event_type,
        title,
        description,
        time as event_date,
        country,
        impact,
        actual,
        forecast,
        previous,
        coins,
        url,
        metadata
      FROM events
      WHERE ${conditions.join(' AND ')}
      ORDER BY time ASC, impact DESC
      LIMIT $${paramIndex}
    `, [...params, limitParam]);

    // 按日期分組
    const eventsByDate: Record<string, any[]> = {};
    
    result.rows.forEach((event: any) => {
      const dateKey = new Date(event.event_date).toISOString().split('T')[0];
      if (!eventsByDate[dateKey]) {
        eventsByDate[dateKey] = [];
      }
      eventsByDate[dateKey].push(event);
    });

    const response = {
      total: result.rows.length,
      days: parseInt(days as string),
      eventsByDate
    };

    // 快取 10 分鐘
    await cache.set(cacheKey, response, 600);

    res.json(response);
  } catch (err) {
    logger.error('Error fetching upcoming events', err);
    return sendError(res, err, 'Failed to fetch upcoming events');
  }
});

/**
 * GET /api/events/today
 * 獲取今日事件
 */
router.get('/today', async (req: Request, res: Response) => {
  const cacheKey = 'events:today';

  try {
    const cached = await cache.get(cacheKey);
    if (cached) {
      return res.json(cached);
    }

    const result = await query(`
      SELECT 
        id,
        source,
        event_type,
        title,
        description,
        time as event_date,
        country,
        impact,
        actual,
        forecast,
        previous,
        coins,
        url
      FROM events
      WHERE DATE(time) = CURRENT_DATE
      ORDER BY time ASC, impact DESC
    `);

    const response = {
      date: new Date().toISOString().split('T')[0],
      count: result.rows.length,
      events: result.rows
    };

    // 快取 5 分鐘（今日事件可能會更新 actual 值）
    await cache.set(cacheKey, response, 300);

    res.json({ data: response });
  } catch (err) {
    logger.error('Error fetching today events', err);
    return sendError(res, err, 'Failed to fetch today events');
  }
});

/**
 * GET /api/events/summary
 * 獲取事件統計摘要
 */
router.get('/summary', async (req: Request, res: Response) => {
  const cacheKey = 'events:summary';

  try {
    const cached = await cache.get(cacheKey);
    if (cached) {
      return res.json(cached);
    }

    const result = await query(`
      SELECT 
        DATE(time) as date,
        COUNT(*) as total_events,
        COUNT(*) FILTER (WHERE source = 'finnhub') as economic_events,
        COUNT(*) FILTER (WHERE source = 'coinmarketcal') as crypto_events,
        COUNT(*) FILTER (WHERE impact = 'high') as high_impact,
        COUNT(*) FILTER (WHERE impact = 'medium') as medium_impact,
        COUNT(*) FILTER (WHERE impact = 'low') as low_impact
      FROM events
      WHERE time >= NOW()
        AND time <= NOW() + INTERVAL '30 days'
      GROUP BY DATE(time)
      ORDER BY date ASC
    `);

    const response = {
      summary: result.rows
    };

    // 快取 30 分鐘
    await cache.set(cacheKey, response, 1800);

    res.json(response);
  } catch (err) {
    logger.error('Error fetching events summary', err);
    return sendError(res, err, 'Failed to fetch events summary');
  }
});

export { router as eventsRoutes };
