import { query } from '../database/pool';

/**
 * 取得富豪榜分佈統計 (Rich List / Whale Tracking)
 */
export const getRichListStats = async (symbol: string, days: number = 30) => {
  // 取得最近 N 天的快照
  const result = await query(`
    SELECT 
      time as timestamp,
      tier_name,
      address_count,
      total_balance
    FROM address_tier_snapshots s
    JOIN blockchains b ON s.blockchain_id = b.id
    WHERE b.name = $1
      AND time >= NOW() - ($2 || ' days')::INTERVAL
    ORDER BY time ASC, total_balance DESC
  `, [symbol, days]);

  return result.rows;
};

/**
 * 取得特定級別的持倉變化 (用於趨勢圖)
 */
export const getWhaleTrend = async (symbol: string, tier: string, days: number = 30) => {
  const result = await query(`
    SELECT 
      time as timestamp,
      address_count,
      total_balance
    FROM address_tier_snapshots s
    JOIN blockchains b ON s.blockchain_id = b.id
    WHERE b.name = $1 AND tier_name = $3
      AND time >= NOW() - ($2 || ' days')::INTERVAL
    ORDER BY time ASC
  `, [symbol, days, tier]);

  return result.rows;
};