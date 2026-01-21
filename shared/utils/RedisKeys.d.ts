/**
 * 統一的 Redis Key 管理器
 */
export declare const REDIS_PREFIX = "crypto:v2";
export declare const RedisKeys: {
    /**
     * 獲取資料收集佇列的 Key
     * 格式: crypto:v2:queue:{exchange}:{type} 或 crypto:v2:queue:{type}
     */
    getQueueKey(type: string, exchange?: string): string;
    /**
     * 獲取訂單簿快照的 Key
     * 格式: crypto:v2:orderbook:{exchange}:{symbol}
     */
    getOrderBookKey(exchange: string, symbol: string): string;
    /**
     * 獲取 API 回應緩存的 Key
     * 格式: crypto:v2:cache:{path}:{params_hash}
     */
    getCacheKey(path: string, params?: string): string;
    /**
     * 獲取系統指標的 Key
     * 格式: crypto:v2:metrics:{name}
     */
    getMetricsKey(name: string): string;
};
//# sourceMappingURL=RedisKeys.d.ts.map