# 交易所 API 設置指南

## 📊 當前狀況總結

### 問題診斷
**不是**因為請求量過大導致封鎖，而是**網路層級的 DNS 封鎖**。

**證據**：
- DNS 解析失敗（NXDOMAIN）
- 即使使用 Google DNS (8.8.8.8) 也無法解析
- 一般網站（google.com）可以正常訪問
- 錯誤發生在 DNS 層，連 HTTP 請求都沒發送

### 交易所可用性

| 交易所 | 狀態 | BTC 價格 | 說明 |
|--------|------|----------|------|
| **Binance** | ❌ 被封鎖 | - | DNS 無法解析 |
| **OKX** | ❌ 被封鎖 | - | DNS 無法解析，需 VPN |
| **Coinbase** | ❌ 被封鎖 | - | DNS 無法解析 |
| **Bybit** | ✅ 可用 | $88,747 | 立即可用 |
| **Kraken** | ✅ 可用 | $88,702 | 立即可用 |

---

## 🚀 方案 A：立即使用 Bybit（推薦）

### 優點
- ✅ **立即可用**，無需 VPN
- ✅ 支援 **483 個 USDT 交易對**
- ✅ API 限流寬鬆（20ms）
- ✅ 支援現貨、合約、期權
- ✅ 中文介面與客服

### 使用步驟

#### 1. 測試 Bybit 連接
```bash
cd collector-py
python src/connectors/bybit_rest.py
```

**預期輸出**：
```
測試獲取 BTC/USDT 1m K線...
2025-12-26 17:27:00 | O:88761.6 H:88763.2 L:88749.8 C:88749.8 V:2.241766
...
✓ 載入 483 個 USDT 現貨交易對
```

#### 2. 修改 Collector 配置

編輯 `collector-py/src/main.py`：

```python
# 原本使用 Binance
# from connectors.binance_rest import BinanceRESTConnector
# client = BinanceRESTConnector()

# 改用 Bybit
from connectors.bybit_rest import BybitClient
client = BybitClient()
```

#### 3. 開始收集資料

```bash
cd collector-py
python src/main.py
```

### Bybit API 範例

```python
from connectors.bybit_rest import BybitClient

# 初始化
client = BybitClient()

# 獲取 K 線
ohlcv = client.fetch_ohlcv('BTC/USDT', '1m', limit=1000)

# 獲取 ticker
ticker = client.fetch_ticker('BTC/USDT')
print(f"BTC 價格: ${ticker['last']:,.2f}")

# 獲取訂單簿
orderbook = client.fetch_order_book('BTC/USDT', limit=50)

# 獲取成交記錄
trades = client.fetch_trades('BTC/USDT', limit=1000)

# 查看所有 USDT 交易對
markets = client.get_markets()
print(f"可用交易對: {len(markets)} 個")
```

---

## 🔧 方案 B：設置 VPN 使用 OKX

### OKX 優點
- 🌏 亞洲最大交易所之一
- 📊 流動性極佳
- 🔥 手續費較低
- 📱 功能完善（現貨、合約、策略交易）

### 設置步驟

#### 1. 安裝並連接 VPN

推薦 VPN 節點：
- 🇭🇰 香港
- 🇸🇬 新加坡
- 🇯🇵 日本
- 🇺🇸 美國

#### 2. 驗證 DNS 已切換

```bash
# 測試 DNS 解析
nslookup www.okx.com

# 應該返回 IP 地址而非 NXDOMAIN
```

#### 3. 測試 OKX 連接

```bash
python test_okx_detailed.py
```

**成功輸出範例**：
```
測試 OKX 預設節點...
  ✓ 連線成功！伺服器時間: 2025-12-26 17:30:00
  ✓ BTC 價格: $88,750.00
✓ 找到 500+ 個 USDT 現貨交易對
```

#### 4. 使用 OKX Connector

```python
from connectors.okx_rest import OKXRESTConnector

# 初始化（公開資料不需要 API 金鑰）
client = OKXRESTConnector()

# 獲取 K 線（OKX 單次最多 100 條）
ohlcv = client.fetch_ohlcv('BTC/USDT', '1m', limit=100)

# 獲取更多資料需要分批
all_ohlcv = []
since = None
for _ in range(10):  # 獲取 1000 條
    batch = client.fetch_ohlcv('BTC/USDT', '1m', since=since, limit=100)
    all_ohlcv.extend(batch)
    since = batch[-1][0] + 60000  # 下一分鐘
```

### OKX API 限制
⚠️ **注意**：
- 單次最多 **100 條** K 線
- 需要分批抓取大量歷史資料
- Rate limit: 約 20 req/s

---

## 🎯 方案 C：多交易所並行（最佳實踐）

### 架構設計

