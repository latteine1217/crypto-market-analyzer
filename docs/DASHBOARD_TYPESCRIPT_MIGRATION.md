# Dashboard TypeScript 遷移指南

## 概述

本專案已完成從 Python Dash 到 TypeScript (Next.js + Express) 的全面重寫。

## 架構變更

### 舊架構 (Python Dash)
```
Python Dash (dashboard/) → TimescaleDB + Redis
├─ 單一 Python 服務
├─ Plotly 圖表
└─ 端口: 8050
```

### 新架構 (TypeScript)
```
Next.js Frontend (dashboard-ts:3000)
           ↓ REST API
Express API Server (api-server:8080)
           ↓
    TimescaleDB + Redis
```

## 快速啟動

### 方法 1: Docker Compose (推薦)

```bash
# 啟動新版 Dashboard (TypeScript)
docker-compose up -d api-server dashboard-ts

# 檢查狀態
docker-compose ps

# 訪問
# - Dashboard: http://localhost:3000
# - API Server: http://localhost:8080
# - API Health: http://localhost:8080/health
```

### 方法 2: 本地開發

#### Terminal 1 - API Server
```bash
cd api-server
cp .env.example .env
npm install
npm run dev
```

#### Terminal 2 - Dashboard
```bash
cd dashboard-ts
cp .env.example .env
npm install
npm run dev
```

## 功能對照表

| 功能 | 舊版 (Dash) | 新版 (TypeScript) | 狀態 |
|------|------------|------------------|------|
| Market Overview | ✅ | ✅ | 完成 |
| Technical Analysis | ✅ | ✅ | 完成 |
| Candlestick Chart | ✅ | ✅ | 完成 |
| MACD Indicator | ✅ | ✅ | 完成 |
| Moving Averages | ✅ | ✅ | 完成 |
| RSI | ✅ | ✅ | 完成 |
| Williams Fractals | ✅ | ✅ | 完成 |
| Liquidity Analysis | ✅ | 🟡 | 框架已建立 |
| Multi-Exchange | ❌ | ✅ | 新增功能 |
| Multi-Symbol | ❌ | ✅ | 新增功能 |
| Real-time Updates | ✅ (1s) | ✅ (5s) | 完成 |
| Redis Caching | ✅ | ✅ | 完成 |

## API 端點

### Markets
- `GET /api/markets` - 取得所有市場
- `GET /api/markets/prices` - 取得最新價格

### OHLCV
- `GET /api/ohlcv/:exchange/:symbol?timeframe=1m&limit=500`
- `GET /api/ohlcv/:exchange/:symbol/summary`

### Orderbook
- `GET /api/orderbook/:exchange/:symbol?limit=100`
- `GET /api/orderbook/:exchange/:symbol/latest`

## 環境變數

### API Server (.env)
```env
PORT=8080
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_db
POSTGRES_USER=crypto
POSTGRES_PASSWORD=crypto_pass
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_TTL=5
ENABLE_CACHE=true
```

### Dashboard (.env)
```env
NEXT_PUBLIC_API_URL=http://localhost:8080
```

## 遷移步驟

### 選項 A: 完全切換到新版
```bash
# 停止舊版
docker-compose stop dashboard

# 啟動新版
docker-compose up -d api-server dashboard-ts
```

### 選項 B: 並行運行 (測試期)
```bash
# 同時運行兩個版本
docker-compose up -d dashboard api-server dashboard-ts

# 訪問
# - 舊版: http://localhost:8050
# - 新版: http://localhost:3000
```

### 選項 C: 完全移除舊版
```bash
# 停用舊版並移除容器
docker-compose rm -s dashboard

# 只啟動新版
docker-compose up -d api-server dashboard-ts
```

## 常見問題

### Q: 新版 Dashboard 無法連接 API
**A**: 檢查 `dashboard-ts/.env` 中的 `NEXT_PUBLIC_API_URL` 設置

### Q: API 回應緩慢
**A**: 確認 Redis 正常運行，檢查 `ENABLE_CACHE=true`

### Q: 圖表無法顯示
**A**: 打開瀏覽器開發者工具檢查 Console 錯誤

### Q: 想同時使用兩個版本
**A**: 使用選項 B，兩個版本在不同端口運行

## 效能比較

| 指標 | 舊版 (Dash) | 新版 (TypeScript) |
|------|------------|------------------|
| 首次載入 | ~3s | ~1s |
| 頁面切換 | 重新載入 | 即時 |
| 資料刷新 | 全頁面 | 局部更新 |
| 記憶體使用 | ~200MB | ~150MB |
| 並發支援 | 低 | 高 |

## 下一步開發

### 高優先級
- [ ] WebSocket 即時價格推送
- [ ] Orderbook 熱力圖視覺化
- [ ] 效能監控整合

### 中優先級
- [ ] 更多技術指標 (Bollinger Bands, Ichimoku)
- [ ] 自訂告警設定
- [ ] 多時間週期支援

### 低優先級
- [ ] 深色/淺色主題切換
- [ ] 使用者偏好設定儲存
- [ ] 匯出資料功能

## 疑難排解

### API Server 啟動失敗
```bash
# 檢查資料庫連接
docker exec -it crypto_timescaledb psql -U crypto -d crypto_db -c "SELECT 1"

# 檢查 Redis 連接
docker exec -it crypto_redis redis-cli ping
```

### Dashboard 建置失敗
```bash
# 清理並重新安裝
cd dashboard-ts
rm -rf node_modules .next
npm install
npm run build
```

## 維護建議

1. **定期更新依賴**: `npm update`
2. **監控 API 效能**: 使用 Prometheus metrics (`:8080/metrics`)
3. **備份舊版**: 在完全移除前保留舊版至少 2 週
4. **日誌檢查**: `docker-compose logs -f api-server dashboard-ts`

## 聯絡與支援

遇到問題請查閱：
- API Server README: `api-server/README.md`
- Dashboard README: `dashboard-ts/README.md`
- 主專案 README: `README.md`
- Session Log: `docs/SESSION_LOG.md`
