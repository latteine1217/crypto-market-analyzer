# Crypto API Server

`api-server` 是市場資料聚合與查詢層，負責：
- 封裝 TimescaleDB 查詢
- Redis 快取
- 市場訊號與價格告警 API
- Socket.IO 推送（price alert / market signal）

## 技術棧

- Node.js + TypeScript
- Express
- PostgreSQL (`pg`)
- Redis (`ioredis`)
- Socket.IO

## 啟動方式

```bash
npm install
npm run dev
```

生產模式：

```bash
npm run build
npm start
```

## 環境變數

主要變數（其餘參考 `.env.example`）：

```env
PORT=8080
NODE_ENV=development

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_db
POSTGRES_USER=crypto
POSTGRES_PASSWORD=crypto_pass

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## 主要路由

- `/api/health`
- `/api/status`
- `/api/markets`
- `/api/ohlcv`
- `/api/orderbook`
- `/api/derivatives`
- `/api/analytics`
- `/api/alerts`
- `/api/events`
- `/api/fear-greed`
- `/api/etf-flows`
- `/api/blockchain`

## 與前端契約重點

- `GET /api/markets/quality` 目前回傳：
  - `exchange`
  - `symbol`
  - `timeframe`
  - `check_time`
  - `missing_rate`
  - `quality_score`
  - `status`（`excellent|good|acceptable|poor|critical`）
  - `missing_count`
  - `expected_count`
  - `actual_count`
  - `backfill_task_created`

## 驗證命令

```bash
npm run build
curl -s http://localhost:8080/api/health | jq .
curl -s http://localhost:8080/api/status | jq .
curl -s "http://localhost:8080/api/markets/quality" | jq '.data[0]'
```

---

最後更新：2026-02-13
