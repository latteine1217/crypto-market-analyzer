#!/bin/bash
# ============================================
# 執行 Migration 004：連續聚合與分層保留
# ============================================

set -e  # 遇到錯誤立即退出

# 載入環境變數（如果存在）
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 資料庫連線參數（可從環境變數覆蓋）
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-crypto_market}"
DB_USER="${DB_USER:-postgres}"

MIGRATION_FILE="database/migrations/004_continuous_aggregates_and_retention.sql"

echo "========================================"
echo "執行 Migration 004"
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

# 詢問確認
read -p "⚠️  此操作將修改資料保留策略，是否繼續？(y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 操作已取消"
    exit 1
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
    echo "✅ Migration 004 執行成功！"
    echo "========================================"
    echo ""
    echo "下一步："
    echo "1. 執行驗證腳本："
    echo "   ./scripts/verify_migration_004.sh"
    echo ""
    echo "2. 查看資料保留狀態："
    echo "   ./scripts/check_retention_status.sh"
    echo ""
else
    echo ""
    echo "========================================"
    echo "❌ Migration 執行失敗"
    echo "========================================"
    exit 1
fi
