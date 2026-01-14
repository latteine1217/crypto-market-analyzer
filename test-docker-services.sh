#!/bin/bash
# Docker 容器完整測試腳本

echo "========================================="
echo "🐳 Docker 容器狀態檢查"
echo "========================================="
echo

# 檢查所有容器狀態
echo "📦 容器列表:"
docker-compose ps
echo

# 測試 API Server
echo "========================================="
echo "🚀 API Server 測試"
echo "========================================="

echo "1. 健康檢查:"
HEALTH=$(curl -s http://localhost:8080/health | jq -r '.status')
if [ "$HEALTH" = "ok" ]; then
    echo "   ✅ API Server 健康狀態: $HEALTH"
else
    echo "   ❌ API Server 健康狀態異常"
fi

echo "2. Markets 端點:"
MARKET_COUNT=$(curl -s http://localhost:8080/api/markets | jq -r '.data | length')
echo "   ✅ 市場數量: $MARKET_COUNT markets"

echo "3. OHLCV 端點:"
BTC_PRICE=$(curl -s "http://localhost:8080/api/ohlcv/binance/BTCUSDT?limit=1" | jq -r '.data[0].close')
echo "   ✅ BTC 價格: \$$BTC_PRICE"

echo "4. Market Prices 端點:"
PRICE_COUNT=$(curl -s http://localhost:8080/api/markets/prices | jq -r '.data | length')
echo "   ✅ 價格資料: $PRICE_COUNT symbols"

# 測試 Dashboard
echo
echo "========================================="
echo "📊 Dashboard 測試"
echo "========================================="

DASHBOARD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001)
if [ "$DASHBOARD_STATUS" = "200" ]; then
    echo "   ✅ Dashboard 首頁: HTTP $DASHBOARD_STATUS"
else
    echo "   ❌ Dashboard 首頁: HTTP $DASHBOARD_STATUS"
fi

# 測試容器間網路
echo
echo "========================================="
echo "🌐 容器間網路測試"
echo "========================================="

INTERNAL_HEALTH=$(docker exec crypto_dashboard_ts wget -q -O- http://api-server:8080/health 2>/dev/null | jq -r '.status')
if [ "$INTERNAL_HEALTH" = "ok" ]; then
    echo "   ✅ Dashboard → API Server: 連接正常"
else
    echo "   ❌ Dashboard → API Server: 連接失敗"
fi

# 檢查容器日誌
echo
echo "========================================="
echo "📝 最新日誌 (最近 5 行)"
echo "========================================="

echo
echo "API Server:"
docker logs crypto_api_server --tail 5
echo
echo "Dashboard:"
docker logs crypto_dashboard_ts --tail 5

# 檢查資源使用
echo
echo "========================================="
echo "💻 資源使用狀況"
echo "========================================="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
  crypto_api_server crypto_dashboard_ts crypto_timescaledb crypto_redis

echo
echo "========================================="
echo "✅ 測試完成"
echo "========================================="
echo
echo "🔗 服務訪問地址:"
echo "   API Server:  http://localhost:8080"
echo "   Dashboard:   http://localhost:3001"
echo "   Grafana:     http://localhost:3000"
echo "   Prometheus:  http://localhost:9090"
echo
