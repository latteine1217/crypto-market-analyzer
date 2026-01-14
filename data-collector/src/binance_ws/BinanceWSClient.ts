/**
 * Binance WebSocket 客戶端
 * 連接 Binance WebSocket Stream 並處理實時數據
 */
import WebSocket from 'ws';
import { EventEmitter } from 'events';
import { log } from '../utils/logger';
import {
  ConnectionState,
  Trade,
  OrderBookUpdate,
  Kline,
  MessageType,
  QueueMessage,
  WSConfig,
  Stats
} from '../types';

export class BinanceWSClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private state: ConnectionState = ConnectionState.DISCONNECTED;
  private reconnectAttempts: number = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private stats: Stats;
  private startTime: number;

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

    log.info('BinanceWSClient initialized', {
      symbols: config.symbols,
      streams: config.streams
    });
  }

  /**
   * 連接到 Binance WebSocket
   */
  public connect(): void {
    if (this.state === ConnectionState.CONNECTED ||
        this.state === ConnectionState.CONNECTING) {
      log.warn('Already connected or connecting');
      return;
    }

    this.state = ConnectionState.CONNECTING;
    const url = this.buildWebSocketURL();

    log.info('Connecting to Binance WebSocket', { url });

    try {
      this.ws = new WebSocket(url);

      this.ws.on('open', () => this.handleOpen());
      this.ws.on('message', (data) => this.handleMessage(data));
      this.ws.on('error', (error) => this.handleError(error));
      this.ws.on('close', (code, reason) => this.handleClose(code, reason.toString()));
      this.ws.on('ping', () => this.handlePing());

    } catch (error) {
      log.error('Failed to create WebSocket connection', error);
      this.scheduleReconnect();
    }
  }

  /**
   * 斷開連接
   */
  public disconnect(): void {
    log.info('Disconnecting from Binance WebSocket');

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
    const baseURL = 'wss://stream.binance.com:9443';

    // 建立 stream 陣列
    const streams: string[] = [];

    for (const symbol of this.config.symbols) {
      const lowerSymbol = symbol.toLowerCase();

      if (this.config.streams.includes('trade')) {
        streams.push(`${lowerSymbol}@trade`);
      }

      if (this.config.streams.includes('depth')) {
        streams.push(`${lowerSymbol}@depth@100ms`);
      }

      if (this.config.streams.includes('kline_1m')) {
        streams.push(`${lowerSymbol}@kline_1m`);
      }
    }

    // 使用 combined stream
    return `${baseURL}/stream?streams=${streams.join('/')}`;
  }

  /**
   * 處理連接開啟
   */
  private handleOpen(): void {
    log.info('WebSocket connected');

    this.state = ConnectionState.CONNECTED;
    this.reconnectAttempts = 0;

    this.startHeartbeat();
    this.emit('connected');
  }

  /**
   * 處理訊息
   */
  private handleMessage(data: WebSocket.Data): void {
    try {
      const raw = JSON.parse(data.toString());

      // Binance combined stream 格式: { stream: "...", data: {...} }
      if (!raw.stream || !raw.data) {
        log.warn('Invalid message format', { raw });
        return;
      }

      const streamName = raw.stream;
      const streamData = raw.data;

      // 更新統計
      this.stats.totalMessages++;
      this.stats.lastMessageTime = Date.now();

      // 解析不同類型的訊息
      if (streamName.includes('@trade')) {
        this.handleTradeMessage(streamData);
      } else if (streamName.includes('@depth')) {
        this.handleDepthMessage(streamData);
      } else if (streamName.includes('@kline')) {
        this.handleKlineMessage(streamData);
      }

    } catch (error) {
      log.error('Failed to parse message', error);
      this.stats.errorCount++;
    }
  }

  /**
   * 處理交易訊息
   */
  private handleTradeMessage(data: any): void {
    const trade: Trade = {
      symbol: data.s,
      tradeId: data.t,
      price: parseFloat(data.p),
      quantity: parseFloat(data.q),
      quoteQuantity: parseFloat(data.q) * parseFloat(data.p),
      timestamp: data.T,
      isBuyerMaker: data.m,
      side: data.m ? 'sell' : 'buy'
    };

    const message: QueueMessage = {
      type: MessageType.TRADE,
      exchange: 'binance',
      data: trade,
      receivedAt: Date.now()
    };

    this.updateStats(MessageType.TRADE);
    this.emit('message', message);
  }

  /**
   * 處理訂單簿深度訊息
   */
  private handleDepthMessage(data: any): void {
    const update: OrderBookUpdate = {
      symbol: data.s,
      timestamp: Date.now(),
      firstUpdateId: data.U,
      lastUpdateId: data.u,
      bids: data.b.map((b: string[]) => ({
        price: parseFloat(b[0]),
        quantity: parseFloat(b[1])
      })),
      asks: data.a.map((a: string[]) => ({
        price: parseFloat(a[0]),
        quantity: parseFloat(a[1])
      }))
    };

    const message: QueueMessage = {
      type: MessageType.ORDERBOOK_UPDATE,
      exchange: 'binance',
      data: update,
      receivedAt: Date.now()
    };

    this.updateStats(MessageType.ORDERBOOK_UPDATE);
    this.emit('message', message);
  }

  /**
   * 處理 K線訊息
   */
  private handleKlineMessage(data: any): void {
    // Binance K線數據格式: data.k 包含 K線資訊
    const k = data.k;
    
    const kline: Kline = {
      symbol: data.s,
      interval: k.i,          // K線週期 (1m, 5m, 1h, etc.)
      openTime: k.t,          // K線開始時間
      closeTime: k.T,         // K線結束時間
      open: parseFloat(k.o),
      high: parseFloat(k.h),
      low: parseFloat(k.l),
      close: parseFloat(k.c),
      volume: parseFloat(k.v),        // 成交量
      quoteVolume: parseFloat(k.q),   // 成交額
      trades: k.n,                     // 成交筆數
      isClosed: k.x                    // K線是否完結
    };

    const message: QueueMessage = {
      type: MessageType.KLINE,
      exchange: 'binance',
      data: kline,
      receivedAt: Date.now()
    };

    this.updateStats(MessageType.KLINE);
    this.emit('message', message);
  }

  /**
   * 處理錯誤
   */
  private handleError(error: Error): void {
    log.error('WebSocket error', error);
    this.stats.errorCount++;
    this.emit('error', error);
  }

  /**
   * 處理連接關閉
   */
  private handleClose(code: number, reason: string): void {
    log.warn('WebSocket closed', { code, reason });

    this.clearTimers();
    this.state = ConnectionState.DISCONNECTED;
    this.emit('disconnected', code, reason);

    // 如果啟用自動重連
    if (this.config.reconnect) {
      this.scheduleReconnect();
    }
  }

  /**
   * 處理 ping
   */
  private handlePing(): void {
    if (this.ws) {
      this.ws.pong();
    }
  }

  /**
   * 排程重連
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      log.error('Max reconnect attempts reached', {
        attempts: this.reconnectAttempts
      });
      this.state = ConnectionState.FAILED;
      this.emit('failed');
      return;
    }

    this.reconnectAttempts++;
    this.stats.reconnectCount++;
    this.state = ConnectionState.RECONNECTING;

    log.info('Scheduling reconnect', {
      attempt: this.reconnectAttempts,
      delayMs: this.config.reconnectDelay
    });

    this.emit('reconnecting', this.reconnectAttempts);

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, this.config.reconnectDelay);
  }

  /**
   * 啟動心跳檢查
   */
  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      const now = Date.now();
      const timeSinceLastMessage = now - this.stats.lastMessageTime;

      // 如果超過 2 倍心跳間隔沒收到訊息，認為連接異常
      if (timeSinceLastMessage > this.config.heartbeatInterval * 2) {
        log.warn('Heartbeat timeout, reconnecting', {
          timeSinceLastMessage
        });
        this.disconnect();
        this.connect();
      }
    }, this.config.heartbeatInterval);
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
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * 更新統計
   */
  private updateStats(type: MessageType): void {
    const count = this.stats.messagesByType.get(type) || 0;
    this.stats.messagesByType.set(type, count + 1);
  }
}
