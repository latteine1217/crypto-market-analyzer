#!/bin/bash
# 測試所有服務狀態

echo "========================================="
echo "🧪 測試服務狀態"
echo "========================================="
echo

# 測試資料庫
echo "📊 TimescaleDB:"
docker exec crypto_timescaledb psql -U crypto -d crypto_db -c "SELECT COUNT(*) as market_count FROM markets;" 2>/dev/null && echo "✅ 資料庫正常" || echo "❌ 資料庫異常"
echo

# 測試 Redis
echo "🔴 Redis:"
docker exec crypto_redis redis-cli ping 2>/dev/null && echo "✅ Redis 正常" || echo "❌ Redis 異常"
echo

# 測試 API Server
echo "🚀 API Server (port 8080):"
if curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "✅ API Server 正常"
    echo "   Health: $(curl -s http://localhost:8080/health | jq -r '.status')"
else
    echo "❌ API Server 異常"
fi
echo

# 測試 Dashboard
echo "📈 Dashboard (port 3001):"
if lsof -i :3001 >/dev/null 2>&1; then
    echo "✅ Dashboard 正常運行"
    echo "   URL: http://localhost:3001"
else
    echo "❌ Dashboard 未運行"
fi
echo

# 測試 API 端點
echo "🔍 測試 API 端點:"
echo "   Markets: $(curl -s http://localhost:8080/api/markets | jq '.data | length') markets"
echo "   BTCUSDT Price: $(curl -s 'http://localhost:8080/api/ohlcv/binance/BTCUSDT?limit=1' | jq -r '.data[0].close')"
echo

echo "========================================="
echo "✅ 測試完成"
echo "========================================="
