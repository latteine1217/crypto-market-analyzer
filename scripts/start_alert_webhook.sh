#!/bin/bash
# 啟動 Alert Webhook Handler

set -e

echo "=== Starting Alert Webhook Handler ==="

# 載入環境變數
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✓ Loaded .env"
fi

# 設定預設值
export ALERT_WEBHOOK_PORT=${ALERT_WEBHOOK_PORT:-9100}
export ALERT_CHART_DIR=${ALERT_CHART_DIR:-/tmp/alert_charts}
export ALERT_LOG_DIR=${ALERT_LOG_DIR:-/tmp/alert_logs}

# 創建目錄
mkdir -p "$ALERT_CHART_DIR"
mkdir -p "$ALERT_LOG_DIR"

echo "Configuration:"
echo "  Port: $ALERT_WEBHOOK_PORT"
echo "  Chart Dir: $ALERT_CHART_DIR"
echo "  Log Dir: $ALERT_LOG_DIR"
echo "  Email: ${SMTP_USER:-Not configured}"

# 啟動服務
cd "$(dirname "$0")/.."
python3 collector-py/src/monitors/alert_webhook_handler.py
