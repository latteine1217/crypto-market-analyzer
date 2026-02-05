import Redis from 'ioredis';
import { SocketService } from './socketService';
import { logger } from '../utils/logger';
import { config } from '../shared/config';

/**
 * RealtimeService
 * 訂閱 Redis Pub/Sub 並將訊息透過 Socket.IO 轉發給前端
 */
export class RealtimeService {
  private static instance: RealtimeService;
  private subClient: Redis;
  private isRunning: boolean = false;

  private constructor() {
    this.subClient = new Redis({
      host: config.redis.host,
      port: config.redis.port,
      password: config.redis.password,
      db: config.redis.db,
    });

    this.subClient.on('error', (err) => {
      logger.error('Redis Subscription Client Error', err);
    });
  }

  public static getInstance(): RealtimeService {
    if (!RealtimeService.instance) {
      RealtimeService.instance = new RealtimeService();
    }
    return RealtimeService.instance;
  }

  /**
   * 啟動訂閱服務
   */
  public async start() {
    if (this.isRunning) return;

    try {
      // 訂閱所有市場更新頻道
      await this.subClient.psubscribe('market_updates:*');
      this.isRunning = true;
      logger.info('RealtimeService: Subscribed to Redis market_updates:*');

      this.subClient.on('pmessage', (pattern, channel, message) => {
        this.handleMessage(channel, message);
      });
    } catch (err) {
      logger.error('Failed to start RealtimeService', err);
    }
  }

  /**
   * 處理接收到的訊息
   */
  private handleMessage(channel: string, message: string) {
    try {
      const data = JSON.parse(message);
      const socketService = SocketService.getInstance();

      // 根據訊息類型決定轉發的事件名稱
      // 例如：market_updates:liquidation:bybit
      const parts = channel.split(':');
      const type = parts[1]; // liquidation, trade, kline, etc.
      
      // 廣播給所有連線的客戶端
      // 前端可以監聽 'liquidation', 'trade' 等事件
      socketService.emit(type, data);

      // 如果是特定交易對的訊息，也可以發送特定事件
      if (data.data && data.data.symbol) {
        socketService.emit(`${type}:${data.data.symbol}`, data.data);
      }
    } catch (err) {
      logger.error('Error handling realtime message', err);
    }
  }
}

/**
 * 啟動實時數據轉發服務
 */
export const startRealtimeService = () => {
  RealtimeService.getInstance().start();
};
