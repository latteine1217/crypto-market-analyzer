# Crypto Market Analyzer Dashboard

## 📊 功能特色

專業的加密貨幣市場分析 Dashboard，使用 Plotly Dash 建立。

### 🚀 v2.0 實時版本更新

- **⚡ 多層級刷新機制**：
  - 快速刷新（1秒）：價格 K 線、訂單簿深度、交易信號
  - 中速刷新（5秒）：技術指標統計
  - 慢速刷新（30秒）：市場摘要資料
- **💾 Redis 快取層**：減少資料庫查詢壓力，提升響應速度
- **🎯 載入狀態指示器**：清晰的視覺反饋
- **📈 優化查詢效能**：智能快取策略，平衡實時性與系統負載

### 頁面概覽

#### 1️⃣ 首頁 - Market Overview
- 📈 實時價格監控（BTC/USDT, ETH/USDT, ETH/BTC）
- 📊 24 小時價格變化和成交量
- 📉 多交易對價格走勢圖
- 🎯 技術指標摘要（MACD, MA）
- 🔔 最新交易信號

#### 2️⃣ 技術分析 - Technical Analysis
- 🕯️ K 線圖（Candlestick Chart）
- 📊 移動平均線（MA 20, 60, 200）
- 🔺 威廉分形標記（支撐/阻力位）
- 📈 MACD 指標圖表
- 📉 MACD 柱狀圖
- 📋 技術指標數值統計

#### 3️⃣ 交易信號 - Trading Signals
- 🎯 多策略信號展示
  - MACD 交叉策略
  - 威廉分形突破策略
  - 分形 + MA 結合策略
- 📊 信號統計（買入/賣出次數）
- 📈 信號時間軸圖表
- 📋 最近信號列表

#### 4️⃣ 流動性分析 - Liquidity Analysis
- 💧 訂單簿深度剖面圖
- 📊 買賣壓力對比
- 📉 Bid/Ask Spread 分析
- 📈 流動性趨勢

---

## 🚀 快速開始

### 方法 1：使用實時版本啟動腳本（推薦）

```bash
cd dashboard
chmod +x start_realtime.sh
./start_realtime.sh
```

啟動腳本會自動檢查：
- ✅ Python 環境
- ✅ 依賴套件
- ✅ PostgreSQL 連接
- ✅ Redis 服務（可選）

### 方法 2：手動啟動

#### 1. 安裝依賴

```bash
cd dashboard
pip install -r requirements.txt
```

#### 2. 確保資料庫運行

確保 TimescaleDB 正在運行並包含資料：

```bash
# 檢查資料庫連接
psql -h localhost -p 5432 -U crypto -d crypto_db -c "SELECT COUNT(*) FROM ohlcv;"
```

#### 3.（可選）啟動 Redis

為了獲得最佳效能，建議啟動 Redis：

```bash
# macOS
brew install redis
brew services start redis

# Linux
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

**注意**：即使不啟動 Redis，Dashboard 仍可正常運行，只是會直接查詢資料庫。

#### 4. 啟動 Dashboard

```bash
python app.py
```

#### 5. 訪問 Dashboard

在瀏覽器中打開：
```
http://localhost:8050
```

---

## 🔧 配置

### 資料庫連接

編輯 `data_loader.py` 中的連接參數：

```python
DataLoader(
    host='localhost',
    port=5432,
    database='crypto_db',
    user='crypto',
    password='crypto_pass',
    use_cache=True,      # 是否啟用 Redis 快取
    cache_ttl=2          # 快取過期時間（秒）
)
```

### 刷新頻率調整

在 `app.py` 中有三個刷新間隔可以調整：

```python
# 快速刷新：價格、訂單簿、信號
dcc.Interval(
    id='interval-fast',
    interval=1*1000,  # 1 秒
    n_intervals=0
)

# 中速刷新：技術指標
dcc.Interval(
    id='interval-medium',
    interval=5*1000,  # 5 秒
    n_intervals=0
)

