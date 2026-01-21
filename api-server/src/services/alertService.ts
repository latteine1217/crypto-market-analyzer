import pool from '../database/pool';
import { CacheService } from '../database/cache';
import { logger } from '../utils/logger';
import { SocketService } from './socketService';

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

// ... (existing functions: createAlert, getActiveAlerts, etc. keep as is) ...

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

export const getMarketSignals = async (limit: number = 50) => {
  const query = `
    SELECT * FROM market_signals
    ORDER BY time DESC
    LIMIT $1
  `;
  const res = await pool.query(query, [limit]);
  return res.rows;
};

// 監控邏輯
export const startAlertMonitor = () => {
  logger.info('Starting Alert & Signal Monitor...');
  
  // 1. 價格警報監控 (Price Alerts) - 每 5 秒
  setInterval(async () => {
    try {
      const alerts = await getActiveAlerts();
      if (alerts.length === 0) return;

      const symbols = [...new Set(alerts.map(a => a.symbol))];
      
      for (const symbol of symbols) {
        const priceQuery = `
          SELECT close FROM ohlcv 
          JOIN markets m ON ohlcv.market_id = m.id
          WHERE m.symbol = $1 AND timeframe = '1m'
          ORDER BY time DESC LIMIT 1
        `;
        const priceRes = await pool.query(priceQuery, [symbol]);
        
        if (priceRes.rows.length === 0) continue;
        
        const currentPrice = Number(priceRes.rows[0].close);
        const symbolAlerts = alerts.filter(a => a.symbol === symbol);
        
        for (const alert of symbolAlerts) {
          let triggered = false;
          if (alert.condition === 'above' && currentPrice >= Number(alert.target_price)) {
            triggered = true;
          } else if (alert.condition === 'below' && currentPrice <= Number(alert.target_price)) {
            triggered = true;
          }

          if (triggered) {
            logger.info(`Alert Triggered! ${symbol} is ${alert.condition} ${alert.target_price}`);
            
            // 更新 Alert 狀態
            await pool.query(`
              UPDATE price_alerts 
              SET is_active = FALSE, is_triggered = TRUE, triggered_at = NOW() 
              WHERE id = $1
            `, [alert.id]);
            
            // Push via WebSocket
            SocketService.getInstance().emit('price_alert', {
              ...alert,
              triggered_at: new Date(),
              trigger_price: currentPrice
            });
          }
        }
      }
    } catch (error) {
      logger.error('Error in Price Alert Monitor', error);
    }
  }, 5000);

  // 2. 市場訊號監控 (Market Signals) - 每 10 秒檢查是否有新訊號寫入
  let lastSignalTime = new Date(Date.now() - 60000); // Start from 1 min ago

  setInterval(async () => {
    try {
      // 查詢比上次檢查時間更新的訊號
      const query = `
        SELECT * FROM market_signals
        WHERE time > $1
        ORDER BY time ASC
      `;
      const res = await pool.query(query, [lastSignalTime]);
      
      if (res.rows.length > 0) {
        logger.info(`Found ${res.rows.length} new market signals`);
        
        for (const signal of res.rows) {
          // Push via WebSocket
          SocketService.getInstance().emit('market_signal', signal);
          
          // Update last check time
          const signalTime = new Date(signal.time);
          if (signalTime > lastSignalTime) {
            lastSignalTime = signalTime;
          }
        }
      } else {
         // Keep lastSignalTime current to avoid lagging too far behind if no signals
         // But ensure we don't miss anything. Actually, just strictly following DB time is safer.
         // If no signals, do nothing.
      }
    } catch (error) {
      logger.error('Error in Signal Poller', error);
    }
  }, 10000);
};
