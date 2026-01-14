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
  Kline,
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

      // 訂閱 K線（1分鐘）
      if (this.config.streams.includes('kline_1m') || this.config.streams.includes('kline')) {
        args.push(`kline.1.${symbol}`);
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
    // 處理 K線數據
    else if (topic.startsWith('kline.')) {
      this.handleKline(data, topic);
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
   * 處理 K線數據
   * Bybit K線格式: topic = "kline.{interval}.{symbol}"
   * interval: 1 = 1分鐘, 3 = 3分鐘, 5 = 5分鐘, 15 = 15分鐘, 30 = 30分鐘, 
   *           60 = 1小時, 120 = 2小時, 240 = 4小時, 360 = 6小時, 720 = 12小時, D = 日, W = 週, M = 月
   */
  private handleKline(klines: any[], topic: string): void {
    const parts = topic.split('.');
    const intervalCode = parts[1]; // "1", "5", "60", "D", etc.
    const symbol = parts[2];

    // 將 Bybit interval code 轉換為標準格式
    const intervalMap: { [key: string]: string } = {
      '1': '1m',
      '3': '3m',
      '5': '5m',
      '15': '15m',
      '30': '30m',
      '60': '1h',
      '120': '2h',
      '240': '4h',
      '360': '6h',
      '720': '12h',
      'D': '1d',
      'W': '1w',
      'M': '1M'
    };

    const interval = intervalMap[intervalCode] || `${intervalCode}m`;

    klines.forEach(kline => {
      const klineData: Kline = {
        symbol: symbol,
        interval: interval,
        openTime: kline.start,
        closeTime: kline.end,
        open: parseFloat(kline.open),
        high: parseFloat(kline.high),
        low: parseFloat(kline.low),
        close: parseFloat(kline.close),
        volume: parseFloat(kline.volume),
        quoteVolume: parseFloat(kline.turnover), // Bybit 使用 turnover 表示成交額
        trades: 0, // Bybit K線不提供交易筆數
        isClosed: kline.confirm // Bybit: confirm = true 表示 K線已完結
      };

      const queueMessage: QueueMessage = {
        type: MessageType.KLINE,
        exchange: 'bybit',
        data: klineData,
        receivedAt: Date.now()
      };

      this.emit('message', queueMessage);

      // 更新統計
      const count = this.stats.messagesByType.get(MessageType.KLINE) || 0;
      this.stats.messagesByType.set(MessageType.KLINE, count + 1);
    });
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
