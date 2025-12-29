#!/bin/bash
# 啟動資料保留策略監控服務

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "啟動資料保留策略監控服務"
echo "========================================"

# 檢查環境變數
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "錯誤：找不到 .env 檔案"
    exit 1
fi

# 載入環境變數
set -a
source "$PROJECT_ROOT/.env"
set +a

# 設定Python路徑
export PYTHONPATH="$PROJECT_ROOT/collector-py/src:$PYTHONPATH"

# 設定日誌目錄
mkdir -p "$PROJECT_ROOT/logs"

# 設定預設值
export RETENTION_MONITOR_METRICS_PORT="${RETENTION_MONITOR_METRICS_PORT:-8003}"
export RETENTION_CHECK_INTERVAL_MINUTES="${RETENTION_CHECK_INTERVAL_MINUTES:-30}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

echo ""
echo "配置："
echo "  - Metrics Port: $RETENTION_MONITOR_METRICS_PORT"
echo "  - Check Interval: $RETENTION_CHECK_INTERVAL_MINUTES 分鐘"
echo "  - Log Level: $LOG_LEVEL"
echo "  - Database: $DB_HOST:$DB_PORT/$DB_NAME"
echo ""

# 啟動監控服務
cd "$PROJECT_ROOT"

python3 "$SCRIPT_DIR/run_retention_monitor.py"
