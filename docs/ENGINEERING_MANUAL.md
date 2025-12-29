# Crypto Market Analyzer 工程手冊

## 專案功能總覽
- 多交易所與鏈上資料蒐集：OHLCV、trades、order book、鏈上大額轉帳
- 資料標準化並寫入 TimescaleDB，支援品質檢查與補資料流程
- 特徵工程與模型評估（Baseline / ML / DL）
- 策略與回測引擎，輸出完整績效指標
- 報表系統（HTML/PDF/JSON）與 Dashboard
- 監控與告警（Prometheus/Grafana/Alertmanager）

## 已實現功能（彙整自所有文件）

### 資料收集（REST / WebSocket）
- REST connectors：Binance / Bybit / OKX
- WebSocket 實時收集：trades / order book
- Redis 佇列 + DB Flusher 批次寫入
- 自動補資料任務排程（缺失檢測 + 優先級 + 重試）
- 完整錯誤分類與重試（network / rate_limit / timeout 等）

### 資料品質與驗證
- 品質檢查：時間序列連續性、價格跳點、成交量異常
- 品質分數（0-100）與品質摘要表
- 檢查結果寫入 DB，異常區段自動排程補資料

### 鏈上/鯨魚追蹤
- Ethereum / BSC / Bitcoin / Tron 追蹤器
- Etherscan API v2 整合
- Whale tracking schema、驗證器、載入器與 ETL 測試
- 交易所流入/流出與異常大額交易標記

### 特徵工程與模型
- 價格、成交量、技術指標、波動度等 80+ 特徵
- 特徵 pipeline 與特徵選擇
- Baseline 模型：MA/EMA/Naive
- ML/DL 模型：XGBoost、LSTM
- 異常偵測：Isolation Forest + 統計方法（Z-score/IQR）

### 策略與回測
- 統一策略介面
- RSI / MACD / 分形策略與組合策略
- 回測引擎（手續費、滑價、資金曲線、績效指標）
- Backtest 報告與圖表輸出

### 報表系統
- ReportAgent 整合資料品質、模型結果、回測績效
- Overview / Detail 雙層報表
- HTML / PDF / JSON 輸出
- 郵件發送與報表日誌表

### Dashboard
- Plotly Dash 實時 Dashboard
- 多層級刷新（1s/5s/30s）+ Redis 快取
- 市場概覽、技術分析、交易信號、流動性分析頁面

### 部署與監控
- `docker-compose.yml` 已包含完整服務組件
- Prometheus + Grafana + Alertmanager 設定檔
- 報表排程腳本（每日/每週）
- 統一 JSON 日誌與輪轉策略

## 研究/測試與結果摘要
- ETL 測試：Ethereum 成功，BSC v2 API 端點待確認（可回退 v1）
- 模型比較：XGBoost 明顯優於 LSTM（RMSE、方向準確率）
- LSTM 完整特徵版本仍需改進（方向準確率接近隨機）
- 回測報告：多策略基準與風險提示

## 重要文件（不包含 AGENTS/CLAUDE/README）

### 部署與監控
- `docs/PHASE6_DEPLOYMENT_GUIDE.md`
- `docs/phase6_implementation_plan.md`
- `docker-compose.yml`
- `monitoring/prometheus/prometheus.yml`
- `monitoring/prometheus/rules/alerts.yml`
- `monitoring/alertmanager/alertmanager.yml`

### 資料收集與交易所連接
- `EXCHANGE_SETUP_GUIDE.md`
- `EXCHANGE_BLOCKING_ANALYSIS.md`
- `data-collector/README.md`

### 鏈上與鯨魚追蹤
- `docs/BLOCKCHAIN_DATA_COLLECTION_GUIDE.md`
- `collector-py/BLOCKCHAIN_API_SETUP.md`
- `database/schemas/02_blockchain_whale_tracking.sql`
- `database/migrations/004_create_whale_tracking_tables.sql`

### 資料品質與補資料
- `PHASE_1_1_COMPLETION.md`
- `collector-py/src/quality_checker.py`
- `collector-py/src/schedulers/backfill_scheduler.py`
- `database/migrations/003_data_quality_tables.sql`

### WebSocket 即時收集
- `PHASE_1_2_COMPLETION.md`
- `data-collector/src/binance_ws/BinanceWSClient.ts`
- `data-collector/src/orderbook_handlers/OrderBookManager.ts`
- `data-collector/src/queues/RedisQueue.ts`
- `data-collector/src/database/DBFlusher.ts`

### 分析與模型
- `PHASE_2_3_COMPLETION.md`
- `data-analyzer/src/features/`
- `data-analyzer/src/feature_selection/selection_pipeline.py`
- `data-analyzer/src/models/`
- `data-analyzer/src/anomaly/`

### 回測與報表
- `data-analyzer/src/backtesting/`
- `data-analyzer/REPORT_USAGE.md`
- `data-analyzer/PHASE5_COMPLETE.md`
- `database/migrations/005_report_logs.sql`
- `dashboard/README.md`

### TimescaleDB 優化
- `database/migrations/004_README.md`
- `database/migrations/004_continuous_aggregates_and_retention.sql`

### 測試與驗證
- `docs/ETL_TEST_RESULTS.md`
- `collector-py/test_blockchain_etl.py`
- `collector-py/test_blockchain_apis.py`
- `collector-py/test_new_features.py`
- `data-analyzer/test_phase_2_3.py`
- `data-analyzer/test_report_system.py`

### 研究結果與報告（Artifacts）
- `data-analyzer/results/xgboost_btc_1h/evaluation_report.md`
- `data-analyzer/results/lstm_full_features_btc_1h/evaluation_report.md`
- `data-analyzer/results/model_comparison/comparison_report.md`
- `data-analyzer/results/final_model_comparison/comprehensive_comparison.md`
- `data-analyzer/results/backtest_results/backtest_report.md`

## 系統資料流（簡版）
```
[Scheduler] → [Collectors] → [TimescaleDB/Redis]
            → [Data Quality] → [Analysis/Models]
            → [Strategy/Backtest] → [Report]
```

## 未完成/待驗證項目（整合自文件的提示）
- BSC v2 API 端點確認與修正（必要時回退 v1）
- LSTM 模型改進與特徵篩選（現階段效果不佳）
- 部署後 7×24 穩定性驗證與告警規則實測
