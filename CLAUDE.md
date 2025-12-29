# 🎯 Agent 角色定位

> **Role**: 資深 Crypto Quant & AI Engineer
> **Specialty**: 加密市場結構理解、時序資料處理、量化策略 & 風控、ML 架構設計

## 核心哲學

1. **Good Taste**：追求邏輯簡潔與資料流清晰；不用花俏但難維護的技巧。
2. **Never Break Userspace**：不破壞既有 API / 資料 schema；改動前先想清楚遷移路徑與相容性。
3. **Pragmatism**：優先解決真實交易/研究問題，而非只為指標好看。
4. **Simplicity**：每個模組只負責一件事；Collector 不做策略，Strategy 不直接碰 DB。
5. **Observability First**：沒有 log 的功能等於不存在；所有關鍵行為都必須可追蹤可回溯。

---

# 🎯 專案目標

**專案名稱**: Crypto Market Analyzer

**任務範圍**：
- 多交易所與鏈上 API 資料（OHLCV / trades / order book / on-chain）
- 標準化後寫入 TimescaleDB
- 分析與模型（預測、異常、策略回測、情緒/鏈上輔助）
- 產出可重現結果與結構化報表

**驗收指標**：
- K 線缺失率（per symbol / timeframe） ≤ 0.1%
- 訂單簿/交易序列時間戳不倒退
- 同一資料集同一策略回測結果可完全重現
- Collector 崩潰可自動重啟，錯誤有 log/錯誤碼
- 監控指標完整導出（Prometheus 格式）
- 告警規則正常觸發（資料缺失、錯誤率、服務異常）
- 容器重啟後資料完整保留（資料庫、日誌、配置）
- 報表排程準時執行且結果正確

---

# 🧠 Agent 角色與規則

## 1. Data Collector Agent
- 只負責正確完整抓資料（REST / WS / 補資料）
- 必須有 timeout / retry / rate limit
- 缺失區段只排程補資料，不補假資料
- 任務配置化（`collector.yml`），不寫死

## 2. Data Quality & Validation Agent
- 只標記（flag），不刪資料
- 修正可關閉且有 `cleaning_version`
- 驗證結果寫回 DB/metadata

## 3. Analysis Agent
- 任務至少有 baseline 模型
- 模型/特徵配置放在 `configs/models/*.yml`
- 輸出包含：預測/分類 + 信心分數 + feature/version + 時間區間

## 4. Strategy & Backtest Agent
- 僅使用清洗後資料
- 嚴格避免未來資訊
- 一致績效指標（年化報酬、Sharpe、Max DD、勝率、交易次數）
- 結果可重現（seed + `results/<exp_id>/meta.json`）

## 5. Report Agent
- Overview / Detail 分層
- 圖表資料可從 DB 或 `results/` 還原
- 標示資料期間、交易所、模型/策略版本

---

# ✅ 已實現功能（重點整理）

## 資料抓取與診斷
- REST API Collectors：Binance / Bybit / OKX
- WebSocket 實時收集：trades / order book
- 自動補資料：缺失檢測 + 優先級 + 退避重試
- 錯誤處理與日誌分類（network / rate_limit / timeout）

## 資料品質與驗證
- 時序連續性、價格跳點、成交量異常檢查
- 品質評分（0-100）
- 異常觸發補資料任務
- 追蹤表：`data_quality_summary`, `backfill_tasks`, `api_error_logs`

## 分析與模型
- 80+ 特徵（價格/成交量/技術指標/波動度）
- Feature selection pipeline
- Baseline / ML / DL 模型
- 異常偵測（Isolation Forest + Statistical）

## 策略與回測
- 統一策略介面與訊號型別
- RSI / MACD / Fractal 等策略
- 回測引擎（滑價、手續費、投組、交易規則）
- 績效指標完整且可重現

## 報表
- HTML / PDF 報表 + 郵件發送
- Dashboard 視覺化介面
- 報表紀錄表：`report_generation_logs`, `email_send_logs`

## 部署與監控
- `docker-compose.yml`：13 服務完整編排（db/redis/collector/ws/analyzer/report-scheduler/monitoring/jupyter）
- Prometheus + Grafana + Alertmanager 已驗證運行
- 3 核心告警規則（K線缺失/資料缺失率/錯誤率）
- Report 排程器：每日 08:00、每週一 09:00 自動產出
- Metrics 導出系統（Prometheus 格式）
- 長期穩定性測試工具（24h 監控腳本）
- 自動測試報告生成
- 資料持久化驗證通過（Docker volumes）
- 自動重啟機制（restart: unless-stopped）

## 資料庫連接管理
- **連接池機制**：psycopg2 ThreadedConnectionPool（min=2, max=10）
- **自動健康檢查**：連接超時（10s）+ 事務超時（30s）
- **殭屍連接監控**：自動檢測與清理 `idle in transaction (aborted)` 狀態
- **定時清理任務**：每 15 分鐘執行一次監控與清理
- **連接池指標**：Prometheus metrics 即時追蹤使用率與連接狀態
  - `collector_db_pool_connections{state}`: 連接數（active/idle/idle_in_transaction）
  - `collector_db_pool_usage_rate`: 使用率百分比（0-100）
  - `collector_db_pool_total_connections`: 總連接數

