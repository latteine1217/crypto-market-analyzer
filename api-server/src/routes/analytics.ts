import { Router, Request, Response } from 'express';
import { query } from '../database/pool';
import { logger } from '../utils/logger';

const router = Router();

/**
 * GET /api/analytics/order-size
 * 計算平均訂單大小並進行分類，用於散點圖展示
 */
router.get('/order-size', async (req: Request, res: Response) => {
  const { exchange = 'bybit', symbol = 'BTCUSDT', interval = '1 hour' } = req.query;

  try {
    const result = await query(`
      WITH bucketed_trades AS (
        SELECT 
          time_bucket($1::interval, time) AS bucket,
          AVG(price) as avg_price,
          -- 分別計算買賣
          AVG(CASE WHEN side = 'buy' THEN amount * price END) as avg_buy_notional,
          AVG(CASE WHEN side = 'sell' THEN amount * price END) as avg_sell_notional,
          SUM(amount * price) as total_notional,
          COUNT(*) as trade_count
        FROM trades t
        JOIN markets m ON t.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = $2 AND m.symbol = $3
          AND time >= NOW() - INTERVAL '7 days'
        GROUP BY bucket
        ORDER BY bucket ASC
      )
      SELECT 
        bucket as time,
        avg_price as price,
        COALESCE(avg_buy_notional, 0) as avg_buy_size,
        COALESCE(avg_sell_notional, 0) as avg_sell_size,
        CASE 
          WHEN (total_notional / trade_count) >= 20000 THEN 'Big Whale'
          WHEN (total_notional / trade_count) >= 5000 THEN 'Small Whale'
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

/**
 * GET /api/analytics/cvd
 * 取得累積成交量差 (Cumulative Volume Delta)
 * 用於判斷主動買賣力道與價格背離
 */
router.get('/cvd', async (req: Request, res: Response) => {
  const { exchange = 'bybit', symbol = 'BTCUSDT', interval = '1m', limit = '1000' } = req.query;

  const intervalMap: Record<string, string> = {
    '1m': '1 minute',
    '5m': '5 minutes',
    '15m': '15 minutes',
    '1h': '1 hour',
    '4h': '4 hours',
    '1d': '1 day',
  };
  const bucketInterval = intervalMap[String(interval)] || intervalMap['1m'];
  
  try {
    const result = await query(`
      WITH vars AS (
        SELECT
          $1::text AS exchange,
          $2::text AS symbol,
          $3::interval AS bucket_interval,
          $4::int AS limit_points
      ),
      target_market AS (
        SELECT m.id
        FROM markets m
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = (SELECT exchange FROM vars)
          AND m.symbol = (SELECT symbol FROM vars)
        LIMIT 1
      ),
      time_grid AS (
        SELECT generate_series(
          time_bucket((SELECT bucket_interval FROM vars), NOW() - ((SELECT limit_points FROM vars) * (SELECT bucket_interval FROM vars))),
          time_bucket((SELECT bucket_interval FROM vars), NOW()),
          (SELECT bucket_interval FROM vars)
        ) AS bucket
      ),
      aggregated_cvd AS (
        SELECT
          time_bucket((SELECT bucket_interval FROM vars), cvd.bucket) AS bucket,
          SUM(cvd.volume_delta) AS volume_delta,
          SUM(cvd.buy_volume) AS buy_volume,
          SUM(cvd.sell_volume) AS sell_volume
        FROM market_cvd_1m cvd
        WHERE cvd.market_id = (SELECT id FROM target_market)
          AND cvd.bucket >= time_bucket((SELECT bucket_interval FROM vars), NOW() - ((SELECT limit_points FROM vars) * (SELECT bucket_interval FROM vars)))
        GROUP BY 1
      ),
      filled_delta AS (
        SELECT
          tg.bucket,
          COALESCE(cvd.volume_delta, 0) as volume_delta,
          COALESCE(cvd.buy_volume, 0) as buy_volume,
          COALESCE(cvd.sell_volume, 0) as sell_volume
        FROM time_grid tg
        LEFT JOIN aggregated_cvd cvd ON tg.bucket = cvd.bucket
      ),
      cumulative_calc AS (
        SELECT
          bucket as time,
          volume_delta as delta,
          SUM(volume_delta) OVER (ORDER BY bucket ASC) as cvd,
          buy_volume,
          sell_volume
        FROM filled_delta
      )
      SELECT * FROM cumulative_calc
      ORDER BY time DESC
      LIMIT $4;
    `, [
      exchange, 
      symbol, 
      bucketInterval,
      parseInt(String(limit))
    ]);

    // 注意：Window Function 是在查詢範圍內計算的。
    // CVD 會從區間起點歸零累積，符合 Session CVD 定義。
    
    res.json({ data: result.rows });
  } catch (err) {
    logger.error('Error in CVD analytics', err);
    res.status(500).json({ error: 'Failed to fetch CVD analytics' });
  }
});

export { router as analyticsRoutes };
