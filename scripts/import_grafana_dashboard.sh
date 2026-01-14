#!/bin/bash
# 自動導入 BTC 地址分層追蹤 Dashboard 到 Grafana

set -e

GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASS="admin"
DASHBOARD_FILE="/Users/latteine/Documents/coding/finance/monitoring/grafana/dashboards/btc_address_tiers.json"

echo "=========================================="
echo "導入 BTC 地址分層追蹤 Dashboard"
echo "=========================================="
echo ""

# 1. 檢查 Grafana 是否在運行
echo "📝 檢查 Grafana 狀態..."
if ! docker ps | grep -q crypto_grafana; then
    echo "❌ Grafana 未運行"
    echo "   請執行: docker-compose up -d grafana"
    exit 1
fi
echo "✅ Grafana 正在運行"

# 2. 檢查 Dashboard 檔案是否存在
if [ ! -f "$DASHBOARD_FILE" ]; then
    echo "❌ Dashboard 檔案不存在: $DASHBOARD_FILE"
    exit 1
fi
echo "✅ Dashboard 檔案存在"

# 3. 等待 Grafana 完全啟動
echo ""
echo "📝 等待 Grafana 完全啟動..."
sleep 3

# 4. 使用 Grafana API 導入 Dashboard
echo ""
echo "📝 導入 Dashboard..."

# 準備 payload
DASHBOARD_JSON=$(cat "$DASHBOARD_FILE")
PAYLOAD=$(cat <<EOJ
{
  "dashboard": $DASHBOARD_JSON,
  "overwrite": true,
  "message": "Imported via script"
}
EOJ
)

# 發送 API 請求
RESPONSE=$(curl -s -X POST "$GRAFANA_URL/api/dashboards/db" \
    -H "Content-Type: application/json" \
    -u "$GRAFANA_USER:$GRAFANA_PASS" \
    -d "$PAYLOAD")

# 檢查結果
if echo "$RESPONSE" | grep -q "success"; then
    DASHBOARD_UID=$(echo "$RESPONSE" | grep -o '"uid":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Dashboard 導入成功！"
    echo ""
    echo "Dashboard 資訊:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo ""
    echo "=========================================="
    echo "✅ 完成"
    echo "=========================================="
    echo ""
    echo "存取 Dashboard:"
    echo "  URL: $GRAFANA_URL/d/$DASHBOARD_UID"
    echo ""
    echo "或從 Grafana 主頁:"
    echo "  1. 打開 $GRAFANA_URL"
    echo "  2. 登入 (admin/admin)"
    echo "  3. Dashboards → BTC Address Tier Tracking"
    echo ""
else
    echo "❌ Dashboard 導入失敗"
    echo ""
    echo "錯誤訊息:"
    echo "$RESPONSE"
    echo ""
    echo "手動導入步驟:"
    echo "  1. 打開 $GRAFANA_URL"
    echo "  2. 登入 (admin/admin)"
    echo "  3. 點擊 + → Import"
    echo "  4. Upload JSON file: $DASHBOARD_FILE"
    exit 1
fi
