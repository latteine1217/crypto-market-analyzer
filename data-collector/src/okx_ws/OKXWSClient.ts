/**
 * OKX WebSocket 客戶端
 * 連接 OKX WebSocket V5 Stream 並處理實時數據
 */
import WebSocket from 'ws';
import { EventEmitter } from 'events';
import { log } from '../utils/logger';
import {
  ConnectionState,
  Trade,
  Kline,
  MessageType,
  WSConfig,
  Stats
} from '../types';

export class OKXWSClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private state: ConnectionState = ConnectionState.DISCONNECTED;
  private reconnectAttempts: number = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
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

    log.info('OKXWSClient initialized', {
      symbols: config.symbols,
      streams: config.streams
    });
  }

  /**
   * 連接到 OKX WebSocket
   */
  public connect(): void {
    if (this.state === ConnectionState.CONNECTED ||
        this.state === ConnectionState.CONNECTING) {
      log.warn('Already connected or connecting');
      return;
    }

    this.state = ConnectionState.CONNECTING;
    const url = 'wss://wsproduct.okx.com:8443/ws/v5/public';

    log.info('Connecting to OKX WebSocket', { url });

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
      log.error('Failed to create OKX WebSocket connection', error);
      this.scheduleReconnect();
    }
  }

  /**
   * 斷開連接
   */
  public disconnect(): void {
    log.info('Disconnecting from OKX WebSocket');
    this.clearTimers();
    if (this.ws) {
      this.ws.removeAllListeners();
      this.ws.close();
      this.ws = null;
    }
    this.state = ConnectionState.DISCONNECTED;
    this.emit('disconnected');
  }

  public getState(): ConnectionState {
    return this.state;
  }

  public getStats(): Stats {
    return {
      ...this.stats,
      uptimeMs: Date.now() - this.startTime
    };
  }

  private handleOpen(): void {
    this.state = ConnectionState.CONNECTED;
    this.reconnectAttempts = 0;
    log.info('✅ Connected to OKX WebSocket');
    this.subscribe();
    this.startPingInterval();
    this.emit('connected');
  }

  private subscribe(): void {
    if (!this.ws || this.state !== ConnectionState.CONNECTED) return;

    const args: any[] = [];
    this.config.symbols.forEach(symbol => {
      // OKX symbol format: BTC-USDT
      const okxSymbol = symbol.includes('-') ? symbol : symbol.replace(/([A-Z]+)(USDT|USDC|BTC|ETH)/, '$1-$2');
      
      if (this.config.streams.includes('trade')) {
        args.push({ channel: 'trades', instId: okxSymbol });
      }
      if (this.config.streams.includes('depth')) {
        args.push({ channel: 'books', instId: okxSymbol });
      }
      if (this.config.streams.includes('kline_1m') || this.config.streams.includes('kline')) {
        args.push({ channel: 'candle1m', instId: okxSymbol });
      }
    });

    if (args.length > 0) {
      const subscribeMessage = { op: 'subscribe', args };
      log.info('Subscribing to OKX streams', { args });
      this.ws.send(JSON.stringify(subscribeMessage));
    }
  }

  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      if (this.ws && this.state === ConnectionState.CONNECTED) {
        this.ws.send('ping');
      }
    }, 25000); // OKX recommends < 30s
  }

  private handleMessage(data: WebSocket.Data): void {
    const messageStr = data.toString();
    if (messageStr === 'pong') return;

    try {
      const message = JSON.parse(messageStr);
      this.stats.totalMessages++;
      this.stats.lastMessageTime = Date.now();

      if (message.event === 'subscribe') {
        log.info('✅ OKX Subscription confirmed', { arg: message.arg });
        return;
      }

      if (message.data && message.arg) {
        this.handleDataMessage(message);
      }
    } catch (error) {
      log.error('Failed to parse OKX message', { error, data: messageStr });
      this.stats.errorCount++;
    }
  }

  private handleDataMessage(message: any): void {
    const channel = message.arg.channel;
    const instId = message.arg.instId;
    const data = message.data;

    if (channel === 'trades') {
      this.handleTrade(data, instId);
    } else if (channel === 'books') {
      this.handleOrderBook(data, instId, message.action);
    } else if (channel === 'candle1m') {
      this.handleKline(data, instId);
    }
  }

  private handleTrade(trades: any[], instId: string): void {
    const symbol = instId.replace('-', '');
    trades.forEach(trade => {
      const tradeData: Trade = {
        symbol,
        price: parseFloat(trade.px),
        quantity: parseFloat(trade.sz),
        timestamp: parseInt(trade.ts),
        isBuyerMaker: trade.side === 'sell', // OKX: side = 'sell' means taker sold (maker was buyer)
        tradeId: trade.tradeId
      };

      this.emit('message', {
        type: MessageType.TRADE,
        exchange: 'okx',
        data: tradeData,
        receivedAt: Date.now()
      });

      const count = this.stats.messagesByType.get(MessageType.TRADE) || 0;
      this.stats.messagesByType.set(MessageType.TRADE, count + 1);
    });
  }

  private handleOrderBook(data: any[], instId: string, action: string): void {
    const symbol = instId.replace('-', '');
    const update = data[0]; // OKX books usually have 1 element in data array

    if (action === 'snapshot') {
      this.emit('message', {
        type: MessageType.ORDERBOOK_SNAPSHOT,
        exchange: 'okx',
        data: {
          symbol,
          bids: update.bids.map((b: string[]) => ({ price: parseFloat(b[0]), quantity: parseFloat(b[1]) })),
          asks: update.asks.map((a: string[]) => ({ price: parseFloat(a[0]), quantity: parseFloat(a[1]) })),
          timestamp: parseInt(update.ts)
        },
        receivedAt: Date.now()
      });
    } else {
      this.emit('message', {
        type: MessageType.ORDERBOOK_UPDATE,
        exchange: 'okx',
        data: {
          symbol,
          bids: update.bids.map((b: string[]) => ({ price: parseFloat(b[0]), quantity: parseFloat(b[1]) })),
          asks: update.asks.map((a: string[]) => ({ price: parseFloat(a[0]), quantity: parseFloat(a[1]) })),
          lastUpdateId: parseInt(update.ts), // OKX doesn't have a simple sequence, using timestamp
          timestamp: parseInt(update.ts)
        },
        receivedAt: Date.now()
      });
    }
    const count = this.stats.messagesByType.get(MessageType.ORDERBOOK_UPDATE) || 0;
    this.stats.messagesByType.set(MessageType.ORDERBOOK_UPDATE, count + 1);
  }

  private handleKline(data: any[], instId: string): void {
    const symbol = instId.replace('-', '');
    data.forEach(k => {
      const klineData: Kline = {
        symbol,
        interval: '1m',
        openTime: parseInt(k[0]),
        closeTime: parseInt(k[0]) + 59999,
        open: parseFloat(k[1]),
        high: parseFloat(k[2]),
        low: parseFloat(k[3]),
        close: parseFloat(k[4]),
        volume: parseFloat(k[5]),
        quoteVolume: parseFloat(k[6]),
        trades: 0,
        isClosed: k[8] === '1' // OKX candle confirm status
      };

      this.emit('message', {
        type: MessageType.KLINE,
        exchange: 'okx',
        data: klineData,
        receivedAt: Date.now()
      });

      const count = this.stats.messagesByType.get(MessageType.KLINE) || 0;
      this.stats.messagesByType.set(MessageType.KLINE, count + 1);
    });
  }

  private handleError(error: Error): void {
    log.error('❌ OKX WebSocket error', { error: error.message });
    this.stats.errorCount++;
    this.emit('error', error);
  }

  private handleClose(code: number, reason: string): void {
    log.warn('⚠️  OKX WebSocket disconnected', { code, reason });
    this.clearTimers();
    this.state = ConnectionState.DISCONNECTED;
    this.emit('disconnected');
    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;
    this.stats.reconnectCount++;
    log.info(`Reconnecting to OKX in ${delay}ms (attempt ${this.reconnectAttempts})`);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private clearTimers(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.pingInterval) clearInterval(this.pingInterval);
    this.reconnectTimer = null;
    this.pingInterval = null;
  }
}
