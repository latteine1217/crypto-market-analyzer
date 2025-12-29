# Crypto Market Analyzer

加密市場數據抓取與 AI 分析系統。從主流交易所收集 OHLCV、訂單簿、交易流水及鏈上數據，儲存至 TimescaleDB 時序資料庫，並使用機器學習模型進行價格趨勢預測、異常檢測、交易策略回測與市場情緒分析。

## 🌟 核心特性

### 資料收集與管理
- ✅ **多時間粒度聚合**：自動生成 5m/15m/1h/1d 聚合資料，節省 94% 儲存空間
- ✅ **智能資料保留**：分層保留策略，7天原始資料 + 長期聚合資料
- ✅ **重要事件保護**：關鍵歷史事件（如閃崩）的原始資料永久保留
- ✅ **實時與批次收集**：REST API + WebSocket 雙模式資料收集
- ✅ **自動補資料機制**：智能檢測缺失區段並自動補齊

### 資料品質保證
- ✅ **多維度品質檢查**：時序連續性 + 價格跳點 + 成交量異常
- ✅ **品質評分系統**：0-100 分資料品質量化評估
- ✅ **異常自動處理**：觸發補資料任務並記錄日誌

### 分析與建模
- ✅ **80+ 技術指標**：價格、成交量、技術分析、波動度特徵
- ✅ **多模型支援**：Baseline（MA/EMA）、ML（XGBoost）、DL（LSTM）
- ✅ **異常偵測**：Isolation Forest + 統計方法
- ✅ **特徵選擇流程**：自動化特徵工程與篩選

### 策略與回測
- ✅ **統一策略框架**：標準化訊號介面與策略基類
- ✅ **內建策略**：RSI、MACD、Fractal 等多種策略
- ✅ **完整回測引擎**：滑價模擬 + 手續費計算 + 績效指標
- ✅ **結果可重現**：種子控制 + 完整 metadata 記錄

### 監控與可觀測性
- ✅ **完整監控棧**：Prometheus + Grafana + Alertmanager
- ✅ **50+ 監控指標**：系統、資料庫、Redis、收集器狀態
- ✅ **視覺化儀表板**：2 個預配置 Grafana Dashboards
- ✅ **智能告警**：多級別告警規則與自動通知

### 系統穩定性
- ✅ **資料庫連接池**：ThreadedConnectionPool + 自動健康檢查
- ✅ **殭屍連接清理**：定期清理長時間 idle 連接
- ✅ **自動重啟機制**：容器崩潰自動恢復
- ✅ **資料持久化**：Docker volumes 確保資料安全
- ✅ **6+ 小時穩定性驗證**：通過連續運行測試

## 系統架構

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Data Collection Layer                            │
│   ┌──────────────────────┐        ┌──────────────────────┐          │
│   │  Python REST API     │        │  Node.js WebSocket   │          │
│   │  • Binance           │        │  • Binance Trades    │          │
│   │  • Bybit             │        │  • Order Book Depth  │          │
│   │  • OKX               │        │  • Auto Reconnect    │          │
│   └──────────────────────┘        └──────────────────────┘          │
└────────────────┬─────────────────────────────┬───────────────────────┘
                 │                             │
                 ▼                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   Data Storage & Processing                          │
