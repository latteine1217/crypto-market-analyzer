/**
 * Redis 佇列管理
 * 使用 Redis List 作為訊息佇列
 */
import Redis from 'ioredis';
import { log } from '../utils/logger';
import { config } from '../config';
import { QueueMessage, MessageType } from '../types';
import { RedisKeys } from '../../../shared/utils/RedisKeys';

export class RedisQueue {
  private client: Redis;
  private readonly MAX_QUEUE_SIZE = 10000;
  private readonly QUEUE_TTL = 3600; // 1 小時

  constructor() {
    this.client = new Redis({
      host: config.redis.host,
      port: config.redis.port,
      password: config.redis.password,
      db: config.redis.db,
      retryStrategy: (times) => {
        const delay = Math.min(times * 50, 2000);
        return delay;
      }
    });

    this.client.on('connect', () => {
      log.info('Redis connected', {
        host: config.redis.host,
        port: config.redis.port
      });
    });

    this.client.on('error', (error) => {
      log.error('Redis error', error);
    });

    this.client.on('reconnecting', () => {
      log.warn('Redis reconnecting...');
    });
  }

  /**
   * 推送訊息到佇列
   */
  public async push(message: QueueMessage): Promise<void> {
    const queueKey = RedisKeys.getQueueKey(message.type);

    try {
      const pipeline = this.client.pipeline();
      
      // 推送到佇列尾端
      pipeline.rpush(queueKey, JSON.stringify(message));
      
      // 設置 TTL
      pipeline.expire(queueKey, this.QUEUE_TTL);
      
      // 限制長度
      pipeline.ltrim(queueKey, -this.MAX_QUEUE_SIZE, -1);

      await pipeline.exec();

    } catch (error) {
      log.error('Failed to push message to queue', error);
      throw error;
    }
  }

  /**
   * 批次推送訊息
   */
  public async pushBatch(messages: QueueMessage[]): Promise<void> {
    if (messages.length === 0) {
      return;
    }

    const pipeline = this.client.pipeline();

    for (const message of messages) {
      const queueKey = RedisKeys.getQueueKey(message.type);
      pipeline.rpush(queueKey, JSON.stringify(message));
      pipeline.expire(queueKey, this.QUEUE_TTL);
      pipeline.ltrim(queueKey, -this.MAX_QUEUE_SIZE, -1);
    }

    try {
      await pipeline.exec();
    } catch (error) {
      log.error('Failed to push batch messages', error);
      throw error;
    }
  }

  /**
   * 從佇列取出訊息（批次）
   */
  public async pop(type: MessageType, count: number = 100): Promise<QueueMessage[]> {
    const queueKey = RedisKeys.getQueueKey(type);
    const messages: QueueMessage[] = [];

    try {
      const multi = this.client.multi();
      multi.lrange(queueKey, 0, count - 1);
      multi.ltrim(queueKey, count, -1);
      const results = await multi.exec();

      const rangeResult = results?.[0]?.[1] as string[] | null;
      if (rangeResult && rangeResult.length > 0) {
        for (const result of rangeResult) {
          try {
            messages.push(JSON.parse(result));
          } catch (parseError) {
            log.error('Failed to parse queue message', parseError);
          }
        }
      }

    } catch (error) {
      log.error('Failed to pop messages from queue', error);
      throw error;
    }

    return messages;
  }

  /**
   * 獲取佇列大小
   */
  public async getQueueSize(type: MessageType): Promise<number> {
    const queueKey = RedisKeys.getQueueKey(type);
    return await this.client.llen(queueKey);
  }

  /**
   * 獲取所有佇列的大小
   */
  public async getAllQueueSizes(): Promise<Map<MessageType, number>> {
    const types = [
      MessageType.TRADE,
      MessageType.ORDERBOOK_SNAPSHOT,
      MessageType.ORDERBOOK_UPDATE,
      MessageType.KLINE
    ];

    const pipeline = this.client.pipeline();
    types.forEach(type => {
      pipeline.llen(RedisKeys.getQueueKey(type));
    });

    const results = await pipeline.exec();
    const sizes = new Map<MessageType, number>();

    types.forEach((type, index) => {
      const size = (results?.[index]?.[1] as number) || 0;
      sizes.set(type, size);
    });

    return sizes;
  }

  /**
   * 清空佇列
   */
  public async clearQueue(type: MessageType): Promise<void> {
    const queueKey = RedisKeys.getQueueKey(type);
    await this.client.del(queueKey);
    log.info(`Queue cleared: ${queueKey}`);
  }

  /**
   * 儲存訂單簿快照（使用 Hash）
   */
  public async saveOrderBookSnapshot(
    symbol: string,
    snapshot: any
  ): Promise<void> {
    // 從快照中獲取 exchange，或者如果傳入參數沒有，就從 config 拿
    const exchange = snapshot.exchange || config.exchange || 'unknown';
    const key = RedisKeys.getOrderBookKey(exchange, symbol);

    try {
      await this.client.hset(
        key,
        'data', JSON.stringify(snapshot),
        'timestamp', Date.now().toString(),
        'exchange', exchange
      );

      // 設置過期時間（10 分鐘）
      await this.client.expire(key, 600);

    } catch (error) {
      log.error('Failed to save orderbook snapshot', error);
      throw error;
    }
  }

  /**
   * 獲取訂單簿快照
   */
  public async getOrderBookSnapshot(exchange: string, symbol: string): Promise<any | null> {
    const key = RedisKeys.getOrderBookKey(exchange, symbol);

    try {
      const data = await this.client.hget(key, 'data');
      return data ? JSON.parse(data) : null;
    } catch (error) {
      log.error('Failed to get orderbook snapshot', error);
      return null;
    }
  }

  /**
   * 獲取統計資訊
   */
  public async getStats(): Promise<any> {
    const queueSizes = await this.getAllQueueSizes();
    const info = await this.client.info('memory');

    return {
      queueSizes: Object.fromEntries(queueSizes),
      memory: this.parseRedisInfo(info)
    };
  }

  /**
   * 解析 Redis INFO 輸出
   */
  private parseRedisInfo(info: string): any {
    const lines = info.split('\r\n');
    const result: any = {};

    for (const line of lines) {
      if (line.includes(':')) {
        const [key, value] = line.split(':');
        result[key] = value;
      }
    }

    return result;
  }

  /**
   * 關閉連接
   */
  public async disconnect(): Promise<void> {
    await this.client.quit();
    log.info('Redis disconnected');
  }
}
