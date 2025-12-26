#!/bin/bash
# ============================================
# 查看資料保留狀態
# ============================================

set -e

if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-crypto_market}"
DB_USER="${DB_USER:-postgres}"

echo "========================================"
echo "資料保留狀態報告"
echo "========================================"
echo "查詢時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

PGPASSWORD=$DB_PASSWORD psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -x \
    -c "SELECT * FROM v_retention_status ORDER BY layer;"

echo ""
echo "========================================"
echo "儲存空間使用情況"
echo "========================================"
echo ""

PGPASSWORD=$DB_PASSWORD psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -c "SELECT * FROM get_storage_statistics();"
