#!/bin/bash
# 啟動長期運行測試的主控腳本

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
TEST_ID="${1:-stability_perf_test_$(date +%Y%m%d_%H%M%S)}"
DURATION_HOURS="${2:-72}"
PROJECT_ROOT="/Users/latteine/Documents/coding/finance"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      Crypto Market Analyzer - Long Run Test Launcher     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}測試 ID:${NC} ${TEST_ID}"
echo -e "${GREEN}測試時長:${NC} ${DURATION_HOURS} 小時"
echo -e "${GREEN}專案路徑:${NC} ${PROJECT_ROOT}"
echo ""

# 切換到專案目錄
cd "${PROJECT_ROOT}"

# 步驟 1: 檢查系統狀態
echo -e "\n${YELLOW}[1/7] 檢查系統狀態...${NC}"
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${RED}錯誤: Docker 容器未運行，請先啟動系統${NC}"
    echo "執行: docker-compose up -d"
    exit 1
fi
echo -e "${GREEN}✓ 容器狀態正常${NC}"

# 步驟 2: 執行系統快照
echo -e "\n${YELLOW}[2/7] 執行測試前系統快照...${NC}"
./scripts/system_snapshot.sh "${TEST_ID}"
echo -e "${GREEN}✓ 快照完成${NC}"

# 步驟 3: 重載 Prometheus 配置（包含長期測試告警規則）
echo -e "\n${YELLOW}[3/7] 重載 Prometheus 配置...${NC}"
docker exec crypto_prometheus killall -HUP prometheus 2>/dev/null || echo "Prometheus 配置重載請求已發送"
echo -e "${GREEN}✓ Prometheus 配置重載${NC}"

# 步驟 4: 啟動告警 Webhook 服務器
echo -e "\n${YELLOW}[4/7] 啟動告警 Webhook 服務器...${NC}"
if lsof -Pi :9099 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Webhook 服務器已在運行${NC}"
else
    nohup python3 ./scripts/alert_webhook.py > monitoring/test_results/alerts/webhook.log 2>&1 &
    WEBHOOK_PID=$!
    echo $WEBHOOK_PID > monitoring/test_results/alerts/webhook.pid
    sleep 2
    if lsof -Pi :9099 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Webhook 服務器已啟動 (PID: ${WEBHOOK_PID})${NC}"
    else
        echo -e "${RED}✗ Webhook 服務器啟動失敗${NC}"
    fi
fi

# 步驟 5: 啟動監控採集
echo -e "\n${YELLOW}[5/7] 啟動監控數據採集...${NC}"
nohup python3 ./scripts/long_run_monitor.py "${TEST_ID}" "${DURATION_HOURS}" > "monitoring/test_results/${TEST_ID}/monitor.log" 2>&1 &
MONITOR_PID=$!
echo $MONITOR_PID > "monitoring/test_results/${TEST_ID}/monitor.pid"
sleep 2
if ps -p $MONITOR_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 監控採集已啟動 (PID: ${MONITOR_PID})${NC}"
else
    echo -e "${RED}✗ 監控採集啟動失敗${NC}"
    exit 1
fi

# 步驟 6: 顯示訪問資訊
echo -e "\n${YELLOW}[6/7] 系統訪問資訊${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}Grafana 儀表板:${NC}      http://localhost:3000"
echo -e "  └─ 用戶名: admin"
echo -e "  └─ 密碼: admin"
echo -e "  └─ 儀表板: Long Run Test - Stability & Performance"
echo ""
echo -e "${GREEN}Prometheus:${NC}          http://localhost:9090"
echo -e "${GREEN}Alertmanager:${NC}        http://localhost:9093"
echo ""
echo -e "${GREEN}監控日誌:${NC}            monitoring/test_results/${TEST_ID}/monitor.log"
echo -e "${GREEN}告警日誌:${NC}            monitoring/test_results/alerts/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 步驟 7: 設置定時報告生成
echo -e "\n${YELLOW}[7/7] 設置報告生成提醒${NC}"
echo ""
echo "測試將持續 ${DURATION_HOURS} 小時"
echo "預計結束時間: $(date -v+${DURATION_HOURS}H '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -d "+${DURATION_HOURS} hours" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "計算失敗")"
echo ""
echo "測試期間可以執行以下操作："
echo "  1. 即時查看監控：tail -f monitoring/test_results/${TEST_ID}/monitor.log"
echo "  2. 查看告警：tail -f monitoring/test_results/alerts/webhook.log"
echo "  3. 生成中期報告：python3 scripts/generate_test_report.py ${TEST_ID}"
echo ""

# 完成
echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            Long Run Test Started Successfully             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}提示:${NC}"
echo "  • 測試將在背景執行 ${DURATION_HOURS} 小時"
echo "  • 監控數據每 5 分鐘採集一次"
echo "  • 告警會自動記錄並顯示"
echo "  • 使用 Ctrl+C 不會中斷測試（監控在背景運行）"
echo ""
echo -e "${YELLOW}停止測試:${NC}"
echo "  kill \$(cat monitoring/test_results/${TEST_ID}/monitor.pid)"
echo "  kill \$(cat monitoring/test_results/alerts/webhook.pid)"
echo ""
echo -e "${YELLOW}測試結束後生成最終報告:${NC}"
echo "  python3 scripts/generate_test_report.py ${TEST_ID}"
echo ""
