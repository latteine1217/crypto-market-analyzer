# Grafana Dashboards 使用指南

**文檔版本**: 1.0
**創建日期**: 2025-12-28
**適用環境**: Docker Compose (local development & production)

---

## 📊 概覽

本系統包含兩個主要的 Grafana Dashboard，用於監控 Crypto Market Analyzer 的資料收集服務：

1. **Crypto Collector Dashboard** - 監控 Python REST API Collector
2. **WebSocket Collector Dashboard** - 監控 TypeScript WebSocket Collector

---

## 🚀 快速開始

### 1. 啟動服務

確保所有必要的服務正在運行：

```bash
# 啟動所有監控相關服務
docker-compose up -d db redis collector ws-collector prometheus grafana

# 檢查服務狀態
docker-compose ps
```

### 2. 訪問 Grafana

**URL**: http://localhost:3000

**預設憑證**:
- Username: `admin`
- Password: `admin`

首次登入後，Grafana 會提示修改密碼。

### 3. 查看 Dashboards

登入後：
1. 點擊左側選單的 "Dashboards"
2. 進入 "Crypto Market Analyzer" 文件夾
3. 選擇要查看的 Dashboard：
   - **Crypto Collector Dashboard**
   - **WebSocket Collector Dashboard**

**直接訪問連結**:
- Collector Dashboard: http://localhost:3000/d/crypto-collector
- WebSocket Collector Dashboard: http://localhost:3000/d/ws-collector

---

## 📈 Dashboard 詳解

### Crypto Collector Dashboard

監控 Python REST API Collector 的資料收集狀態、API 性能與資料品質。

#### 面板說明

**Row 1: 系統概覽**
- **Collector Status** (左上)
  - 顯示: `Running` (綠色) 或 `Down` (紅色)
  - 指標: `collector_running`

- **Uptime** (中上)
  - 顯示: Collector 運行時間（秒）
  - 指標: `collector_uptime_seconds`

- **Total OHLCV Candles** (中右上)
  - 顯示: 已收集的 K 線總數
  - 指標: `sum(collector_ohlcv_collected_total)`

- **API Success Rate** (右上)
  - 顯示: API 請求成功率 (%)
  - 指標: `rate(collector_api_requests_total{status="success"}[5m]) / rate(collector_api_requests_total[5m])`

**Row 2: 資料收集速率**
- **OHLCV Collection Rate**
  - 顯示: 每分鐘收集的 K 線數量
  - 按交易所、交易對、時間框架分組
  - 指標: `rate(collector_ohlcv_collected_total[5m]) * 60`

- **API Request Rate**
  - 顯示: 每分鐘 API 請求數量
  - 按交易所、端點、狀態分組
  - 指標: `rate(collector_api_requests_total[5m]) * 60`

**Row 3: API 性能**
- **API Request Latency (P50/P95/P99)**
  - 顯示: API 請求延遲的百分位數
  - P50: 中位數延遲
  - P95: 95% 請求的延遲上限
  - P99: 99% 請求的延遲上限
  - 指標: `histogram_quantile(0.50/0.95/0.99, rate(collector_api_request_duration_seconds_bucket[5m]))`

**Row 4: 資料品質**
- **Data Quality Score (0-100)**
  - 顯示: 資料品質分數（越高越好）
  - 按交易所、交易對、時間框架分組
  - 指標: `collector_data_quality_score`

- **Validation Failures**
  - 顯示: 資料驗證失敗次數
  - 區分失敗率與連續失敗計數
  - 指標: `rate(collector_validation_failures_total[5m])`, `collector_consecutive_failures`

**Row 5: 補資料狀態**
- **Backfill Tasks Status**
  - 顯示: 補資料任務狀態
  - 排隊中、完成率、失敗率
  - 指標: `collector_backfill_tasks_queued`, `rate(collector_backfill_tasks_completed[5m])`, `rate(collector_backfill_tasks_failed[5m])`

---

### WebSocket Collector Dashboard

監控 TypeScript WebSocket Collector 的實時訂單簿數據收集與 WebSocket 連線健康度。

#### 面板說明

**Row 1: 系統概覽**
- **WS Collector Status** (左上)
  - 顯示: `Running` (綠色) 或 `Down` (紅色)
  - 指標: `ws_collector_running`

