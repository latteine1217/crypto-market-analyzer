#!/bin/bash
# 郵件功能互動式設定腳本

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 專案根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Crypto Market Analyzer - 郵件功能設定精靈            ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# 步驟 1: 檢查 .env 檔案
echo -e "${GREEN}[步驟 1/6] 檢查環境檔案${NC}"
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${YELLOW}⚠️  .env 檔案已存在${NC}"
    read -p "是否備份現有檔案？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp "$PROJECT_ROOT/.env" "$PROJECT_ROOT/.env.backup.$(date +%Y%m%d_%H%M%S)"
        echo -e "${GREEN}✓ 已備份至 .env.backup.$(date +%Y%m%d_%H%M%S)${NC}"
    fi
else
    echo "建立新的 .env 檔案..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo -e "${GREEN}✓ 已從 .env.example 建立 .env${NC}"
fi
echo

# 步驟 2: 說明如何取得 Gmail App Password
echo -e "${GREEN}[步驟 2/6] 取得 Gmail 應用程式專用密碼${NC}"
echo -e "${YELLOW}請按照以下步驟操作：${NC}\n"
echo "1. 前往 https://myaccount.google.com/security"
echo "2. 找到「登入 Google」→「兩步驟驗證」"
echo "3. 如果未啟用，請先啟用兩步驟驗證"
echo "4. 在「兩步驟驗證」頁面，找到「應用程式密碼」"
echo "5. 選擇「郵件」→「其他（自訂名稱）」"
echo "6. 輸入名稱：Crypto Market Analyzer"
echo "7. 點擊「產生」並複製 16 碼密碼（移除空格）"
echo
read -p "按 Enter 繼續（完成上述步驟後）..."
echo

# 步驟 3: 輸入郵件配置
echo -e "${GREEN}[步驟 3/6] 輸入郵件配置${NC}"
echo

# Gmail 地址
read -p "請輸入您的 Gmail 地址: " GMAIL_ADDRESS
while [[ ! "$GMAIL_ADDRESS" =~ ^[a-zA-Z0-9._%+-]+@gmail\.com$ ]]; do
    echo -e "${RED}❌ 請輸入有效的 Gmail 地址${NC}"
    read -p "請輸入您的 Gmail 地址: " GMAIL_ADDRESS
done
echo -e "${GREEN}✓ Gmail 地址: $GMAIL_ADDRESS${NC}"

# App Password
read -sp "請輸入應用程式專用密碼（16碼，不含空格）: " APP_PASSWORD
echo
while [ ${#APP_PASSWORD} -ne 16 ]; do
    echo -e "${RED}❌ 密碼應為 16 碼${NC}"
    read -sp "請輸入應用程式專用密碼（16碼，不含空格）: " APP_PASSWORD
    echo
done
echo -e "${GREEN}✓ 應用程式密碼已設定${NC}"

# 預設收件人
echo
read -p "預設收件人郵件地址（可直接按 Enter 使用 $GMAIL_ADDRESS）: " RECIPIENT_EMAIL
if [ -z "$RECIPIENT_EMAIL" ]; then
    RECIPIENT_EMAIL="$GMAIL_ADDRESS"
fi
echo -e "${GREEN}✓ 預設收件人: $RECIPIENT_EMAIL${NC}"
echo

# 步驟 4: 寫入配置
echo -e "${GREEN}[步驟 4/6] 寫入配置到 .env${NC}"

# 更新 .env 檔案
if grep -q "^SMTP_USER=" "$PROJECT_ROOT/.env"; then
    # 更新現有設定
    sed -i.bak "s|^SMTP_USER=.*|SMTP_USER=$GMAIL_ADDRESS|" "$PROJECT_ROOT/.env"
    sed -i.bak "s|^SMTP_PASSWORD=.*|SMTP_PASSWORD=$APP_PASSWORD|" "$PROJECT_ROOT/.env"
    sed -i.bak "s|^SMTP_FROM=.*|SMTP_FROM=$GMAIL_ADDRESS|" "$PROJECT_ROOT/.env"
    sed -i.bak "s|^SMTP_TO=.*|SMTP_TO=$RECIPIENT_EMAIL|" "$PROJECT_ROOT/.env"
    rm -f "$PROJECT_ROOT/.env.bak"
else
    # 新增設定
    cat >> "$PROJECT_ROOT/.env" << EOF

# ============================================
# SMTP 郵件設定（由 setup_email.sh 自動生成）
# ============================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=$GMAIL_ADDRESS
SMTP_PASSWORD=$APP_PASSWORD
SMTP_FROM=$GMAIL_ADDRESS
SMTP_TO=$RECIPIENT_EMAIL
EOF
fi

echo -e "${GREEN}✓ 配置已寫入 .env${NC}"
echo

# 步驟 5: 重啟容器
echo -e "${GREEN}[步驟 5/6] 重啟報表排程容器${NC}"
cd "$PROJECT_ROOT"

if docker-compose ps | grep -q "crypto_report_scheduler"; then
    echo "重啟 report-scheduler 容器..."
    docker-compose restart report-scheduler
    echo -e "${GREEN}✓ 容器已重啟${NC}"

    # 等待容器啟動
    echo "等待容器啟動..."
    sleep 3

    # 驗證環境變數
    echo "驗證環境變數載入..."
    if docker exec crypto_report_scheduler env | grep -q "SMTP_USER=$GMAIL_ADDRESS"; then
        echo -e "${GREEN}✓ 環境變數載入成功${NC}"
    else
        echo -e "${YELLOW}⚠️  環境變數可能未正確載入，請手動重啟：${NC}"
        echo "   docker-compose down"
        echo "   docker-compose up -d"
    fi
else
    echo -e "${YELLOW}⚠️  report-scheduler 容器未運行${NC}"
    echo "請執行：docker-compose up -d report-scheduler"
fi
echo

# 步驟 6: 測試郵件發送
echo -e "${GREEN}[步驟 6/6] 測試郵件發送${NC}"
read -p "是否立即測試郵件發送？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "執行測試..."
    echo

    # 匯出環境變數供測試腳本使用
    export SMTP_HOST=smtp.gmail.com
    export SMTP_PORT=587
    export SMTP_USER="$GMAIL_ADDRESS"
    export SMTP_PASSWORD="$APP_PASSWORD"
    export SMTP_FROM="$GMAIL_ADDRESS"
    export SMTP_TO="$RECIPIENT_EMAIL"

    # 執行測試
    python3 "$PROJECT_ROOT/scripts/test_email.py"
else
    echo "跳過測試"
    echo "您可以稍後執行：python3 scripts/test_email.py"
fi

echo
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                   設定完成！                              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

echo -e "${GREEN}✅ 郵件功能已啟用${NC}\n"

echo "配置摘要："
echo "  SMTP 伺服器: smtp.gmail.com:587"
echo "  寄件人: $GMAIL_ADDRESS"
echo "  預設收件人: $RECIPIENT_EMAIL"
echo

echo "自動排程："
echo "  每日報表: 每天 08:00 (台北時間)"
echo "  每週報表: 每週一 09:00 (台北時間)"
echo

echo "手動觸發報表："
echo "  python3 scripts/generate_daily_report.py"
echo "  python3 scripts/generate_weekly_report.py"
echo

echo "查看排程器日誌："
echo "  docker logs crypto_report_scheduler -f"
echo
