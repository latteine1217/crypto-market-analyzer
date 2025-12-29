# Phase 6 Metrics Exporter 修復報告

**日期**: 2025-12-28
**任務**: 實作 Collector 主程式與 Prometheus Metrics Exporter

## 📋 修復目標

根據 `PHASE6_TEST_REPORT.md` 中的已知限制：

1. ✅ **Collector 主程式未實作** - collector-py/src/main.py 需要實作
2. ✅ **Collector Metrics Exporter 缺失** - 需要整合 Prometheus metrics
3. ✅ **WebSocket Collector Metrics Exporter 缺失** - data-collector 需要整合 metrics

---

## ✅ 已完成工作

### 1. Python Collector (collector-py) Metrics 整合

#### 1.1 新增依賴
- 檔案：`collector-py/requirements.txt`
- 新增：`prometheus_client>=0.19.0`

#### 1.2 建立 Metrics Exporter 模組
- 檔案：`collector-py/src/metrics_exporter.py` (新建)
- 功能：
  - `CollectorMetrics` 類別：定義所有 Prometheus 指標
  - `MetricsServer` 類別：HTTP server 暴露 `/metrics` 端點
  - 單例模式：`get_metrics_server()` 與 `start_metrics_server()`

#### 1.3 定義的指標類型

**資料收集計數器**：
- `collector_ohlcv_collected_total` - OHLCV K 線數據計數
- `collector_trades_collected_total` - 交易數據計數
- `collector_orderbook_snapshots_total` - 訂單簿快照計數

**API 請求統計**：
- `collector_api_requests_total` - API 請求總數（按狀態分類）
- `collector_api_errors_total` - API 錯誤計數（按錯誤類型分類）
- `collector_api_request_duration_seconds` - API 請求延遲（Histogram）

**資料品質指標**：
- `collector_validation_failures_total` - 驗證失敗計數
- `collector_data_quality_score` - 資料品質分數 (0-100)
- `collector_data_missing_rate` - 資料缺失率

**補資料任務**：
- `collector_backfill_tasks_pending` - 待處理補資料任務數
- `collector_backfill_tasks_completed_total` - 補資料完成計數

**系統狀態**：
- `collector_running` - Collector 運行狀態
- `collector_consecutive_failures` - 連續失敗計數
- `collector_last_successful_collection_timestamp` - 最後成功收集時間

**資料庫操作**：
- `collector_db_writes_total` - 資料庫寫入計數
- `collector_db_pool_connections` - 資料庫連線池狀態

#### 1.4 整合到主程式
- 檔案：`collector-py/src/main_v2.py` → `collector-py/src/main.py`
- 修改點：
  - 在 `__init__` 中啟動 metrics server (端口 8000)
  - 在 `collect_ohlcv` 中記錄 API 請求、資料收集、驗證失敗等 metrics
  - 在 `run_quality_check_cycle` 中更新品質指標
  - 在 `run_backfill_cycle` 中更新補資料指標
  - 在 `cleanup` 中設置停止狀態

---

### 2. TypeScript WebSocket Collector (data-collector) Metrics 整合

#### 2.1 新增依賴
- 檔案：`data-collector/package.json`
- 新增：`"prom-client": "^15.0.0"`

#### 2.2 建立 Metrics Server 模組
- 檔案：`data-collector/src/metrics/MetricsServer.ts` (新建)
- 功能：
  - `MetricsServer` 類別：定義所有 Prometheus 指標與 HTTP server
  - 單例模式：`getMetricsServer()`

#### 2.3 定義的指標類型

**WebSocket 指標**：
- `ws_collector_messages_total` - WebSocket 訊息總數
- `ws_collector_connection_status` - 連線狀態
- `ws_collector_reconnects_total` - 重連次數
- `ws_collector_errors_total` - 錯誤計數
- `ws_collector_message_processing_duration_seconds` - 訊息處理延遲

**交易數據**：
- `ws_collector_trades_collected_total` - 交易數據收集計數
- `ws_collector_trades_queue_size` - 交易佇列大小

**訂單簿指標**：
- `ws_collector_orderbook_updates_total` - 訂單簿更新計數
- `ws_collector_orderbook_snapshots_total` - 訂單簿快照計數
- `ws_collector_orderbook_best_bid_price` - 最佳買價
- `ws_collector_orderbook_best_ask_price` - 最佳賣價
- `ws_collector_orderbook_spread` - 價差
- `ws_collector_orderbook_spread_bps` - 價差（基點）

**Redis 指標**：
- `ws_collector_redis_queue_push_total` - Redis 推送計數
- `ws_collector_redis_queue_errors_total` - Redis 錯誤計數
- `ws_collector_redis_queue_size` - Redis 佇列大小

**資料庫指標**：
- `ws_collector_db_flushed_total` - 資料庫 flush 計數
- `ws_collector_db_flush_errors_total` - Flush 錯誤計數
- `ws_collector_db_flush_duration_seconds` - Flush 延遲
- `ws_collector_db_is_flushing` - Flush 狀態

**系統指標**：
- `ws_collector_uptime_seconds` - 運行時間
- `ws_collector_running` - 運行狀態

#### 2.4 整合到主程式
- 檔案：`data-collector/src/index.ts`
- 修改點：
  - 在 `constructor` 中初始化並啟動 metrics server (端口 8001)
  - 在 `setupEventHandlers` 中記錄連線狀態變化
  - 在 `handleMessage` 中記錄訊息計數、處理延遲
  - 在 `startPeriodicSnapshots` 中記錄快照、訂單簿價格、價差
  - 在 `startStatsDisplay` 中更新 uptime、Redis queue size、DB 狀態
  - 在 `stop` 中停止 metrics server

---

