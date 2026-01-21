#!/bin/bash
# ============================================
# 資料庫自動初始化與 Migration 執行腳本
# 目的：確保每次 DB 容器啟動時自動執行所有 migrations
# 位置：/docker-entrypoint-initdb.d/01_apply_migrations.sh
# ============================================

set -e

echo "=========================================="
echo "Starting Database Initialization"
echo "=========================================="

# 1. 執行基礎 schema
echo ""
echo "Step 1: Creating base schema..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/00_v3_optimized.sql

# 2. 執行所有 migrations（按順序）
echo ""
echo "Step 2: Applying migrations..."

MIGRATION_DIR="/docker-entrypoint-initdb.d/migrations"

if [ -d "$MIGRATION_DIR" ]; then
    for migration in $(ls -1 $MIGRATION_DIR/*.sql 2>/dev/null | sort); do
        echo "  - Applying $(basename $migration)..."
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$migration" 2>&1 | grep -v "NOTICE" || true
    done
    echo "  ✓ All migrations applied"
else
    echo "  ⚠ No migrations directory found, skipping"
fi

# 3. 驗證關鍵表
echo ""
echo "Step 3: Verifying critical tables..."

REQUIRED_TABLES=(
    "exchanges"
    "markets"
    "ohlcv"
    "trades"
    "market_metrics"
    "backfill_tasks"
    "data_quality_summary"
    "api_error_logs"
)

MISSING_TABLES=()

for table in "${REQUIRED_TABLES[@]}"; do
    if psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -tAc "SELECT to_regclass('public.$table');" | grep -q "$table"; then
        echo "  ✓ $table"
    else
        echo "  ✗ $table (MISSING)"
        MISSING_TABLES+=("$table")
    fi
done

if [ ${#MISSING_TABLES[@]} -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Database Initialization Complete"
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "⚠️  Warning: Missing tables detected"
    echo "Missing: ${MISSING_TABLES[*]}"
    echo "=========================================="
fi
