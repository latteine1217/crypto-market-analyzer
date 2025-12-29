/**
 * Bybit WebSocket 客戶端
 * 連接 Bybit WebSocket Stream 並處理實時數據
 */
import WebSocket from 'ws';
import { EventEmitter } from 'events';
import { log } from '../utils/logger';
import {
  ConnectionState,
  Trade,
  OrderBookUpdate,
  OrderBookSnapshot,
  MessageType,
  QueueMessage,
  WSConfig,
  Stats
} from '../types';

export class BybitWSClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private state: ConnectionState = ConnectionState.DISCONNECTED;
  private reconnectAttempts: number = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private stats: Stats;
  private startTime: number;
  private pingInterval: NodeJS.Timeout | null = null;

  constructor(private config: WSConfig) {
    super();
    this.startTime = Date.now();
    this.stats = {
      totalMessages: 0,
      messagesByType: new Map(),
      lastMessageTime: 0,
      reconnectCount: 0,
      errorCount: 0,
      uptimeMs: 0
    };

    log.info('BybitWSClient initialized', {
      symbols: config.symbols,
      streams: config.streams
    });
  }

  /**
   * 連接到 Bybit WebSocket
   */
  public connect(): void {
    if (this.state === ConnectionState.CONNECTED ||
        this.state === ConnectionState.CONNECTING) {
      log.warn('Already connected or connecting');
      return;
    }

    this.state = ConnectionState.CONNECTING;
    const url = this.buildWebSocketURL();

    log.info('Connecting to Bybit WebSocket', { url });

    try {
      this.ws = new WebSocket(url, {
        handshakeTimeout: 10000,
        perMessageDeflate: false
      });

      this.ws.on('open', () => this.handleOpen());
      this.ws.on('message', (data) => this.handleMessage(data));
      this.ws.on('error', (error) => this.handleError(error));
      this.ws.on('close', (code, reason) => this.handleClose(code, reason.toString()));

    } catch (error) {
      log.error('Failed to create WebSocket connection', error);
      this.scheduleReconnect();
    }
  }

  /**
   * 斷開連接
   */
  public disconnect(): void {
    log.info('Disconnecting from Bybit WebSocket');

    this.clearTimers();

    if (this.ws) {
      this.ws.removeAllListeners();
      this.ws.close();
      this.ws = null;
    }

    this.state = ConnectionState.DISCONNECTED;
    this.emit('disconnected');
  }

  /**
   * 獲取連接狀態
   */
  public getState(): ConnectionState {
    return this.state;
  }

  /**
   * 獲取統計資訊
   */
  public getStats(): Stats {
    return {
      ...this.stats,
      uptimeMs: Date.now() - this.startTime
    };
  }

  /**
   * 建立 WebSocket URL
   */
  private buildWebSocketURL(): string {
    // Bybit V5 公開 WebSocket 端點
    return 'wss://stream.bybit.com/v5/public/spot';
  }

  /**
   * 處理連接開啟
   */
  private handleOpen(): void {
    this.state = ConnectionState.CONNECTED;
    this.reconnectAttempts = 0;

    log.info('✅ Connected to Bybit WebSocket');

    // 訂閱交易流和訂單簿
    this.subscribe();

    // 啟動 ping 定時器（Bybit 需要定期 ping）
    this.startPingInterval();

    this.emit('connected');
  }

  /**
   * 訂閱交易流和訂單簿
   */
  private subscribe(): void {
    if (!this.ws || this.state !== ConnectionState.CONNECTED) {
      return;
    }

    const args: string[] = [];

    this.config.symbols.forEach(symbol => {
      // 訂閱交易流
      if (this.config.streams.includes('trade')) {
        args.push(`publicTrade.${symbol}`);
      }

      // 訂閱訂單簿（50 檔）
      if (this.config.streams.includes('depth')) {
        args.push(`orderbook.50.${symbol}`);
      }
    });

    const subscribeMessage = {
      op: 'subscribe',
      args: args
    };

    log.info('Subscribing to Bybit streams', { args });
    this.ws.send(JSON.stringify(subscribeMessage));
  }

  /**
   * 啟動 ping 定時器
   */
  private startPingInterval(): void {
    // Bybit 需要每 20 秒發送 ping
    this.pingInterval = setInterval(() => {
      if (this.ws && this.state === ConnectionState.CONNECTED) {
        this.ws.send(JSON.stringify({ op: 'ping' }));
      }
    }, 20000);
  }

  /**
   * 處理訊息
   */
  private handleMessage(data: WebSocket.Data): void {
    try {
      const message = JSON.parse(data.toString());

      // 更新統計
      this.stats.totalMessages++;
      this.stats.lastMessageTime = Date.now();

      // 處理 pong 回應
      if (message.op === 'pong') {
        return;
      }

      // 處理訂閱確認
      if (message.op === 'subscribe') {
        log.info('✅ Subscription confirmed', { success: message.success });
        return;
      }

      // 處理數據訊息
      if (message.topic) {
        this.handleDataMessage(message);
      }

    } catch (error) {
      log.error('Failed to parse message', error);
      this.stats.errorCount++;
    }
  }

  /**
   * 處理數據訊息
   */
  private handleDataMessage(message: any): void {
    const topic = message.topic;
    const data = message.data;

    // 處理交易數據
    if (topic.startsWith('publicTrade.')) {
      this.handleTrade(data, topic);
    }
    // 處理訂單簿數據
    else if (topic.startsWith('orderbook.')) {
      this.handleOrderBook(data, topic, message.type);
    }
  }

  /**
   * 處理交易數據
   */
  private handleTrade(trades: any[], topic: string): void {
    const symbol = topic.split('.')[1];

    trades.forEach(trade => {
      const tradeData: Trade = {
        symbol: symbol,
        price: parseFloat(trade.p),
        quantity: parseFloat(trade.v),
        timestamp: trade.T,
        isBuyerMaker: trade.S === 'Sell', // Bybit: Sell = 賣單（主動賣出）
        tradeId: trade.i
      };

      const queueMessage: QueueMessage = {
        type: MessageType.TRADE,
        exchange: 'bybit',
        data: tradeData,
        receivedAt: Date.now()
      };

      this.emit('message', queueMessage);

      // 更新統計
      const count = this.stats.messagesByType.get(MessageType.TRADE) || 0;
      this.stats.messagesByType.set(MessageType.TRADE, count + 1);
    });
  }

  /**
   * 處理訂單簿數據
   */
  private handleOrderBook(data: any, topic: string, type: string): void {
    const symbol = topic.split('.')[2];

    if (type === 'snapshot') {
      // 訂單簿快照
      const snapshot: OrderBookSnapshot = {
        symbol: symbol,
        bids: data.b.map((b: string[]) => ({ price: parseFloat(b[0]), quantity: parseFloat(b[1]) })),
        asks: data.a.map((a: string[]) => ({ price: parseFloat(a[0]), quantity: parseFloat(a[1]) })),
        lastUpdateId: data.u,
        timestamp: data.ts
      };

      const queueMessage: QueueMessage = {
        type: MessageType.ORDERBOOK_SNAPSHOT,
        exchange: 'bybit',
        data: snapshot,
        receivedAt: Date.now()
      };

      this.emit('message', queueMessage);

    } else if (type === 'delta') {
      // 訂單簿更新
      const update: OrderBookUpdate = {
        symbol: symbol,
        bids: data.b.map((b: string[]) => ({ price: parseFloat(b[0]), quantity: parseFloat(b[1]) })),
        asks: data.a.map((a: string[]) => ({ price: parseFloat(a[0]), quantity: parseFloat(a[1]) })),
        firstUpdateId: data.u,
        lastUpdateId: data.u,
        timestamp: data.ts
      };

      const queueMessage: QueueMessage = {
        type: MessageType.ORDERBOOK_UPDATE,
        exchange: 'bybit',
        data: update,
        receivedAt: Date.now()
      };

      this.emit('message', queueMessage);

      // 更新統計
      const count = this.stats.messagesByType.get(MessageType.ORDERBOOK_UPDATE) || 0;
      this.stats.messagesByType.set(MessageType.ORDERBOOK_UPDATE, count + 1);
    }
  }

  /**
   * 處理錯誤
   */
  private handleError(error: Error): void {
    log.error('❌ WebSocket error', { error: error.message });
    this.stats.errorCount++;
    this.emit('error', error);
  }

  /**
   * 處理連接關閉
   */
  private handleClose(code: number, reason: string): void {
    log.warn('⚠️  WebSocket disconnected', { code, reason });

    this.clearTimers();
    this.state = ConnectionState.DISCONNECTED;
    this.emit('disconnected');

    // 自動重連
    this.scheduleReconnect();
  }

  /**
   * 排程重連
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return;
    }

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;
    this.stats.reconnectCount++;

    log.info(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  /**
   * 清除定時器
   */
  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}
