#!/bin/bash

# ============================================
# 資料庫初始化腳本
# Purpose: 確保資料庫 schema 完整且正確
# Usage: ./scripts/init_database.sh [--reset]
# ============================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
DB_CONTAINER="crypto_timescaledb"
DB_USER="${POSTGRES_USER:-crypto}"
DB_NAME="${POSTGRES_DB:-crypto_db}"

# 函數：顯示訊息
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函數：執行 SQL
exec_sql() {
    local sql="$1"
    docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "$sql" 2>&1
}

# 函數：執行 SQL 檔案
exec_sql_file() {
    local file="$1"
    local filename=$(basename "$file")
    log_info "執行 $filename ..."
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME < "$file" 2>&1
}

# 函數：檢查容器是否運行
check_container() {
    if ! docker ps | grep -q $DB_CONTAINER; then
        log_error "資料庫容器未運行。請先執行: docker-compose up -d db"
        exit 1
    fi
    log_success "資料庫容器運行中"
}

# 函數：等待資料庫就緒
wait_for_db() {
    log_info "等待資料庫就緒 ..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker exec $DB_CONTAINER pg_isready -U $DB_USER -d $DB_NAME > /dev/null 2>&1; then
            log_success "資料庫已就緒"
            return 0
        fi

        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done

    log_error "資料庫未在 ${max_attempts} 秒內就緒"
    exit 1
}

# 函數：檢查表是否存在
check_table_exists() {
    local table="$1"
    local result=$(exec_sql "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '$table');" | grep -o 't\|f' | head -1)

    if [ "$result" = "t" ]; then
        return 0
    else
        return 1
    fi
}

# 函數：初始化基礎 schema
init_base_schema() {
    log_info "初始化基礎 schema ..."

    local schema_file="database/schemas/00_v3_optimized.sql"

    if [ ! -f "$schema_file" ]; then
        log_error "找不到基礎 schema 檔案: $schema_file"
        exit 1
    fi

    exec_sql_file "$schema_file"
    log_success "基礎 schema 初始化完成"
}

# 函數：執行 migrations
run_migrations() {
    log_info "執行 migrations ..."

    local migration_dir="database/migrations"

    if [ ! -d "$migration_dir" ]; then
        log_warning "找不到 migrations 目錄"
        return
    fi

    # 按照檔名順序執行所有 .sql 檔案
    for file in $(ls -1 $migration_dir/*.sql 2>/dev/null | sort); do
        if [ -f "$file" ]; then
            exec_sql_file "$file"
        fi
    done

    log_success "Migrations 執行完成"
}

# 函數：驗證 schema
verify_schema() {
    log_info "驗證 schema ..."

    local required_tables=(
        "exchanges"
        "blockchains"
        "markets"
        "ohlcv"
        "trades"
        "market_metrics"
        "global_indicators"
        "whale_transactions"
        "address_tier_snapshots"
        "system_logs"
        "events"
        "price_alerts"
        "backfill_tasks"
        "data_quality_summary"
        "api_error_logs"
    )

    local missing_tables=()

    for table in "${required_tables[@]}"; do
        if ! check_table_exists "$table"; then
            missing_tables+=("$table")
        fi
    done

    if [ ${#missing_tables[@]} -eq 0 ]; then
        log_success "所有必要的表都存在"
    else
        log_warning "以下表缺失: ${missing_tables[*]}"
        return 1
    fi
}

# 函數：顯示統計資訊
show_stats() {
    log_info "資料庫統計資訊："

    echo ""
    echo "=== 表格列表 ==="
    exec_sql "\dt" | grep -v "^$"

    echo ""
    echo "=== Hypertables ==="
    exec_sql "SELECT hypertable_name, num_chunks FROM timescaledb_information.hypertables ORDER BY hypertable_name;" | grep -v "^$"

    echo ""
    echo "=== 資料量統計 ==="
    exec_sql "
        SELECT
            'exchanges' as table_name,
            COUNT(*) as count
        FROM exchanges
        UNION ALL
        SELECT 'markets', COUNT(*) FROM markets
        UNION ALL
        SELECT 'ohlcv', COUNT(*) FROM ohlcv
        UNION ALL
        SELECT 'trades', COUNT(*) FROM trades
        UNION ALL
        SELECT 'market_metrics', COUNT(*) FROM market_metrics
        ORDER BY table_name;
    " | grep -v "^$"
}

# 主程式
main() {
    log_info "========================================="
    log_info "資料庫初始化腳本"
    log_info "========================================="
    echo ""

    # 檢查參數
    local reset_mode=false
    if [ "$1" = "--reset" ]; then
        reset_mode=true
        log_warning "重置模式：將刪除並重建資料庫"
        read -p "確定要繼續嗎？(yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log_info "操作已取消"
            exit 0
        fi
    fi

    # 檢查容器
    check_container

    # 等待資料庫就緒
    wait_for_db

    # 重置模式：刪除資料庫
    if [ "$reset_mode" = true ]; then
        log_warning "刪除現有資料庫 ..."
        docker exec $DB_CONTAINER psql -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>&1 || true
        docker exec $DB_CONTAINER psql -U $DB_USER -c "CREATE DATABASE $DB_NAME;" 2>&1
        log_success "資料庫已重置"
    fi

    # 初始化基礎 schema
    if [ "$reset_mode" = true ] || ! check_table_exists "exchanges"; then
        init_base_schema
    else
        log_info "基礎 schema 已存在，跳過初始化"
    fi

    # 執行 migrations
    run_migrations

    # 驗證 schema
    echo ""
    verify_schema

    # 顯示統計
    echo ""
    show_stats

    echo ""
    log_success "========================================="
    log_success "資料庫初始化完成"
    log_success "========================================="
}

# 執行主程式
main "$@"
