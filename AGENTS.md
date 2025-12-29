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

## 部署與監控（已具備骨架）
- `docker-compose.yml` 包含 db/redis/collector/ws/analyzer/report-scheduler/monitoring/jupyter
- Prometheus + Grafana + Alertmanager 設定檔已就位
- Report 排程腳本：每日/每週產出

## 鏈上與鯨魚追蹤
- Ethereum / Bitcoin / BSC / Tron whale tracker connectors
- Whale tracking schema 與 migration
- Chain data 收集設定與指引文件

---

# 📌 重要文件

- Collector 連接器：`collector-py/src/connectors/{binance,bybit,okx}_rest.py`
- WS Collector：`data-collector/src/binance_ws/BinanceWSClient.ts`
- 補資料排程：`collector-py/src/schedulers/backfill_scheduler.py`
- 資料品質：`collector-py/src/quality_checker.py`
- 特徵工程：`data-analyzer/src/features/`
- Feature selection：`data-analyzer/src/feature_selection/selection_pipeline.py`
- 模型註冊：`data-analyzer/src/models/model_registry.py`
- 策略/回測：`data-analyzer/src/strategies/`、`data-analyzer/src/backtesting/`
- 報表系統：`data-analyzer/src/reports/`
- Dashboard：`dashboard/static/reports_dashboard.html`
- DB migration：`database/migrations/`
- 報表說明：`data-analyzer/REPORT_USAGE.md`
- Compose：`docker-compose.yml`
- Monitoring：`monitoring/prometheus/prometheus.yml`、`monitoring/prometheus/rules/alerts.yml`、`monitoring/alertmanager/alertmanager.yml`
- Report scheduler：`scripts/report_scheduler.py`、`scripts/generate_daily_report.py`、`scripts/generate_weekly_report.py`
- Env templates：`.env.example`、`collector-py/.env.example`、`data-collector/.env.example`
- Whale tracking：`configs/whale_tracker.yml`、`database/schemas/02_blockchain_whale_tracking.sql`、`database/migrations/004_create_whale_tracking_tables.sql`
- Whale guide：`docs/BLOCKCHAIN_DATA_COLLECTION_GUIDE.md`

---

# ✅ Phase TODO（僅列未完成）

## 部署與自動化
- [ ] Docker 實測 7×24 穩定運行（含資料/日誌持久化驗證）
- [ ] 排程報表實際跑通（每日/每週）並寫入 report logs
- [ ] Prometheus + Grafana 面板與告警規則實際驗證

## 實驗管理與模型穩固
- [ ] MLflow 安裝與整合（SQLite backend + `mlruns/`）
- [ ] 記錄模型參數/指標/feature 版本/時間區間/Git hash
- [ ] 穩定 XGBoost 與 LSTM baseline
- [ ] Feature pipeline 文檔化

## 資料源擴展
- [ ] Coinbase connector（統一 schema / error handling / rate limit）
- [ ] Ethereum 大額轉帳指標（Etherscan v2）
- [ ] on-chain 特徵整合到 pipeline

## Paper Trading（研究性質）
- [ ] 準實時模式回測改造
- [ ] 虛擬交易與 PnL 紀錄表
- [ ] 風控規則（單筆 2%、每日 5%、倉位 20%）

## 性能與穩定性（按需）
- [ ] Profiling 後針對性優化
- [ ] TimescaleDB 壓縮/保留策略
- [ ] 熱路徑快取策略（Dashboard）

---

# 🧬 系統資料流（簡版）

```
[Scheduler] → [Collectors] → [TimescaleDB/Redis]
            → [Data Quality] → [Analysis/Models]
            → [Strategy/Backtest] → [Report]
```
