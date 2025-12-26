# 加密貨幣市場分析器 (Data Analyzer)

## 📊 功能概覽

本模組提供完整的加密貨幣技術分析功能，包括技術指標計算、交易策略實現和流動性分析。

### 已實現功能

#### 1. **技術指標計算** (`features/technical_indicators.py`)

- ✅ **MACD** (Moving Average Convergence Divergence)
  - 快線（12 日 EMA）、慢線（26 日 EMA）、信號線（9 日 EMA）
  - MACD 柱狀圖

- ✅ **移動平均線** (Moving Averages)
  - MA 20、MA 60、MA 200
  - 支援 SMA 和 EMA 兩種類型

- ✅ **威廉分形** (Williams Fractal)
  - 識別局部高點（上分形）和低點（下分形）
  - 可配置週期（預設 2）

- ✅ **頭肩形態** (Head & Shoulders)
  - 自動識別頭肩頂（看跌反轉）
  - 自動識別頭肩底（看漲反轉）
  - 基於威廉分形的形態識別

#### 2. **交易策略** (`strategies/`)

##### 2.1 MACD 策略 (`macd_strategy.py`)

- **MACD 交叉策略** (`MACDStrategy`)
  - 金叉（MACD 上穿 Signal）→ 買入
  - 死叉（MACD 下穿 Signal）→ 賣出
  - 可選：柱狀圖過濾弱信號

- **MACD 背離策略** (`MACDDivergenceStrategy`)
  - 牛背離（價格新低，MACD 未新低）→ 買入
  - 熊背離（價格新高，MACD 未新高）→ 賣出

##### 2.2 威廉分形策略 (`fractal_pattern_strategy.py`)

- **分形突破策略** (`FractalBreakoutStrategy`)
  - 突破上分形（阻力位）→ 做多
  - 跌破下分形（支撐位）→ 做空

- **頭肩形態策略** (`HeadShouldersStrategy`)
  - 頭肩頂完成 → 做空
  - 頭肩底完成 → 做多
  - 頸線突破確認

- **分形 + MA 結合策略** (`CombinedFractalMAStrategy`)
  - 價格在 MA 之上 + 突破上分形 → 做多
  - 價格在 MA 之下 + 跌破下分形 → 做空

#### 3. **流動性分析** (`features/liquidity_heatmap.py`)

- ✅ **訂單簿資料聚合**
  - 從資料庫讀取歷史 orderbook snapshots
  - 計算不同價格層級的累計掛單量

- ✅ **流動性熱力圖**
  - 時間 × 價格 的 2D 熱力圖
  - 識別流動性集中區域

- ✅ **流動性剖面圖**
  - Bids/Asks 分布可視化
  - 潛在支撐/阻力位識別

---

## 🚀 快速開始

### 安裝依賴

```bash
cd data-analyzer
pip install -r requirements.txt
```

### 使用範例

#### 方式 1：使用便捷函數

```python
import pandas as pd
from features.technical_indicators import calculate_indicators_for_symbol

# 載入 OHLCV 資料
df = load_your_data()  # pd.DataFrame with columns: open, high, low, close, volume

# 計算所有指標
df_with_indicators = calculate_indicators_for_symbol(df, symbol='BTC/USDT')

# 查看結果
print(df_with_indicators[['close', 'macd', 'ma_20', 'fractal_up']].tail())
```

#### 方式 2：使用策略類

```python
from strategies.macd_strategy import MACDStrategy

# 初始化策略
strategy = MACDStrategy(name="My_MACD", params={
    'fast_period': 12,
    'slow_period': 26,
    'signal_period': 9
})

# 生成交易信號
signals = strategy.generate_signals(df_with_indicators)

# 查看買賣信號
buy_signals = signals[signals == 1]   # 買入點
sell_signals = signals[signals == -1]  # 賣出點
```

#### 方式 3：完整分析流程

```bash
# 執行範例腳本
python example_usage.py
```

### 測試所有功能

```bash
# 執行完整測試
python test_all_features.py
```

---

## 📁 檔案結構

```
data-analyzer/
├── src/
│   ├── features/
│   │   ├── technical_indicators.py   # 技術指標計算
│   │   └── liquidity_heatmap.py      # 流動性分析
│   │
│   ├── strategies/
│   │   ├── strategy_base.py          # 策略基類
│   │   ├── macd_strategy.py          # MACD 策略
│   │   └── fractal_pattern_strategy.py  # 分形策略
│   │
│   ├── models/                        # 機器學習模型（待實現）
│   ├── backtesting/                   # 回測引擎（待實現）
│   └── reports/                       # 報表生成（待實現）
│
├── notebooks/                         # Jupyter 筆記本
├── example_usage.py                   # 使用範例
├── test_all_features.py              # 功能測試
└── README.md                          # 本文檔
```

---

## 🎯 使用案例

### 案例 1：單一策略回測

```python
from strategies.macd_strategy import MACDStrategy
import pandas as pd

# 1. 載入資料
df = load_market_data('binance', 'BTC/USDT')

# 2. 計算指標
df = TechnicalIndicators.add_all_indicators(df)

# 3. 應用策略
strategy = MACDStrategy()
signals = strategy.generate_signals(df)

# 4. 分析結果
buy_count = (signals == 1).sum()
sell_count = (signals == -1).sum()
print(f"買入信號: {buy_count}, 賣出信號: {sell_count}")
```