│   ┌─────────────────────────────────────────────────────────┐       │
│   │  TimescaleDB (時序資料庫)                                 │       │
│   │  • Hypertables & Continuous Aggregates                 │       │
│   │  • 分層保留策略 (1m→5m→15m→1h→1d)                        │       │
│   │  • 重要事件保護機制                                        │       │
│   │  • 235 MB 資料 (19 張表)                                  │       │
│   └─────────────────────────────────────────────────────────┘       │
│   ┌─────────────────────────────────────────────────────────┐       │
│   │  Redis (快取 & 佇列)                                      │       │
│   │  • WebSocket 資料暫存                                     │       │
│   │  • Dashboard 快取                                        │       │
│   └─────────────────────────────────────────────────────────┘       │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     Analysis & Strategy Layer                        │
│   ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│   │  Feature Eng.    │  │  ML Models       │  │  Strategies     │  │
│   │  • 80+ Indicators│  │  • XGBoost       │  │  • RSI          │  │
│   │  • Selection     │  │  • LSTM          │  │  • MACD         │  │
│   │  • Versioning    │  │  • Anomaly Detect│  │  • Fractal      │  │
│   └──────────────────┘  └──────────────────┘  └─────────────────┘  │
│   ┌──────────────────────────────────────────────────────────┐     │
│   │  Backtest Engine                                         │     │
│   │  • 滑價模擬 • 手續費計算 • 績效指標 • 結果可重現          │     │
│   └──────────────────────────────────────────────────────────┘     │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Monitoring & Reporting Layer                      │
│   ┌────────────────────────┐    ┌────────────────────────┐          │
│   │  Prometheus            │───▶│  Grafana Dashboards    │          │
│   │  • 50+ Metrics         │    │  • Collector Dashboard │          │
│   │  • 30d Retention       │    │  • WS Dashboard        │          │
│   └────────────────────────┘    └────────────────────────┘          │
│   ┌────────────────────────┐    ┌────────────────────────┐          │
│   │  Report Scheduler      │    │  Alertmanager          │          │
│   │  • Daily (08:00)       │    │  • Alert Rules         │          │
│   │  • Weekly (Mon 09:00)  │    │  • Email Notifications │          │
│   └────────────────────────┘    └────────────────────────┘          │
└──────────────────────────────────────────────────────────────────────┘
```

## 專案結構

```
crypto-market-analyzer/
├── collector-py/                 # Python 資料收集器
│   ├── src/
│   │   ├── connectors/              # 交易所連接器
│   │   │   ├── binance_rest.py         # Binance REST API
│   │   │   ├── bybit_rest.py           # Bybit REST API
│   │   │   ├── okx_rest.py             # OKX REST API
│   │   │   └── *_whale_tracker.py      # 鏈上鯨魚追蹤器
│   │   ├── loaders/                 # 資料庫載入器
│   │   │   └── database_loader.py      # TimescaleDB 寫入
│   │   ├── schedulers/              # 排程任務
│   │   │   └── backfill_scheduler.py   # 自動補資料
│   │   ├── quality_checker.py       # 資料品質檢查
│   │   ├── metrics_exporter.py      # Prometheus metrics
│   │   └── config.py                # 配置管理
│   ├── logs/                        # 日誌目錄（9.2 MB）
│   └── requirements.txt             # Python 依賴
│
├── data-collector/               # Node.js WebSocket 收集器
│   ├── src/
│   │   ├── binance_ws/              # Binance WebSocket
│   │   │   └── BinanceWSClient.ts      # 客戶端實現
│   │   ├── orderbook_handlers/      # 訂單簿處理
│   │   │   └── OrderBookManager.ts     # 本地維護
│   │   ├── queues/                  # Redis 佇列
│   │   │   └── RedisQueue.ts           # 批次寫入
│   │   ├── database/                # 資料庫
│   │   │   └── DBFlusher.ts            # 批次刷新
│   │   └── metrics/                 # Metrics
│   │       └── MetricsServer.ts        # Prometheus exporter
│   ├── package.json
│   └── tsconfig.json
│
├── data-analyzer/                # Python 資料分析
│   ├── src/
│   │   ├── features/                # 特徵工程（80+ 指標）
│   │   │   ├── price_features.py       # 價格特徵
│   │   │   ├── volume_features.py      # 成交量特徵
│   │   │   └── technical_features.py   # 技術指標
│   │   ├── feature_selection/       # 特徵選擇
│   │   │   └── selection_pipeline.py   # 自動化 pipeline
│   │   ├── models/                  # ML 模型
│   │   │   ├── model_registry.py       # 模型註冊系統
│   │   │   ├── baseline/               # Baseline 模型
│   │   │   ├── ml/                     # XGBoost 等
│   │   │   └── anomaly/                # 異常偵測
│   │   ├── strategies/              # 交易策略
│   │   │   ├── base_strategy.py        # 策略基類
│   │   │   ├── rsi_strategy.py         # RSI 策略
│   │   │   └── macd_strategy.py        # MACD 策略
│   │   ├── backtesting/             # 回測引擎
│   │   │   ├── backtest_engine.py      # 核心引擎
│   │   │   └── performance_metrics.py  # 績效計算
│   │   └── reports/                 # 報表生成
│   │       ├── report_agent.py         # 主控制器
│   │       ├── html_generator.py       # HTML 生成
│   │       ├── pdf_generator.py        # PDF 生成
│   │       └── email_sender.py         # 郵件發送
│   ├── notebooks/                   # Jupyter 分析筆記本
│   ├── results/                     # 實驗結果輸出
│   │   ├── xgboost_btc_1h/             # XGBoost 結果
│   │   ├── lstm_full_features_btc_1h/  # LSTM 結果
│   │   └── backtest_results/           # 回測報告
│   ├── REPORT_USAGE.md              # 報表使用說明
│   ├── PHASE5_COMPLETE.md           # 階段5完成報告
│   └── requirements.txt
│
├── database/
│   ├── schemas/                     # 資料庫結構定義
│   │   ├── 01_init.sql                 # 核心 schema
│   │   └── 02_blockchain_whale_tracking.sql  # 鏈上追蹤
│   └── migrations/                  # 資料庫遷移
│       ├── 002_add_indexes.sql         # 索引優化
│       ├── 003_data_quality_tables.sql # 品質監控表
│       ├── 004_continuous_aggregates_and_retention.sql  # 分層聚合
│       ├── 004_README.md               # Migration 004 說明
│       ├── 005_report_logs.sql         # 報表日誌表
│       └── 006_connection_tracking.sql # 連接追蹤
│
├── dashboard/                       # Plotly Dash 儀表板
│   ├── pages/                       # 多頁面
│   │   ├── overview.py                 # 市場概覽
│   │   ├── technical.py                # 技術分析
│   │   ├── signals.py                  # 交易信號
│   │   └── liquidity.py                # 流動性分析
│   ├── app.py                       # 主程式
│   ├── data_loader.py               # 資料載入
│   └── cache_manager.py             # Redis 快取
│
├── monitoring/                      # 監控與告警
│   ├── prometheus/
│   │   ├── prometheus.yml              # Prometheus 配置
│   │   └── rules/
│   │       └── alerts.yml              # 告警規則
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── datasources/            # 資料源配置
│   │   │   └── dashboards/             # 儀表板配置
│   │   └── dashboards/
│   │       ├── crypto_collector.json   # Collector Dashboard
│   │       └── ws_collector.json       # WS Dashboard
│   └── alertmanager/
│       └── alertmanager.yml            # Alertmanager 配置
│
├── scripts/                         # 開發與運維腳本
│   ├── setup_test_db.sh                # 測試環境設置
│   ├── apply_migration_004.sh          # 執行 migration
│   ├── verify_migration_004.sh         # 驗證 migration
│   ├── check_retention_status.sh       # 檢查保留狀態
│   ├── report_scheduler.py             # 報表排程器
│   ├── generate_daily_report.py        # 每日報表
│   ├── generate_weekly_report.py       # 每週報表
│   ├── long_run_monitor.py             # 長期監控
│   ├── start_long_run_test.sh          # 啟動測試
│   ├── stop_long_run_test.sh           # 停止測試
│   └── system_snapshot.sh              # 系統快照
│
├── docs/                            # 專案文檔
│   ├── PROJECT_STATUS_REPORT.md        # 專案狀態報告
│   ├── STABILITY_VERIFICATION_REPORT.md # 穩定性驗證
│   ├── LONG_RUN_TEST_GUIDE.md          # 長期測試指南
│   ├── GRAFANA_DASHBOARDS_GUIDE.md     # Grafana 使用指南
│   ├── ENGINEERING_MANUAL.md           # 工程手冊
│   └── PROJECT_DOC_SUMMARY.md          # 文檔彙整
│
├── configs/                         # 系統配置
│   ├── collector/                      # 收集器配置
│   ├── models/                         # 模型配置
│   ├── strategies/                     # 策略配置
│   └── whale_tracker.yml               # 鯨魚追蹤配置
│
├── reports/                         # 報表輸出目錄
│   └── daily/                          # 每日報表
│
├── docker-compose.yml               # 容器編排（13 服務）
├── .env.example                     # 環境變數範本
├── CLAUDE.md                        # 專案開發指南
├── AGENTS.md                        # Agent 角色定位
└── README.md                        # 本文件（你正在閱讀）
```

### 關鍵目錄說明

- **collector-py/**：Python REST API 收集器，負責歷史資料抓取、補資料、品質檢查
- **data-collector/**：Node.js WebSocket 收集器，負責實時資料串流
- **data-analyzer/**：核心分析模組，包含特徵工程、模型訓練、回測、報表
- **database/**：資料庫 schema 與 migrations，包含 TimescaleDB 優化
- **monitoring/**：完整監控棧配置，Prometheus + Grafana + Alertmanager
- **scripts/**：各種自動化腳本與運維工具
- **docs/**：完整專案文檔與測試報告

## 🚀 快速開始

### 系統需求

- Docker & Docker Compose
- Python 3.13+
- Node.js 18+ (用於 WebSocket 收集器)
- PostgreSQL Client (可選)
- 至少 8GB RAM
- 至少 50GB 可用磁碟空間

### 快速訪問連結

啟動系統後，可通過以下端口訪問各項服務：

| 服務 | URL | 說明 |
|------|-----|------|
| **Grafana Dashboard** | http://localhost:3000 | 監控儀表板（admin/admin） |
| **Prometheus** | http://localhost:9090 | Metrics 查詢介面 |
| **Alertmanager** | http://localhost:9093 | 告警管理介面 |
| **Jupyter Lab** | http://localhost:8888 | 資料分析環境（無需 token） |
| **Collector Metrics** | http://localhost:8000/metrics | Python Collector 指標 |
| **WS Metrics** | http://localhost:8001/metrics | WebSocket Collector 指標 |
| **TimescaleDB** | localhost:5432 | 資料庫連接（crypto/crypto_pass） |
| **Redis** | localhost:6379 | 快取服務 |

### 步驟一：啟動系統

```bash
# 複製環境變數範本
cp .env.example .env