```python
# collector-py/src/multi_exchange_collector.py

from connectors.bybit_rest import BybitClient
from connectors.okx_rest import OKXRESTConnector  # 需 VPN
# from connectors.kraken_rest import KrakenClient  # 可選

class MultiExchangeCollector:
    def __init__(self):
        self.exchanges = {
            'bybit': BybitClient(),
            # 'okx': OKXRESTConnector(),  # 需 VPN
        }

    def fetch_all_prices(self, symbol: str):
        """從所有交易所獲取價格"""
        prices = {}
        for name, client in self.exchanges.items():
            try:
                ticker = client.fetch_ticker(symbol)
                prices[name] = ticker['last']
            except Exception as e:
                print(f"{name} 失敗: {e}")

        return prices

    def get_consensus_price(self, symbol: str):
        """獲取共識價格（中位數）"""
        prices = self.fetch_all_prices(symbol)
        if prices:
            price_list = sorted(prices.values())
            median = price_list[len(price_list) // 2]
            return median
        return None
```

### 使用範例

```python
collector = MultiExchangeCollector()

# 獲取所有交易所的 BTC 價格
prices = collector.fetch_all_prices('BTC/USDT')
print(prices)
# {'bybit': 88747.3, 'okx': 88750.2}

# 獲取共識價格
consensus = collector.get_consensus_price('BTC/USDT')
print(f"共識價格: ${consensus:,.2f}")
```

### 多交易所優勢

1. **互為備援**
   - 單一交易所故障不影響系統
   - 自動切換到可用交易所

2. **資料驗證**
   - 交叉比對價格，發現異常
   - 識別單一交易所的資料問題

3. **套利機會**
   - 發現價差
   - 優化交易執行

4. **更全面的市場視角**
   - 不同交易所的流動性
   - 更準確的市場深度

---

## 📝 常見問題

### Q1: 為什麼 Binance/OKX 連不上？

**A**: 這是 DNS 層級的封鎖，可能原因：
1. ISP 封鎖加密貨幣交易所域名
2. 地區性網路審查
3. 企業/校園網路防火牆

**解決**：
- 使用 VPN 連接到香港/新加坡節點
- 或使用可用的 Bybit/Kraken

### Q2: 是否因為請求太多被封鎖？

**A**: **不是**。證據：
- DNS 解析失敗（NXDOMAIN）
- 連 HTTP 請求都沒發送
- 如果是 rate limit，會收到 HTTP 429 錯誤

Rate limit 錯誤範例：
```python
ccxt.RateLimitExceeded: binance
{"code":-1003,"msg":"Too much request weight used"}
```

我們的錯誤是：
```python
ccxt.NetworkError: binance GET https://api.binance.com/api/v3/time
# DNS 根本無法解析
```

### Q3: Bybit 和 OKX 有什麼差異？

| 特性 | Bybit | OKX |
|------|-------|-----|
| 可用性 | ✅ 無需 VPN | ❌ 需 VPN |
| USDT 交易對 | 483 個 | 500+ 個 |
| API 限流 | 20ms | 20ms |
| 單次 K 線 | 1000 條 | 100 條 |
| 中文支援 | ✅ | ✅ |
| 手續費 | 0.1% | 0.08% |

**建議**：
- 無 VPN → 使用 Bybit
- 有 VPN → 可選 OKX
- 最佳方案 → 兩者都用（互為備援）

### Q4: 如何確認是否需要 VPN？

**測試方法**：
```bash
# 測試 OKX DNS
nslookup www.okx.com

# 如果返回 NXDOMAIN → 需要 VPN
# 如果返回 IP 地址 → 不需要 VPN
```

### Q5: 可以同時使用多個交易所嗎？

**A**: 可以，而且**強烈推薦**！

優點：
- 🔄 互為備援
- 📊 資料交叉驗證
- 🎯 發現套利機會
- 💪 降低單點失敗風險

---

## 🎯 建議行動

### 立即執行（推薦）

```bash
# 1. 測試 Bybit 連接
python collector-py/src/connectors/bybit_rest.py

# 2. 如果測試成功，開始收集資料
cd collector-py
python src/main.py  # 確保已改用 BybitClient
```

### VPN 使用者（可選）

```bash
# 1. 連接 VPN（香港/新加坡節點）

# 2. 測試 OKX
python test_okx_detailed.py

# 3. 如果成功，可以使用 OKX
```

### 長期優化

1. 建立多交易所並行架構
2. 實現自動故障切換
3. 建立健康度監控
4. 設置價格交叉驗證

---

## 📚 相關檔案

- `collector-py/src/connectors/bybit_rest.py` - Bybit 連接器（已測試）
- `collector-py/src/connectors/okx_rest.py` - OKX 連接器（需 VPN）
- `test_binance_alternatives.py` - 交易所可用性測試
- `test_okx_detailed.py` - OKX 詳細測試
- `EXCHANGE_BLOCKING_ANALYSIS.md` - 封鎖問題分析

---

## ✅ 總結

1. **問題原因**：網路層級 DNS 封鎖（不是 rate limit）
2. **立即方案**：使用 Bybit（無需 VPN，已測試）
3. **VPN 方案**：OKX 可用（需連接 VPN）
4. **最佳實踐**：多交易所並行架構

**下一步**：選擇方案 A（Bybit）或方案 B（OKX + VPN），開始收集資料！
