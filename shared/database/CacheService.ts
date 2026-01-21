import Redis from 'ioredis';
import { RedisKeys } from '../utils/RedisKeys';
import { config } from '../config';

export class CacheService {
  private client: Redis;
  private ttl: number;
  private enabled: boolean;

  constructor(client: Redis, ttl: number = config.server.cacheTtl) {
    this.client = client;
    this.ttl = ttl;
    this.enabled = config.server.enableCache;
  }

  async get<T>(key: string): Promise<T | null> {
    if (!this.enabled) return null;
    
    try {
      const data = await this.client.get(key);
      if (data) {
        return JSON.parse(data) as T;
      }
      return null;
    } catch (err) {
      return null;
    }
  }

  async set(key: string, value: any, ttl?: number): Promise<void> {
    if (!this.enabled) return;

    try {
      const expiry = ttl || this.ttl;
      await this.client.setex(key, expiry, JSON.stringify(value));
    } catch (err) {
      // Ignore cache set errors
    }
  }

  async del(key: string): Promise<void> {
    try {
      await this.client.del(key);
    } catch (err) {
      // Ignore
    }
  }

  async hget(key: string, field: string): Promise<string | null> {
    try {
      return await this.client.hget(key, field);
    } catch (err) {
      return null;
    }
  }

  makeKey(...parts: (string | number)[]): string {
    return RedisKeys.getCacheKey(parts.join(':'));
  }
}