- **WebSocket Connection** (中左上)
  - 顯示: `Connected` (綠色) 或 `Disconnected` (紅色)
  - 指標: `ws_collector_connection_status{exchange="binance"}`

- **Uptime** (中右上)
  - 顯示: WebSocket Collector 運行時間（秒）
  - 指標: `ws_collector_uptime_seconds`

- **Total WebSocket Messages** (右上)
  - 顯示: 已接收的 WebSocket 訊息總數
  - 指標: `sum(ws_collector_messages_total)`

**Row 2: 訂單簿即時數據**
- **Best Bid Price** (左)
  - 顯示: 各交易對的最佳買價（即時）
  - 單位: USD
  - 指標: `ws_collector_orderbook_best_bid_price`

- **Best Ask Price** (中)
  - 顯示: 各交易對的最佳賣價（即時）
  - 單位: USD
  - 指標: `ws_collector_orderbook_best_ask_price`

- **Spread (basis points)** (中右)
  - 顯示: 訂單簿價差（基點，bps）
  - 閾值: 綠色 < 5 bps, 黃色 5-10 bps, 紅色 > 10 bps
  - 指標: `ws_collector_orderbook_spread_bps`

- **Spread (absolute)** (右)
  - 顯示: 訂單簿絕對價差
  - 單位: USD
  - 指標: `ws_collector_orderbook_spread`

**Row 3: 訂單簿價差監控**
- **Order Book Spread (bps) - Time Series** (左)
  - 顯示: 價差隨時間的變化趨勢
  - 包含統計值: 平均、最新、最大、最小
  - 指標: `ws_collector_orderbook_spread_bps`

- **Order Book Activity** (右)
  - 顯示: 訂單簿快照與更新速率
  - Snapshots/min: 每分鐘快照數量
  - Updates/min: 每分鐘更新數量
  - 指標: `rate(ws_collector_orderbook_snapshots_total[5m]) * 60`, `rate(ws_collector_orderbook_updates_total[5m]) * 60`

**Row 4: WebSocket 連線健康度**
- **WebSocket Connection Health**
  - 顯示: WebSocket 連線狀態指標
  - Messages/min: 每分鐘接收訊息數
  - Reconnects/min: 每分鐘重連次數
  - Errors/min: 每分鐘錯誤次數
  - 指標: `rate(ws_collector_messages_total[5m])`, `rate(ws_collector_reconnects_total[5m])`, `rate(ws_collector_errors_total[5m])`

**Row 5: Redis 佇列與訊息處理**
- **Redis Queue Status** (左)
  - 顯示: Redis 佇列大小與推送速率
  - Queue Size: 當前佇列積壓數量
  - Push Rate/min: 每分鐘推送速率
  - 指標: `ws_collector_redis_queue_size`, `rate(ws_collector_redis_queue_push_total[5m])`

- **Message Processing Latency (P50/P95/P99)** (右)
  - 顯示: 訊息處理延遲的百分位數
  - 按訊息類型分組
  - 指標: `histogram_quantile(0.50/0.95/0.99, rate(ws_collector_message_processing_duration_seconds_bucket[5m]))`

---

## 🎛️ Dashboard 操作

### 時間範圍選擇

- 點擊右上角的時間選擇器
- 預設: `Last 1 hour`
- 常用選項: Last 5m, Last 15m, Last 1h, Last 6h, Last 24h
- 也可自訂時間範圍

### 自動刷新

- 點擊右上角的刷新圖示
- 預設: `10s` 自動刷新
- 可選擇: 5s, 10s, 30s, 1m, 5m, 關閉

### 變數過濾（Templating）

**Crypto Collector Dashboard** 提供三個過濾變數：

- **Exchange**: 選擇要監控的交易所
  - 選項: Binance（目前支援）
  - 支援多選與 "All" 選項

- **Symbol**: 選擇要監控的交易對
  - 選項: BTC/USDT, ETH/USDT 等（依交易所而定）
  - 支援多選與 "All" 選項
  - 依賴於 Exchange 選擇

- **Timeframe**: 選擇 K 線時間框架
  - 選項: 1m, 5m, 15m, 1h 等（依系統配置而定）
  - 支援多選與 "All" 選項
  - 依賴於 Exchange 選擇

**WebSocket Collector Dashboard** 提供一個過濾變數：

- **Symbol**: 選擇要監控的交易對
  - 選項: BTCUSDT, ETHUSDT 等
  - 支援多選與 "All" 選項

