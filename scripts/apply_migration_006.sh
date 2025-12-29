#!/bin/bash
# ============================================
# 執行 Migration 006：Orderbook Snapshot Indexes
# ============================================

set -e  # 遇到錯誤立即退出

# 載入環境變數（如果存在）
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 資料庫連線參數（可從環境變數覆蓋）
DB_HOST="${DB_HOST:-${POSTGRES_HOST:-localhost}}"
DB_PORT="${DB_PORT:-${POSTGRES_PORT:-5432}}"
DB_NAME="${DB_NAME:-${POSTGRES_DB:-crypto_db}}"
DB_USER="${DB_USER:-${POSTGRES_USER:-postgres}}"
DB_PASSWORD="${DB_PASSWORD:-${POSTGRES_PASSWORD:-}}"

MIGRATION_FILE="database/migrations/006_orderbook_snapshot_indexes.sql"

echo "========================================"
echo "執行 Migration 006"
echo "========================================"
echo "資料庫: $DB_NAME"
echo "主機: $DB_HOST:$DB_PORT"
echo "用戶: $DB_USER"
echo ""

# 檢查檔案是否存在
if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ 錯誤：找不到 migration 檔案 $MIGRATION_FILE"
    exit 1
fi

echo "📂 Migration 檔案: $MIGRATION_FILE"
echo ""

# 詢問確認（可用 AUTO_APPROVE=1 跳過）
if [ "${AUTO_APPROVE:-0}" != "1" ]; then
    read -p "⚠️  此操作將新增索引，是否繼續？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 操作已取消"
        exit 1
    fi
fi

echo ""
echo "🚀 開始執行 migration..."
echo ""

# 執行 SQL
PGPASSWORD=$DB_PASSWORD psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "✅ Migration 006 執行成功！"
    echo "========================================"
else
    echo ""
    echo "========================================"
    echo "❌ Migration 執行失敗"
    echo "========================================"
    exit 1
fi
