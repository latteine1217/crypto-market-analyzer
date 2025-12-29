# Crypto Market Analyzer 文檔彙整摘要

本文檔整理專案內所有 .md 文件（排除 AGENTS.md、CLAUDE.md、README.md），彙總專案功能、已實現部分、測試與結果、已知限制，並列出重點文件。

## 專案功能總覽
- 多交易所/鏈上資料收集：REST + WebSocket，涵蓋 OHLCV、trades、order book、whale transfers。
- 資料標準化與寫入 TimescaleDB，含資料品質檢查、異常標記與補資料排程。
- 特徵工程與模型評估（Baseline / ML / DL），含異常偵測。
- 策略介面、回測引擎、統一績效指標與可重現輸出。
- 報表系統（HTML/PDF/JSON）與郵件發送。
- Dashboard 與監控告警（Prometheus/Grafana/Alertmanager）。

## 已實現功能（依模組彙整）
### 資料收集（REST / WebSocket）
- REST connectors：Binance / Bybit / OKX。
- WebSocket 實時收集：Trades、Order Book，含本地 order book 維護與快照。
- Redis 佇列暫存 + 批次寫入 TimescaleDB。
- 自動重連、錯誤分類與重試。

### 資料品質與補資料
- 時序連續性、價格跳點、成交量異常檢查。
- 品質評分（0-100）與品質摘要表。
- 缺失區段檢測與補資料排程、優先級、退避重試。

### 鏈上/鯨魚追蹤
- Ethereum / BSC / Bitcoin / Tron 追蹤器與 schema。
- Etherscan v2 等 API 配置與測試流程（需有效 key）。
- Whale tracking ETL、驗證器、載入器與測試腳本。

### 特徵工程 / 模型 / 異常偵測
- 80+ 技術指標與價格/成交量/波動度特徵。
- Feature selection pipeline。
- Baseline / ML / DL 模型（XGBoost、LSTM）。
- 異常偵測：Isolation Forest + 統計方法（Z-score/IQR）。

### 策略與回測
- 統一策略介面、訊號型別。
- RSI / MACD / 分形與組合策略。
- 回測引擎：滑價、手續費、投組、績效指標。

### 報表與排程
- ReportAgent 整合資料品質、回測、模型結果。
- Overview/Detail 雙層報表（HTML/PDF/JSON）。
- 郵件發送與 DB 日誌記錄。
- 每日/每週報表排程腳本與 APScheduler 範例。

### Dashboard
- Plotly Dash 多頁面（Market Overview / Technical / Signals / Liquidity）。
- 多層級刷新（1s/5s/30s）+ Redis 快取。

### 監控與可觀測性
- Collector 與 WS Collector Prometheus metrics exporter（30+ / 20+ 指標）。
- Grafana dashboards（Collector / WS Collector），含變數過濾。
- Alertmanager 告警配置、Prometheus 抓取與警規範本。

### 資料庫優化
- TimescaleDB 連續聚合與分層保留策略。
- 重要事件保留機制、最佳粒度查詢函數。

## 測試與研究結果摘要
- Phase 6 測試：Docker Compose、監控配置、服務啟動、依賴檢查全數通過。
- Metrics Exporter 測試：Collector/WS Collector metrics 端點可用，Prometheus 抓取為 up。
- WS Collector healthcheck 問題調查：原 Redis ping healthcheck 不相容新版 redis client；建議改為 HTTP `/metrics` 健康檢查。
- 穩定性驗證（6+ 小時）：11/13 服務可用、資料持久化與重啟恢復正常；WS Collector 狀態不穩定但資料仍寫入。
- 模型評估：XGBoost 明顯優於 LSTM（RMSE/MAE/方向準確率）；LSTM 完整特徵仍需改進。
- 回測結果：多策略基準表現偏弱，需強化風控與參數搜尋。

## 已知限制與待辦（來自文件整理）
- 長期 7×24 穩定性與告警規則實測仍需完整執行。
- 報表排程需驗證每日/每週實際產出與 log 寫入。
- WS 連線不穩定與 healthcheck 閾值需持續調整觀測。
- BscScan API 需獨立 key；CoinGecko/Blockchair 有免費限額限制。
- LSTM 模型特徵工程與架構仍需優化。

