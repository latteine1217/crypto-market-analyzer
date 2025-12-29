#!/bin/bash
# 停止長期運行測試

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TEST_ID="${1}"

if [ -z "${TEST_ID}" ]; then
    echo -e "${RED}錯誤: 請提供測試 ID${NC}"
    echo "使用方式: ./scripts/stop_long_run_test.sh <test_id>"
    exit 1
fi

echo -e "${YELLOW}正在停止測試: ${TEST_ID}${NC}"
echo ""

# 停止監控採集
if [ -f "monitoring/test_results/${TEST_ID}/monitor.pid" ]; then
    MONITOR_PID=$(cat "monitoring/test_results/${TEST_ID}/monitor.pid")
    if ps -p $MONITOR_PID > /dev/null 2>&1; then
        kill $MONITOR_PID
        echo -e "${GREEN}✓ 監控採集已停止${NC}"
    else
        echo -e "${YELLOW}⚠ 監控採集進程未運行${NC}"
    fi
    rm "monitoring/test_results/${TEST_ID}/monitor.pid"
else
    echo -e "${YELLOW}⚠ 找不到監控 PID 檔案${NC}"
fi

# 停止 Webhook 服務器
if [ -f "monitoring/test_results/alerts/webhook.pid" ]; then
    WEBHOOK_PID=$(cat "monitoring/test_results/alerts/webhook.pid")
    if ps -p $WEBHOOK_PID > /dev/null 2>&1; then
        kill $WEBHOOK_PID
        echo -e "${GREEN}✓ Webhook 服務器已停止${NC}"
    else
        echo -e "${YELLOW}⚠ Webhook 服務器未運行${NC}"
    fi
    rm "monitoring/test_results/alerts/webhook.pid"
fi

# 執行測試後快照
echo ""
echo -e "${YELLOW}執行測試後系統快照...${NC}"
./scripts/system_snapshot.sh "${TEST_ID}_end"

# 生成最終報告
echo ""
echo -e "${YELLOW}生成測試報告...${NC}"
python3 scripts/generate_test_report.py "${TEST_ID}"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Test Stopped & Report Generated              ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}測試報告位置:${NC}"
echo "  monitoring/test_results/${TEST_ID}/test_report.html"
echo ""
echo -e "${YELLOW}在瀏覽器中打開:${NC}"
echo "  open monitoring/test_results/${TEST_ID}/test_report.html"
echo ""
