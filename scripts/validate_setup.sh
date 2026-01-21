#!/bin/bash
# ============================================
# 專案設置驗證腳本
# 目的：在啟動前檢查所有必要配置
# Usage: ./scripts/validate_setup.sh
# ============================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

log_error() {
    echo -e "${RED}✗${NC} $1"
    ERRORS=$((ERRORS + 1))
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

echo "=========================================="
echo "專案設置驗證"
echo "=========================================="
echo ""

# 檢查 1: Docker 環境
echo "📦 檢查 Docker 環境..."
if command -v docker &> /dev/null; then
    log_success "Docker 已安裝: $(docker --version | head -1)"

    if docker info &> /dev/null; then
        log_success "Docker daemon 運行中"
    else
        log_error "Docker daemon 未運行，請啟動 Docker"
    fi
else
    log_error "Docker 未安裝"
fi

if command -v docker-compose &> /dev/null; then
    log_success "Docker Compose 已安裝: $(docker-compose --version | head -1)"
else
    log_error "Docker Compose 未安裝"
fi

# 檢查 2: 環境變數檔案
echo ""
echo "🔐 檢查環境變數..."
if [ -f ".env" ]; then
    log_success ".env 檔案存在"

    # 檢查必要變數
    REQUIRED_VARS=(
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" .env; then
            log_success "$var 已設定"
        else
            log_warning "$var 未在 .env 中設定（將使用預設值）"
        fi
    done
else
    log_warning ".env 檔案不存在（將使用 .env.example 的預設值）"
    if [ -f ".env.example" ]; then
        log_info "可執行: cp .env.example .env"
    fi
fi

# 檢查 3: 資料庫 Schema 與 Migrations
echo ""
echo "🗄️  檢查資料庫設置..."

if [ -f "database/schemas/00_v3_optimized.sql" ]; then
    log_success "基礎 schema 存在"
else
    log_error "基礎 schema 不存在: database/schemas/00_v3_optimized.sql"
fi

if [ -f "database/schemas/01_apply_migrations.sh" ]; then
    log_success "自動初始化腳本存在"

    if [ -x "database/schemas/01_apply_migrations.sh" ]; then
        log_success "初始化腳本可執行"
    else
        log_warning "初始化腳本不可執行"
        log_info "執行: chmod +x database/schemas/01_apply_migrations.sh"
    fi
else
    log_error "自動初始化腳本不存在"
fi

MIGRATION_COUNT=$(ls -1 database/migrations/*.sql 2>/dev/null | wc -l | tr -d ' ')
if [ "$MIGRATION_COUNT" -gt 0 ]; then
    log_success "找到 $MIGRATION_COUNT 個 migration 檔案"
else
    log_warning "沒有找到 migration 檔案"
fi

# 檢查 4: Node.js 專案依賴同步
echo ""
echo "📦 檢查 Node.js 依賴..."

check_npm_sync() {
    local dir=$1
    local name=$2

    if [ -f "$dir/package.json" ]; then
        if [ -f "$dir/package-lock.json" ]; then
            log_success "$name: package-lock.json 存在"

            # 檢查是否同步（簡化版）
            if [ "$dir/node_modules" ]; then
                log_info "$name: node_modules 存在（建議執行 npm install 確保同步）"
            fi
        else
            log_warning "$name: package-lock.json 不存在"
            log_info "執行: cd $dir && npm install"
        fi
    fi
}

check_npm_sync "data-collector" "data-collector"
check_npm_sync "api-server" "api-server"
check_npm_sync "dashboard-ts" "dashboard-ts"

# 檢查 5: Python 環境
echo ""
echo "🐍 檢查 Python 環境..."

if command -v python3 &> /dev/null; then
    log_success "Python 3 已安裝: $(python3 --version)"
else
    log_warning "Python 3 未安裝"
fi

if [ -f "collector-py/requirements.txt" ]; then
    log_success "Python requirements.txt 存在"
else
    log_error "Python requirements.txt 不存在"
fi

# 檢查 6: Git Hooks
echo ""
echo "🪝 檢查 Git Hooks..."

if [ -f ".githooks/pre-commit" ]; then
    log_success "Pre-commit hook 模板存在"

    if [ -f ".git/hooks/pre-commit" ]; then
        log_success "Pre-commit hook 已安裝"
    else
        log_warning "Pre-commit hook 未安裝"
        log_info "執行: cp .githooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit"
    fi
else
    log_warning "Pre-commit hook 模板不存在"
fi

# 檢查 7: 重要目錄結構
echo ""
echo "📁 檢查目錄結構..."

REQUIRED_DIRS=(
    "database/schemas"
    "database/migrations"
    "collector-py/src"
    "data-collector/src"
    "api-server/src"
    "dashboard-ts/src"
    "shared"
    "configs/collector"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        log_success "$dir/"
    else
        log_error "目錄不存在: $dir/"
    fi
done

# 總結
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有檢查通過！專案設置完整。${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  發現 $WARNINGS 個警告，但可以繼續。${NC}"
else
    echo -e "${RED}❌ 發現 $ERRORS 個錯誤，$WARNINGS 個警告。${NC}"
    echo -e "${RED}請修復錯誤後再啟動專案。${NC}"
    exit 1
fi
echo "=========================================="
