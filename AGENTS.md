# 🎯 Agent 角色定位

> **Role**: 資深 Crypto 量化交易員、typescript資深工程師 
> **Specialty**: 加密市場結構理解、時序資料處理、監控系統架構、即時 Dashboard 開發

---

## 🚀 快速開始（AI Agent 必讀）

**開始任何任務前，請先執行以下步驟**：

1. **讀取本文件** (`AGENTS.md`)  
   → 了解核心哲學、架構原則、Agent 角色規則

2. **讀取最新進度** (`docs/SESSION_LOG.md`) ⭐ **最重要**  
   → 了解最新進度、當前優先級任務、待辦事項、已知問題、重要決策

3. **（可選）讀取補充狀態文件**（若存在 `docs/PROJECT_STATUS_REPORT.md`）  
   → 目前以 `docs/SESSION_LOG.md` 為主，補充文件僅作參考

**工作流程**：閱讀進度 → 選擇任務 → 開發 → 測試 → 更新 `SESSION_LOG.md`

---

## 🎯 專案使命與驗收標準

**專案名稱**: Crypto Market Dashboard

**核心任務**：
- **多維度資料收集**:
  - **交易所市場數據**: Bybit OHLCV, Trades, Orderbook 即時抓取
- **總體經濟與資金流**: 美國現貨 ETF 流量 (Farside)、鏈上數據
  - **市場情緒**: Fear & Greed Index 等情緒指標追蹤
- **標準化存儲**: 資料統一格式後寫入 TimescaleDB，並實施資料保留政策 (Retention Policies)
- **即時視覺化**: 提供高效、易讀的 K 線圖與深度圖，支援多種技術指標與時區切換
- **全面監控**: 透過 Prometheus + Grafana 監控資料流健康度與系統效能

**驗收指標**：
- K 線缺失率 (per symbol / timeframe) ≤ 3%
- ETF 與總經數據每日定期更新，無缺漏
- 訂單簿/交易序列時間戳不倒退，Symbol 格式全局統一 (原生格式如 BTCUSDT)
- Collector 崩潰可自動重啟 (Docker auto-restart)，錯誤有結構化日誌
- 監控指標完整導出 (Prometheus 格式)，包含資料延遲、寫入速度等
- 告警規則正常觸發 (資料缺失、API 錯誤、磁碟空間、服務異常)
- 容器重啟後資料完整保留 (DB, Redis, Logs 持久化)
- Dashboard 查詢響應時間 < 2s (利用 Redis 快取與查詢優化)

---

## 🧠 Agent 角色與規則

### 1. Documentation Agent（文檔維護優先）
**觸發條件**：重大變更、階段完成、決策記錄時  
**行動**：更新 `docs/SESSION_LOG.md`（最新進度、決策、問題追蹤）  
**原則**：狀態變更必須留下紀錄，避免資訊散失

### 2. Data Collector Agent
- 負責多源異質資料抓取 (REST / WS / Web Scraping)
  - **Crypto Market**: OHLCV, Orderbook, Trades (Bybit)
- **Macro & Flows**: Farside ETF Data, Fear & Greed Index
- 必須遵循 Rate Limit 與 Timeout 限制，具備重試機制
- 確保 Symbol 解析符合專案統一標準 (`shared/utils/symbol_utils.py`)
- 任務配置化 (`configs/collector/*.yml`)，不寫死

### 3. Data Quality & Infrastructure Agent
- 監測資料完整度與延遲，處理 TimescaleDB Hypertable 與索引優化
- 實施 Data Retention 政策，確保磁碟空間可用性
- 驗證結果寫回 DB 或 Metadata，支援品質報告產出

### 4. Dashboard & UI Agent
- 開發與維護 Next.js / TypeScript / Plotly 視覺化組件
- 負責前端效能優化 (Code Splitting, Rendering logic)
- 確保 API 與 Dashboard 之間的資料載入與快取 (Redis) 邏輯正確

### 5. Monitoring & Ops Agent
- 維護 Prometheus 告警規則與 Grafana 儀表板
- 負責 Docker 編排與容器健康檢查
- 實施自動化測試與系統快照 (Snapshot)

---

## 🏗️ 系統架構原則

### 資料流設計
```
[User] → [Nginx (Gateway :80)]
            ↓
    ┌───────┴───────┬───────────────┐
[Dashboard]    [API Server]    [Grafana]
    ↓               ↓               ↑
[Browser]      [Redis / DB]    [Prometheus]

[Scheduler] → [Collectors (Py/TS)] → [Redis Cache] → [TimescaleDB]
            → [Monitoring] → [Prometheus/Alertmanager] → [Alerts]
```

### 模組職責分離
- **Collector**: 只負責資料獲取與初步驗證，不處理複雜業務邏輯
- **Database**: 專注於時序資料存儲與高效查詢
- **API Server**: 處理資料聚合、指標計算與快取
- **Dashboard**: 專注於即時呈現與交互體驗

### 技術債務管理
- 新功能必須有單元測試 (Python: pytest, TS: Vitest)
- 臨時方案必須標記 `# TODO` 並記錄到 `SESSION_LOG`
- 不可合併破壞現有 API 的變更 (維持向後相容)

---

## 📂 關鍵文件索引

### 進度與狀態追蹤
- **開發進度**: `docs/SESSION_LOG.md` - 最新進度、決策、待辦、問題追蹤
- **專案狀態**: 目前以 `docs/SESSION_LOG.md` 為唯一維護中的狀態來源

### 核心程式碼路徑
- **REST Collector**: `collector-py/src/connectors/`
- **WS Collector**: `data-collector/src/`
- **API Server**: `api-server/src/`
- **Dashboard**: `dashboard-ts/src/`
- **共享工具**: `shared/utils/`

### 資料庫與監控
- **DB Schemas**: `database/schemas/`
- **Migrations**: `database/migrations/`
- **Metrics Exporter**: `collector-py/src/metrics_exporter.py`、`data-collector/src/metrics/MetricsServer.ts`
- **監控棧說明**: 目前專案未內建 `monitoring/` 目錄（如需 Prometheus/Grafana 請外接部署）

### 部署與配置
- **Docker Compose**: `docker-compose.yml`
- **系統配置**: `configs/collector/`

---

## 📋 快速參考

### 常用命令
```bash
# Docker 管理
docker-compose up -d
docker-compose ps
docker-compose logs -f [service_name]

# 資料庫檢查
docker exec -it crypto_timescaledb psql -U crypto -d crypto_db
\dt (列出資料表)
SELECT * FROM ohlcv ORDER BY time DESC LIMIT 10;

# 測試執行
pytest collector-py/tests/
npm test (在各專案目錄下)
```

### 重要端口
- TimescaleDB: `5432`
- Redis: `6379`
- Dashboard: `3001` (Next.js) / `8050` (Legacy Dash)
- API Server: `8080`
- Prometheus/Grafana: 目前非內建服務（外接部署時再定義端口）

---

**最後更新**: 2026-01-21  
**維護原則**: 本文件聚焦核心哲學與架構規則，實施細節請查閱 `docs/SESSION_LOG.md`
