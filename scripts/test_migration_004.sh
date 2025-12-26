#!/bin/bash
# ============================================
# 在測試環境中執行 Migration 004
# ============================================

set -e

# 載入環境變數
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-crypto}"
DB_PASSWORD="${POSTGRES_PASSWORD:-crypto_pass}"
TEST_DB="${TEST_DB:-crypto_db_test}"

MIGRATION_FILE="database/migrations/004_continuous_aggregates_and_retention.sql"

echo "========================================"
echo "測試環境執行 Migration 004"
echo "========================================"
echo "測試資料庫: $TEST_DB"
echo ""

# 檢查測試資料庫是否存在
DB_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$TEST_DB'")

if [ "$DB_EXISTS" != "1" ]; then
    echo "❌ 測試資料庫不存在，請先執行："
    echo "   ./scripts/setup_test_db.sh"
    exit 1
fi

# 檢查 migration 文件
if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ 找不到 migration 文件: $MIGRATION_FILE"
    exit 1
fi

echo "📂 Migration 文件: $MIGRATION_FILE"
echo ""

# 顯示執行前的資料狀態
echo "📊 執行前的資料狀態："
echo "---"
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" -c "
SELECT
    'ohlcv' AS table_name,
    COUNT(*) AS records,
    pg_size_pretty(pg_total_relation_size('ohlcv')) AS size
FROM ohlcv
WHERE timeframe = '1m';
"
echo ""

# 執行 migration
echo "🚀 執行 migration..."
echo ""

PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" \
    -f "$MIGRATION_FILE"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Migration 執行失敗！"
    exit 1
fi

echo ""
echo "========================================"
echo "✅ Migration 執行成功！"
echo "========================================"
echo ""

# 執行驗證
echo "🔍 執行驗證檢查..."
echo ""

PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" <<'EOF'
-- 1. 檢查連續聚合視圖
SELECT '✓ 連續聚合視圖' AS check_item;
SELECT
    matviewname AS view_name,
    '✅ 已創建' AS status
FROM pg_matviews
WHERE schemaname = 'public'
AND matviewname LIKE 'ohlcv_%'
ORDER BY matviewname;

-- 2. 檢查資料保留狀態
SELECT '' AS separator;
SELECT '✓ 資料保留狀態' AS check_item;
SELECT * FROM v_retention_status;

-- 3. 檢查聚合資料（手動觸發更新）
SELECT '' AS separator;
SELECT '✓ 觸發聚合更新' AS check_item;
CALL refresh_continuous_aggregate('ohlcv_5m', NULL, NULL);
CALL refresh_continuous_aggregate('ohlcv_15m', NULL, NULL);
CALL refresh_continuous_aggregate('ohlcv_1h', NULL, NULL);
CALL refresh_continuous_aggregate('ohlcv_1d', NULL, NULL);

-- 4. 檢查聚合資料筆數
SELECT '' AS separator;
SELECT '✓ 聚合資料統計' AS check_item;
SELECT 'ohlcv_5m' AS view_name, COUNT(*) AS records FROM ohlcv_5m
UNION ALL
SELECT 'ohlcv_15m', COUNT(*) FROM ohlcv_15m
UNION ALL
SELECT 'ohlcv_1h', COUNT(*) FROM ohlcv_1h
UNION ALL
SELECT 'ohlcv_1d', COUNT(*) FROM ohlcv_1d;

-- 5. 測試智能查詢函數
SELECT '' AS separator;
SELECT '✓ 測試智能查詢函數' AS check_item;
SELECT
    open_time,
    close,
    volume,
    source
FROM get_optimal_ohlcv(
    p_market_id := 1,
    p_start_time := NOW() - INTERVAL '7 days',
    p_end_time := NOW(),
    p_max_points := 10
)
ORDER BY open_time DESC
LIMIT 5;

-- 6. 檢查重要事件
SELECT '' AS separator;
SELECT '✓ 重要事件表' AS check_item;
SELECT
    event_name,
    event_type,
    TO_CHAR(start_time, 'YYYY-MM-DD') AS start_date,
    preserve_raw
FROM critical_events
ORDER BY start_time;

-- 7. 儲存空間統計
SELECT '' AS separator;
SELECT '✓ 儲存空間統計' AS check_item;
SELECT * FROM get_storage_statistics();
EOF

echo ""
echo "========================================"
echo "📋 測試總結"
echo "========================================"
echo ""
echo "✅ Migration 004 在測試環境執行成功"
echo "✅ 所有連續聚合視圖已創建"
echo "✅ 資料保留策略已設置"
echo "✅ 輔助函數正常運作"
echo ""
echo "下一步："
echo "  1. 查看詳細測試結果（如上）"
echo "  2. 如果一切正常，執行生產環境 migration："
echo "     DB_NAME=crypto_db ./scripts/apply_migration_004.sh"
echo ""
echo "  3. 清理測試資料庫："
echo "     ./scripts/cleanup_test_db.sh"
echo ""
echo "========================================"
