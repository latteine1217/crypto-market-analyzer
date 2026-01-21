import Redis from 'ioredis';
import { logger } from '../utils/logger';
import { config } from '../shared/config';
import { CacheService as SharedCacheService } from '../shared/database/CacheService';

const redis = new Redis({
  ...config.redis,
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

export class CacheService extends SharedCacheService {
  constructor(ttl: number = config.server.cacheTtl) {
    super(redis, ttl);
  }
}

export default redis;