# 啟動所有核心服務
docker-compose up -d db redis collector ws-collector

# 等待服務啟動（約 20 秒）
docker-compose logs -f db

# 驗證服務狀態
docker-compose ps
```

預期輸出：
```
NAME                  STATUS         PORTS
crypto_timescaledb    Up (healthy)   0.0.0.0:5432->5432/tcp
crypto_redis          Up (healthy)   0.0.0.0:6379->6379/tcp
crypto_collector      Up             0.0.0.0:8000->8000/tcp
crypto_ws_collector   Up             0.0.0.0:8001->8001/tcp
```

### 步驟二：啟動監控服務（可選）

```bash
# 啟動 Prometheus + Grafana + Alertmanager
docker-compose up -d prometheus grafana alertmanager

# 啟動 Exporters（資料庫與 Redis 監控）
docker-compose up -d postgres-exporter redis-exporter

# 訪問 Grafana：http://localhost:3000
# 預設帳號：admin / admin
```

Grafana 已預配置 2 個儀表板：
- **Crypto Collector Dashboard**：REST API 收集器監控
- **WebSocket Collector Dashboard**：實時資料流監控

### 步驟三：啟動報表排程（可選）

```bash
# 啟動報表自動排程
docker-compose up -d report-scheduler

# 查看排程狀態
docker logs crypto_report_scheduler

