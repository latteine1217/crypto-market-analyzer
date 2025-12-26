#!/bin/bash
# ============================================
# 設置測試資料庫環境
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
PROD_DB="${POSTGRES_DB:-crypto_db}"
TEST_DB="${TEST_DB:-crypto_db_test}"

echo "========================================"
echo "設置測試資料庫環境"
echo "========================================"
echo "生產資料庫: $PROD_DB"
echo "測試資料庫: $TEST_DB"
echo ""

# 1. 創建測試資料庫（如果不存在）
echo "📦 創建測試資料庫..."
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "
DROP DATABASE IF EXISTS $TEST_DB;
CREATE DATABASE $TEST_DB;
" 2>/dev/null || echo "資料庫已存在或創建失敗"

# 2. 初始化測試資料庫 schema
echo "🔧 初始化資料庫 schema..."
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" \
    -f database/schemas/01_init.sql > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Schema 初始化成功"
else
    echo "❌ Schema 初始化失敗"
    exit 1
fi

# 3. 執行其他 migrations（002, 003）
echo "📋 執行前置 migrations..."
for migration in database/migrations/002_add_indexes.sql database/migrations/003_data_quality_tables.sql; do
    if [ -f "$migration" ]; then
        echo "  - 執行 $(basename $migration)..."
        PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" \
            -f "$migration" > /dev/null 2>&1
    fi
done

# 4. 插入測試資料
echo "📊 插入測試資料..."
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" <<EOF
-- 確保有 exchanges 和 markets 資料
INSERT INTO exchanges (name, api_type, is_active)
VALUES ('binance', 'ccxt', TRUE)
ON CONFLICT (name) DO NOTHING;

INSERT INTO markets (exchange_id, symbol, base_asset, quote_asset, market_type)
SELECT id, 'BTC/USDT', 'BTC', 'USDT', 'spot'
FROM exchanges WHERE name = 'binance'
ON CONFLICT (exchange_id, symbol) DO NOTHING;

-- 插入測試 OHLCV 資料（最近 30 天的 1 分鐘資料）
INSERT INTO ohlcv (market_id, timeframe, open_time, open, high, low, close, volume)
SELECT
    1 AS market_id,
    '1m' AS timeframe,
    generate_series(
        NOW() - INTERVAL '30 days',
        NOW(),
        INTERVAL '1 minute'
    ) AS open_time,
    50000 + random() * 5000 AS open,
    50000 + random() * 5000 AS high,
    50000 + random() * 5000 AS low,
    50000 + random() * 5000 AS close,
    random() * 100 AS volume
ON CONFLICT (market_id, timeframe, open_time) DO NOTHING;

-- 顯示插入的資料統計
SELECT
    COUNT(*) AS total_candles,
    MIN(open_time) AS oldest,
    MAX(open_time) AS newest,
    pg_size_pretty(pg_total_relation_size('ohlcv')) AS table_size
FROM ohlcv;
EOF

echo ""
echo "========================================"
echo "✅ 測試資料庫設置完成！"
echo "========================================"
echo ""
echo "測試資料庫: $TEST_DB"
echo "連線指令:"
echo "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $TEST_DB"
echo ""
echo "下一步："
echo "  ./scripts/test_migration_004.sh"
echo "========================================"
