/**
 * 配置管理
 * 從環境變數載入配置
 */
import * as dotenv from 'dotenv';
import { DBConfig, RedisConfig, FlushConfig } from '../types';

dotenv.config();

export const config = {
  // Redis 配置
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
    password: process.env.REDIS_PASSWORD,
    db: parseInt(process.env.REDIS_DB || '0')
  } as RedisConfig,

  // TimescaleDB 配置
  database: {
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5432'),
    database: process.env.POSTGRES_DB || 'crypto_db',
    user: process.env.POSTGRES_USER || 'crypto',
    password: process.env.POSTGRES_PASSWORD || 'crypto_pass'
  } as DBConfig,

  // Flush 配置
  flush: {
    batchSize: parseInt(process.env.FLUSH_BATCH_SIZE || '100'),
    intervalMs: parseInt(process.env.FLUSH_INTERVAL_MS || '5000'),
    maxRetries: parseInt(process.env.FLUSH_MAX_RETRIES || '3'),
    maxBatchesPerFlush: parseInt(process.env.FLUSH_MAX_BATCHES || '3')
  } as FlushConfig,

  // WebSocket 配置
  websocket: {
    reconnect: process.env.WS_RECONNECT !== 'false',
    reconnectDelay: parseInt(process.env.WS_RECONNECT_DELAY || '5000'),
    heartbeatInterval: parseInt(process.env.WS_HEARTBEAT_INTERVAL || '30000'),
    maxReconnectAttempts: parseInt(process.env.WS_MAX_RECONNECT_ATTEMPTS || '10')
  },

  // 訂閱配置
  subscriptions: {
    symbols: (process.env.SYMBOLS || 'BTCUSDT,ETHUSDT').split(','),
    streams: (process.env.STREAMS || 'trade,depth').split(',')
  },

  // 日誌配置
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: process.env.LOG_FILE
  }
};

// 驗證必要配置
export function validateConfig(): void {
  const required = [
    'POSTGRES_HOST',
    'POSTGRES_DB',
    'POSTGRES_USER',
    'POSTGRES_PASSWORD',
    'REDIS_HOST'
  ];

  const missing = required.filter(key => !process.env[key]);

  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
  }
}

// 顯示配置（隱藏敏感資訊）
export function displayConfig(): void {
  console.log('Configuration:');
  console.log('  Redis:', `${config.redis.host}:${config.redis.port}`);
  console.log('  Database:', `${config.database.host}:${config.database.port}/${config.database.database}`);
  console.log('  Symbols:', config.subscriptions.symbols.join(', '));
  console.log('  Streams:', config.subscriptions.streams.join(', '));
  console.log('  Flush batch size:', config.flush.batchSize);
  console.log('  Flush interval:', `${config.flush.intervalMs}ms`);
}
