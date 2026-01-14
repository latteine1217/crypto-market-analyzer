#!/bin/bash
# ============================================
# 驗證 Migration 004 執行結果
# ============================================

set -e

# 載入環境變數
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-crypto_market}"
DB_USER="${DB_USER:-postgres}"

echo "========================================"
echo "驗證 Migration 004 執行結果"
echo "========================================"
echo ""

# 執行驗證 SQL
PGPASSWORD=$DB_PASSWORD psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -c "
-- 1. 檢查連續聚合視圖是否存在
SELECT '✓ 檢查連續聚合視圖' AS step;
SELECT
    viewname AS view_name,
    CASE WHEN viewname IS NOT NULL THEN '✅ 存在' ELSE '❌ 不存在' END AS status
FROM pg_views
WHERE schemaname = 'public'
AND viewname IN ('ohlcv_5m', 'ohlcv_15m', 'ohlcv_1h', 'ohlcv_1d')
ORDER BY viewname;

-- 2. 檢查 critical_events 表
SELECT '' AS separator;
SELECT '✓ 檢查重要事件表' AS step;
SELECT
    event_name,
    event_type,
    TO_CHAR(start_time, 'YYYY-MM-DD') AS start_date,
    TO_CHAR(end_time, 'YYYY-MM-DD') AS end_date,
    preserve_raw
FROM critical_events
ORDER BY start_time;

-- 3. 檢查連續聚合策略
SELECT '' AS separator;
SELECT '✓ 檢查連續聚合更新策略' AS step;
SELECT
    view_name,
    schedule_interval,
    config->>'start_offset' AS start_offset,
    config->>'end_offset' AS end_offset
FROM timescaledb_information.jobs j
JOIN timescaledb_information.continuous_aggregates ca
    ON j.hypertable_name = ca.materialization_hypertable_name
WHERE view_name LIKE 'ohlcv_%'
ORDER BY view_name;

-- 4. 檢查保留策略
SELECT '' AS separator;
SELECT '✓ 檢查資料保留策略' AS step;
SELECT
    hypertable_name,
    schedule_interval,
    config->>'drop_after' AS retention_period
FROM timescaledb_information.jobs
WHERE proc_name = 'policy_retention'
ORDER BY hypertable_name;

-- 5. 查看資料保留狀態
SELECT '' AS separator;
SELECT '✓ 資料保留狀態總覽' AS step;
SELECT * FROM v_retention_status
ORDER BY
    CASE layer
        WHEN 'ohlcv (1m)' THEN 1
        WHEN 'ohlcv_5m' THEN 2
        WHEN 'ohlcv_15m' THEN 3
        WHEN 'ohlcv_1h' THEN 4
        WHEN 'ohlcv_1d' THEN 5
    END;

-- 6. 儲存空間統計
SELECT '' AS separator;
SELECT '✓ 儲存空間使用情況' AS step;
SELECT * FROM get_storage_statistics();

-- 7. 測試輔助函數
SELECT '' AS separator;
SELECT '✓ 測試智能查詢函數' AS step;
SELECT
    'get_optimal_ohlcv() 函數' AS function_name,
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'get_optimal_ohlcv'
    ) THEN '✅ 可用' ELSE '❌ 不存在' END AS status;

SELECT
    'check_data_availability() 函數' AS function_name,
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'check_data_availability'
    ) THEN '✅ 可用' ELSE '❌ 不存在' END AS status;

SELECT
    'is_critical_event_period() 函數' AS function_name,
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'is_critical_event_period'
    ) THEN '✅ 可用' ELSE '❌ 不存在' END AS status;
"

echo ""
echo "========================================"
echo "✅ 驗證完成"
echo "========================================"