# 手動觸發報表生成測試
docker exec crypto_report_scheduler python /app/scripts/generate_daily_report.py
```

### 步驟四：啟動分析環境

```bash
# 啟動 Jupyter Lab
docker-compose up -d jupyter

# 訪問 Jupyter：http://localhost:8888
# 無需 token，直接開啟瀏覽器
```

Jupyter Lab 已預載入：
- 所有分析套件（pandas, numpy, matplotlib, seaborn）
- 機器學習套件（scikit-learn, xgboost, pytorch）
- 資料庫連接配置
- 範例 notebook

### 驗證系統運行

```bash
# 檢查所有服務狀態
docker-compose ps

# 檢查資料收集狀態
curl http://localhost:8000/metrics | grep collector_api_success

# 檢查資料庫資料量
docker exec crypto_timescaledb psql -U crypto -d crypto_db \
  -c "SELECT COUNT(*) FROM ohlcv;"

# 查看最近收集的資料
docker exec crypto_timescaledb psql -U crypto -d crypto_db \
  -c "SELECT * FROM ohlcv ORDER BY open_time DESC LIMIT 5;"
```

### 停止系統

```bash
# 停止所有服務（保留資料）
docker-compose down

# 完全清理（包含 volumes）
docker-compose down -v

# 僅重啟特定服務
docker-compose restart collector
```

## 📊 資料管理特性

### 分層資料聚合（Migration 004）

系統自動維護多時間粒度的聚合資料：

| 粒度 | 來源 | 保留期限 | 更新頻率 | 用途 |
|------|------|----------|----------|------|
| **1m** (原始) | Collector | 7 天 | 實時 | 短期精細分析、高頻策略 |
| **5m** | 1m | 30 天 | 每小時 | 日內分析、中頻策略 |
| **15m** | 5m | 90 天 | 每 2 小時 | 週內趨勢分析 |
| **1h** | 15m | 180 天 | 每 4 小時 | 月度趨勢、中期回測 |
| **1d** | 1h | **永久** | 每天 | 長期趨勢、基本面分析 |

**儲存效益**：相較於保留所有原始資料，節省約 **94% 儲存空間**。

### 智能查詢

使用 `get_optimal_ohlcv()` 函數會自動選擇最佳資料粒度：

```sql
-- 查詢最近 7 天（自動使用 5m 聚合）
SELECT * FROM get_optimal_ohlcv(
    p_market_id := 1,
    p_start_time := NOW() - INTERVAL '7 days',
    p_end_time := NOW()
);
```

查詢規則：
- ≤ 12 小時 → 使用 1m 原始資料
- ≤ 3 天 → 使用 5m 聚合
- ≤ 30 天 → 使用 15m 聚合
- ≤ 180 天 → 使用 1h 聚合
- \> 180 天 → 使用 1d 聚合

### 重要事件保護

系統預設保護以下歷史重要事件的原始資料：
- **2021-05-19**: BTC Flash Crash（單日暴跌 30%）
- **2022-05-09~13**: LUNA Collapse（UST 脫錨事件）
- **2022-11-06~12**: FTX Collapse（交易所破產）

新增自定義事件：

```sql
INSERT INTO critical_events (
    event_name, event_type, start_time, end_time,
    markets, preserve_raw, description, tags
) VALUES (
    '2024 BTC ETF Approval',
    'regulatory',
    '2024-01-10 00:00:00+00',
    '2024-01-12 00:00:00+00',
    ARRAY(SELECT id FROM markets WHERE base_asset = 'BTC'),
    TRUE,
    'BTC 現貨 ETF 獲批准上市',
    ARRAY['btc', 'etf', 'institutional']
);
```

## 🔧 核心功能

### 數據收集

- **OHLCV K線數據**：支援多時間週期（1m, 5m, 15m, 1h, 4h, 1d）
- **交易流水**：實時成交記錄
- **訂單簿快照**：買賣盤深度數據
- **自動補齊**：檢測並補齊缺失的歷史資料
- **品質監控**：追蹤資料完整性、異常值、時序正確性

### 數據分析

- **技術指標**：MA、EMA、RSI、MACD、布林通道等
- **價格趨勢預測**：LSTM、Transformer 時間序列模型
- **異常檢測**：Isolation Forest 識別市場異常波動
- **市場情緒分析**：基於成交量、波動度的情緒指數
- **策略回測**：支援自定義交易策略回測與績效評估

### 資料庫功能

- **時序優化**：TimescaleDB 自動分區與壓縮
- **連續聚合**：自動維護多時間粒度聚合視圖
- **分層保留**：智能資料保留策略，平衡儲存成本與資料價值
- **完整性檢查**：檢測缺失 K 線的輔助函數
- **空間監控**：即時追蹤各表儲存空間使用情況

## 📚 常用查詢

### 查看資料保留狀態

```sql
SELECT * FROM v_retention_status;
```

### 查看儲存空間統計

```sql
SELECT * FROM get_storage_statistics();
```

### 檢查資料可用性

```sql
SELECT * FROM check_data_availability(
    p_market_id := 1,
    p_start_time := '2024-01-01 00:00:00+00',
    p_end_time := '2024-12-31 23:59:59+00'
);
```

### 查詢最近 24 小時的 BTC K 線

```sql
-- 使用智能查詢（自動選擇最佳粒度）
SELECT
    open_time,
    open, high, low, close, volume,
    source  -- 顯示資料來源 (1m/5m/15m/1h/1d)
