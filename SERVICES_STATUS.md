# 🚀 服務狀態與快速指令

> **最後更新**: 2026-01-14  
> **狀態**: ✅ 所有服務正常運行（Docker 容器化部署）

---

## 📊 服務端口一覽

| 服務 | 端口 | 狀態 | 部署方式 | 訪問地址 |
|------|------|------|----------|----------|
| **TimescaleDB** | 5432 | ✅ Running | Docker | `localhost:5432` |
| **Redis** | 6379 | ✅ Running | Docker | `localhost:6379` |
| **Prometheus** | 9090 | ✅ Running | Docker | http://localhost:9090 |
| **Grafana** | 3000 | ✅ Running | Docker | http://localhost:3000 |
| **API Server** | 8080 | ✅ Running | Docker | http://localhost:8080 |
| **Dashboard (TS)** | 3001 | ✅ Running | Docker | http://localhost:3001 |
| **Collector (Python)** | 8000 | ✅ Running | Docker | http://localhost:8000/metrics |
| **WS Collector** | 8001 | ✅ Running | Docker | http://localhost:8001/metrics |

**部署狀態**: 🐳 **完全容器化** - 所有服務運行在 Docker 容器中

---

## 🎯 快速測試

### 自動測試腳本
```bash
# 測試所有 Docker 服務
./test-docker-services.sh

# 測試本機服務（如果有運行）
./test-services.sh
```

### 手動測試
```bash
# 1. 測試 API Server 健康檢查
curl http://localhost:8080/health

# 2. 測試市場列表
curl http://localhost:8080/api/markets | jq

# 3. 測試 OHLCV 資料
curl "http://localhost:8080/api/ohlcv/binance/BTCUSDT?limit=5" | jq

# 4. 測試市場價格
curl http://localhost:8080/api/markets/prices | jq

# 5. 訪問 Dashboard
open http://localhost:3001
```

---

## 🔧 服務管理

### 🐳 Docker 部署（推薦）

#### 啟動所有服務
```bash
cd /Users/latteine/Documents/coding/finance

# 啟動所有服務
docker-compose up -d

# 只啟動核心服務
docker-compose up -d db redis api-server dashboard-ts

# 啟動監控服務
docker-compose up -d prometheus grafana
```

#### 構建映像
```bash
# 構建 API Server
docker-compose build api-server

# 構建 Dashboard
docker-compose build dashboard-ts

# 重新構建（不使用快取）
docker-compose build --no-cache api-server dashboard-ts
```

#### 停止服務
```bash
# 停止所有服務
docker-compose down

# 停止特定服務
docker-compose stop api-server dashboard-ts

# 停止並移除容器（保留資料）
docker-compose down

# 停止並移除所有資料
docker-compose down -v
```

#### 查看狀態與日誌
```bash
# 查看所有容器狀態
docker-compose ps

# 查看 API Server 日誌
docker-compose logs -f api-server

# 查看 Dashboard 日誌
docker-compose logs -f dashboard-ts

# 查看所有服務日誌
docker-compose logs -f

# 查看資源使用
docker stats
```

### 💻 本機開發模式

#### 啟動 API Server（本機）
```bash
cd api-server
npm run dev
# 背景執行: nohup npm run dev > /tmp/api-server.log 2>&1 &
```

### 啟動 Dashboard（本機）
```bash
cd dashboard-ts
npm run dev
# 背景執行: npm run dev > /tmp/dashboard-ts.log 2>&1 &
```

### 停止服務
```bash
# 停止 Docker 容器
docker-compose down

# 停止 Node.js 進程
pkill -f "ts-node src/index.ts"  # API Server
pkill -f "next dev"              # Dashboard
```

### 查看日誌
```bash
# API Server 日誌
tail -f /tmp/api-server.log

# Dashboard 日誌
tail -f /tmp/dashboard-ts.log

# Docker 容器日誌
docker-compose logs -f [service_name]
```

---

## 📝 開發檢查清單

### API Server 開發
- [x] TypeScript 編譯通過
- [x] 資料庫 schema 對齊
- [x] 所有端點正常返回資料
- [x] Redis 快取功能運作
- [x] 錯誤處理與日誌記錄
- [ ] 單元測試（待補充）

### Dashboard 開發
- [x] Next.js 15 配置正確
- [x] API 端點連接正常
- [x] TypeScript 型別定義正確
- [ ] UI 頁面測試（待瀏覽器驗證）
- [ ] 圖表渲染測試（待瀏覽器驗證）
- [ ] 自動刷新功能測試（待驗證）

---

## ⚠️ 已知問題

### 已修復 ✅
1. ~~TypeScript 編譯錯誤（參數型別不匹配）~~ - 已修復
2. ~~資料庫欄位名稱不一致（base_currency vs base_asset）~~ - 已修復
3. ~~API Server 無法啟動~~ - 已修復

### 待處理
1. Orderbook 端點返回 `null`（可能是資料庫中沒有快照資料）
2. WebSocket 即時更新功能尚未實作
3. UI 功能需在瀏覽器中測試驗證

---

## 🎉 里程碑

- ✅ **2026-01-14**: TypeScript 架構完成並成功運行
  - API Server 正常提供資料
  - Dashboard 成功連接 API
  - 所有核心端點測試通過

---

## 📌 下一步

1. **瀏覽器測試** Dashboard UI
   - 訪問 http://localhost:3001
   - 測試市場總覽頁面
   - 測試技術分析頁面
   - 驗證圖表渲染

2. **Docker 整合測試**
   - 構建 Docker 映像
   - 測試容器化部署
   - 驗證網路連接

3. **補充缺失功能**
   - 訂單簿資料收集
   - WebSocket 即時推送
   - 單元測試

---

**快速連結**:
- 📘 [專案文檔](./docs/)
- 🔧 [API 文檔](./api-server/README.md)
- 📊 [Dashboard 文檔](./dashboard-ts/README.md)
- 🐳 [Docker 指南](./docs/QUICK_START_COMMANDS.md)
