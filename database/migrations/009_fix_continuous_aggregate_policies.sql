-- ============================================
-- Migration: 009 - Fix Continuous Aggregate Policies
-- Description: 修正連續聚合的 end_offset 配置，使近期資料能及時聚合
-- Created: 2025-12-30
-- Issue: ContinuousAggregateStale 告警 - 聚合視圖資料過時
-- ============================================

-- 問題描述：
-- 原配置的 end_offset 過於保守（1h-1d），導致最近的資料長時間不被聚合
-- 例如：ohlcv_5m 的 end_offset 為 1h，意味著最近 1 小時的資料永遠不會被處理

-- 解決方案：
-- 調整 end_offset 為更小的值，配合各視圖的時間粒度：
-- - ohlcv_5m:  1h  → 5m  (只排除最近 5 分鐘正在寫入的資料)
-- - ohlcv_15m: 2h  → 15m (只排除最近 15 分鐘正在寫入的資料)
-- - ohlcv_1h:  4h  → 1h  (只排除最近 1 小時正在寫入的資料)
-- - ohlcv_1d:  1d  → 2h  (只排除最近 2 小時正在寫入的資料)

-- ============================================
-- Part 1: 移除舊策略
-- ============================================

SELECT remove_continuous_aggregate_policy('ohlcv_5m', if_exists => TRUE);
SELECT remove_continuous_aggregate_policy('ohlcv_15m', if_exists => TRUE);
SELECT remove_continuous_aggregate_policy('ohlcv_1h', if_exists => TRUE);
SELECT remove_continuous_aggregate_policy('ohlcv_1d', if_exists => TRUE);

-- ============================================
-- Part 2: 添加優化後的策略
-- ============================================

-- ohlcv_5m: 每小時更新，處理最近 3 天資料，排除最近 5 分鐘
SELECT add_continuous_aggregate_policy('ohlcv_5m',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ohlcv_15m: 每 2 小時更新，處理最近 7 天資料，排除最近 15 分鐘
SELECT add_continuous_aggregate_policy('ohlcv_15m',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '15 minutes',
    schedule_interval => INTERVAL '2 hours',
    if_not_exists => TRUE
);

-- ohlcv_1h: 每 4 小時更新，處理最近 14 天資料，排除最近 1 小時
SELECT add_continuous_aggregate_policy('ohlcv_1h',
    start_offset => INTERVAL '14 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '4 hours',
    if_not_exists => TRUE
);

-- ohlcv_1d: 每天更新，處理最近 30 天資料，排除最近 2 小時
SELECT add_continuous_aggregate_policy('ohlcv_1d',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '2 hours',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================
-- Part 3: 手動觸發立即刷新（可選）
-- ============================================

-- 注意：這些語句需要在 transaction block 外執行
-- 執行方式：逐條執行或使用 psql 的 \gexec

-- CALL refresh_continuous_aggregate('ohlcv_5m', NULL, NULL);
-- CALL refresh_continuous_aggregate('ohlcv_15m', NULL, NULL);
-- CALL refresh_continuous_aggregate('ohlcv_1h', NULL, NULL);
-- CALL refresh_continuous_aggregate('ohlcv_1d', NULL, NULL);

-- ============================================
-- 驗證
-- ============================================

-- 檢查新的 policy 配置
SELECT 
    job_id,
    application_name,
    config->>'end_offset' as end_offset,
    schedule_interval
FROM timescaledb_information.jobs
WHERE application_name LIKE '%Refresh Continuous%'
ORDER BY job_id DESC;

-- 檢查各視圖的最新資料時間
DO $$
BEGIN
    RAISE NOTICE '=== 連續聚合視圖資料狀態 ===';
    RAISE NOTICE 'ohlcv_5m 最新資料: %', (SELECT MAX(open_time) FROM ohlcv_5m);
    RAISE NOTICE 'ohlcv_15m 最新資料: %', (SELECT MAX(open_time) FROM ohlcv_15m);
    RAISE NOTICE 'ohlcv_1h 最新資料: %', (SELECT MAX(open_time) FROM ohlcv_1h);
    RAISE NOTICE 'ohlcv_1d 最新資料: %', (SELECT MAX(open_time) FROM ohlcv_1d);
    RAISE NOTICE 'ohlcv 源資料最新: %', (SELECT MAX(open_time) FROM ohlcv);
END $$;