FROM get_optimal_ohlcv(
    p_market_id := (SELECT id FROM markets WHERE symbol = 'BTC/USDT' LIMIT 1),
    p_start_time := NOW() - INTERVAL '24 hours',
    p_end_time := NOW()
)
ORDER BY open_time DESC;
```

### 檢查數據完整性

```sql
-- 檢查缺失的 K 線
SELECT * FROM check_missing_candles(
    1,                                  -- market_id
    '1m',                              -- timeframe
    NOW() - INTERVAL '1 day',
    NOW()
);
```

更多範例請參考 [`database/migrations/004_USAGE_EXAMPLES.sql`](database/migrations/004_USAGE_EXAMPLES.sql)

## ⚙️ 配置說明

### 環境變數（.env）

```env
# TimescaleDB 配置
POSTGRES_USER=crypto
POSTGRES_PASSWORD=crypto_pass
POSTGRES_DB=crypto_db
POSTGRES_PORT=5432

# Redis 配置
REDIS_PORT=6379

# Jupyter Lab 配置
JUPYTER_PORT=8888
JUPYTER_TOKEN=
JUPYTER_PASSWORD=

# 環境配置
ENVIRONMENT=development
TZ=UTC
```

### 收集器配置（collector-py/.env）

```env
# 收集器配置
COLLECTOR_INTERVAL_SECONDS=60  # 抓取間隔（秒）
DEFAULT_TIMEFRAME=1m           # 預設時間週期
DEFAULT_LIMIT=1000             # 每次抓取條數

# 日誌級別
LOG_LEVEL=INFO
```

## 🛠️ 開發指南

### 資料庫遷移

```bash
# 檢查當前狀態
./scripts/verify_migration_004.sh

# 查看資料保留狀態
./scripts/check_retention_status.sh

# 在測試環境執行新的 migration
./scripts/setup_test_db.sh
./scripts/test_migration_004.sh

