#!/bin/bash

# ============================================
# 環境配置驗證腳本
# 用途：檢查所有 .env 檔案是否正確設定
# ============================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=== 環境配置驗證 ===${NC}\n"

# 檢查 .env 檔案是否存在
check_env_file() {
    local file=$1
    local name=$2

    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $name: 存在"
        return 0
    else
        echo -e "${RED}✗${NC} $name: 不存在"
        return 1
    fi
}

# 驗證環境變數
validate_env_var() {
    local file=$1
    local var_name=$2
    local required=$3

    if [ -f "$file" ]; then
        value=$(grep "^${var_name}=" "$file" | cut -d'=' -f2- | tr -d ' ')

        if [ -z "$value" ]; then
            if [ "$required" = "true" ]; then
                echo -e "  ${RED}✗${NC} $var_name: 未設定（必填）"
                return 1
            else
                echo -e "  ${YELLOW}⚠${NC} $var_name: 未設定（可選）"
                return 0
            fi
        else
            echo -e "  ${GREEN}✓${NC} $var_name: 已設定"
            return 0
        fi
    fi
}

errors=0

# ===== 檢查根目錄 .env =====
echo -e "${BLUE}1. 根目錄 .env (Docker Compose)${NC}"
if check_env_file "$PROJECT_ROOT/.env" "根目錄 .env"; then
    validate_env_var "$PROJECT_ROOT/.env" "POSTGRES_USER" true || ((errors++))
    validate_env_var "$PROJECT_ROOT/.env" "POSTGRES_PASSWORD" true || ((errors++))
    validate_env_var "$PROJECT_ROOT/.env" "POSTGRES_DB" true || ((errors++))
else
    ((errors++))
fi
echo ""

# ===== 檢查 collector-py/.env =====
echo -e "${BLUE}2. collector-py/.env${NC}"
if check_env_file "$PROJECT_ROOT/collector-py/.env" "collector-py/.env"; then
    validate_env_var "$PROJECT_ROOT/collector-py/.env" "POSTGRES_HOST" true || ((errors++))
    validate_env_var "$PROJECT_ROOT/collector-py/.env" "POSTGRES_PASSWORD" true || ((errors++))
    validate_env_var "$PROJECT_ROOT/collector-py/.env" "BINANCE_API_KEY" false
    validate_env_var "$PROJECT_ROOT/collector-py/.env" "LOG_LEVEL" true || ((errors++))
else
    ((errors++))
fi
echo ""

# ===== 檢查 data-analyzer/.env =====
echo -e "${BLUE}3. data-analyzer/.env${NC}"
if check_env_file "$PROJECT_ROOT/data-analyzer/.env" "data-analyzer/.env"; then
    validate_env_var "$PROJECT_ROOT/data-analyzer/.env" "POSTGRES_HOST" true || ((errors++))
    validate_env_var "$PROJECT_ROOT/data-analyzer/.env" "RANDOM_SEED" true || ((errors++))
else
    ((errors++))
fi
echo ""

# ===== 檢查 Docker 服務 =====
echo -e "${BLUE}4. Docker 服務狀態${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker 已安裝"

    if docker ps &> /dev/null; then
        echo -e "${GREEN}✓${NC} Docker daemon 運行中"

        # 檢查容器是否運行
        if docker ps --format '{{.Names}}' | grep -q "crypto_timescaledb"; then
            echo -e "${GREEN}✓${NC} TimescaleDB 容器運行中"
        else
            echo -e "${YELLOW}⚠${NC} TimescaleDB 容器未運行（執行 docker-compose up -d 啟動）"
        fi

        if docker ps --format '{{.Names}}' | grep -q "crypto_redis"; then
            echo -e "${GREEN}✓${NC} Redis 容器運行中"
        else
            echo -e "${YELLOW}⚠${NC} Redis 容器未運行（執行 docker-compose up -d 啟動）"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Docker daemon 未運行"
    fi
else
    echo -e "${YELLOW}⚠${NC} Docker 未安裝"
fi
echo ""

# ===== 總結 =====
echo -e "${BLUE}=== 驗證總結 ===${NC}"
if [ $errors -eq 0 ]; then
    echo -e "${GREEN}✓ 所有必要配置都已正確設定${NC}"
    echo ""
    echo -e "${BLUE}下一步：${NC}"
    echo "  1. 啟動 Docker 服務: docker-compose up -d"
    echo "  2. 初始化資料庫: docker exec crypto_timescaledb psql -U crypto -d crypto_db -f /docker-entrypoint-initdb.d/01_init.sql"
    echo "  3. 啟動 Collector: ./scripts/run_collector.sh"
    exit 0
else
    echo -e "${RED}✗ 發現 $errors 個配置問題，請修正後重新執行${NC}"
    exit 1
fi
