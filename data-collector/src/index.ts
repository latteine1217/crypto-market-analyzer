/**
 * WebSocket 實時數據收集器主程式
 * 整合所有組件
 */
import { log } from './utils/logger';
import { config, validateConfig, displayConfig } from './config';
import { BinanceWSClient } from './binance_ws/BinanceWSClient';
import { OrderBookManager } from './orderbook_handlers/OrderBookManager';
import { RedisQueue } from './queues/RedisQueue';
import { DBFlusher } from './database/DBFlusher';
import {
  WSConfig,
  QueueMessage,
  MessageType,
  OrderBookUpdate,
  OrderBookSnapshot
} from './types';

class WebSocketCollector {
  private wsClient: BinanceWSClient | null = null;
  private orderBookManager: OrderBookManager;
  private redisQueue: RedisQueue;
  private dbFlusher: DBFlusher;
  private snapshotTimer: NodeJS.Timeout | null = null;
  private statsTimer: NodeJS.Timeout | null = null;

  constructor() {
    this.orderBookManager = new OrderBookManager();
    this.redisQueue = new RedisQueue();
    this.dbFlusher = new DBFlusher(config.flush);

    log.info('WebSocketCollector initialized');
  }

  /**
   * 啟動收集器
   */
  public async start(): Promise<void> {
    try {
      log.info('================================');
      log.info('WebSocket Data Collector');
      log.info('================================\n');

      // 驗證配置
      validateConfig();
      displayConfig();

      // 測試資料庫連接
      log.info('\nTesting database connection...');
      const dbOk = await this.dbFlusher.testConnection();
      if (!dbOk) {
        throw new Error('Database connection failed');
      }

      // 初始化訂單簿
      log.info('\nInitializing order books...');
      for (const symbol of config.subscriptions.symbols) {
        await this.orderBookManager.initializeOrderBook(symbol);
      }

      // 建立 WebSocket 配置
      const wsConfig: WSConfig = {
        exchange: 'binance',
        symbols: config.subscriptions.symbols,
        streams: config.subscriptions.streams,
        ...config.websocket
      };

      // 建立 WebSocket 客戶端
      this.wsClient = new BinanceWSClient(wsConfig);

      // 設置事件處理
      this.setupEventHandlers();

      // 連接 WebSocket
      log.info('\nConnecting to WebSocket...');
      this.wsClient.connect();

      // 啟動定期快照
      this.startPeriodicSnapshots();

      // 啟動資料庫 flush
      log.info('Starting database flusher...');
      this.dbFlusher.start();

      // 啟動統計輸出
      this.startStatsDisplay();

      log.info('\n✅ WebSocket Collector started successfully!\n');

    } catch (error) {
      log.error('Failed to start collector', error);
      throw error;
    }
  }

  /**
   * 設置事件處理器
   */
  private setupEventHandlers(): void {
    if (!this.wsClient) {
      return;
    }

    // 連接成功
    this.wsClient.on('connected', () => {
      log.info('✅ WebSocket connected');
    });

    // 連接斷開
    this.wsClient.on('disconnected', (code, reason) => {
      log.warn('⚠️ WebSocket disconnected', { code, reason });
    });

    // 重連中
    this.wsClient.on('reconnecting', (attempt) => {
      log.info(`🔄 Reconnecting... (attempt ${attempt})`);
    });

    // 錯誤
    this.wsClient.on('error', (error) => {
      log.error('❌ WebSocket error', error);
    });

    // 收到訊息
    this.wsClient.on('message', (message: QueueMessage) => {
      this.handleMessage(message);
    });
  }

  /**
   * 處理訊息
   */
  private async handleMessage(message: QueueMessage): Promise<void> {
    try {
      if (message.type === MessageType.TRADE) {
        // 直接推送到 Redis
        await this.redisQueue.push(message);

      } else if (message.type === MessageType.ORDERBOOK_UPDATE) {
        // 更新本地訂單簿
        const update = message.data as OrderBookUpdate;
        const updated = this.orderBookManager.processUpdate(update);

        if (!updated) {
          log.debug(`Order book update skipped for ${update.symbol}`);
        }
      }

    } catch (error) {
      log.error('Failed to handle message', error);
    }
  }