# 清理測試環境
./scripts/cleanup_test_db.sh
```

### 添加新的數據收集器

1. 在 `collector-py/src/` 建立新的客戶端（參考 `binance_client.py`）
2. 實作 `fetch_ohlcv()`、`fetch_trades()` 等方法
3. 在 `main.py` 中註冊新的收集任務

### 添加新的分析模型

1. 在 `data-analyzer/src/models/` 建立模型目錄
2. 實作訓練、預測、評估方法
3. 在 notebook 中測試模型效果
4. 整合到自動化報表中

## 📊 專案狀態

### 整體完成度：**80%** (8/10 階段完成)

| 階段 | 狀態 | 完成度 | 說明 |
|------|------|--------|------|
| 資料收集基礎設施 | ✅ 完成 | 100% | REST + WebSocket 多交易所 |
| 資料品質保證 | ✅ 完成 | 100% | 品質檢查 + 自動補資料 |
| 分析與建模 | ✅ 完成 | 100% | 80+ 特徵 + 多種模型 |
| 策略與回測 | ✅ 完成 | 100% | 統一介面 + 完整引擎 |
| 報表與自動化 | ✅ 完成 | 100% | HTML/PDF + 排程系統 |
| 監控與可觀測性 | ✅ 完成 | 100% | Prometheus + Grafana |
| 穩定性驗證 | ✅ 完成 | 100% | 6+ 小時連續運行 |
| 長期穩定性測試 | 🔄 進行中 | 70% | 測試框架完成 |
| 實驗管理與優化 | ⚪ 未開始 | 0% | MLflow 整合待實現 |
| 資料源擴展 | ⚪ 未開始 | 20% | 鏈上 schema 已建立 |

### 系統能力摘要

#### ✅ 已驗證功能
- **資料收集**：Binance / Bybit / OKX REST + Binance WebSocket
- **資料品質**：3,287+ OHLCV 資料點，API 成功率 100%
- **資料庫**：19 張表，235 MB 資料，持久化完整
- **監控指標**：50+ Prometheus metrics 實時追蹤
- **服務穩定性**：11/13 服務運行，核心服務 100% 可用
- **資料持久化**：5 個 Docker volumes 正常運作
- **自動恢復**：容器重啟後資料完整保留

#### 🔄 待驗證功能
- 72 小時長期穩定性測試
- 報表自動生成實際產出
- 告警規則實戰觸發
- 鏈上數據收集整合

#### ⚠️ 已知限制
- WebSocket 連接偶爾不穩定（有自動重連）
- Node Exporter 無法在 macOS Docker 運行（生產環境使用 Linux）
- LSTM 模型性能待優化（方向準確率低於 XGBoost）
- PDF 報表生成暫時禁用（需系統依賴 weasyprint）

## 🎯 路線圖

> **💡 提示**：詳細進度與待辦事項請查閱 [開發進度日誌](docs/SESSION_LOG.md)

### ✅ Phase 1: 資料收集基礎設施（已完成）
- [x] Docker 環境建立
- [x] TimescaleDB 資料庫設計與優化
- [x] 多交易所 REST API 收集器（Binance / Bybit / OKX）
- [x] WebSocket 實時資料收集
- [x] 連續聚合與分層保留策略
- [x] 自動補資料機制

### ✅ Phase 2: 資料品質保證（已完成）
- [x] 多維度品質檢查系統
- [x] 品質評分與異常標記
- [x] 缺失區段自動補齊
- [x] API 錯誤追蹤與重試機制

### ✅ Phase 3: 分析與建模（已完成）
- [x] 80+ 技術指標特徵工程
- [x] Feature selection pipeline
- [x] Baseline / ML / DL 模型實現
- [x] 異常偵測系統
- [x] 模型註冊與管理

### ✅ Phase 4: 策略與回測（已完成）
- [x] 統一策略介面
- [x] 多種內建策略（RSI / MACD / Fractal）
- [x] 完整回測引擎（滑價、手續費、績效指標）
- [x] 結果可重現機制

### ✅ Phase 5: 報表與自動化（已完成）
- [x] HTML / PDF 報表生成
- [x] 郵件自動發送
- [x] 報表排程系統（每日/每週）
- [x] Dashboard 視覺化介面

### ✅ Phase 6: 監控與可觀測性（已完成）
- [x] Prometheus metrics exporter
- [x] Grafana 儀表板（2 個預配置）
- [x] Alertmanager 告警系統
- [x] 完整監控指標（50+）
- [x] 資料庫連接池監控
- [x] 殭屍連接自動清理

### ✅ Phase 7: 部署與自動化（已完成）
- [x] Docker Compose 完整編排（13 服務）
- [x] 資料持久化配置（5 個 volumes）
- [x] 自動重啟機制
- [x] 健康檢查與依賴管理
- [x] 報表自動排程

### 🔄 Phase 8: 穩定性驗證（進行中 - 70%）
- [x] 6+ 小時連續運行測試通過
- [x] 資料持久化驗證通過
- [x] 容器重啟恢復測試通過
- [x] 資料庫連接問題修復
- [ ] **72 小時長期穩定性測試**（當前優先級）
- [ ] 性能基準建立
- [ ] 告警規則實戰驗證

### ⚪ Phase 9: 實驗管理（未開始）
- [ ] MLflow 安裝與整合（SQLite backend）
- [ ] 模型參數與指標追蹤
- [ ] Feature 版本管理
- [ ] XGBoost 與 LSTM baseline 穩定化

### ⚪ Phase 10: 資料源擴展（20%）
- [x] 鏈上 schema 與 migration 建立
- [ ] Coinbase REST API connector
- [ ] Ethereum 大額轉帳指標
- [ ] On-chain 特徵整合到 analysis pipeline

### ⚪ Phase 11: Paper Trading（研究性質）
- [ ] 準實時模式回測改造
- [ ] 虛擬交易記錄表設計
- [ ] PnL 追蹤與績效統計
- [ ] 風控規則實現（單筆/每日/倉位限制）

## 📖 文檔

### 🔥 最新動態
- **[開發進度日誌](docs/SESSION_LOG.md)** - 最新進度、決策記錄與待辦事項 🆕

### 核心文檔
- [專案開發指南](CLAUDE.md) - 詳細的開發規範與架構說明
- [Agent 角色定位](AGENTS.md) - Agent 工作流程與規範
- [工程手冊](docs/ENGINEERING_MANUAL.md) - 系統功能與技術棧總覽

### 資料庫文檔
- [Migration 004 文檔](database/migrations/004_README.md) - 分層資料管理完整說明
- [使用範例集](database/migrations/004_USAGE_EXAMPLES.sql) - SQL 查詢範例

### 報表與儀表板
- [報表系統使用說明](data-analyzer/REPORT_USAGE.md) - 報表生成與使用指南
- [階段5完成報告](data-analyzer/PHASE5_COMPLETE.md) - 自動化報表系統完整說明
- [Grafana 儀表板指南](docs/GRAFANA_DASHBOARDS_GUIDE.md) - Dashboard 配置與使用

### 測試與驗證
- [專案狀態報告](docs/PROJECT_STATUS_REPORT.md) - 完整進度與功能清單
- [穩定性驗證報告](docs/STABILITY_VERIFICATION_REPORT.md) - 6+ 小時運行測試結果
- [長期運行測試指南](docs/LONG_RUN_TEST_GUIDE.md) - 72 小時穩定性測試方案
- [Phase 6 測試報告](docs/PHASE6_TEST_REPORT.md) - 監控系統測試結果
- [Phase 6 Metrics 測試結果](docs/PHASE6_METRICS_TEST_RESULTS.md) - Metrics 功能驗證

### 鏈上數據
- [區塊鏈數據收集指南](docs/BLOCKCHAIN_DATA_COLLECTION_GUIDE.md) - 鯨魚追蹤配置
- [區塊鏈 API 設定](collector-py/BLOCKCHAIN_API_SETUP.md) - API 金鑰配置

### 配置與部署
- [郵件設定指南](docs/EMAIL_SETUP_GUIDE.md) - SMTP 配置與報表發送
- [文檔彙整摘要](docs/PROJECT_DOC_SUMMARY.md) - 所有文檔快速索引

## ❓ 常見問題

### 系統配置

**Q: 如何修改數據保留時間？**

編輯 `database/migrations/004_continuous_aggregates_and_retention.sql` 或使用：
```sql
-- 修改 1m 原始資料保留期為 14 天
SELECT remove_retention_policy('ohlcv');
SELECT add_retention_policy('ohlcv', INTERVAL '14 days');
```

**Q: 如何配置報表排程時間？**

編輯 `scripts/report_scheduler.py` 中的排程設定：
```python
# 每日報表（預設 08:00 UTC）
scheduler.add_job(generate_daily_report, 'cron', hour=8, minute=0)

