import { Pool, PoolConfig } from 'pg';
import { config } from '../config';

/**
 * 建立標準 PostgreSQL 連接池配置
 */
export const getPoolConfig = (): PoolConfig => ({
  host: config.database.host,
  port: config.database.port,
  database: config.database.database,
  user: config.database.user,
  password: config.database.password,
  max: config.database.max,
  idleTimeoutMillis: config.database.idleTimeoutMillis,
  connectionTimeoutMillis: config.database.connectionTimeoutMillis,
});

/**
 * 建立並初始化連接池
 */
export const createPool = (overrideConfig?: Partial<PoolConfig>): Pool => {
  return new Pool({
    ...getPoolConfig(),
    ...overrideConfig
  });
};
