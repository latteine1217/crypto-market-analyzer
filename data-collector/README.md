# WebSocket Data Collector

`data-collector` 負責 Bybit WebSocket 實時收集與批次寫庫：
- `trade`
- `orderbook`
- `kline`
- `liquidation`

## 目前範圍

- 交易所：`bybit`
- 主要流程：WS -> Redis queue -> DBFlusher -> TimescaleDB
- Symbol 標準：原生格式（`BTCUSDT`），支援解析 `BTC/USDT:USDT`

## 目錄重點

```text
src/bybit_ws/         Bybit WS 客戶端
src/orderbook_handlers/ 訂單簿維護
src/queues/           Redis 佇列
src/database/         DB Flusher
src/metrics/          指標導出
src/utils/            Symbol / Logger 等工具
```

## 啟動

```bash
npm install
npm run dev
```

生產模式：

```bash
npm run build
npm start
```

## 主要環境變數

```env
EXCHANGE=bybit
SYMBOLS=BTCUSDT,ETHUSDT
STREAMS=trade,depth,kline_1m,liquidation

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_db
POSTGRES_USER=crypto
POSTGRES_PASSWORD=crypto_pass

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## 驗證

```bash
npm run build
```

若使用 Docker Compose：

```bash
docker-compose up -d ws-collector-bybit
docker-compose logs -f ws-collector-bybit
```

## 已知設計

- `DBFlusher` 各類資料（trade/orderbook/kline/liquidation）分開 flush，避免單一失敗阻塞全鏈路
- metrics server 會在容器內啟動，若要外部抓取需在 compose 額外映射端口

---

最後更新：2026-02-13
