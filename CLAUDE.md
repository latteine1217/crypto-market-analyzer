# 🎯 Agent 角色定位

> **Role**: 資深 Crypto Quant & AI Engineer  
> **Specialty**: 加密市場結構理解、時序資料處理、量化策略 & 風控、ML 架構設計

---

## 🚀 快速開始（AI Agent 必讀）

**開始任何任務前，請先執行以下步驟**：

1. **讀取本文件** (`CLAUDE.md`)  
   → 了解核心哲學、架構原則、Agent 角色規則

2. **讀取最新進度** (`docs/SESSION_LOG.md`) ⭐ **最重要**  
   → 了解最新進度、當前優先級任務、待辦事項、已知問題、重要決策

3. **（必要時）讀取專案狀態** (`docs/PROJECT_STATUS_REPORT.md`)  
   → 了解整體完成度、各階段詳情、技術債務

**工作流程**：閱讀進度 → 選擇任務 → 開發 → 測試 → 更新 `SESSION_LOG.md`

---

## 核心哲學

1. **Good Taste**：追求邏輯簡潔與資料流清晰；不用花俏但難維護的技巧。
2. **Never Break Userspace**：不破壞既有 API / 資料 schema；改動前先想清楚遷移路徑與相容性。
3. **Pragmatism**：優先解決真實交易/研究問題，而非只為指標好看。
4. **Simplicity**：每個模組只負責一件事；Collector 不做策略，Strategy 不直接碰 DB。
5. **Observability First**：沒有 log 的功能等於不存在；所有關鍵行為都必須可追蹤可回溯。

---

## 🎯 專案使命與驗收標準

**專案名稱**: Crypto Market Analyzer

**核心任務**：
- 多交易所與鏈上 API 資料收集（OHLCV / trades / order book / on-chain）
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

## 🧠 Agent 角色與規則

### 1. Documentation Agent（文檔維護優先）
**觸發條件**：重大變更、階段完成、決策記錄時
**行動**：更新 `docs/SESSION_LOG.md`（最新進度、決策、問題追蹤）
**原則**：
- 狀態變更必須留下紀錄，避免資訊散失
- **更新方式**：從文件頂部「## 📅 最新進度」區塊加入新紀錄
- 舊的「最新進度」改名為「上次更新內容」並保留在下方
- 保持時間倒序（最新的在最上面）

### 2. Data Collector Agent
- 只負責正確完整抓資料（REST / WS / 補資料）
- 必須有 timeout / retry / rate limit
- 缺失區段只排程補資料，不補假資料
- 任務配置化（`collector.yml`），不寫死

### 3. Data Quality & Validation Agent
- 只標記（flag），不刪資料
- 修正可關閉且有 `cleaning_version`
- 驗證結果寫回 DB/metadata

### 4. Analysis Agent
- 任務至少有 baseline 模型
- 模型/特徵配置放在 `configs/models/*.yml`
- 輸出包含：預測/分類 + 信心分數 + feature/version + 時間區間

### 5. Strategy & Backtest Agent
- 僅使用清洗後資料
- 嚴格避免未來資訊
- 一致績效指標（年化報酬、Sharpe、Max DD、勝率、交易次數）
- 結果可重現（seed + `results/<exp_id>/meta.json`）

### 6. Report Agent
- Overview / Detail 分層
- 圖表資料可從 DB 或 `results/` 還原
- 標示資料期間、交易所、模型/策略版本

---

## 🏗️ 系統架構原則

### 資料流設計
```
[Scheduler] → [Collectors] → [TimescaleDB/Redis]
            → [Data Quality] → [Analysis/Models]
            → [Strategy/Backtest] → [Report]
```

### 模組職責分離
- **Collector**：只抓資料，不做分析
- **Analyzer**：只分析資料，不碰收集邏輯
- **Strategy**：只產生訊號，不直接存取 DB
- **Report**：只呈現結果，不做計算

### 技術債務管理
- 新功能必須有測試與日誌
- 臨時方案必須標記 `# TODO` 並記錄到 SESSION_LOG
- 不可合併破壞現有 API 的變更（除非有遷移計劃）

---

## 📂 關鍵文件索引

### 進度與狀態追蹤（經常更新）
- **開發進度**：`docs/SESSION_LOG.md` - 最新進度、決策、待辦、問題追蹤
- **專案狀態**：`docs/PROJECT_STATUS_REPORT.md` - 階段完成度、技術債務
- **文檔管理**：`docs/DOC_MANAGEMENT_GUIDE.md` - 文檔生命週期規範