## 重點文件（排除 AGENTS.md / CLAUDE.md / README.md）
### 資料收集與品質
- `collector-py/src/main.py`
- `collector-py/src/connectors/binance_rest.py`
- `collector-py/src/connectors/bybit_rest.py`
- `collector-py/src/connectors/okx_rest.py`
- `collector-py/src/quality_checker.py`
- `collector-py/src/schedulers/backfill_scheduler.py`
- `data-collector/src/binance_ws/BinanceWSClient.ts`
- `data-collector/src/orderbook_handlers/OrderBookManager.ts`
- `data-collector/src/queues/RedisQueue.ts`
- `data-collector/src/database/DBFlusher.ts`

### 鏈上/鯨魚追蹤
- `configs/whale_tracker.yml`
- `collector-py/src/connectors/ethereum_whale_tracker.py`
- `collector-py/src/connectors/bsc_whale_tracker.py`
- `collector-py/src/connectors/bitcoin_whale_tracker.py`
- `collector-py/src/utils/config_loader.py`
- `database/migrations/004_create_whale_tracking_tables.sql`
- `database/schemas/02_blockchain_whale_tracking.sql`

### 特徵/模型/異常
- `data-analyzer/src/features/`
- `data-analyzer/src/feature_selection/selection_pipeline.py`
- `data-analyzer/src/models/model_registry.py`
- `data-analyzer/src/models/anomaly/isolation_forest_detector.py`
- `data-analyzer/src/models/anomaly/statistical_detector.py`

### 策略與回測
- `data-analyzer/src/strategies/`
- `data-analyzer/src/backtesting/`

### 報表與排程
- `data-analyzer/src/reports/report_agent.py`
- `data-analyzer/src/reports/html_generator.py`
- `data-analyzer/src/reports/pdf_generator.py`
- `data-analyzer/src/reports/email_sender.py`
- `scripts/report_scheduler.py`
- `scripts/generate_daily_report.py`
- `scripts/generate_weekly_report.py`

### Dashboard
- `dashboard/app.py`
- `dashboard/data_loader.py`
- `dashboard/cache_manager.py`
- `dashboard/pages/overview.py`
- `dashboard/pages/technical.py`
- `dashboard/pages/signals.py`
- `dashboard/pages/liquidity.py`

### 監控與告警
- `collector-py/src/metrics_exporter.py`
- `data-collector/src/metrics/MetricsServer.ts`
- `monitoring/prometheus/prometheus.yml`
- `monitoring/prometheus/rules/alerts.yml`
- `monitoring/alertmanager/alertmanager.yml`
- `monitoring/grafana/provisioning/dashboards/dashboards/`

### 部署、測試與資料庫
- `docker-compose.yml`
- `database/migrations/004_README.md`
- `database/migrations/004_continuous_aggregates_and_retention.sql`
- `docs/PHASE6_TEST_REPORT.md`
- `docs/PHASE6_METRICS_TEST_RESULTS.md`
- `docs/PHASE6_METRICS_FIX_REPORT.md`
- `docs/STABILITY_VERIFICATION_REPORT.md`
- `docs/WS_COLLECTOR_HEALTHCHECK_INVESTIGATION.md`
- `docs/LONG_RUN_TEST_GUIDE.md`
- `docs/GRAFANA_DASHBOARDS_GUIDE.md`
- `docs/EMAIL_SETUP_GUIDE.md`
- `docs/PROJECT_STATUS_REPORT.md`

### 結果與產出（Artifacts）
- `data-analyzer/results/xgboost_btc_1h/evaluation_report.md`
- `data-analyzer/results/lstm_full_features_btc_1h/evaluation_report.md`
- `data-analyzer/results/model_comparison/comparison_report.md`
- `data-analyzer/results/final_model_comparison/comprehensive_comparison.md`
- `data-analyzer/results/backtest_results/backtest_report.md`
