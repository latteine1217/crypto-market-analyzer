import { Router, Request, Response } from 'express';
import pool from '../database/pool';
import { CacheService } from '../database/cache';
import { sendError } from '../shared/utils/sendError';

const cacheService = new CacheService();

const router = Router();

/**
 * GET /api/fear-greed/latest
 * 取得最新 Fear & Greed Index
 */
router.get('/latest', async (req: Request, res: Response) => {
  try {
    const cacheKey = 'fear_greed:latest';
    const cached = await cacheService.get(cacheKey);
    
    if (cached) {
      return res.json(cached);
    }

    const result = await pool.query(
      `SELECT time as timestamp, value, classification 
       FROM global_indicators 
       WHERE category = 'sentiment' AND name = 'fear_greed'
       ORDER BY time DESC
       LIMIT 1`
    );

    if (result.rows.length === 0) {
      return res.json({ data: null, message: 'No Fear & Greed data available' });
    }

    const data = {
      timestamp: result.rows[0].timestamp,
      value: parseInt(result.rows[0].value),
      classification: result.rows[0].classification,
      description: getFearGreedDescription(parseInt(result.rows[0].value))
    };

    // 快取 5 分鐘（資料每日更新一次）
    const response = { data };
    await cacheService.set(cacheKey, response, 300);

    res.json(response);
  } catch (error) {
    console.error('Error fetching Fear & Greed Index:', error);
    return sendError(res, error, 'Failed to fetch Fear & Greed Index');
  }
});

/**
 * GET /api/fear-greed/history?days=30
 * 取得歷史 Fear & Greed Index
 */
router.get('/history', async (req: Request, res: Response) => {
  try {
    const days = Math.min(parseInt(req.query.days as string) || 30, 365);
    const cacheKey = `fear_greed:history:${days}`;
    const cached = await cacheService.get(cacheKey);

    if (cached) {
      return res.json(cached);
    }

    const result = await pool.query(
      `SELECT time as timestamp, value, classification
       FROM global_indicators
       WHERE category = 'sentiment' AND name = 'fear_greed'
         AND time >= NOW() - INTERVAL '${days} days'
       ORDER BY time DESC`,
      []
    );

    const data = result.rows.map(row => ({
      timestamp: row.timestamp,
      value: parseInt(row.value),
      classification: row.classification
    }));

    // 快取 10 分鐘
    await cacheService.set(cacheKey, data, 600);

    res.json({ data });
  } catch (error) {
    console.error('Error fetching Fear & Greed history:', error);
    return sendError(res, error, 'Failed to fetch Fear & Greed history');
  }
});

/**
 * 根據數值取得描述
 */
function getFearGreedDescription(value: number): string {
  if (value <= 24) {
    return 'Markets are in extreme fear. This could be a buying opportunity.';
  } else if (value <= 44) {
    return 'Markets are fearful. Investors are worried.';
  } else if (value <= 55) {
    return 'Markets are in a neutral state.';
  } else if (value <= 75) {
    return 'Markets are greedy. Be cautious about overvaluation.';
  } else {
    return 'Markets are in extreme greed. High risk of correction.';
  }
}

export default router;
