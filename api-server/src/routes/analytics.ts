import { Router, Request, Response } from 'express';
import { query } from '../database/pool';
import { logger } from '../utils/logger';

const router = Router();

/**
 * GET /api/analytics/order-size
 * 計算平均訂單大小並進行分類，用於散點圖展示
 */
router.get('/order-size', async (req: Request, res: Response) => {
  const { exchange = 'binance', symbol = 'BTCUSDT', interval = '1 hour' } = req.query;

  try {
    const result = await query(`
      WITH bucketed_trades AS (
        SELECT 
          time_bucket($1::interval, timestamp) AS bucket,
          AVG(price) as avg_price,
          SUM(quantity) as total_volume,
          COUNT(*) as trade_count
        FROM trades t
        JOIN markets m ON t.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = $2 AND m.symbol = $3
          AND timestamp >= NOW() - INTERVAL '7 days'
        GROUP BY bucket
        ORDER BY bucket ASC
      )
      SELECT 
        bucket as time,
        avg_price as price,
        (total_volume / trade_count) as avg_order_size,
        CASE 
          WHEN (total_volume / trade_count) >= 0.5 THEN 'Big Whale'
          WHEN (total_volume / trade_count) >= 0.1 THEN 'Small Whale'
          WHEN (total_volume / trade_count) >= 0.02 THEN 'Normal'
          ELSE 'Retail'
        END as category
      FROM bucketed_trades
      WHERE trade_count > 0;
    `, [interval, exchange, symbol]);

    res.json({ data: result.rows });
  } catch (err) {
    logger.error('Error in order-size analytics', err);
    res.status(500).json({ error: 'Failed to fetch order size analytics' });
  }
});

export { router as analyticsRoutes };