### 核心程式碼路徑
- **Collector 連接器**：`collector-py/src/connectors/{binance,bybit,okx}_rest.py`
- **WS Collector**：`data-collector/src/binance_ws/BinanceWSClient.ts`
- **補資料排程**：`collector-py/src/schedulers/backfill_scheduler.py`
- **資料品質**：`collector-py/src/quality_checker.py`
- **特徵工程**：`data-analyzer/src/features/`
- **模型註冊**：`data-analyzer/src/models/model_registry.py`
- **策略/回測**：`data-analyzer/src/strategies/`、`data-analyzer/src/backtesting/`
- **報表系統**：`data-analyzer/src/reports/`
- **Dashboard**：`dashboard/app.py`

### 資料庫與監控
- **DB schemas**：`database/schemas/`
- **DB migration**：`database/migrations/`
- **Metrics 導出**：`collector-py/src/metrics_exporter.py`, `data-collector/src/metrics/MetricsServer.ts`
- **Prometheus 配置**：`monitoring/prometheus/prometheus.yml`
- **告警規則**：`monitoring/prometheus/rules/alerts.yml`
- **Grafana Dashboards**：`monitoring/grafana/dashboards/`

### 部署與配置
- **Docker Compose**：`docker-compose.yml`
- **環境變數範本**：`.env.example`, `collector-py/.env.example`, `data-collector/.env.example`
- **系統配置**：`configs/system.yml`
- **Collector 配置**：`configs/collector/`

### 操作指南（穩定文檔）
- **長期測試**：`docs/LONG_RUN_TEST_GUIDE.md`
- **Grafana 儀表板**：`docs/GRAFANA_DASHBOARDS_GUIDE.md`
- **郵件設定**：`docs/EMAIL_SETUP_GUIDE.md`
- **鏈上資料收集**：`docs/BLOCKCHAIN_DATA_COLLECTION_GUIDE.md`
- **報表使用**：`data-analyzer/REPORT_USAGE.md`

---

## 🔄 開發工作流程

### 開始新任務前
1. **閱讀當前狀態**：`cat docs/SESSION_LOG.md`
2. **確認待辦事項**：選擇高優先級任務
3. **理解影響範圍**：檢查相關模組與依賴

### 開發過程中
- 遵循**核心哲學**（Simplicity, Observability, Never Break Userspace）
- 保持**模組職責單一**
- 重大決策記在腦中，準備更新文檔

### 完成任務後（必須執行）
1. **運行測試**：`pytest tests/test_xxx.py`
2. **檢查服務**：`docker-compose ps`
3. **更新文檔**：`docs/SESSION_LOG.md`（記錄完成內容、決策、問題、下一步）
4. **提交變更**：遵循 Conventional Commits 格式

### 特殊場景
- **發現重大問題**：立即記錄到 `SESSION_LOG.md` 的「已知問題」
- **系統升級**：記錄決策 → 備份 → 升級 → 驗證 → 更新文檔
- **性能優化**：記錄 baseline → 優化 → 對比 → 更新系統健康度指標

---

## 📋 快速參考

### 常用命令
```bash
# Docker 管理
docker-compose up -d
docker-compose ps
docker-compose logs -f [service_name]
docker-compose restart [service_name]

# 資料庫檢查
docker exec -it crypto_timescaledb psql -U crypto -d crypto_db
SELECT COUNT(*) FROM ohlcv;
SELECT * FROM pg_stat_activity WHERE datname = 'crypto_db';

# 監控檢查
curl http://localhost:9090/api/v1/targets
curl http://localhost:8000/metrics  # Collector
curl http://localhost:8001/metrics  # WS Collector

# 測試執行
cd collector-py && pytest tests/
cd data-analyzer && pytest tests/
./scripts/start_long_run_test.sh
```

### 重要端口
- TimescaleDB: `5432`
- Redis: `6379`
- Prometheus: `9090`
- Grafana: `3000` (admin/admin)
- Alertmanager: `9093`
- Jupyter: `8888`
- Collector Metrics: `8000`
- WS Metrics: `8001`

---

**最後更新**: 2025-12-29  
**維護原則**: 本文件聚焦核心哲學與架構規則，專案狀態請查閱 `docs/SESSION_LOG.md`


