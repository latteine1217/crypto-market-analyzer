import pool from '../database/pool';
import { CacheService } from '../database/cache';
import { logger } from '../utils/logger';

export interface Alert {
  id: number;
  symbol: string;
  condition: 'above' | 'below';
  target_price: number;
  is_active: boolean;
  is_triggered: boolean;
  triggered_at: Date | null;
  created_at: Date;
}

const cache = new CacheService(0); // Redis instance

export const createAlert = async (symbol: string, condition: 'above' | 'below', targetPrice: number) => {
  const query = `
    INSERT INTO price_alerts (symbol, condition, target_price)
    VALUES ($1, $2, $3)
    RETURNING *
  `;
  const res = await pool.query(query, [symbol, condition, targetPrice]);
  return res.rows[0];
};

export const getActiveAlerts = async () => {
  const query = `
    SELECT * FROM price_alerts
    WHERE is_active = TRUE
    ORDER BY created_at DESC
  `;
  const res = await pool.query(query);
  return res.rows;
};

export const getAllAlerts = async () => {
  const query = `
    SELECT * FROM price_alerts
    ORDER BY created_at DESC
    LIMIT 50
  `;
  const res = await pool.query(query);
  return res.rows;
};

export const deleteAlert = async (id: number) => {
  const query = `DELETE FROM price_alerts WHERE id = $1`;
  await pool.query(query, [id]);
};

// 監控邏輯
export const startAlertMonitor = () => {
  logger.info('Starting Price Alert Monitor...');
  
  // 每 5 秒檢查一次
  setInterval(async () => {
    try {
      const alerts = await getActiveAlerts();
      if (alerts.length === 0) return;

      // 取得所有相關的 symbols
      const symbols = [...new Set(alerts.map(a => a.symbol))];
      
      for (const symbol of symbols) {
        // 從 Redis 或 DB 獲取最新價格 (這裡簡化使用 DB Summary Query 的邏輯，或直接查 latest_price)
        // 為了效能，我們嘗試從 CacheService 獲取最新的 Summary (由 API 路由緩存)
        // 但最準確的是直接查 OHLCV 
        const priceQuery = `
          SELECT close FROM ohlcv 
          JOIN markets m ON ohlcv.market_id = m.id
          WHERE m.symbol = $1 AND timeframe = '1m'
          ORDER BY open_time DESC LIMIT 1
        `;
        const priceRes = await pool.query(priceQuery, [symbol]);
        
        if (priceRes.rows.length === 0) continue;
        
        const currentPrice = Number(priceRes.rows[0].close);

        // 檢查該 Symbol 的所有 Alerts
        const symbolAlerts = alerts.filter(a => a.symbol === symbol);
        
        for (const alert of symbolAlerts) {
          let triggered = false;
          if (alert.condition === 'above' && currentPrice >= Number(alert.target_price)) {
            triggered = true;
          } else if (alert.condition === 'below' && currentPrice <= Number(alert.target_price)) {
            triggered = true;
          }

          if (triggered) {
            logger.info(`Alert Triggered! ${symbol} is ${alert.condition} ${alert.target_price} (Current: ${currentPrice})`);
            
            // 更新 Alert 狀態
            await pool.query(`
              UPDATE price_alerts 
              SET is_active = FALSE, is_triggered = TRUE, triggered_at = NOW() 
              WHERE id = $1
            `, [alert.id]);
          }
        }
      }
    } catch (error) {
      logger.error('Error in Alert Monitor', error);
    }
  }, 5000);
};
