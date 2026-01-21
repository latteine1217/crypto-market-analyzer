/**
 * 訂單簿管理器
 * 維護本地訂單簿快照並處理增量更新
 */
import axios from 'axios';
import { log } from '../utils/logger';
import {
  OrderBookSnapshot,
  OrderBookUpdate,
  OrderBookState,
  PriceLevel
} from '../types';

export class OrderBookManager {
  private orderBooks: Map<string, OrderBookState> = new Map();
  private readonly SNAPSHOT_INTERVAL_MS = 60000; // 每分鐘生成一次快照
  private readonly MAX_DEPTH = 20; // 保留的訂單簿深度

  constructor(private exchange: string = 'bybit') {
    log.info(`OrderBookManager initialized for ${exchange}`);
  }

  /**
   * 初始化指定交易對的訂單簿
   * 從 REST API 獲取完整快照
   */
  public async initializeOrderBook(symbol: string): Promise<void> {
    try {
      log.info(`Initializing order book for ${symbol} on ${this.exchange}`);

      const snapshot = await this.fetchOrderBookSnapshot(symbol);

      const state: OrderBookState = {
        symbol,
        lastUpdateId: snapshot.lastUpdateId || 0,
        bids: new Map(snapshot.bids.map(b => [b.price, b.quantity])),
        asks: new Map(snapshot.asks.map(a => [a.price, a.quantity])),
        lastSnapshotTime: Date.now(),
        updateCount: 0
      };

      this.orderBooks.set(symbol, state);

      log.info(`Order book initialized for ${symbol}`, {
        lastUpdateId: state.lastUpdateId,
        bids: state.bids.size,
        asks: state.asks.size
      });

    } catch (error) {
      log.error(`Failed to initialize order book for ${symbol}`, error);
      // 注意：某些交易所透過 WebSocket 直接提供快照，REST 可能失敗
    }
  }

  /**
   * 從交易所 REST API 獲取訂單簿快照
   */
  private async fetchOrderBookSnapshot(symbol: string): Promise<OrderBookSnapshot> {
    if (this.exchange === 'bybit') {
      const url = `https://api.bybit.com/v5/market/orderbook`;
      const params = {
        category: 'linear',
        symbol: symbol,
        limit: 50
      };

      const response = await axios.get(url, { params });
      const data = response.data;

      if (data.retCode !== 0) {
        throw new Error(`Bybit API error: ${data.retMsg}`);
      }

      return {
        symbol,
        timestamp: parseInt(data.result.ts),
        lastUpdateId: data.result.u,
        bids: data.result.b.map((b: [string, string]) => ({
          price: parseFloat(b[0]),
          quantity: parseFloat(b[1])
        })),
        asks: data.result.a.map((a: [string, string]) => ({
          price: parseFloat(a[0]),
          quantity: parseFloat(a[1])
        }))
      };
    } else {
      throw new Error(`Unsupported exchange for REST snapshot: ${this.exchange}`);
    }
  }

  /**
   * 處理訂單簿更新
   */
  public processUpdate(update: OrderBookUpdate): boolean {
    const state = this.orderBooks.get(update.symbol);

    if (!state) {
      log.warn(`Order book not initialized for ${update.symbol}`);
      return false;
    }

    // 驗證更新順序
    // 跳過舊的更新（lastUpdateId < state.lastUpdateId）
    if (update.lastUpdateId <= state.lastUpdateId) {
      return false;
    }

    // 檢查是否有遺漏的更新
    if (update.firstUpdateId && update.firstUpdateId > state.lastUpdateId + 1) {
      log.warn(`Missing updates detected for ${update.symbol}`, {
        expected: state.lastUpdateId + 1,
        received: update.firstUpdateId
      });
      // 需要重新初始化訂單簿
      this.initializeOrderBook(update.symbol).catch(err => {
        log.error(`Failed to reinitialize order book`, err);
      });
      return false;
    }

    // 應用更新
    this.applyBidsUpdate(state.bids, update.bids);
    this.applyAsksUpdate(state.asks, update.asks);

    state.lastUpdateId = update.lastUpdateId;
    state.updateCount++;

    return true;
  }

  /**
   * 應用 Bids 更新
   */
  private applyBidsUpdate(bids: Map<number, number>, updates: PriceLevel[]): void {
    for (const { price, quantity } of updates) {
      if (quantity === 0) {
        // 數量為 0 表示刪除該價位
        bids.delete(price);
      } else {
        // 更新或新增價位
        bids.set(price, quantity);
      }
    }
  }

  /**
   * 應用 Asks 更新
   */
  private applyAsksUpdate(asks: Map<number, number>, updates: PriceLevel[]): void {
    for (const { price, quantity } of updates) {
      if (quantity === 0) {
        asks.delete(price);
      } else {
        asks.set(price, quantity);
      }
    }
  }

  /**
   * 生成當前訂單簿快照（Top N）
   */
  public getSnapshot(symbol: string, depth: number = this.MAX_DEPTH): OrderBookSnapshot | null {
    const state = this.orderBooks.get(symbol);

    if (!state) {
      return null;
    }

    // 排序並取前 N 檔
    const sortedBids = Array.from(state.bids.entries())
      .sort((a, b) => b[0] - a[0]) // 價格從高到低
      .slice(0, depth)
      .map(([price, quantity]) => ({ price, quantity }));

    const sortedAsks = Array.from(state.asks.entries())
      .sort((a, b) => a[0] - b[0]) // 價格從低到高
      .slice(0, depth)
      .map(([price, quantity]) => ({ price, quantity }));

    return {
      symbol,
      timestamp: Date.now(),
      lastUpdateId: state.lastUpdateId,
      bids: sortedBids,
      asks: sortedAsks
    };
  }

  /**
   * 獲取訂單簿統計資訊
   */
  public getStats(symbol: string): any {
    const state = this.orderBooks.get(symbol);

    if (!state) {
      return null;
    }

    const snapshot = this.getSnapshot(symbol, 1);
    const bestBid = snapshot?.bids[0];
    const bestAsk = snapshot?.asks[0];

    return {
      symbol,
      lastUpdateId: state.lastUpdateId,
      updateCount: state.updateCount,
      bidsCount: state.bids.size,
      asksCount: state.asks.size,
      bestBid: bestBid?.price,
      bestAsk: bestAsk?.price,
      spread: bestBid && bestAsk ? bestAsk.price - bestBid.price : null,
      spreadBps: bestBid && bestAsk
        ? ((bestAsk.price - bestBid.price) / bestBid.price) * 10000
        : null
    };
  }

  /**
   * 啟動定期快照生成
   */
  public startPeriodicSnapshots(
    callback: (snapshot: OrderBookSnapshot) => void
  ): NodeJS.Timeout {
    return setInterval(() => {
      for (const symbol of this.orderBooks.keys()) {
        const snapshot = this.getSnapshot(symbol);
        if (snapshot) {
          callback(snapshot);
        }
      }
    }, this.SNAPSHOT_INTERVAL_MS);
  }

  /**
   * 清理資源
   */
  public cleanup(): void {
    this.orderBooks.clear();
    log.info('OrderBookManager cleaned up');
  }
}