### 案例 2：多策略比較

```python
strategies = [
    MACDStrategy(name="MACD"),
    FractalBreakoutStrategy(name="Fractal"),
    CombinedFractalMAStrategy(name="Fractal_MA")
]

for strategy in strategies:
    signals = strategy.generate_signals(df)
    print(f"{strategy.name}: {(signals == 1).sum()} 買入, {(signals == -1).sum()} 賣出")
```

### 案例 3：流動性分析

```python
from features.liquidity_heatmap import analyze_liquidity

# 執行完整流動性分析
analyze_liquidity(
    exchange='binance',
    symbol='BTC/USDT',
    output_dir='./reports/liquidity'
)
```

---

## 📊 技術指標說明

### MACD (Moving Average Convergence Divergence)

**計算公式：**
- MACD Line = EMA(12) - EMA(26)
- Signal Line = EMA(9) of MACD
- Histogram = MACD - Signal

**交易信號：**
- 金叉（MACD 上穿 Signal）→ 買入
- 死叉（MACD 下穿 Signal）→ 賣出

### 威廉分形 (Williams Fractal)

**定義：**
- 上分形：中間 K 線的高點是左右各 N 根 K 線中的最高點
- 下分形：中間 K 線的低點是左右各 N 根 K 線中的最低點

**用途：**
- 識別局部高點和低點
- 確定支撐和阻力位
- 形態識別（頭肩頂/底）

### 頭肩形態 (Head & Shoulders)

**頭肩頂（看跌）：**
- 三個上分形：左肩 < 頭部 > 右肩
- 跌破頸線確認反轉

**頭肩底（看漲）：**
- 三個下分形：左肩 > 頭部 < 右肩
- 突破頸線確認反轉

---

## 🧪 測試結果

### 技術指標計算

```
✅ MACD: 500 個有效值
✅ MA (20, 60, 200): 481, 441, 301 個有效值
✅ Williams Fractal: 42 上分形, 49 下分形
✅ 頭肩形態: 11 頭肩頂, 15 頭肩底
```

### 策略信號生成

```
✅ MACD 策略: 18 買入, 18 賣出
✅ 威廉分形策略: 1 買入, 6 賣出
✅ 結合策略: 4 買入, 8 賣出
```

---

## ⚙️ 參數配置

### MACD 參數

```python
{
    'fast_period': 12,      # 快線週期
    'slow_period': 26,      # 慢線週期
    'signal_period': 9,     # 信號線週期
    'use_histogram_filter': False,  # 是否使用柱狀圖過濾
    'histogram_threshold': 0.0      # 柱狀圖閾值
}
```

### 威廉分形參數

```python
{
    'fractal_period': 2,           # 分形週期
    'lookback_fractals': 3,        # 回溯分形數量
    'breakout_threshold': 0.001    # 突破閾值（0.1%）
}
```

### 頭肩形態參數

```python
{
    'tolerance': 0.02,                  # 左右肩容忍度（2%）
    'neckline_break_threshold': 0.005,  # 頸線突破閾值（0.5%）
    'confirm_bars': 2                   # 確認 K 線數
}
```

---

## 📈 效能優化

### 計算效率

- 使用 pandas 向量化操作
- 避免迴圈，優先使用 `.shift()` 和 `.rolling()`
- MACD 計算使用高效的 EWM

### 記憶體優化

- 只保留必要的指標欄位
- 支援資料分批處理
- 使用 `dtype` 優化記憶體使用

---

## 🔮 未來擴展

### 短期規劃

- [ ] 回測引擎實現（`backtesting/`）
- [ ] 績效指標計算（Sharpe, Max Drawdown）
- [ ] 更多技術指標（RSI, Bollinger Bands）
- [ ] 策略參數優化

### 中期規劃

- [ ] 機器學習模型整合
- [ ] 鏈上資料分析
- [ ] 情緒指標分析
- [ ] 自動化報告生成

### 長期規劃

- [ ] 實盤交易接口
- [ ] 風險管理模組
- [ ] 組合優化
- [ ] Dashboard 視覺化

---

## 📝 注意事項

1. **避免未來資訊洩漏**
   - 所有策略嚴格使用 `.shift()` 避免看到未來資料
   - 回測時不允許使用 t+1 的資料決定 t 時點的交易

2. **資料品質要求**
   - 確保 OHLCV 資料完整無缺失
   - 移動平均線需要足夠的歷史資料（至少 200 根 K 線）
   - 分形識別需要左右各 2 根 K 線

3. **策略限制**
   - 技術指標存在滯後性
   - 歷史績效不代表未來表現
   - 需結合風險管理使用

---

## 🤝 貢獻指南

### 新增策略

1. 繼承 `StrategyBase`
2. 實現 `generate_signals()` 方法
3. 定義所需特徵 `get_required_features()`
4. 添加測試案例

### 新增技術指標

1. 在 `TechnicalIndicators` 類中添加靜態方法
2. 更新 `add_all_indicators()` 函數
3. 添加文檔說明和測試

---

## 📞 聯繫方式

若有問題或建議，請通過以下方式聯繫：

- 項目 GitHub: [你的 repo]
- Email: [你的 email]

---

## 📄 授權

本專案採用 MIT 授權。
