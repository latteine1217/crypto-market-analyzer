# Crypto Market Analyzer

加密市場數據抓取與 AI 分析系統。從主流交易所收集 OHLCV、訂單簿、交易流水及鏈上數據，儲存至 TimescaleDB 時序資料庫，並使用機器學習模型進行價格趨勢預測、異常檢測、交易策略回測與市場情緒分析。

## 🌟 核心特性

- ✅ **多時間粒度聚合**：自動生成 5m/15m/1h/1d 聚合資料，節省 94% 儲存空間
- ✅ **智能資料保留**：分層保留策略，7天原始資料 + 長期聚合資料
- ✅ **重要事件保護**：關鍵歷史事件（如閃崩）的原始資料永久保留
- ✅ **智能查詢優化**：自動選擇最佳資料粒度，提升查詢效能
- ✅ **實時數據收集**：支援 REST API 與 WebSocket 雙模式
- ✅ **資料品質監控**：自動檢測缺失、異常與完整性

## 系統架構

```
┌────────────────────────────────────────────────────────────────┐
│         Data Collection Layer (Python + Node.js)               │
│   Python: 歷史資料抓取 | Node.js: WebSocket 實時串流            │
└─────────────────┬──────────────────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────────────────┐
│    Data Storage Layer (TimescaleDB + Redis)                    │
│   • 連續聚合 (5m/15m/1h/1d)                                     │
│   • 分層保留策略 (7天→永久)                                      │
│   • 重要事件保護機制                                             │
└─────────────────┬──────────────────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────────────────┐
│         Analysis Layer (Python + Jupyter)                      │
│   特徵工程 | ML 模型 | 回測引擎 | 報表生成                       │
└────────────────────────────────────────────────────────────────┘
```

## 專案結構

```
crypto-market-analyzer/
├── collector-py/             # Python 歷史數據抓取
│   ├── src/
│   │   ├── binance_client.py    # Binance REST API
│   │   ├── loaders/             # 資料庫載入器
│   │   ├── schedulers/          # 排程任務
│   │   └── config.py            # 配置管理
│   └── requirements.txt
│
├── data-collector/           # Node.js 實時數據抓取 (WebSocket)
│   ├── src/
│   │   ├── binance_ws.ts        # Binance WebSocket
│   │   ├── orderbook_handlers/  # 訂單簿處理
│   │   └── queues/              # Redis 任務佇列
│   └── package.json
│
├── data-analyzer/            # Python 數據分析
│   ├── src/
│   │   ├── features/            # 特徵工程
│   │   ├── models/              # ML 模型
│   │   ├── backtesting/         # 回測引擎
│   │   └── reports/             # 報表生成
│   ├── notebooks/               # Jupyter 分析筆記本
│   └── requirements.txt
│
├── database/
│   ├── schemas/                 # 資料庫結構定義
│   │   └── 01_init.sql
│   └── migrations/              # 資料庫遷移
│       ├── 002_add_indexes.sql
│       ├── 003_data_quality_tables.sql
│       ├── 004_continuous_aggregates_and_retention.sql  # 🆕
│       └── 004_README.md        # Migration 004 詳細文檔
│
├── scripts/                     # 開發與運維腳本
│   ├── setup_test_db.sh         # 測試環境設置
│   ├── apply_migration_004.sh   # 執行 migration
│   ├── verify_migration_004.sh  # 驗證 migration
│   └── check_retention_status.sh # 監控資料保留狀態
│
├── shared/                      # 共用配置
│   ├── config/
│   └── types/
│
├── configs/                     # 系統配置
│   ├── collector/
│   ├── models/
│   └── strategies/
│
├── docker-compose.yml           # 容器編排
├── CLAUDE.md                    # 專案開發指南
└── README.md                    # 本文件
```

## 🚀 快速開始

### 前置需求

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (可選，用於 WebSocket 收集器)
- PostgreSQL Client (可選，用於手動查詢)

### 步驟一：啟動資料庫服務

