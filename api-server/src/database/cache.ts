import Redis from 'ioredis';
import { logger } from '../utils/logger';
import { RedisKeys } from '../shared_copy/utils/RedisKeys';

const ENABLE_CACHE = process.env.ENABLE_CACHE !== 'false';

const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  db: parseInt(process.env.REDIS_DB || '0'),
  password: process.env.REDIS_PASSWORD || undefined,
  retryStrategy: (times) => {
    if (times > 3) {
      logger.error('Redis connection failed after 3 retries');
      return null;
    }
    return Math.min(times * 200, 2000);
  },
});

redis.on('connect', () => {
  logger.info('Redis connection established');
});

redis.on('error', (err) => {
  logger.error('Redis error', err);
});

export class CacheService {
  private ttl: number;

  constructor(ttl: number = 5) {
    this.ttl = ttl;
  }

  async get<T>(key: string): Promise<T | null> {
    if (!ENABLE_CACHE) return null;
    
    try {
      const data = await redis.get(key);
      if (data) {
        return JSON.parse(data) as T;
      }
      return null;
    } catch (err) {
      logger.error(`Cache get error for key ${key}`, err);
      return null;
    }
  }

  async set(key: string, value: any, ttl?: number): Promise<void> {
    if (!ENABLE_CACHE) return;

    try {
      const expiry = ttl || this.ttl;
      await redis.setex(key, expiry, JSON.stringify(value));
    } catch (err) {
      logger.error(`Cache set error for key ${key}`, err);
    }
  }

  async del(key: string): Promise<void> {
    if (!ENABLE_CACHE) return;

    try {
      await redis.del(key);
    } catch (err) {
      logger.error(`Cache delete error for key ${key}`, err);
    }
  }

  /**
   * 直接獲取 Redis 中的原始字串（用於讀取 data-collector 寫入的 JSON）
   */
  async getRaw(key: string): Promise<string | null> {
    try {
      return await redis.get(key);
    } catch (err) {
      logger.error(`Redis getRaw error for key ${key}`, err);
      return null;
    }
  }

  /**
   * 獲取 Hash 中的欄位
   */
  async hget(key: string, field: string): Promise<string | null> {
    try {
      return await redis.hget(key, field);
    } catch (err) {
      logger.error(`Redis hget error for key ${key} field ${field}`, err);
      return null;
    }
  }

  makeKey(...parts: (string | number)[]): string {
    return RedisKeys.getCacheKey(parts.join(':'));
  }

  getRedisKeys() {
    return RedisKeys;
  }
}

export default redis;
