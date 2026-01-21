import { Pool, PoolClient } from 'pg';
import { logger } from '../utils/logger';
import { createPool } from '../shared/database/pool';

const pool = createPool();

pool.on('connect', () => {
  logger.info('Database connection established');
});

pool.on('error', (err) => {
  logger.error('Unexpected database error', err);
});

export const query = async (text: string, params?: any[]) => {
  const start = Date.now();
  try {
    const res = await pool.query(text, params);
    const duration = Date.now() - start;
    logger.debug(`Query executed in ${duration}ms: ${text}`);
    return res;
  } catch (err) {
    logger.error('Database query error', { text, params, err });
    throw err;
  }
};

export const getClient = (): Promise<PoolClient> => {
  return pool.connect();
};

export default pool;
