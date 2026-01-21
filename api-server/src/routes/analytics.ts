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

  // 映射 interval 到 time_bucket 支援的格式 (若需要聚合大於 1m 的週期)
  // 目前 market_cvd_1m 是 1分鐘粒度。若請求 1h，我們需再聚合。
  // 為求簡化與效能，Phase 2.1 先直接回傳 1m 粒度，讓前端處理或之後做更複雜聚合。
  
  try {
    const result = await query(`
      WITH raw_delta AS (
        SELECT
          bucket,
          volume_delta,
          buy_volume,
          sell_volume
        FROM market_cvd_1m cvd
        JOIN markets m ON cvd.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = $1 
          AND m.symbol = $2
          AND bucket >= NOW() - ($3 || ' minutes')::INTERVAL -- 動態計算時間範圍
        ORDER BY bucket ASC
      ),
      cumulative_calc AS (
        SELECT
          bucket as time,
          volume_delta as delta,
          SUM(volume_delta) OVER (ORDER BY bucket ASC) as cvd,
          buy_volume,
          sell_volume
        FROM raw_delta
      )
      SELECT * FROM cumulative_calc
      ORDER BY time DESC -- 回傳時通常最新在前，或者前端要求
      LIMIT $4;
    `, [
      exchange, 
      symbol, 
      parseInt(String(limit)) * 1, // 粗略估算時間範圍 (1000 points * 1 min)
      limit
    ]);

    // 注意：Window Function 是在篩選後的結果集上計算的。
    // 這意味著 CVD 會從查詢範圍的第一筆開始歸零累積。
    // 這符合 Session CVD 的定義。若要全歷史 CVD，需先計算一個初始 Offset (較慢)。
    
    res.json({ data: result.rows });
  } catch (err) {
    logger.error('Error in CVD analytics', err);
    res.status(500).json({ error: 'Failed to fetch CVD analytics' });
  }
});

export { router as analyticsRoutes };
