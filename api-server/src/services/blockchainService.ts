import pool from '../database/pool';
import { logger } from '../utils/logger';

export const getRichListStats = async (symbol: string, days: number = 30) => {
  const query = `
    SELECT 
      snapshot_date,
      rank_group,
      address_count,
      total_balance,
      total_balance_usd,
      percentage_of_supply
    FROM rich_list_stats
    WHERE symbol = $1
      AND snapshot_date > NOW() - INTERVAL '${days} days'
    ORDER BY snapshot_date ASC, rank_group ASC
  `;
  
  try {
    const result = await pool.query(query, [symbol]);
    return result.rows;
  } catch (error) {
    logger.error(`Error fetching rich list stats for ${symbol}:`, error);
    throw error;
  }
};
