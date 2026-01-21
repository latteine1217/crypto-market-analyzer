#!/bin/bash

# ============================================
# 服務啟動腳本
# Purpose: 統一啟動與驗證所有 Docker 服務
# Usage: ./scripts/start_services.sh [--rebuild]
# ============================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# 函數：檢查環境變數檔案
check_env_file() {
    if [ ! -f ".env" ]; then
        log_warning ".env 檔案不存在"

        if [ -f ".env.example" ]; then
            log_info "複製 .env.example 到 .env ..."
            cp .env.example .env
            log_success ".env 檔案已建立"
            log_warning "請檢查並更新 .env 中的配置"
        else
            log_error "找不到 .env.example 檔案"
            exit 1
        fi
    else
        log_success ".env 檔案存在"
    fi
}

# 函數：檢查 Docker 是否運行
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker 未運行，請先啟動 Docker"
        exit 1
    fi
    log_success "Docker 正在運行"
}

# 函數：停止所有服務
stop_all_services() {
    log_info "停止所有服務 ..."
    docker-compose down
}

# 函數：啟動服務
start_services() {
    local rebuild=$1

    if [ "$rebuild" = "true" ]; then
        log_step "重新建構並啟動所有服務 ..."
        docker-compose up -d --build
    else
        log_step "啟動所有服務 ..."
        docker-compose up -d
    fi
}

# 函數：等待服務就緒
wait_for_service() {
    local service=$1
    local max_attempts=60
    local attempt=1

    log_info "等待 $service 就緒 ..."

    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps | grep $service | grep -q "healthy\|Up"; then
            log_success "$service 已就緒"
            return 0
        fi

        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done

    log_error "$service 未在 ${max_attempts} 秒內就緒"
    return 1
}

# 函數：檢查所有服務狀態
check_services_status() {
    log_step "檢查服務狀態 ..."

    local all_healthy=true
    local services=(
        "db:crypto_timescaledb"
        "redis:crypto_redis"
        "collector:crypto_collector"
        "api-server:crypto_api_server"
        "dashboard-ts:crypto_dashboard_ts"
    )

    echo ""
    echo "=== 服務狀態 ==="
    docker-compose ps

    echo ""
    echo "=== 健康檢查 ==="

    for service_pair in "${services[@]}"; do
        IFS=':' read -r service container <<< "$service_pair"

        if docker-compose ps | grep $container | grep -q "healthy\|Up"; then
            echo -e "${GREEN}✓${NC} $service ($container)"
        else
            echo -e "${RED}✗${NC} $service ($container)"
            all_healthy=false
        fi
    done

    echo ""

    if [ "$all_healthy" = true ]; then
        log_success "所有核心服務都在運行"
        return 0
    else
        log_warning "部分服務未正常運行"
        return 1
    fi
}

# 函數：顯示訪問資訊
show_access_info() {
    echo ""
    echo "=========================================="
    echo "  服務訪問資訊"
    echo "=========================================="
    echo ""
    echo "🌐 Dashboard (Frontend):  http://localhost:3001"
    echo "🔌 API Server (Backend):  http://localhost:8080"
    echo "📊 Grafana (監控):        http://localhost:3000 (admin/admin)"
    echo "🔥 Prometheus:            http://localhost:9090"
    echo "🔔 Alertmanager:          http://localhost:9093"
    echo ""
    echo "📦 資料庫:"
    echo "   TimescaleDB:  localhost:5432"
    echo "   Redis:        localhost:6379"
    echo ""
    echo "=========================================="
}

# 函數：顯示日誌指令
show_log_commands() {
    echo ""
    echo "=========================================="
    echo "  常用指令"
    echo "=========================================="
    echo ""
    echo "查看所有服務日誌:"
    echo "  docker-compose logs -f"
    echo ""
    echo "查看特定服務日誌:"
    echo "  docker-compose logs -f db"
    echo "  docker-compose logs -f collector"
    echo "  docker-compose logs -f api-server"
    echo ""
    echo "重啟特定服務:"
    echo "  docker-compose restart collector"
    echo ""
    echo "停止所有服務:"
    echo "  docker-compose down"
    echo ""
    echo "查看資料庫:"
    echo "  docker exec crypto_timescaledb psql -U crypto -d crypto_db"
    echo ""
    echo "初始化資料庫:"
    echo "  ./scripts/init_database.sh"
    echo ""
    echo "=========================================="
}

# 函數：初始化資料庫
init_database() {
    log_step "初始化資料庫 ..."

    if [ -f "./scripts/init_database.sh" ]; then
        ./scripts/init_database.sh
    else
        log_warning "找不到 init_database.sh 腳本，跳過資料庫初始化"
    fi
}

# 主程式
main() {
    log_info "========================================="
    log_info "Crypto Market Analyzer - 服務啟動"
    log_info "========================================="
    echo ""

    # 檢查參數
    local rebuild=false
    local init_db=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --rebuild)
                rebuild=true
                shift
                ;;
            --init-db)
                init_db=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --rebuild     重新建構 Docker 映像"
                echo "  --init-db     初始化資料庫（執行 migrations）"
                echo "  --help        顯示此幫助訊息"
                exit 0
                ;;
            *)
                log_error "未知參數: $1"
                echo "使用 --help 查看可用選項"
                exit 1
                ;;
        esac
    done

    # 步驟 1: 檢查環境
    log_step "步驟 1/6: 檢查環境"
    check_docker
    check_env_file
    echo ""

    # 步驟 2: 停止現有服務（如果 rebuild）
    if [ "$rebuild" = true ]; then
        log_step "步驟 2/6: 停止現有服務"
        stop_all_services
        echo ""
    else
        log_step "步驟 2/6: 跳過停止服務"
        echo ""
    fi

    # 步驟 3: 啟動服務
    log_step "步驟 3/6: 啟動 Docker 服務"
    start_services "$rebuild"
    echo ""

    # 步驟 4: 等待核心服務就緒
    log_step "步驟 4/6: 等待核心服務就緒"
    wait_for_service "crypto_timescaledb" || true
    wait_for_service "crypto_redis" || true
    echo ""

    # 步驟 5: 初始化資料庫（如果需要）
    if [ "$init_db" = true ]; then
        log_step "步驟 5/6: 初始化資料庫"
        init_database
        echo ""
    else
        log_step "步驟 5/6: 跳過資料庫初始化"
        echo ""
    fi

    # 步驟 6: 檢查服務狀態
    log_step "步驟 6/6: 檢查服務狀態"
    sleep 3  # 等待服務啟動
    check_services_status

    # 顯示訪問資訊
    show_access_info
    show_log_commands

    echo ""
    log_success "========================================="
    log_success "所有服務已啟動"
    log_success "========================================="
}

# 執行主程式
main "$@"
