/**
 * 統一的 Redis Key 管理器
 */

export const REDIS_PREFIX = 'crypto:v2';

export const RedisKeys = {
  /**
   * 獲取資料收集佇列的 Key
   * 格式: crypto:v2:queue:{exchange}:{type} 或 crypto:v2:queue:{type}
   */
  getQueueKey(type: string, exchange: string = ''): string {
    const exchangePart = exchange ? `${exchange.toLowerCase()}:` : '';
    return `${REDIS_PREFIX}:queue:${exchangePart}${type}`;
  },

  /**
   * 獲取訂單簿快照的 Key
   * 格式: crypto:v2:orderbook:{exchange}:{symbol}
   */
  getOrderBookKey(exchange: string, symbol: string): string {
    return `${REDIS_PREFIX}:orderbook:${exchange.toLowerCase()}:${symbol.toUpperCase()}`;
  },

  /**
   * 獲取 API 回應緩存的 Key
   * 格式: crypto:v2:cache:{path}:{params_hash}
   */
  getCacheKey(path: string, params: string = ''): string {
    return `${REDIS_PREFIX}:cache:${path}${params ? ':' + params : ''}`;
  },

  /**
   * 獲取系統指標的 Key
   * 格式: crypto:v2:metrics:{name}
   */
  getMetricsKey(name: string): string {
    return `${REDIS_PREFIX}:metrics:${name}`;
  }
};