**使用方式**:
1. 在 Dashboard 頂部會看到下拉式變數選擇器
2. 點擊變數名稱選擇要過濾的值
3. 可以勾選多個值或選擇 "All"
4. 所有面板會自動根據選擇的變數過濾數據

**範例**:
- 只查看 Binance 的 BTC/USDT 1m 數據：
  - Exchange = Binance
  - Symbol = BTC/USDT
  - Timeframe = 1m

- 比較多個交易對：
  - Symbol = BTC/USDT + ETH/USDT

### 面板互動

- **縮放**: 在圖表上拖曳選取區域
- **重置縮放**: 雙擊圖表
- **查看詳情**: 滑鼠移到圖表上查看數值
- **編輯面板**: 點擊面板標題 → Edit（需管理員權限）

### 分享 Dashboard

1. 點擊右上角的 "Share" 按鈕
2. 選擇分享方式：
   - **Link**: 生成可分享的 URL
   - **Snapshot**: 創建靜態快照
   - **Export**: 匯出 JSON 配置

---

## ⚙️ 配置文件

Dashboard 配置採用 Provisioning 自動化管理：

### 目錄結構

```
monitoring/grafana/
├── provisioning/
│   ├── datasources/
│   │   └── datasource.yml          # Prometheus 數據源配置
│   └── dashboards/
│       ├── dashboard.yml            # Dashboard Provisioning 配置
│       └── dashboards/
│           ├── collector-dashboard.json
│           └── ws-collector-dashboard.json
```

### 修改 Dashboard

**方式一：在 UI 中修改並匯出**
1. 在 Grafana UI 中編輯 Dashboard
2. 測試修改是否符合需求
3. 點擊 Share → Export → Save to file
4. 將匯出的 JSON 替換對應的文件
5. 重啟 Grafana: `docker-compose restart grafana`

**方式二：直接編輯 JSON**
1. 編輯 `monitoring/grafana/provisioning/dashboards/dashboards/*.json`
2. 修改面板配置、查詢語句等
3. 重啟 Grafana: `docker-compose restart grafana`

**注意**:
- Provisioned dashboards 預設為可編輯（`allowUiUpdates: true`）
- UI 中的修改不會持久化，除非匯出並替換 JSON 文件
- 建議在測試環境先測試修改，再應用到生產環境

---

## 🔍 常見問題排查

### 問題 1: Dashboard 顯示 "No Data"

**可能原因**:
1. Collector 服務未運行
2. Prometheus 未抓取到 metrics
3. 時間範圍選擇錯誤

**排查步驟**:
```bash
# 檢查 Collector 狀態
docker-compose ps collector ws-collector

# 檢查 Prometheus targets
curl http://localhost:9090/api/v1/targets

# 測試 metrics 端點
curl http://localhost:8000/metrics  # Python Collector
curl http://localhost:8001/metrics  # WebSocket Collector

# 檢查 Grafana 日誌
docker-compose logs grafana | tail -100
```

### 問題 2: Dashboard 無法載入

**可能原因**:
1. Grafana 服務未啟動
2. Datasource 配置錯誤
3. Dashboard JSON 格式錯誤

**排查步驟**:
```bash
# 檢查 Grafana 狀態
docker-compose ps grafana
curl http://localhost:3000/api/health

# 檢查 datasources
curl -u admin:admin http://localhost:3000/api/datasources

# 檢查 dashboards
curl -u admin:admin "http://localhost:3000/api/search?type=dash-db"

# 查看 Grafana 日誌
docker-compose logs grafana | grep -i error
```

### 問題 3: 圖表顯示異常值

**可能原因**:
1. 資料收集異常
2. Prometheus 抓取間隔不一致
3. 查詢語句問題

**排查步驟**:
```bash
# 直接查詢 Prometheus
curl "http://localhost:9090/api/v1/query?query=collector_running"

# 檢查 Collector 日誌
docker-compose logs collector | grep -i error
docker-compose logs ws-collector | grep -i error
```

### 問題 4: Dashboard 修改未生效

**解決方案**:
```bash
# 重啟 Grafana 載入新配置
docker-compose restart grafana

# 強制重新創建容器
docker-compose stop grafana
docker-compose rm -f grafana
docker-compose up -d grafana
```

---

## 📊 監控指標參考

### Python Collector 關鍵指標

