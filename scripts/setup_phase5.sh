#!/bin/bash

# ============================================
# 階段5報表系統設置腳本
# ============================================

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 專案根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  階段5報表系統 - 自動設置腳本                   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================
# 1. 檢查環境變數
# ============================================

echo -e "${YELLOW}[1/5]${NC} 檢查環境變數..."

# 資料庫配置
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-crypto_db}
DB_USER=${DB_USER:-crypto}
DB_PASSWORD=${DB_PASSWORD:-crypto_pass}

echo "  資料庫配置:"
echo "    Host: $DB_HOST:$DB_PORT"
echo "    Database: $DB_NAME"
echo "    User: $DB_USER"

# 郵件配置（選用）
if [ -n "$SMTP_USER" ] && [ -n "$SMTP_PASSWORD" ]; then
    echo -e "  ${GREEN}✓${NC} SMTP 配置已設定: $SMTP_USER"
    HAS_EMAIL=true
else
    echo -e "  ${YELLOW}⚠${NC} SMTP 配置未設定（郵件功能將無法使用）"
    HAS_EMAIL=false
fi

echo ""

# ============================================
# 2. 安裝 Python 依賴
# ============================================

echo -e "${YELLOW}[2/5]${NC} 安裝 Python 依賴..."

cd data-analyzer

if [ -f "requirements.txt" ]; then
    echo "  安裝套件..."
    pip install -r requirements.txt -q
    echo -e "  ${GREEN}✓${NC} 依賴安裝完成"
else
    echo -e "  ${RED}✗${NC} requirements.txt 不存在"
    exit 1
fi

cd "$PROJECT_ROOT"
echo ""

# ============================================
# 3. 執行資料庫遷移
# ============================================

echo -e "${YELLOW}[3/5]${NC} 執行資料庫遷移..."

# 檢查 PostgreSQL 是否可連接
if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\q' 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} 資料庫連接成功"

    # 執行遷移
    MIGRATION_FILE="database/migrations/005_report_logs.sql"

    if [ -f "$MIGRATION_FILE" ]; then
        echo "  執行遷移: $MIGRATION_FILE"
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$MIGRATION_FILE" -q

        # 驗證表是否創建成功
        TABLE_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc \
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'report_generation_logs')")

        if [ "$TABLE_EXISTS" = "t" ]; then
            echo -e "  ${GREEN}✓${NC} report_generation_logs 表創建成功"
        else
            echo -e "  ${RED}✗${NC} 表創建失敗"
            exit 1
        fi
    else
        echo -e "  ${RED}✗${NC} 遷移檔案不存在: $MIGRATION_FILE"
        exit 1
    fi
else
    echo -e "  ${RED}✗${NC} 無法連接資料庫"
    echo "  請確認 TimescaleDB 正在運行且環境變數正確"
    exit 1
fi

echo ""

# ============================================
# 4. 建立必要目錄
# ============================================

echo -e "${YELLOW}[4/5]${NC} 建立必要目錄..."

DIRS=(
    "reports/daily"
    "reports/weekly"
    "reports/monthly"
    "reports/test"
    "data-analyzer/models/registry"
    "results/backtest_reports"
)

for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "  建立: $dir"
    fi
done

echo -e "  ${GREEN}✓${NC} 目錄結構建立完成"
echo ""

# ============================================
# 5. 執行測試
# ============================================

echo -e "${YELLOW}[5/5]${NC} 執行系統測試..."

cd data-analyzer

# 設定測試環境變數
export DB_HOST=$DB_HOST
export DB_PORT=$DB_PORT
export DB_NAME=$DB_NAME
export DB_USER=$DB_USER
export DB_PASSWORD=$DB_PASSWORD

if [ "$HAS_EMAIL" = true ]; then
    export SMTP_USER=$SMTP_USER
    export SMTP_PASSWORD=$SMTP_PASSWORD
fi

# 執行測試（不發送郵件）
echo "  執行基礎測試..."
python test_report_system.py

echo ""

# ============================================
# 完成
# ============================================

echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ 階段5報表系統設置完成！                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

echo "📋 下一步操作："
echo ""
echo "1. 生成報表："
echo "   cd data-analyzer"
echo "   python -c \"from reports.report_agent import ReportAgent; agent = ReportAgent(); agent.generate_daily_report()\""
echo ""
echo "2. 查看 Dashboard："
echo "   open ../dashboard/static/reports_dashboard.html"
echo ""
echo "3. 測試郵件發送（需設定 SMTP）："
echo "   export TEST_EMAIL_SEND=true"
echo "   export TEST_EMAIL_TO='felix.tc.tw@gmail.com'"
echo "   python test_report_system.py"
echo ""

if [ "$HAS_EMAIL" = false ]; then
    echo -e "${YELLOW}💡 提示：要啟用郵件功能，請設定以下環境變數：${NC}"
    echo "   export SMTP_USER='felix.tc.tw@gmail.com'"
    echo "   export SMTP_PASSWORD='your-gmail-app-password'"
    echo ""
    echo "   Gmail App Password 設定："
    echo "   1. 登入 Google 帳號 → 安全性"
    echo "   2. 啟用兩步驟驗證"
    echo "   3. 建立「應用程式密碼」"
    echo ""
fi

echo "📚 詳細文件："
echo "   - 使用說明: data-analyzer/REPORT_USAGE.md"
echo "   - 完成報告: data-analyzer/PHASE5_COMPLETE.md"
echo ""
