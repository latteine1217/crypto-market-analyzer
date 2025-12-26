#!/bin/bash

# ============================================
# Collector 停止腳本
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/collector.pid"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== 停止 Collector ===${NC}"

if [ ! -f "$PID_FILE" ]; then
    echo -e "${RED}✗ Collector 未在運行（找不到 PID 檔案）${NC}"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Collector 進程不存在 (PID: $PID)${NC}"
    rm -f "$PID_FILE"
    exit 0
fi

echo -e "${YELLOW}正在停止 Collector (PID: $PID)...${NC}"
kill "$PID"

# 等待進程結束
WAIT_TIME=0
while ps -p "$PID" > /dev/null 2>&1 && [ $WAIT_TIME -lt 10 ]; do
    sleep 1
    ((WAIT_TIME++))
done

if ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}進程未響應，強制終止...${NC}"
    kill -9 "$PID"
    sleep 1
fi

rm -f "$PID_FILE"
echo -e "${GREEN}✓ Collector 已停止${NC}"