| 指標名稱 | 類型 | 說明 | Labels |
|---------|------|------|--------|
| `collector_running` | Gauge | Collector 運行狀態 (0/1) | - |
| `collector_uptime_seconds` | Gauge | 運行時間（秒） | - |
| `collector_ohlcv_collected_total` | Counter | K 線收集總數 | exchange, symbol, timeframe |
| `collector_api_requests_total` | Counter | API 請求總數 | exchange, endpoint, status |
| `collector_api_request_duration_seconds` | Histogram | API 請求延遲 | exchange, endpoint |
| `collector_data_quality_score` | Gauge | 資料品質分數 (0-100) | exchange, symbol, timeframe |
| `collector_validation_failures_total` | Counter | 驗證失敗總數 | exchange, symbol |
| `collector_consecutive_failures` | Gauge | 連續失敗計數 | exchange, symbol |
| `collector_backfill_tasks_queued` | Gauge | 補資料任務排隊數 | priority |

### WebSocket Collector 關鍵指標

| 指標名稱 | 類型 | 說明 | Labels |
|---------|------|------|--------|
| `ws_collector_running` | Gauge | WebSocket Collector 運行狀態 (0/1) | - |
| `ws_collector_uptime_seconds` | Gauge | 運行時間（秒） | - |
| `ws_collector_connection_status` | Gauge | WebSocket 連線狀態 (0/1) | exchange |
| `ws_collector_messages_total` | Counter | WebSocket 訊息總數 | exchange, type |
| `ws_collector_reconnects_total` | Counter | 重連總次數 | exchange |
| `ws_collector_errors_total` | Counter | 錯誤總次數 | exchange, error_type |
| `ws_collector_orderbook_best_bid_price` | Gauge | 最佳買價 | exchange, symbol |
| `ws_collector_orderbook_best_ask_price` | Gauge | 最佳賣價 | exchange, symbol |
| `ws_collector_orderbook_spread` | Gauge | 訂單簿價差（絕對值） | exchange, symbol |
| `ws_collector_orderbook_spread_bps` | Gauge | 訂單簿價差（基點） | exchange, symbol |
| `ws_collector_orderbook_snapshots_total` | Counter | 訂單簿快照總數 | exchange, symbol |
| `ws_collector_redis_queue_size` | Gauge | Redis 佇列大小 | queue_type |
| `ws_collector_redis_queue_push_total` | Counter | Redis 推送總數 | queue_type |

---

## 🎯 最佳實踐

### 監控策略

1. **實時監控**
   - 使用 10s 自動刷新監控關鍵指標
   - 關注 API Success Rate、連線狀態、價差異常

2. **歷史分析**
   - 調整時間範圍查看長期趨勢
   - 使用 Last 24h 或 Last 7d 進行週期性分析

3. **告警設置**
   - 在 Prometheus 中配置告警規則
   - 整合 Alertmanager 發送通知

4. **性能優化**
   - 監控 API 延遲百分位數
   - 識別慢查詢與瓶頸

### Dashboard 維護

1. **定期備份**
   ```bash
   # 匯出所有 dashboards
   curl -u admin:admin "http://localhost:3000/api/search?type=dash-db" | \
     python3 -m json.tool > dashboards_backup.json
   ```

2. **版本控制**
   - Dashboard JSON 文件已納入 Git 版本控制
   - 修改後提交變更並註明原因

3. **測試驗證**
   - 修改後先在測試環境驗證
   - 確認查詢效能不影響 Prometheus

---

## 📚 相關文檔

- [PHASE6_METRICS_TEST_RESULTS.md](./PHASE6_METRICS_TEST_RESULTS.md) - Metrics Exporter 測試報告
- [Prometheus 配置](../monitoring/prometheus/prometheus.yml)
- [Grafana 官方文檔](https://grafana.com/docs/)
- [PromQL 查詢語法](https://prometheus.io/docs/prometheus/latest/querying/basics/)

---

## ✅ 總結

本指南涵蓋了 Grafana Dashboards 的完整使用方式，包括：
- 快速啟動與訪問
- 兩個 Dashboard 的詳細面板說明
- Dashboard 操作與互動
- 配置文件管理
- 常見問題排查
- 監控指標參考
- 最佳實踐建議

如有任何問題或建議，請參考相關文檔或聯繫系統管理員。

---

**文檔維護**: 本文檔應隨 Dashboard 更新而更新
**最後更新**: 2025-12-28
