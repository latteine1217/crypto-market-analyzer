# Crypto Market Dashboard

以 **Bybit** 為核心資料源的加密市場監督系統，提供：
- REST + WebSocket 多源收集
- TimescaleDB 時序存儲
- API 聚合與快取
- Next.js 交易監看面板
- 多時框訊號監測（短線 + 波段）

## 核心定位

- 交易所範圍：目前以 `bybit` 為主
- 訊號時框：`5m`（短線）與 `1h/4h/1d`（波段）
- Symbol 標準：全鏈路採用原生格式（例如 `BTCUSDT`）

## 架構總覽

```text
[Bybit REST/WS + ETF/F&G + On-chain]
                 |
     +-----------+-----------+
     |                       |
[collector-py]        [data-collector]
 (REST & Scheduler)    (WS & Queue Flush)
     |                       |
     +-----------+-----------+
                 |
               [Redis]
                 |
            [TimescaleDB]
                 |
            [api-server]
                 |
           [dashboard-ts]
                 |
               [nginx]
```

## 服務與端口

- `nginx`: `80`
- `db` (TimescaleDB): `5432`
- `redis`: `6379`
- `api-server`: `8080`
- `dashboard-ts`: `3001`

備註：目前 `docker-compose.yml` 未內建 Prometheus/Grafana stack；collector 端已有 metrics exporter，後續可外接監控棧。

## 專案結構

```text
collector-py/        Python 排程/REST 收集器與訊號監控
data-collector/      TypeScript WebSocket 收集器與 DB Flusher
api-server/          TypeScript API 聚合層
dashboard-ts/        Next.js 前端
database/            Schema 與 migration 說明
configs/             系統與 collector 配置
docs/                開發與維護紀錄（SESSION_LOG）
```

## 快速啟動

1. 建立環境檔：

```bash
cp .env.example .env
```

2. 啟動服務：

```bash
docker-compose up -d
```

3. 檢查狀態：

```bash
docker-compose ps
make status
```

## 常用操作

```bash
make logs-collector      # Collector 日誌
make logs-api            # API Server 日誌
make logs-dashboard      # Dashboard 日誌
make db-shell            # 進入 PostgreSQL
```

## 快速驗證

```bash
curl -s http://localhost/api/health | jq .
curl -s http://localhost/api/status | jq .
curl -s http://localhost/api/markets/prices | jq '.data | length'
curl -s http://localhost/api/alerts/signals?limit=5 | jq '.data | length'
```

## ETF Flow (Farside)

ETF flow 資料目前來源為 Farside（網頁表格解析後寫入 `global_indicators`）。

現實限制：
- 該頁面可能觸發反自動化保護，導致抓取回傳 challenge HTML 或 403，進而「寫入 0 筆」。

落地策略（已實作）：
- Hybrid：`Playwright` 嘗試取得 cookies/UA，`curl_cffi` 重用身份抓取 HTML。
- Identity cache：預設寫到 `collector-py/logs/etf_cookie_cache.json`（容器內為 `/app/logs/...`）。
- 手動注入：若你有合法存取權限，建議直接在 `collector-py/.env` 設定 `ETF_COOKIES_JSON` + `ETF_USER_AGENT`，成功率最高。

相關環境變數請見：`/Users/latteine/Documents/coding/finance/collector-py/.env.example`

## 文件索引

- 最新進度：`/Users/latteine/Documents/coding/finance/docs/SESSION_LOG.md`
- API 服務說明：`/Users/latteine/Documents/coding/finance/api-server/README.md`
- WS 收集器說明：`/Users/latteine/Documents/coding/finance/data-collector/README.md`
- 前端說明：`/Users/latteine/Documents/coding/finance/dashboard-ts/README.md`
- 配置說明：`/Users/latteine/Documents/coding/finance/configs/README.md`

---

最後更新：2026-02-13
