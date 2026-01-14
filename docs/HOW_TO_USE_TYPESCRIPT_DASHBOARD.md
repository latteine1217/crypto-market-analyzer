# 🚀 TypeScript Dashboard - 完整使用指南

## 📋 目錄
- [系統需求](#系統需求)
- [快速開始](#快速開始)
- [本地開發](#本地開發)
- [功能使用](#功能使用)
- [常見問題](#常見問題)
- [進階配置](#進階配置)

---

## 系統需求

### 必須
- Docker Desktop (或 Docker Engine + Docker Compose)
- 已運行的 TimescaleDB 與 Redis

### 開發環境 (可選)
- Node.js 18+ 
- npm 或 yarn

---

## 快速開始

### 🎯 30 秒啟動

```bash
# 1. 進入專案目錄
cd /path/to/finance

# 2. 啟動新版 Dashboard (前提：DB 已有資料)
docker-compose up -d api-server dashboard-ts

# 3. 訪問 Dashboard
open http://localhost:3000
```

### 📊 完整系統啟動

```bash
# 啟動所有服務 (資料庫 + 收集器 + Dashboard)
docker-compose up -d

# 檢查服務狀態
docker-compose ps

# 查看日誌
docker-compose logs -f dashboard-ts api-server
```

### ✅ 驗證安裝

```bash
# 1. 檢查 API Server
curl http://localhost:8080/health
# 預期輸出: {"status":"ok","timestamp":"..."}

# 2. 檢查 Dashboard
open http://localhost:3000
```

---

## 本地開發

適合需要修改程式碼的開發者。

### Step 1: 啟動後端服務

```bash
# 啟動 Database + Redis + API Server
docker-compose up -d db redis api-server
```

### Step 2: 本地運行 Dashboard

```bash
cd dashboard-ts

# 首次運行：安裝依賴
npm install

# 開發模式 (支援熱重載)
npm run dev

# 訪問: http://localhost:3000
```

### Step 3: 修改程式碼

Dashboard 會自動偵測檔案變更並重新載入！

**常見修改場景**:
- 修改頁面: `src/app/*/page.tsx`
- 新增元件: `src/components/`
- 調整樣式: `src/app/globals.css`

---

## 功能使用

### 1. 市場總覽 (Overview)

**路徑**: http://localhost:3000/overview

**功能**:
- 即時查看所有 11 個市場的價格
- 24 小時價格變化（綠色上漲 / 紅色下跌）
- 24 小時高點、低點、成交量
- 每 5 秒自動刷新

**使用技巧**:
- 價格按交易所分組
- 點擊表頭可排序（瀏覽器功能）

---

### 2. 技術分析 (Technical)

**路徑**: http://localhost:3000/technical

**功能**:
- **交易所切換**: Binance / Bybit / OKX
- **交易對切換**: 所有可用市場（如 BTCUSDT, ETHUSDT）
- **K 線圖**: 顯示最近 200 根 K 線
- **移動平均線**: MA 20 (綠色) / MA 50 (橘色)
- **MACD 指標**: MACD 線、Signal 線、Histogram
- **技術指標統計**: 
  - 最新價格
  - RSI (14) - 超買/超賣提示
  - MACD 趨勢 (Bullish/Bearish)
  - MA 相對位置

**使用技巧**:
1. 先選擇交易所
2. 再選擇交易對
3. 圖表會自動更新

**指標解讀**:
- **RSI ≥ 70**: Overbought (超買)
- **RSI ≤ 30**: Oversold (超賣)
- **MACD > Signal**: Bullish (看漲)
- **MACD < Signal**: Bearish (看跌)

---

### 3. 流動性分析 (Liquidity)

**路徑**: http://localhost:3000/liquidity

**狀態**: 🚧 框架已建立，視覺化開發中

---

## 常見問題

### Q1: Dashboard 無法連接 API

**錯誤訊息**: "Failed to fetch" 或 ERR_CONNECTION_REFUSED

**解決方案**:
```bash
# 1. 確認 API Server 正在運行
docker-compose ps api-server

# 2. 檢查 API Server 日誌
docker-compose logs api-server

# 3. 手動測試 API
curl http://localhost:8080/health

# 4. 檢查環境變數 (dashboard-ts/.env)
cat dashboard-ts/.env
# 確保 NEXT_PUBLIC_API_URL=http://localhost:8080
```

---

### Q2: 圖表無法顯示或顯示 "No data available"

**可能原因**:
1. 資料庫中沒有該交易對的資料
2. API 查詢失敗

**解決方案**:
```bash
# 1. 檢查資料庫是否有資料
docker exec -it crypto_timescaledb psql -U crypto -d crypto_db -c \
  "SELECT COUNT(*) FROM ohlcv;"

# 2. 手動測試 API
curl "http://localhost:8080/api/ohlcv/binance/BTCUSDT?limit=10"

# 3. 檢查 Collector 是否正常運行
docker-compose logs collector ws-collector
```

---

### Q3: npm install 失敗

**錯誤訊息**: "EACCES" 或 permission denied

**解決方案**:
```bash
# 清理並重新安裝
cd dashboard-ts
rm -rf node_modules package-lock.json
npm install

# 如果仍然失敗，檢查 Node.js 版本
node -v  # 應該 >= 18.0.0
```

---

### Q4: Docker 建置失敗

**解決方案**:
```bash
# 清理 Docker 快取
docker-compose down
docker system prune -a

# 重新建置
docker-compose build --no-cache api-server dashboard-ts
docker-compose up -d api-server dashboard-ts
```

---

### Q5: 想同時運行新舊版本

**解決方案**:
```bash
# 啟動新版 (port 3000)
docker-compose up -d api-server dashboard-ts

# 啟動舊版 (port 8050) - 使用 profile
docker-compose --profile legacy up -d dashboard

# 訪問
# - 新版: http://localhost:3000
# - 舊版: http://localhost:8050
```

---

## 進階配置

### 自訂 API 端口

**修改**: `api-server/.env`
```env
PORT=8888  # 改為 8888
```

**對應修改**: `dashboard-ts/.env`
```env
NEXT_PUBLIC_API_URL=http://localhost:8888
```

**重啟服務**:
```bash
docker-compose restart api-server dashboard-ts
```

---

### 調整快取時間

**修改**: `api-server/.env`
```env
CACHE_TTL=10  # 從 5 秒改為 10 秒
```

**影響**: API 回應會快取 10 秒，減少資料庫查詢

---

### 調整自動刷新頻率

**修改**: `dashboard-ts/src/components/Providers.tsx`
```typescript
refetchInterval: 10 * 1000, // 從 5 秒改為 10 秒
```

---

### 停用快取 (用於除錯)

**修改**: `api-server/.env`
```env
ENABLE_CACHE=false
```

---

## 🛠️ 開發工具

### 熱重載開發

```bash
# Dashboard (前端)
cd dashboard-ts && npm run dev

# API Server (後端)
cd api-server && npm run dev
```

### 型別檢查

```bash
cd dashboard-ts && npm run type-check
cd api-server && npm run build  # TypeScript 編譯會檢查型別
```

### 程式碼格式化

```bash
cd dashboard-ts && npm run lint
```

---

## 📚 相關文檔

- **遷移指南**: `docs/DASHBOARD_TYPESCRIPT_MIGRATION.md`
- **快速指令**: `docs/QUICK_START_COMMANDS.md`
- **完成報告**: `docs/DASHBOARD_TS_COMPLETION_REPORT.md`
- **API 文檔**: `api-server/README.md`
- **Dashboard 文檔**: `dashboard-ts/README.md`

---

## 🆘 需要幫助？

1. 查看日誌: `docker-compose logs -f [service_name]`
2. 檢查服務狀態: `docker-compose ps`
3. 重啟服務: `docker-compose restart [service_name]`
4. 完全重置: `docker-compose down && docker-compose up -d`

---

**版本**: v2.1.0  
**最後更新**: 2026-01-15  
**維護者**: Development Team
