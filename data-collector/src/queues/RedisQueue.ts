/**
 * Redis 佇列管理
 * 使用 Redis List 作為訊息佇列
 */
import Redis from 'ioredis';
import { log } from '../utils/logger';
import { config } from '../config';
import { QueueMessage, MessageType } from '../types';

export class RedisQueue {
  private client: Redis;
  private readonly QUEUE_PREFIX = 'crypto:queue:';
  private readonly MAX_QUEUE_SIZE = 10000;

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
    const queueKey = this.getQueueKey(message.type);

    try {
      // 檢查佇列大小
      const queueSize = await this.client.llen(queueKey);

      if (queueSize >= this.MAX_QUEUE_SIZE) {
        log.warn('Queue size limit reached', {
          queue: queueKey,
          size: queueSize
        });
        // 移除最舊的訊息
        await this.client.lpop(queueKey);
      }

      // 推送到佇列尾端
      await this.client.rpush(queueKey, JSON.stringify(message));

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
      const queueKey = this.getQueueKey(message.type);
      pipeline.rpush(queueKey, JSON.stringify(message));
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
    const queueKey = this.getQueueKey(type);
    const messages: QueueMessage[] = [];

    try {
      const pipeline = this.client.pipeline();

      // 使用 LPOP 取出多個訊息
      for (let i = 0; i < count; i++) {
        pipeline.lpop(queueKey);
      }

      const results = await pipeline.exec();

      if (results) {
        for (const [error, result] of results) {
          if (!error && result) {
            try {
              messages.push(JSON.parse(result as string));
            } catch (parseError) {
              log.error('Failed to parse queue message', parseError);
            }
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
    const queueKey = this.getQueueKey(type);
    return await this.client.llen(queueKey);
  }

  /**
   * 獲取所有佇列的大小
   */
  public async getAllQueueSizes(): Promise<Map<MessageType, number>> {
    const sizes = new Map<MessageType, number>();
    const types = [
      MessageType.TRADE,
      MessageType.ORDERBOOK_SNAPSHOT,
      MessageType.ORDERBOOK_UPDATE
    ];

    for (const type of types) {
      const size = await this.getQueueSize(type);
      sizes.set(type, size);
    }

    return sizes;
  }

  /**
   * 清空佇列
   */
  public async clearQueue(type: MessageType): Promise<void> {
    const queueKey = this.getQueueKey(type);
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
    const key = `crypto:orderbook:${symbol}`;

    try {
      await this.client.hset(
        key,
        'data', JSON.stringify(snapshot),
        'timestamp', Date.now().toString()
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
  public async getOrderBookSnapshot(symbol: string): Promise<any | null> {
    const key = `crypto:orderbook:${symbol}`;

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
   * 取得佇列鍵名
   */
  private getQueueKey(type: MessageType): string {
    return `${this.QUEUE_PREFIX}${type}`;
  }

  /**
   * 關閉連接
   */
  public async disconnect(): Promise<void> {
    await this.client.quit();
    log.info('Redis disconnected');
  }
}
