# Crypto Market Analyzer Dashboard

## 📊 功能特色

專業的加密貨幣市場分析 Dashboard，使用 Plotly Dash 建立。

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

### 1. 安裝依賴

```bash
cd dashboard
pip install -r requirements.txt
```

### 2. 確保資料庫運行

確保 TimescaleDB 正在運行並包含資料：

```bash
# 檢查資料庫連接
psql -h localhost -p 5432 -U crypto -d crypto_db -c "SELECT COUNT(*) FROM ohlcv;"
```

### 3. 啟動 Dashboard

```bash
python app.py
```

或使用啟動腳本：

```bash
chmod +x start.sh
./start.sh
```

### 4. 訪問 Dashboard

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
    password='crypto_pass'
)
```

### 自動刷新間隔

在 `app.py` 中調整：

```python
dcc.Interval(
    id='interval-component',
    interval=60*1000,  # 60 秒刷新一次
    n_intervals=0
)
```

---

## 📁 專案結構

```
dashboard/
├── app.py                  # 主應用程式
├── data_loader.py          # 資料載入模組
├── requirements.txt        # 依賴清單
├── pages/                  # 頁面模組
│   ├── __init__.py
│   ├── overview.py         # 首頁
│   ├── technical.py        # 技術分析頁面
│   ├── signals.py          # 交易信號頁面
│   └── liquidity.py        # 流動性分析頁面
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

## 🔄 即時更新

Dashboard 每 60 秒自動刷新資料，包括：
- ✅ 最新價格
- ✅ 技術指標
- ✅ 交易信號
- ✅ 訂單簿深度

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

## 📝 授權

本專案採用 MIT 授權。
