# 🚀 啟動指令快速參考

## 📦 完整系統啟動

### 啟動所有服務 (包含新版 Dashboard)
```bash
docker-compose up -d
```

### 啟動特定服務組合

**基礎設施** (資料庫 + 快取)
```bash
docker-compose up -d db redis
```

**資料收集** (REST + WebSocket)
```bash
docker-compose up -d collector ws-collector
```

**新版 Dashboard 完整系統** (推薦)
```bash
docker-compose up -d db redis collector ws-collector api-server dashboard-ts
```

**舊版 Dashboard 系統** (相容模式)
```bash
docker-compose --profile legacy up -d db redis collector ws-collector dashboard
```

**監控系統**
```bash
docker-compose up -d prometheus grafana alertmanager
```

---

## 🎯 快速測試場景

### 場景 1: 只測試新 Dashboard
```bash
# 前提：資料庫已有資料
docker-compose up -d db redis api-server dashboard-ts

# 訪問: http://localhost:3000
```

### 場景 2: 新舊 Dashboard 並行測試
```bash
docker-compose --profile legacy up -d db redis api-server dashboard-ts dashboard

# 新版: http://localhost:3000
# 舊版: http://localhost:8050
```

### 場景 3: 本地開發 Dashboard + 容器化後端
```bash
# 啟動後端服務
docker-compose up -d db redis api-server

# 本地啟動 Dashboard
cd dashboard-ts
npm run dev
# 訪問: http://localhost:3000
```

---

## 🔧 常用管理指令

### 查看服務狀態
```bash
docker-compose ps
```

### 查看日誌
```bash
# 所有服務
docker-compose logs -f

# 特定服務
docker-compose logs -f api-server
docker-compose logs -f dashboard-ts
docker-compose logs -f collector
```

### 重啟服務
```bash
# 重啟特定服務
docker-compose restart api-server
docker-compose restart dashboard-ts

# 重建並重啟
docker-compose up -d --build api-server dashboard-ts
```

### 停止服務
```bash
# 停止所有
docker-compose down

# 停止但保留資料
docker-compose stop

# 停止特定服務
docker-compose stop dashboard-ts
```

---

## 🌐 服務端口一覽

| 服務 | 端口 | 用途 |
|------|------|------|
| **新版 Dashboard** | 3000 | Next.js Frontend |
| **API Server** | 8080 | Express REST API |
| **舊版 Dashboard** | 8050 | Python Dash (legacy) |
| **TimescaleDB** | 5432 | 資料庫 |
| **Redis** | 6379 | 快取 |
| **Prometheus** | 9090 | 監控指標 |
| **Grafana** | 3000* | 監控面板 (與新 Dashboard 衝突) |
| **Collector Metrics** | 8000 | REST Collector 指標 |
| **WS Collector Metrics** | 8001 | WebSocket Collector 指標 |

*註: 如需同時運行 Grafana 與新 Dashboard，需修改其中一個的端口*

---

## ⚡ 開發工作流程

### 前端開發 (Dashboard)
```bash
cd dashboard-ts
npm install
npm run dev    # 開發模式 (熱重載)
npm run build  # 生產建置
npm run lint   # 程式碼檢查
```

### 後端開發 (API Server)
```bash
cd api-server
npm install
npm run dev    # 開發模式 (ts-node)
npm run build  # 編譯 TypeScript
npm start      # 生產模式
```

### 資料庫操作
```bash
# 進入資料庫
docker exec -it crypto_timescaledb psql -U crypto -d crypto_db

# 執行遷移
docker exec -it crypto_timescaledb psql -U crypto -d crypto_db -f /migrations/xxx.sql

# 備份資料庫
docker exec crypto_timescaledb pg_dump -U crypto crypto_db > backup.sql
```

---

## 🧪 測試與驗證

### 健康檢查
```bash
# API Server
curl http://localhost:8080/health

# Database
docker exec crypto_timescaledb pg_isready -U crypto

# Redis
docker exec crypto_redis redis-cli ping
```

### API 測試
```bash
# 取得市場列表
curl http://localhost:8080/api/markets

# 取得 OHLCV 資料
curl "http://localhost:8080/api/ohlcv/binance/BTCUSDT?limit=10"

# 取得市場摘要
curl http://localhost:8080/api/ohlcv/binance/BTCUSDT/summary
```

---

## 📊 監控與除錯

### Prometheus Metrics
```bash
# Collector metrics
curl http://localhost:8000/metrics

# WS Collector metrics
curl http://localhost:8001/metrics
```

### 容器資源使用
```bash
docker stats
```

### 清理與重置
```bash
# 清理未使用的 Docker 資源
docker system prune -a

# 完全重置 (會刪除資料!)
docker-compose down -v
docker-compose up -d
```

---

## 🎓 學習路徑建議

### 新手入門
1. 啟動基礎設施: `docker-compose up -d db redis`
2. 啟動 API Server: `docker-compose up -d api-server`
3. 本地運行 Dashboard: `cd dashboard-ts && npm run dev`

### 進階開發
1. 完整系統: `docker-compose up -d`
2. 修改程式碼並觀察熱重載
3. 檢查日誌排查問題: `docker-compose logs -f`

### 生產部署
1. 設置環境變數: `cp .env.example .env`
2. 建置映像: `docker-compose build`
3. 啟動服務: `docker-compose up -d`
4. 配置監控告警
