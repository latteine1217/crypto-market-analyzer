#!/bin/bash
# ============================================
# 清理測試資料庫
# ============================================

set -e

if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-crypto}"
DB_PASSWORD="${POSTGRES_PASSWORD:-crypto_pass}"
TEST_DB="${TEST_DB:-crypto_db_test}"

echo "========================================"
echo "清理測試資料庫"
echo "========================================"
echo "測試資料庫: $TEST_DB"
echo ""

read -p "⚠️  確定要刪除測試資料庫 '$TEST_DB' 嗎？(y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 操作已取消"
    exit 1
fi

PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "
DROP DATABASE IF EXISTS $TEST_DB;
"

echo ""
echo "✅ 測試資料庫已刪除"
