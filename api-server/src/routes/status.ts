import { Router } from 'express';
import { query } from '../database/pool';
import redis from '../database/cache';
import { asyncHandler } from '../shared/utils/asyncHandler';
import { config } from '../shared/config';

const router = Router();

// GET /api/status - 獲取系統真實狀態
router.get('/', asyncHandler(async (req, res) => {
  const startTime = Date.now();
  
  // 1. 檢查資料庫
  let dbStatus = 'operational';
  let dbMetrics = { total_records: 0, db_size: '0 MB' };
  try {
    const recordsResult = await query(`
      SELECT 
        (SELECT count(*) FROM ohlcv) + 
        (SELECT count(*) FROM trades) as total_count
    `);
    dbMetrics.total_records = parseInt(recordsResult.rows[0].total_count);
    
    const sizeResult = await query("SELECT pg_size_pretty(pg_database_size(current_database()))");
    dbMetrics.db_size = sizeResult.rows[0].pg_size_pretty;
  } catch (err) {
    dbStatus = 'degraded';
  }

  // 2. 檢查 Redis
  let redisStatus = 'operational';
  let redisMetrics = { uptime: 0, memory_used: '0 MB' };
  try {
    const info = await redis.info();
    const uptimeMatch = info.match(/uptime_in_seconds:(\d+)/);
    const memoryMatch = info.match(/used_memory_human:([^\r\n]+)/);
    
    redisMetrics.uptime = uptimeMatch ? parseInt(uptimeMatch[1]) : 0;
    redisMetrics.memory_used = memoryMatch ? memoryMatch[1] : '0 MB';
  } catch (err) {
    redisStatus = 'error';
  }

  // 3. 檢查 Collectors (透過資料庫中的最新數據時間判定)
  const collectorStatus = await query(`
    SELECT 
      e.name as exchange,
      m.symbol,
      MAX(o.time) as last_data_time,
      NOW() - MAX(o.time) < INTERVAL '1 minute' as is_active
    FROM ohlcv o
    JOIN markets m ON o.market_id = m.id
    JOIN exchanges e ON m.exchange_id = e.id
    WHERE o.time > NOW() - INTERVAL '1 hour'
    GROUP BY e.name, m.symbol
  `);

  // 4. 系統資訊
  const systemInfo = {
    env: config.server.env,
    node_version: process.version,
    uptime: process.uptime(),
    memory_usage: process.memoryUsage(),
    api_latency_ms: Date.now() - startTime
  };

  res.json({
    success: true,
    data: {
      services: {
        database: { status: dbStatus, ...dbMetrics },
        redis: { status: redisStatus, ...redisMetrics },
        api_server: { status: 'operational', ...systemInfo }
      },
      collectors: collectorStatus.rows,
      timestamp: new Date().toISOString()
    }
  });
}));

export { router as statusRoutes };