# 每週報表（預設週一 09:00 UTC）
scheduler.add_job(generate_weekly_report, 'cron', day_of_week='mon', hour=9, minute=0)
```

### 資料收集

**Q: 收集器報錯「API rate limit exceeded」**

增加 `COLLECTOR_INTERVAL_SECONDS` 或確認 ccxt 已啟用 `enableRateLimit=True`

**Q: 如何添加新的交易對？**

無需手動添加，`DatabaseLoader.get_market_id()` 會自動建立新市場記錄

**Q: WebSocket 連接不穩定怎麼辦？**

檢查日誌並調整重連邏輯：
```bash
# 查看 WS Collector 日誌
docker logs crypto_ws_collector

# 調整 healthcheck 閾值
# 編輯 docker-compose.yml 中的 ws-collector 服務
```

### 資料庫

**Q: 聚合資料沒有更新？**

手動刷新聚合視圖：
```sql
CALL refresh_continuous_aggregate('ohlcv_5m', NULL, NULL);
CALL refresh_continuous_aggregate('ohlcv_1h', NULL, NULL);
```

**Q: 如何查看系統儲存空間使用？**

```bash
# 使用腳本查看
./scripts/check_retention_status.sh

# 或直接查詢資料庫
docker exec crypto_timescaledb psql -U crypto -d crypto_db \
  -c "SELECT * FROM get_storage_statistics();"
