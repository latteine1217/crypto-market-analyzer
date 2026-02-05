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
    
    /**
     * 取得最近的巨鯨大額交易
     */
    export const getRecentWhaleTransactions = async (limit: number = 50) => {
      try {
        const result = await query(`
          SELECT 
            w.time as timestamp,
            w.tx_hash,
            COALESCE(w.from_addr, 'unknown') as from_addr,
            COALESCE(w.to_addr, 'unknown') as to_addr,
            COALESCE(w.amount_usd, 0) as amount_usd,
            COALESCE(w.asset, 'BTC') as asset,
            b.name as blockchain
          FROM whale_transactions w
          JOIN blockchains b ON w.blockchain_id = b.id
          ORDER BY w.time DESC
          LIMIT $1
        `, [limit]);
    
            return result.rows;
    
          } catch (error: any) {
    
            console.error('Whale transaction query failed:', error.message);
    
            return []; // 失敗時回傳空陣列而非拋出 500
    
          }
    
        };
    
            