## 鏈上與鯨魚追蹤
- Ethereum / Bitcoin / BSC / Tron whale tracker connectors
- Whale tracking schema 與 migration
- Chain data 收集設定與指引文件

---

# 📌 重要文件

## 資料收集
- Collector 連接器：`collector-py/src/connectors/{binance,bybit,okx}_rest.py`
- WS Collector：`data-collector/src/binance_ws/BinanceWSClient.ts`
- 補資料排程：`collector-py/src/schedulers/backfill_scheduler.py`
- 資料品質：`collector-py/src/quality_checker.py`
- 資料驗證器：`collector-py/src/validators/data_validator.py`

## 分析與模型
- 特徵工程：`data-analyzer/src/features/`
- Feature selection：`data-analyzer/src/feature_selection/selection_pipeline.py`
- 模型註冊：`data-analyzer/src/models/model_registry.py`
- 策略/回測：`data-analyzer/src/strategies/`、`data-analyzer/src/backtesting/`

## 報表與視覺化
- 報表系統：`data-analyzer/src/reports/`
- Dashboard：`dashboard/static/reports_dashboard.html`、`dashboard/app.py`
- 報表說明：`data-analyzer/REPORT_USAGE.md`

## 資料庫
- DB schemas：`database/schemas/`
- DB migration：`database/migrations/`
- Whale tracking schema：`database/schemas/02_blockchain_whale_tracking.sql`

## 監控與測試
- Metrics 導出：`data-collector/src/metrics/MetricsServer.ts`、`collector-py/src/metrics_exporter.py`
- Prometheus 配置：`monitoring/prometheus/prometheus.yml`
- 告警規則：`monitoring/prometheus/rules/alerts.yml`
- Alertmanager：`monitoring/alertmanager/alertmanager.yml`
- Grafana dashboards：`monitoring/grafana/dashboards/long_run_test.json`
- 長期測試監控：`scripts/long_run_monitor.py`、`scripts/start_long_run_test.sh`、`scripts/stop_long_run_test.sh`
- 測試報告生成：`scripts/generate_test_report.py`
- 告警 webhook：`scripts/alert_webhook.py`
- **資料庫連接監控**：`scripts/monitor_db_connections.py` - 殭屍連接檢測與自動清理

## 排程與自動化
- Report scheduler：`scripts/report_scheduler.py`
- 日報生成：`scripts/generate_daily_report.py`
- 週報生成：`scripts/generate_weekly_report.py`

## 部署與配置
- Docker Compose：`docker-compose.yml`
- Env templates：`.env.example`、`collector-py/.env.example`、`data-collector/.env.example`
- Whale tracker 配置：`configs/whale_tracker.yml`

## 文檔
- 鏈上資料收集指南：`docs/BLOCKCHAIN_DATA_COLLECTION_GUIDE.md`
- Email 設定指南：`docs/EMAIL_SETUP_GUIDE.md`
- Grafana Dashboards 指南：`docs/GRAFANA_DASHBOARDS_GUIDE.md`
- 長期測試指南：`docs/LONG_RUN_TEST_GUIDE.md`
- 專案狀態報告：`docs/PROJECT_STATUS_REPORT.md`
- 穩定性驗證報告：`docs/STABILITY_VERIFICATION_REPORT.md`

---

# 📊 系統當前狀態

**最後驗證時間**: 2025-12-29 15:25
**測試版本**: v1.3.0

## 服務運行狀態（13/13 服務運行中）
- ✅ **TimescaleDB**: 運行正常（235 MB 資料，19 張表）
- ✅ **Redis**: 運行正常（1.42M memory, 14.8k commands）
- ✅ **Collector (Python)**: 運行正常（連接池 + 監控，Metrics port 8000）
- ✅ **WS Collector (TypeScript)**: 運行正常（Metrics port 8001）
- ✅ **Whale Tracker**: 運行正常（10 分鐘間隔）
- ✅ **Prometheus**: 運行正常（30d retention）
- ✅ **Grafana**: 運行正常（Port 3000）
- ✅ **Alertmanager**: 運行正常（SMTP configured）
- ✅ **Postgres Exporter**: 運行正常
- ✅ **Redis Exporter**: 運行正常
- ⚠️ **Node Exporter**: macOS Docker 限制（生產環境可用）
- ✅ **Report Scheduler**: 運行正常（Daily 08:00, Weekly Mon 09:00）
- ✅ **Jupyter Lab**: 運行正常（Port 8888）
- ⏸️ **Analyzer**: 批次任務（手動/排程執行）

## 資料庫連接池狀態
- **連接池配置**: min=2, max=10
- **當前連接數**: 8 (1 active, 7 idle)
- **使用率**: 80.0%
- **殭屍連接**: 0（自動監控與清理每 15 分鐘執行）
- **事務回滾率**: 0.14%（正常範圍）

## 穩定性測試結果

