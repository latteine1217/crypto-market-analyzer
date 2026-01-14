# 🚀 快速啟動指南

> 一分鐘啟動 Crypto Market Dashboard

---

## 📋 前置需求

確保已安裝：
- Docker Desktop (macOS)
- Docker Compose

---

## ⚡ 一鍵啟動（推薦）

```bash
# 1. 進入專案目錄
cd /Users/latteine/Documents/coding/finance

# 2. 啟動所有服務
docker-compose up -d

# 3. 等待 10 秒讓服務啟動
sleep 10

# 4. 驗證服務狀態
./test-docker-services.sh
```

**就是這樣！** 🎉

訪問服務：
- 📊 **Dashboard**: http://localhost:3001
- 🚀 **API Server**: http://localhost:8080
- 📈 **Grafana**: http://localhost:3000 (admin/admin)
- 🔍 **Prometheus**: http://localhost:9090

---

## 🎯 核心服務啟動

如果只需要核心功能（Dashboard + API）：

```bash
docker-compose up -d db redis api-server dashboard-ts
```

---

## 🔄 常用命令

### 查看狀態
```bash
docker-compose ps
```

### 查看日誌
```bash
# 即時日誌
docker-compose logs -f api-server dashboard-ts

# 最近 50 行
docker logs crypto_api_server --tail 50
```

### 重啟服務
```bash
docker-compose restart api-server dashboard-ts
```

### 停止服務
```bash
docker-compose down
```

---

## 🐛 問題排查

### 服務無法啟動？

1. **檢查端口是否被佔用**
   ```bash
   lsof -i :8080  # API Server
   lsof -i :3001  # Dashboard
   lsof -i :5432  # Database
   ```

2. **查看容器日誌**
   ```bash
   docker-compose logs api-server
   docker-compose logs dashboard-ts
   ```

3. **檢查資料庫健康狀態**
   ```bash
   docker exec crypto_timescaledb pg_isready -U crypto
   ```

### API 連接失敗？

```bash
# 測試 API 健康檢查
curl http://localhost:8080/health

# 測試資料庫連接
docker exec crypto_api_server wget -q -O- http://db:5432 || echo "DB unreachable"
```

### Dashboard 無法連接 API？

```bash
# 測試容器間網路
docker exec crypto_dashboard_ts wget -q -O- http://api-server:8080/health
```

---

## 🔧 開發模式

如果需要修改程式碼並即時看到變化：

### API Server 本機開發
```bash
cd api-server
npm run dev
```

### Dashboard 本機開發
```bash
cd dashboard-ts
npm run dev
```

**注意**: 本機開發時需確保資料庫和 Redis 容器正在運行：
```bash
docker-compose up -d db redis
```

---

## 📦 重新構建

修改程式碼後需要重新構建映像：

```bash
# 重新構建特定服務
docker-compose build api-server

# 重新構建並啟動
docker-compose up -d --build api-server

# 強制重新構建（不使用快取）
docker-compose build --no-cache api-server dashboard-ts
```

---

## 🎉 驗證部署

執行完整測試：

```bash
./test-docker-services.sh
```

預期輸出：
```
✅ API Server 健康狀態: ok
✅ 市場數量: 13 markets
✅ BTC 價格: $96,XXX
✅ Dashboard 首頁: HTTP 200
✅ Dashboard → API Server: 連接正常
```

---

## 📚 更多文檔

- 📘 [服務狀態](./SERVICES_STATUS.md)
- 🐳 [Docker 整合報告](./docs/DOCKER_INTEGRATION_REPORT.md)
- 🔧 [API 文檔](./api-server/README.md)
- 📊 [Dashboard 文檔](./dashboard-ts/README.md)

---

**快速支援**:
- 查看日誌: `docker-compose logs -f`
- 查看狀態: `docker-compose ps`
- 完整測試: `./test-docker-services.sh`
