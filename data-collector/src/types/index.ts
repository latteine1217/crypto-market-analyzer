/**
 * WebSocket 數據收集器類型定義
 */
import { EventEmitter } from 'events';

// WebSocket 訊息類型
export enum MessageType {
  TRADE = 'trade',
  ORDERBOOK_SNAPSHOT = 'orderbook_snapshot',
  ORDERBOOK_UPDATE = 'orderbook_update',
  KLINE = 'kline',
  TICKER = 'ticker',
  LIQUIDATION = 'liquidation'
}

// 爆倉數據
export interface Liquidation {
  symbol: string;
  side: 'buy' | 'sell'; // Buy 代表空單爆倉(強制買入), Sell 代表多單爆倉(強制賣出)
  price: number;
  quantity: number;
  timestamp: number;
}

// 交易數據
export interface Trade {
  symbol: string;
  tradeId: string | number;
  price: number;
  quantity: number;
  quoteQuantity?: number;
  timestamp: number;
  isBuyerMaker: boolean;
  side?: 'buy' | 'sell';
}

// 訂單簿價格層級
export interface PriceLevel {
  price: number;
  quantity: number;
}

// 訂單簿快照
export interface OrderBookSnapshot {
  symbol: string;
  timestamp: number;
  lastUpdateId?: number;
  bids: PriceLevel[];
  asks: PriceLevel[];
  obi?: number; // Order Book Imbalance
}

// 訂單簿增量更新
export interface OrderBookUpdate {
  symbol: string;
  timestamp: number;
  firstUpdateId?: number;
  lastUpdateId: number;
  bids: PriceLevel[];
  asks: PriceLevel[];
}

// K線數據
export interface Kline {
  symbol: string;
  interval: string;
  openTime: number;
  closeTime: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  quoteVolume: number;
  trades: number;
  isClosed: boolean;
}

// Redis 佇列訊息
export interface QueueMessage {
  type: MessageType;
  exchange: string;
  data: Trade | OrderBookSnapshot | OrderBookUpdate | Kline | Liquidation;
  receivedAt: number;
}

// WebSocket 配置
export interface WSConfig {
  exchange: string;
  symbols: string[];
  streams: string[];
  reconnect: boolean;
  reconnectDelay: number;
  heartbeatInterval: number;
  maxReconnectAttempts: number;
}

// 連接狀態
export enum ConnectionState {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
  FAILED = 'failed'
}

// WebSocket 事件
export interface WSEvents {
  onConnected: () => void;
  onDisconnected: (code: number, reason: string) => void;
  onError: (error: Error) => void;
  onMessage: (message: QueueMessage) => void;
  onReconnecting: (attempt: number) => void;
}

// 訂單簿管理器狀態
export interface OrderBookState {
  symbol: string;
  lastUpdateId: number;
  bids: Map<number, number>;  // price -> quantity
  asks: Map<number, number>;
  lastSnapshotTime: number;
  updateCount: number;
}

// Flush 配置
export interface FlushConfig {
  batchSize: number;
  intervalMs: number;
  maxRetries: number;
  maxBatchesPerFlush: number;
}

// 資料庫連接配置
export interface DBConfig {
  host: string;
  port: number;
  database: string;
  user: string;
  password: string;
}

// Redis 配置
export interface RedisConfig {
  host: string;
  port: number;
  password?: string;
  db?: number;
}

// 統計數據
export interface Stats {
  totalMessages: number;
  messagesByType: Map<MessageType, number>;
  lastMessageTime: number;
  reconnectCount: number;
  errorCount: number;
  uptimeMs: number;
}

// WebSocket 客戶端通用介面
export interface IWSClient extends EventEmitter {
  connect(): void;
  disconnect(): void;
  getState(): ConnectionState;
  getStats(): Stats;
  on(event: string, listener: (...args: any[]) => void): this;
}