  /**
   * 啟動定期快照
   */
  private startPeriodicSnapshots(): void {
    log.info('Starting periodic snapshots...');

    this.snapshotTimer = this.orderBookManager.startPeriodicSnapshots(
      async (snapshot: OrderBookSnapshot) => {
        // 推送到 Redis 佇列
        const message: QueueMessage = {
          type: MessageType.ORDERBOOK_SNAPSHOT,
          exchange: 'binance',
          data: snapshot,
          receivedAt: Date.now()
        };

        await this.redisQueue.push(message);

        // 同時儲存到 Redis Hash（供即時查詢）
        await this.redisQueue.saveOrderBookSnapshot(
          snapshot.symbol,
          snapshot
        );
      }
    );
  }

  /**
   * 啟動統計顯示
   */
  private startStatsDisplay(): void {
    this.statsTimer = setInterval(async () => {
      if (!this.wsClient) {
        return;
      }

      // WebSocket 統計
      const wsStats = this.wsClient.getStats();

      // Redis 佇列統計
      const queueSizes = await this.redisQueue.getAllQueueSizes();

      // DB Flusher 統計
      const dbStats = this.dbFlusher.getStats();

      // 訂單簿統計
      const obStats: any[] = [];
      for (const symbol of config.subscriptions.symbols) {
        const stats = this.orderBookManager.getStats(symbol);
        if (stats) {
          obStats.push(stats);
        }
      }

      // 輸出統計
      console.log('\n' + '='.repeat(80));
      console.log('📊 Statistics');
      console.log('='.repeat(80));

      console.log('\n🌐 WebSocket:');
      console.log(`  Total messages: ${wsStats.totalMessages}`);
      console.log(`  Reconnects: ${wsStats.reconnectCount}`);
      console.log(`  Errors: ${wsStats.errorCount}`);
      console.log(`  Uptime: ${Math.floor(wsStats.uptimeMs / 1000)}s`);

      console.log('\n📦 Redis Queues:');
      for (const [type, size] of queueSizes.entries()) {
        console.log(`  ${type}: ${size} messages`);
      }

      console.log('\n💾 Database:');
      console.log(`  Total flushed: ${dbStats.totalFlushed}`);
      console.log(`  Errors: ${dbStats.errorCount}`);
      console.log(`  Is flushing: ${dbStats.isFlushing}`);

      console.log('\n📈 Order Books:');
      for (const stats of obStats) {
        console.log(`  ${stats.symbol}:`);
        console.log(`    Best bid: ${stats.bestBid?.toFixed(2)}`);
        console.log(`    Best ask: ${stats.bestAsk?.toFixed(2)}`);
        console.log(`    Spread: ${stats.spread?.toFixed(2)} (${stats.spreadBps?.toFixed(2)} bps)`);
        console.log(`    Updates: ${stats.updateCount}`);
      }

      console.log('\n' + '='.repeat(80) + '\n');

    }, 30000); // 每 30 秒
  }

  /**
   * 停止收集器
   */
  public async stop(): Promise<void> {
    log.info('Stopping WebSocket Collector...');

    // 停止統計顯示
    if (this.statsTimer) {
      clearInterval(this.statsTimer);
    }

    // 停止快照
    if (this.snapshotTimer) {
      clearInterval(this.snapshotTimer);
    }

    // 斷開 WebSocket
    if (this.wsClient) {
      this.wsClient.disconnect();
    }

    // 停止資料庫 flusher
    this.dbFlusher.stop();

    // 最後一次 flush
    log.info('Flushing remaining data...');
    await this.dbFlusher.flushAll();

    // 關閉資源
    await this.dbFlusher.shutdown();
    this.orderBookManager.cleanup();

    log.info('✅ WebSocket Collector stopped');
  }
}

// 主函數
async function main() {
  const collector = new WebSocketCollector();

  // 處理程序終止信號
  process.on('SIGINT', async () => {
    log.info('\nReceived SIGINT, shutting down gracefully...');
    await collector.stop();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    log.info('\nReceived SIGTERM, shutting down gracefully...');
    await collector.stop();
    process.exit(0);
  });

  // 啟動收集器
  try {
    await collector.start();
  } catch (error) {
    log.error('Failed to start collector', error);
    process.exit(1);
  }
}

// 執行
if (require.main === module) {
  main().catch((error) => {
    log.error('Fatal error', error);
    process.exit(1);
  });
}

export { WebSocketCollector };