```

**Q: 資料庫連接池滿了怎麼辦？**

檢查連接池狀態並清理殭屍連接：
```sql
-- 查看當前連接
SELECT * FROM pg_stat_activity WHERE datname = 'crypto_db';

-- 終止 idle 連接
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'crypto_db' 
  AND state = 'idle' 
  AND state_change < NOW() - INTERVAL '30 minutes';
```

### 監控與告警

**Q: Grafana 無法訪問怎麼辦？**

```bash
# 檢查 Grafana 容器狀態
docker logs crypto_grafana

# 重啟 Grafana
docker-compose restart grafana

# 訪問 http://localhost:3000
# 預設帳號: admin / admin
```

**Q: Prometheus 沒有抓取到 metrics？**

```bash
# 檢查 targets 狀態
# 訪問 http://localhost:9090/targets

# 檢查 metrics exporter
curl http://localhost:8000/metrics  # Collector
curl http://localhost:8001/metrics  # WS Collector

# 重啟 Prometheus
docker-compose restart prometheus
```

**Q: 如何配置郵件告警？**

編輯 `monitoring/alertmanager/alertmanager.yml`：
```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'your-email@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'your-email@gmail.com'
        auth_password: 'your-app-password'
```

### 容器管理

**Q: 如何重啟特定服務？**

```bash
# 重啟單一服務
docker-compose restart collector

# 重啟多個服務
docker-compose restart db redis collector

# 完全重建容器
docker-compose up -d --force-recreate collector
```

**Q: 如何查看服務日誌？**

```bash
# 即時查看日誌
docker-compose logs -f collector

# 查看最近 100 行
docker-compose logs --tail=100 ws-collector

# 查看所有服務日誌
docker-compose logs --tail=50
```

**Q: 磁碟空間不足怎麼辦？**

```bash
# 清理未使用的 Docker 資源
docker system prune -a --volumes

# 檢查 volume 大小
docker volume ls
du -sh /var/lib/docker/volumes/*

# 清理舊日誌
find collector-py/logs -type f -mtime +7 -delete
```

## 🔒 授權

MIT License

## 📞 聯絡

如有問題或建議，請開 Issue 討論。

---

**最後更新**：2025-12-29
**版本**：v1.4.0（穩定性驗證完成 + 監控系統完善）

## 🔄 最新更新（v1.4.0 - 2025-12-29）

### 穩定性驗證完成 ✅
- ✅ 6+ 小時連續運行測試通過
- ✅ 11/13 服務穩定運行（核心服務 100% 可用）
- ✅ 資料持久化驗證通過（235 MB 資料完整保留）
- ✅ 容器重啟自動恢復機制驗證通過
- ✅ 日誌持久化正常（9.2 MB 累積日誌）

### 監控與可觀測性增強
- ✅ Prometheus + Grafana + Alertmanager 全棧運行
- ✅ 50+ Prometheus metrics 實時監控
- ✅ 2 個 Grafana Dashboards（Collector + WS Collector）
- ✅ 變數過濾功能（Exchange / Symbol / Timeframe）
- ✅ Postgres Exporter + Redis Exporter 正常採集

### 報表系統自動化
- ✅ Report Scheduler 成功配置
- ✅ 每日報表（08:00 UTC）+ 每週報表（週一 09:00 UTC）
- ✅ APScheduler 自動排程機制
- ✅ 報表日誌記錄與追蹤

### 系統優化
- ✅ 升級至 Python 3.13（解決 pandas-ta 依賴）
- ✅ 資料庫連接池優化（ThreadedConnectionPool）
- ✅ 自動重啟機制（restart: unless-stopped）
- ✅ 健康檢查與依賴管理優化
