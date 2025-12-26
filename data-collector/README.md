# WebSocket 實時數據收集器

階段 1.2 實現：透過 WebSocket 收集實時交易與訂單簿數據

## 功能特點

- ✅ Binance WebSocket 連接（支援多交易對）
- ✅ 實時交易流（Trades）收集
- ✅ 訂單簿增量更新處理
- ✅ 本地訂單簿維護與快照生成
- ✅ Redis 作為訊息佇列暫存層
- ✅ 批次寫入 TimescaleDB
- ✅ 自動重連與錯誤處理
- ✅ 實時統計監控

## 架構流程

```
Binance WebSocket
      ↓
   訊息解析
      ↓
  ┌──────────┬──────────┐
  │          │          │
 Trade   OrderBook   K線
  │       Update      │
  ↓          ↓         ↓
     Redis Queue
          ↓
    批次 Flush
          ↓
    TimescaleDB
```

## 安裝依賴

```bash
npm install
```

## 配置

1. 複製環境變數範例：

```bash
cp .env.example .env
```

2. 編輯 `.env` 設定：

```bash
# Redis 配置（確保 Redis 正在運行）
REDIS_HOST=localhost
REDIS_PORT=6379

# TimescaleDB 配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_db
POSTGRES_USER=crypto
POSTGRES_PASSWORD=crypto_pass

# 訂閱的交易對
SYMBOLS=BTCUSDT,ETHUSDT

# 訂閱的數據流
STREAMS=trade,depth
```

## 啟動前準備

### 1. 確保 TimescaleDB 運行中

```bash
docker ps | grep timescale
```

如果沒有運行：

```bash
cd ..
docker-compose up -d db
```

### 2. 確保 Redis 運行中

```bash
docker ps | grep redis
```

如果沒有運行：

```bash
docker-compose up -d redis
```

## 編譯

```bash
npm run build
```

## 啟動

### 開發模式（使用 ts-node）

```bash
npm run dev
```

### 生產模式（編譯後執行）

```bash
npm run build
npm start
```

## 監控

啟動後，系統會每 30 秒輸出統計資訊：

```
================================================================================
📊 Statistics
================================================================================

🌐 WebSocket:
  Total messages: 15234
  Reconnects: 0
  Errors: 0
  Uptime: 180s

📦 Redis Queues:
  trade: 42 messages
  orderbook_snapshot: 2 messages

💾 Database:
  Total flushed: 2150
  Errors: 0
  Is flushing: false

📈 Order Books:
  BTCUSDT:
    Best bid: 43521.50
    Best ask: 43521.60
    Spread: 0.10 (0.23 bps)
    Updates: 1523
```

## 資料流說明

### 1. Trade 數據

- 來源：`<symbol>@trade` stream
- 處理：直接推送到 Redis 佇列
- 寫入：批次寫入 `trades` 表

### 2. OrderBook 數據

- 來源：`<symbol>@depth@100ms` stream
- 處理：
  1. 更新本地訂單簿快照
  2. 每分鐘生成完整快照
  3. 推送到 Redis 佇列
- 寫入：批次寫入 `orderbook_snapshots` 表

## 停止服務

按 `Ctrl+C` 會觸發優雅停止：

1. 停止 WebSocket 連接
2. Flush 剩餘數據
3. 關閉資料庫連接
4. 斷開 Redis

## 故障排除

### WebSocket 連接失敗

- 檢查網路連接
- 確認 Binance API 可訪問
- 檢查 symbols 是否正確

### Redis 連接失敗

```bash
# 檢查 Redis 是否運行
docker ps | grep redis

# 查看 Redis 日誌
docker logs crypto_redis
```

### 資料庫寫入失敗

```bash
# 檢查 TimescaleDB 是否運行
docker ps | grep timescale

# 查看資料庫日誌
docker logs crypto_timescaledb

# 測試連接
docker exec -it crypto_timescaledb psql -U crypto -d crypto_db -c "SELECT 1"
```

## 性能調整

### 調整 Flush 頻率

在 `.env` 中：

```bash
# 批次大小（一次處理多少訊息）
FLUSH_BATCH_SIZE=100

# Flush 間隔（毫秒）
FLUSH_INTERVAL_MS=5000
```

### 調整訂單簿深度

修改 `src/orderbook_handlers/OrderBookManager.ts`：

```typescript
private readonly MAX_DEPTH = 20; // 改為需要的深度
```

## 開發

### 專案結構

```
src/
├── types/             # 類型定義
├── config/            # 配置管理
├── utils/             # 工具（日誌等）
├── binance_ws/        # Binance WebSocket 客戶端
├── orderbook_handlers/# 訂單簿管理
├── queues/            # Redis 佇列
├── database/          # 資料庫 Flusher
└── index.ts           # 主程式入口
```

### 新增交易所

1. 在 `src/` 下建立新目錄，例如 `okx_ws/`
2. 實作 WebSocket 客戶端（參考 `BinanceWSClient`）
3. 在 `index.ts` 中整合

## 與 Python Collector 的關係

- **Python Collector (階段 1.1)**：負責歷史數據補齊、品質檢查
- **Node.js WebSocket (階段 1.2)**：負責實時數據收集
- **共用**：TimescaleDB、Redis

兩者可以同時運行，互補工作。

## 下一步

- [ ] 新增 OKX WebSocket 支援
- [ ] 實作更多數據流（K線、Ticker）
- [ ] 效能優化（批次處理）
- [ ] 監控告警系統
