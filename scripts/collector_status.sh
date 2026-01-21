#!/bin/bash

# ============================================
# Collector 狀態檢查腳本
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/collector.pid"
LOG_FILE="$LOG_DIR/collector.log"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Collector 運行狀態 ===${NC}"
echo ""

# 檢查 PID 檔案
if [ ! -f "$PID_FILE" ]; then
    echo -e "${RED}✗ Collector 未運行${NC}"
    echo ""
    echo -e "${YELLOW}啟動指令: ./scripts/start_collector_background.sh${NC}"
    exit 1
fi

PID=$(cat "$PID_FILE")

# 檢查進程
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${RED}✗ Collector 進程已終止 (PID: $PID)${NC}"
    rm -f "$PID_FILE"
    exit 1
fi

# 顯示狀態
echo -e "${GREEN}✓ Collector 運行中${NC}"
echo -e "${BLUE}  PID: $PID${NC}"
echo -e "${BLUE}  運行時間:${NC} $(ps -p $PID -o etime= | tr -d ' ')"
echo -e "${BLUE}  CPU: $(ps -p $PID -o %cpu= | tr -d ' ')%${NC}"
echo -e "${BLUE}  記憶體: $(ps -p $PID -o %mem= | tr -d ' ')%${NC}"
echo ""

# 資料庫統計
echo -e "${BLUE}=== 資料庫統計 ===${NC}"
docker exec crypto_timescaledb psql -U crypto -d crypto_db -t -c "
SELECT
    '  OHLCV 資料筆數: ' || COUNT(*)
FROM ohlcv;
" 2>/dev/null || echo -e "${RED}  ✗ 無法連線資料庫${NC}"

docker exec crypto_timescaledb psql -U crypto -d crypto_db -t -c "
SELECT
    '  最新資料時間: ' || MAX(time)
FROM ohlcv;
" 2>/dev/null

echo ""

# 最近日誌
echo -e "${BLUE}=== 最近日誌 (最後 10 行) ===${NC}"
if [ -f "$LOG_FILE" ]; then
    tail -10 "$LOG_FILE"
else
    echo -e "${YELLOW}  日誌檔案不存在${NC}"
fi

echo ""
echo -e "${YELLOW}管理指令：${NC}"
echo "  查看完整日誌: tail -f $LOG_FILE"
echo "  停止服務: ./scripts/stop_collector.sh"
echo "  重啟服務: ./scripts/stop_collector.sh && ./scripts/start_collector_background.sh"