```bash
# 啟動 TimescaleDB 和 Redis
docker-compose up -d db redis

# 等待資料庫啟動（約 10 秒）
docker-compose logs -f db

# 驗證資料庫
docker exec crypto_timescaledb psql -U crypto -d crypto_db -c "\dt"
```

### 步驟二：初始化資料庫

資料庫 schema 會在容器啟動時自動執行，包含：
- 基礎表結構 (exchanges, markets, ohlcv, trades)
- TimescaleDB hypertables
- 索引優化
- 資料品質監控表
- **連續聚合與分層保留策略** 🆕

### 步驟三：執行數據收集器

```bash
cd collector-py

# 安裝依賴
pip install -r requirements.txt

# 執行收集器
python src/main.py
```

收集器會：
- 立即抓取一次歷史資料
- 每 60 秒自動抓取最新資料
- 自動處理 API 限流
- 自動補齊缺失資料

### 步驟四：啟動 Jupyter Lab 進行分析

```bash
# 啟動 Jupyter 容器
docker-compose up -d jupyter

# 訪問 Jupyter
echo "Jupyter Lab: http://localhost:8888"
```

開啟瀏覽器訪問 `http://localhost:8888`，無需 token。

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

## 🎯 路線圖

### ✅ 階段一：基礎設施
- [x] Docker 環境建立
- [x] TimescaleDB 資料庫設計
- [x] Binance 數據抓取器
- [x] Jupyter 分析環境
- [x] **連續聚合與分層保留策略** 🆕

### 🔄 階段二：多數據源整合（進行中）
- [x] Node.js WebSocket 實時數據收集器
- [ ] 添加 Coinbase 數據源
- [ ] 整合鏈上數據（Etherscan/BSCScan）
- [ ] 訂單簿深度分析

### 📋 階段三：進階分析
- [ ] LSTM 價格預測模型
- [ ] Transformer 時間序列模型
- [ ] 市場情緒 NLP 分析
- [ ] 完整回測框架

### 📊 階段四：自動化報表
- [ ] 日報/週報自動生成
- [ ] Plotly 交互式儀表板
- [ ] 郵件/Telegram 推送

### 💰 階段五：交易執行層
- [ ] 模擬交易環境
- [ ] 實盤交易接口
- [ ] 風險管理模組

## 📖 文檔

- [專案開發指南](CLAUDE.md) - 詳細的開發規範與架構說明
- [Migration 004 文檔](database/migrations/004_README.md) - 分層資料管理完整說明
- [使用範例集](database/migrations/004_USAGE_EXAMPLES.sql) - SQL 查詢範例

## ❓ 常見問題

**Q: 如何修改數據保留時間？**

編輯 `database/migrations/004_continuous_aggregates_and_retention.sql` 或使用：
```sql
-- 修改 1m 原始資料保留期為 14 天
SELECT remove_retention_policy('ohlcv');
SELECT add_retention_policy('ohlcv', INTERVAL '14 days');
```

**Q: 收集器報錯「API rate limit exceeded」**

增加 `COLLECTOR_INTERVAL_SECONDS` 或確認 ccxt 已啟用 `enableRateLimit=True`

**Q: 如何添加新的交易對？**

無需手動添加，`DatabaseLoader.get_market_id()` 會自動建立新市場記錄

**Q: 聚合資料沒有更新？**

手動刷新聚合視圖：
```sql
CALL refresh_continuous_aggregate('ohlcv_5m', NULL, NULL);
CALL refresh_continuous_aggregate('ohlcv_1h', NULL, NULL);
```

**Q: 如何查看系統儲存空間使用？**

```bash
./scripts/check_retention_status.sh
```

或直接查詢：
```sql
SELECT * FROM get_storage_statistics();
```

## 🔒 授權

MIT License

## 📞 聯絡

如有問題或建議，請開 Issue 討論。

---

**最後更新**：2024-12-26
**版本**：v1.1.0（新增分層資料管理）
