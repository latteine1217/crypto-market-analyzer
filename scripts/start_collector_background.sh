#!/bin/bash

# ============================================
# Collector 背景啟動腳本
# 用途：在背景啟動資料收集服務
# ============================================

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COLLECTOR_DIR="$PROJECT_ROOT/collector-py"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/collector.pid"
LOG_FILE="$LOG_DIR/collector.log"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 創建 log 目錄
mkdir -p "$LOG_DIR"

echo -e "${BLUE}=== Crypto Market Data Collector - Background Mode ===${NC}"

# 檢查是否已在運行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Collector 已在運行中 (PID: $OLD_PID)${NC}"
        echo -e "${YELLOW}如需重啟，請先執行: ./scripts/stop_collector.sh${NC}"
        exit 1
    else
        echo -e "${YELLOW}移除過期的 PID 檔案${NC}"
        rm -f "$PID_FILE"
    fi
fi

# 檢查環境
if [ ! -f "$COLLECTOR_DIR/.env" ]; then
    echo -e "${RED}✗ .env 檔案不存在${NC}"
    exit 1
fi

# 檢查 Python 依賴
echo -e "${GREEN}檢查 Python 依賴...${NC}"
if ! python3 -c "import ccxt, psycopg2, loguru" 2>/dev/null; then
    echo -e "${YELLOW}安裝依賴...${NC}"
    pip3 install -q -r "$COLLECTOR_DIR/requirements.txt"
fi

# 啟動 collector
echo -e "${GREEN}啟動 Collector...${NC}"
cd "$COLLECTOR_DIR"

nohup python3 src/main.py > "$LOG_FILE" 2>&1 &
COLLECTOR_PID=$!

# 儲存 PID
echo "$COLLECTOR_PID" > "$PID_FILE"

# 等待啟動
sleep 2

# 檢查是否成功啟動
if ps -p "$COLLECTOR_PID" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Collector 已成功啟動${NC}"
    echo -e "${BLUE}  PID: $COLLECTOR_PID${NC}"
    echo -e "${BLUE}  日誌: $LOG_FILE${NC}"
    echo ""
    echo -e "${YELLOW}管理指令：${NC}"
    echo "  查看日誌: tail -f $LOG_FILE"
    echo "  停止服務: ./scripts/stop_collector.sh"
    echo "  查看狀態: ./scripts/collector_status.sh"
    echo ""

    # 顯示最初幾行日誌
    echo -e "${BLUE}=== 初始日誌 ===${NC}"
    sleep 1
    tail -20 "$LOG_FILE"
else
    echo -e "${RED}✗ Collector 啟動失敗${NC}"
    echo -e "${YELLOW}查看日誌以了解詳情: cat $LOG_FILE${NC}"
    rm -f "$PID_FILE"
    exit 1
fi
