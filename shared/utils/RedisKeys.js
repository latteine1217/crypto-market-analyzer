"use strict";
/**
 * 統一的 Redis Key 管理器
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.RedisKeys = exports.REDIS_PREFIX = void 0;
exports.REDIS_PREFIX = 'crypto:v2';
exports.RedisKeys = {
    /**
     * 獲取資料收集佇列的 Key
     * 格式: crypto:v2:queue:{exchange}:{type} 或 crypto:v2:queue:{type}
     */
    getQueueKey(type, exchange = '') {
        const exchangePart = exchange ? `${exchange.toLowerCase()}:` : '';
        return `${exports.REDIS_PREFIX}:queue:${exchangePart}${type}`;
    },
    /**
     * 獲取訂單簿快照的 Key
     * 格式: crypto:v2:orderbook:{exchange}:{symbol}
     */
    getOrderBookKey(exchange, symbol) {
        return `${exports.REDIS_PREFIX}:orderbook:${exchange.toLowerCase()}:${symbol.toUpperCase()}`;
    },
    /**
     * 獲取 API 回應緩存的 Key
     * 格式: crypto:v2:cache:{path}:{params_hash}
     */
    getCacheKey(path, params = '') {
        return `${exports.REDIS_PREFIX}:cache:${path}${params ? ':' + params : ''}`;
    },
    /**
     * 獲取系統指標的 Key
     * 格式: crypto:v2:metrics:{name}
     */
    getMetricsKey(name) {
        return `${exports.REDIS_PREFIX}:metrics:${name}`;
    }
};
//# sourceMappingURL=RedisKeys.js.map