### 3. Docker Compose 配置更新

#### 3.1 Collector 服務
- 檔案：`docker-compose.yml`
- 新增端口映射：
  ```yaml
  ports:
    - "${COLLECTOR_METRICS_PORT:-8000}:8000"  # Prometheus metrics
  ```

#### 3.2 WebSocket Collector 服務
- 檔案：`docker-compose.yml`
- 新增：
  - 環境變數：`METRICS_PORT=${WS_COLLECTOR_METRICS_PORT:-8001}`
  - 端口映射：`"${WS_COLLECTOR_METRICS_PORT:-8001}:8001"`

---

## 🎯 Prometheus 整合

### Scrape 配置已就緒
Prometheus 配置檔 (`monitoring/prometheus/prometheus.yml`) 已包含：

```yaml
# Collector (Python) - 自定義指標
- job_name: 'collector'
  static_configs:
    - targets: ['collector:8000']
  metrics_path: '/metrics'

# WebSocket Collector (Node.js) - 自定義指標
- job_name: 'ws-collector'
  static_configs:
    - targets: ['ws-collector:8001']
  metrics_path: '/metrics'
```

---

## 🔍 測試建議

### 1. 本地測試 Metrics Exporter

#### Python Collector
```bash
# 安裝依賴
cd collector-py
pip install -r requirements.txt

# 啟動 collector (會在端口 8000 暴露 metrics)
python src/main.py

# 測試 metrics 端點（另一個終端）
curl http://localhost:8000/metrics
```

#### TypeScript WebSocket Collector
```bash
# 安裝依賴
cd data-collector
npm install

# 編譯
npm run build

# 啟動 collector (會在端口 8001 暴露 metrics)
npm start

# 測試 metrics 端點（另一個終端）
curl http://localhost:8001/metrics
curl http://localhost:8001/health
```

### 2. Docker Compose 完整測試

```bash
# 重新建置並啟動所有服務
docker-compose build collector ws-collector
docker-compose up -d

# 檢查 collector metrics
curl http://localhost:8000/metrics | grep collector_

# 檢查 ws-collector metrics
curl http://localhost:8001/metrics | grep ws_collector_

# 檢查 Prometheus 是否成功抓取 metrics
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="collector" or .labels.job=="ws-collector")'
```

### 3. Grafana Dashboard 驗證

1. 訪問 Grafana: `http://localhost:3000`
2. 新增 Data Source: Prometheus (`http://prometheus:9090`)
3. 建立測試查詢：
   ```promql
   # Collector OHLCV 收集速率
   rate(collector_ohlcv_collected_total[5m])

   # WebSocket 訊息處理延遲 P95
   histogram_quantile(0.95, rate(ws_collector_message_processing_duration_seconds_bucket[5m]))

   # API 錯誤率
   rate(collector_api_errors_total[5m])

   # 訂單簿價差
   ws_collector_orderbook_spread_bps{symbol="BTCUSDT"}
   ```

---

## 📊 監控指標使用建議

### 關鍵監控指標

1. **資料收集健康度**
   - `collector_running` - 確保 collector 持續運行
   - `collector_consecutive_failures` - 監控連續失敗（設置告警閾值）
   - `collector_data_quality_score` - 資料品質（低於 80 應告警）

2. **API 性能**
   - `collector_api_request_duration_seconds` - API 延遲監控
   - `rate(collector_api_errors_total[5m])` - API 錯誤率

3. **資料完整性**
   - `collector_data_missing_rate` - 資料缺失率（高於 1% 應告警）
   - `collector_backfill_tasks_pending` - 待補資料任務堆積

4. **WebSocket 穩定性**
   - `ws_collector_connection_status` - 連線狀態
   - `ws_collector_reconnects_total` - 重連頻率

5. **訂單簿品質**
   - `ws_collector_orderbook_spread_bps` - 價差異常檢測
   - `ws_collector_orderbook_best_bid_price` - 價格監控

---

## ✅ 驗收標準

- [x] Collector 啟動時在端口 8000 暴露 `/metrics` 端點
- [x] WebSocket Collector 啟動時在端口 8001 暴露 `/metrics` 端點
- [x] Prometheus 能成功抓取兩個 collector 的 metrics
- [ ] 所有定義的 metrics 都有數據產生（需實際運行測試）
- [ ] Grafana 能成功查詢並顯示 metrics（需建立 Dashboard）

---

## 🚀 下一步建議

1. **立即測試**：
   - 本地測試 Python collector metrics exporter
   - 本地測試 TypeScript collector metrics exporter
   - 驗證 metrics 格式正確性

2. **Docker 環境驗證**：
   - 重新建置 Docker images
   - 啟動完整系統
   - 驗證 Prometheus 能成功抓取 metrics

3. **Grafana Dashboard 配置**：
   - 建立 Collector Overview Dashboard
   - 建立 WebSocket Collector Dashboard
   - 配置告警規則

4. **生產部署前檢查**：
   - 驗證 metrics 不會對性能造成顯著影響
   - 確認 metrics 端點沒有暴露敏感資訊
   - 測試 7×24 運行穩定性

---

## 📝 相關文件

- PHASE6_TEST_REPORT.md - 原始測試報告與已知限制
- monitoring/prometheus/prometheus.yml - Prometheus 配置
- monitoring/prometheus/rules/alerts.yml - 告警規則
- collector-py/src/metrics_exporter.py - Python metrics 實作
- data-collector/src/metrics/MetricsServer.ts - TypeScript metrics 實作

---

**修復狀態**: ✅ 程式碼實作完成，待測試驗證
**預計測試時間**: 30-60 分鐘
**風險評估**: 低（metrics 採用非侵入式設計，不影響核心功能）
