#!/bin/bash
# 初始化區塊鏈巨鯨追蹤資料庫

set -e

echo "============================================"
echo "初始化區塊鏈巨鯨追蹤資料庫"
echo "============================================"

# 載入環境變數
if [ -f collector-py/.env ]; then
    export $(cat collector-py/.env | grep -v '^#' | xargs)
    echo "✓ 已載入環境變數"
else
    echo "✗ 找不到 collector-py/.env 文件"
    exit 1
fi

# 檢查 PostgreSQL 連接
echo ""
echo "檢查 PostgreSQL 連接..."
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "\conninfo" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✓ PostgreSQL 連接成功"
else
    echo "✗ PostgreSQL 連接失敗，請檢查資料庫是否運行"
    exit 1
fi

# 執行 schema 初始化
echo ""
echo "執行資料庫 schema 初始化..."

# 基礎 schema
echo "  → 執行 01_init.sql (基礎交易所資料)"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f database/schemas/01_init.sql

# 區塊鏈 schema
echo "  → 執行 02_blockchain_whale_tracking.sql (區塊鏈巨鯨追蹤)"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f database/schemas/02_blockchain_whale_tracking.sql

echo ""
echo "============================================"
echo "資料庫初始化完成!"
echo "============================================"

# 顯示統計資訊
echo ""
echo "資料庫統計:"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

echo ""
echo "區塊鏈列表:"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "
SELECT id, name, full_name, native_token, is_active
FROM blockchains
ORDER BY id;
"

echo ""
echo "準備開始收集區塊鏈資料!"
echo "執行測試: cd collector-py && python3 test_blockchain_etl.py"
