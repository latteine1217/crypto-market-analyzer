/**
 * 配置管理
 * 封裝 ./shared/config 並維持相容性
 */
import { config as sharedConfig } from '../shared/config';
import { DBConfig, RedisConfig, FlushConfig } from '../types';

export const config = {
  // 交易所名稱
  exchange: sharedConfig.collector.exchange,

  // Redis 配置
  redis: {
    host: sharedConfig.redis.host,
    port: sharedConfig.redis.port,
    password: sharedConfig.redis.password,
    db: sharedConfig.redis.db
  } as RedisConfig,

  // TimescaleDB 配置
  database: {
    host: sharedConfig.database.host,
    port: sharedConfig.database.port,
    database: sharedConfig.database.database,
    user: sharedConfig.database.user,
    password: sharedConfig.database.password
  } as DBConfig,

  // Flush 配置
  flush: {
    batchSize: sharedConfig.collector.flushBatchSize,
    intervalMs: sharedConfig.collector.flushIntervalMs,
    maxRetries: 3, // Default
    maxBatchesPerFlush: sharedConfig.collector.maxBatchesPerFlush
  } as FlushConfig,

  // WebSocket 配置
  websocket: {
    reconnect: true,
    reconnectDelay: sharedConfig.collector.reconnectDelay,
    heartbeatInterval: sharedConfig.collector.heartbeatInterval,
    maxReconnectAttempts: sharedConfig.collector.maxReconnectAttempts
  },

  // 訂閱配置
  subscriptions: {
    symbols: sharedConfig.collector.symbols,
    streams: sharedConfig.collector.streams
  },

  // 日誌配置
  logging: {
    level: sharedConfig.server.logLevel,
    file: undefined
  }
};

// 驗證必要配置
export function validateConfig(): void {
  // ConfigSchema.parse already validated this
}

// 顯示配置（隱藏敏感資訊）
export function displayConfig(): void {
  console.log('Configuration (Unified):');
  console.log('  Redis:', `${config.redis.host}:${config.redis.port}`);
  console.log('  Database:', `${config.database.host}:${config.database.port}/${config.database.database}`);
  console.log('  Symbols:', config.subscriptions.symbols.join(', '));
  console.log('  Streams:', config.subscriptions.streams.join(', '));
  console.log('  Flush batch size:', config.flush.batchSize);
  console.log('  Flush interval:', `${config.flush.intervalMs}ms`);
}