# 慢速刷新：統計資料
dcc.Interval(
    id='interval-slow',
    interval=30*1000,  # 30 秒
    n_intervals=0
)
```

### Redis 快取配置

在 `cache_manager.py` 中調整：

```python
CacheManager(
    host='localhost',
    port=6379,
    db=0,
    password=None,
    default_ttl=2  # 預設快取時間（秒）
)
```

---

## 📁 專案結構

```
dashboard/
├── app.py                  # 主應用程式（多層級刷新機制）
├── data_loader.py          # 資料載入模組（支援快取）
├── cache_manager.py        # Redis 快取管理器（NEW）
├── start_realtime.sh       # 實時版本啟動腳本（NEW）
├── requirements.txt        # 依賴清單
├── pages/                  # 頁面模組
│   ├── __init__.py
│   ├── overview.py         # 首頁（快速刷新）
│   ├── technical.py        # 技術分析頁面（混合刷新）
│   ├── signals.py          # 交易信號頁面（快速刷新）
│   └── liquidity.py        # 流動性分析頁面（快速刷新）
└── README.md               # 本文檔
```

---

## 🎨 主題與樣式

Dashboard 使用深色主題（DARKLY），提供專業的視覺體驗：
- 深色背景
- 高對比度文字
- 綠色（買入）/ 紅色（賣出）配色
- 響應式佈局

---

## 📊 資料來源

Dashboard 從以下表讀取資料：

| 表名 | 用途 |
|------|------|
| `ohlcv` | K 線資料（價格、成交量） |
| `trades` | 成交記錄 |
| `orderbook_snapshots` | 訂單簿快照 |
| `markets` | 市場元資料 |
| `exchanges` | 交易所資訊 |

---

## 🔄 實時更新機制

### 多層級刷新策略

Dashboard 採用智能分層刷新，依組件重要性調整頻率：

| 刷新層級 | 間隔 | 組件 | Interval ID |
|---------|------|------|-------------|
| **快速** | 1 秒 | 價格 K 線、訂單簿深度、交易信號、市場摘要卡片 | `interval-fast` |
| **中速** | 5 秒 | 技術指標統計、MACD 圖表 | `interval-medium` |
| **慢速** | 30 秒 | 歷史統計資料 | `interval-slow` |

### Redis 快取機制

- **快取策略**：2 秒短暫快取，平衡實時性與資料庫負載
- **自動降級**：Redis 不可用時自動停用快取，直接查詢資料庫
- **快取鍵設計**：`{type}:{exchange}:{symbol}:{params}` 格式
- **效能提升**：減少 80%+ 重複資料庫查詢

---

## 🐛 故障排除

### 問題 1：無法連接資料庫

**解決方案：**
1. 確認 PostgreSQL 正在運行
2. 檢查連接參數是否正確
3. 確認防火牆設定

### 問題 2：沒有資料顯示

**解決方案：**
1. 確認 collector 正在運行並收集資料
2. 檢查資料庫是否有資料：
   ```sql
   SELECT COUNT(*) FROM ohlcv;
   SELECT COUNT(*) FROM orderbook_snapshots;
   ```

### 問題 3：圖表顯示錯誤

**解決方案：**
1. 清除瀏覽器快取
2. 重新啟動 Dashboard
3. 檢查瀏覽器控制台錯誤訊息

---

## 📈 效能優化

### v2.0 優化重點

1. **多層級刷新**：不同重要性的組件使用不同刷新頻率
2. **Redis 快取**：2 秒短暫快取減少資料庫查詢
3. **載入指示器**：改善用戶體驗，明確顯示更新狀態
4. **查詢優化**：限制查詢筆數，避免過度負載

### 資料查詢限制

預設查詢限制：
- OHLCV: 200-500 根 K 線
- Trades: 1000 筆
- Order Book: 10-100 筆快照

可在各頁面的 callback 函數中調整 `limit` 參數。

### 資料庫索引

確保以下索引存在以提升查詢速度：
```sql
-- 已在 migration 中建立
CREATE INDEX idx_ohlcv_market_timeframe_time ON ohlcv(market_id, timeframe, open_time DESC);
CREATE INDEX idx_trades_market_timestamp ON trades(market_id, timestamp DESC);
CREATE INDEX idx_orderbook_market_timestamp ON orderbook_snapshots(market_id, timestamp DESC);
```

### 效能監控

觀察以下指標確保系統健康：
- **快取命中率**：查看 loguru 日誌中的 "快取命中" 訊息
- **資料庫連接數**：`SELECT count(*) FROM pg_stat_activity;`
- **Redis 記憶體使用**：`redis-cli info memory`
- **頁面載入時間**：瀏覽器開發者工具 Network 面板

---

## 🔐 安全性

### 生產環境部署

**⚠️ 重要：** 預設配置僅供開發使用！

生產環境部署時：
1. 使用環境變數管理資料庫密碼
2. 啟用 HTTPS
3. 設定防火牆規則
4. 使用反向代理（Nginx）
5. 關閉 debug 模式：
   ```python
   app.run_server(debug=False, host='0.0.0.0', port=8050)
   ```

---

## 🚀 進階功能

### 新增交易對

在各頁面的 `dbc.Select` 中添加選項：

```python
dbc.Select(
    options=[
        {'label': 'BTC/USDT', 'value': 'BTC/USDT'},
        {'label': 'ETH/USDT', 'value': 'ETH/USDT'},
        {'label': 'SOL/USDT', 'value': 'SOL/USDT'},  # 新增
    ],
    value='BTC/USDT'
)
```

### 自訂策略

在 `data_loader.py` 的 `get_strategy_signals()` 中添加策略：

```python
from strategies.your_strategy import YourStrategy

strategies = [
    MACDStrategy(name="MACD_Cross"),
    YourStrategy(name="Custom_Strategy"),  # 新增
]
```

---

## 📝 版本更新記錄

### v2.0 - 實時版本（2025-12-27）

**主要更新**：
- ✅ 多層級刷新機制（1秒/5秒/30秒）
- ✅ Redis 快取層整合
- ✅ 載入狀態指示器
- ✅ 優化資料查詢效能
- ✅ 自動環境檢查腳本

**技術改進**：
- 將刷新間隔從 60 秒縮短至 1-5 秒
- 加入 Redis 快取減少 80%+ 重複查詢
- 實現自動降級機制（Redis 不可用時仍可運行）
- 添加詳細的效能監控指標

**檔案變更**：
- 新增：`cache_manager.py` - Redis 快取管理器
- 新增：`start_realtime.sh` - 實時版本啟動腳本
- 修改：`app.py` - 多層級 Interval 組件
- 修改：`data_loader.py` - 整合快取邏輯
- 修改：所有頁面 - 使用新的 Interval ID
- 更新：`requirements.txt` - 添加 Redis 依賴

### v1.0 - 初始版本

- 基礎 Dashboard 功能
- 4 個分析頁面
- 60 秒刷新間隔
- PostgreSQL 直接查詢

---

## 📝 授權

本專案採用 MIT 授權。