### 當前測試（進行中）
- **測試 ID**: stability_24h_20251229_final
- **開始時間**: 2025-12-29 15:25:41 CST
- **預計結束**: 2025-12-30 15:25:41 CST
- **監控頻率**: 每 5 分鐘
- **監控進程**: PID 49351（正常運行）

### 先前測試結果（已修復問題）
- **測試時長**: 12.08 小時（發現並修復資料庫連接問題）
- **容器重啟**: 1 次（測試期間）
- **發現問題**:
  - ✅ 已修復：資料庫殭屍連接（idle in transaction aborted）
  - ✅ 已修復：167 個 "connection already closed" 錯誤
- **實施改進**:
  - ✅ 升級到連接池機制（ThreadedConnectionPool）
  - ✅ 添加自動健康檢查與重連
  - ✅ 添加殭屍連接監控與自動清理
  - ✅ 添加連接池使用率 Prometheus 指標
- **CPU 使用率**: 平均 13.6%（4.0%-61.3%）
- **記憶體使用率**: 平均 78.5%（75.3%-83.4%）
- **磁碟使用率**: 平均 13.0%（12.8%-14.3%）
- **資料持久化**: ✅ 通過（重啟後完整保留）

## 資料收集統計
- **支援交易所**: Binance, Bybit, OKX（REST + WebSocket）
- **支援鏈上**: Ethereum, Bitcoin, BSC, Tron（Whale tracking）
- **資料類型**: OHLCV, Trades, Order Book, On-chain transfers
- **資料庫大小**: 235 MB（TimescaleDB）
- **日誌累積**: ~9.2 MB

---

# ⚠️ 已知問題

## 穩定性問題
1. **WebSocket 定期重連**
   - 現象：WebSocket 連接每數小時會自動重連（正常行為）
   - 影響：重連期間可能短暫遺失 1-2 秒資料（通過補資料機制修復）
   - 位置：`data-collector/src/binance_ws/BinanceWSClient.ts`
   - 優先級：低（已有補資料機制保障完整性）

2. **Node Exporter 無法在 macOS Docker 運行**
   - 現象：需掛載主機根目錄 `/`，macOS Docker Desktop 限制
   - 影響：缺少主機系統層級監控指標
   - 解決方案：生產環境 Linux 部署時可正常運行
   - 優先級：低（開發環境限制）

## 資源使用問題
3. **記憶體使用率偏高**
   - 現象：平均 78.5%（測試期間 75.3%-83.4%）
   - 影響：長時間運行後可能需要優化
   - 優先級：低（正常運行範圍）

## 待驗證項目
4. **完整 24 小時穩定性測試**
   - 現況：正在執行（2025-12-29 15:25 開始）
   - 預計完成：2025-12-30 15:25
   - 優先級：高

## 已修復問題 ✅
- ✅ **資料庫殭屍連接**（2025-12-29 修復）
  - 問題：idle in transaction (aborted) 狀態連接累積
  - 解決：實施連接池 + 自動監控清理（每 15 分鐘）
- ✅ **資料庫連接錯誤**（2025-12-29 修復）
  - 問題：167 個 "connection already closed" 錯誤
  - 解決：連接健康檢查 + 自動重連機制

---

# 📋 Phase TODO（尚未實現功能）

## 實驗管理與模型穩固
- [ ] MLflow 安裝與整合（SQLite backend + `mlruns/`）
- [ ] 記錄模型參數/指標/feature 版本/時間區間/Git hash
- [ ] 穩定 XGBoost 與 LSTM baseline（消除警告、確保可重現）
- [ ] Feature pipeline 完整文檔化

## 資料源擴展
- [ ] Coinbase REST API connector（統一 schema / error handling / rate limit）
- [ ] Ethereum 大額轉帳指標（Etherscan API v2 整合）
- [ ] On-chain 特徵整合到 analysis pipeline（目前僅收集未分析）
- [ ] 更多鏈上指標（Gas price, Active addresses, DEX volume）

## Paper Trading（研究性質）
- [ ] 準實時模式回測改造（模擬實盤延遲與滑點）
- [ ] 虛擬交易記錄表設計與實現
- [ ] PnL 追蹤與績效統計
- [ ] 風控規則實現（單筆 2%、每日 5%、倉位 20%）
- [ ] 訂單模擬器（市價/限價/止損）

## 性能與穩定性優化（按需）
- [ ] Python/TypeScript 程式碼 profiling
- [ ] TimescaleDB 自動壓縮策略（chunk_time_interval 調整）
- [ ] TimescaleDB 資料保留政策（自動刪除舊資料）
- [ ] Dashboard 熱路徑快取策略（Redis/內存）
- [ ] Database query 優化（索引、查詢計劃分析）
- [ ] WebSocket 重連機制優化（減少重連頻率）

## 生產環境部署
- [ ] Linux 生產環境部署測試
- [ ] SSL/TLS 憑證配置（Grafana/API endpoints）
- [ ] 備份與災難恢復策略
- [ ] 多節點部署方案（如需要）

---

# 🧬 系統資料流（簡版）

```
[Scheduler] → [Collectors] → [TimescaleDB/Redis]
            → [Data Quality] → [Analysis/Models]
            → [Strategy/Backtest] → [Report]
```
