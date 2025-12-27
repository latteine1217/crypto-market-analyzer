# 交易所 API 連接問題診斷報告

## 📊 問題現象

### 無法連接的交易所
- ❌ **Binance** (api.binance.com)
- ❌ **OKX** (www.okx.com, aws.okx.com)
- ❌ **Coinbase** (api.coinbase.com)

### 可以連接的交易所
- ✅ **Bybit** (api.bybit.com) - BTC 價格 $88,747
- ✅ **Kraken** (api.kraken.com) - BTC 價格 $88,702

---

## 🔍 問題根因分析

### ❌ 不是 API 請求量過大

**證據 1: DNS 解析失敗**
```bash
$ nslookup api.binance.com
Server:		192.168.10.1
Address:	192.168.10.1#53

** server can't find api.binance.com: NXDOMAIN
```

**NXDOMAIN 的意義**：
- DNS 伺服器**完全無法解析**該域名
- 表示在 DNS 層級就被封鎖，連嘗試連接的機會都沒有
- 這發生在**發送任何 HTTP 請求之前**

**證據 2: Google DNS 也無法解析**
```bash
$ nslookup api.binance.com 8.8.8.8
Server:		8.8.8.8
Address:	8.8.8.8#53

** server can't find api.binance.com: NXDOMAIN
```

即使使用 Google 公共 DNS (8.8.8.8) 也無法解析，排除本地 DNS 問題。

### ✅ 真正的原因：網路層級封鎖

**原因分析**：

1. **地區性封鎖**
   - 台灣或部分地區的 ISP 可能封鎖加密貨幣交易所
   - DNS 污染或封鎖特定域名

2. **防火牆規則**
   - 企業/校園網路可能封鎖交易所域名
   - 路由器或防火牆的黑名單

3. **ISP 層級限制**
   - 某些 ISP 會主動封鎖加密貨幣相關服務

---

## 📈 如果是 API 請求量過大，會看到什麼？

### Rate Limit 錯誤範例

**HTTP 429 錯誤**：
```python
ccxt.RateLimitExceeded: binance
{"code":-1003,"msg":"Too much request weight used"}
```

**特徵**：
- ✅ DNS 解析成功
- ✅ 成功建立 TCP 連接
- ✅ 成功發送 HTTP 請求
- ❌ 收到 HTTP 429 或 418 錯誤回應
- ⏰ 通常有明確的「重試時間」或「剩餘額度」

**我們的情況**：
```python
ccxt.NetworkError: binance GET https://api.binance.com/api/v3/time
# 連 DNS 都無法解析，根本沒發送請求
```

---

## 🔬 對比測試結果

| 項目 | Binance/OKX | Bybit/Kraken |
|------|-------------|--------------|
| DNS 解析 | ❌ NXDOMAIN | ✅ 成功 |
| TCP 連接 | ❌ 無法建立 | ✅ 成功 |
| HTTP 請求 | ❌ 未發送 | ✅ 成功 |
| API 回應 | ❌ 無回應 | ✅ 正常資料 |

**結論**：這是**網路層級的封鎖**，而非 API 層級的限流。

---

## 💡 解決方案

### 方案 1: 使用 VPN（推薦用於 OKX）

**步驟**：
1. 連接到支援加密貨幣交易的 VPN 節點
2. 確認 DNS 已改用 VPN 提供的 DNS
3. 測試連接：
```bash
python test_okx_detailed.py
```

**推薦 VPN 節點**：
- 香港
- 新加坡
- 日本
- 美國

### 方案 2: 使用可用的交易所（立即可用）

**Bybit 優勢**：
- ✅ 目前可正常連接
- ✅ 支援 483 個 USDT 交易對
- ✅ API 限流寬鬆 (20ms)
- ✅ 支援現貨、合約、期權

**Kraken 優勢**：
- ✅ 目前可正常連接
- ✅ 老牌交易所，信譽良好
- ✅ 監管合規

### 方案 3: 多交易所並行（最佳實踐）

同時從多個交易所收集資料：
```python
# collector 配置
exchanges = {
    'bybit': BybitClient(),
    'kraken': KrakenClient(),
    # 'okx': OKXClient(),  # 需 VPN
}

# 交叉驗證價格
for exchange_name, client in exchanges.items():
    ticker = client.fetch_ticker('BTC/USDT')
    print(f"{exchange_name}: ${ticker['last']:,.2f}")
```

**好處**：
- 🔄 互為備援
- 📊 資料交叉驗證
- 🎯 更全面的市場視角
- 💪 降低單點失效風險

---

## 🧪 驗證方法

### 測試 1: 檢查是否為 Rate Limit

```bash
# 如果是 rate limit，應該能解析域名
nslookup api.binance.com

# 如果返回 IP，則是 rate limit
# 如果返回 NXDOMAIN，則是網路封鎖
```

### 測試 2: 確認網路連通性

```bash
# 測試一般網站（應該成功）
curl -I https://www.google.com

# 測試 Binance（會失敗）
curl -I https://api.binance.com
```

### 測試 3: 嘗試不同 DNS

```bash
# 使用 Cloudflare DNS
nslookup api.binance.com 1.1.1.1

# 使用 Google DNS
nslookup api.binance.com 8.8.8.8
```

如果所有 DNS 都返回 NXDOMAIN → **確定是網路封鎖**

---

## 📝 建議行動方案

### 短期方案（立即可用）
1. ✅ 使用 Bybit 替代 Binance
2. ✅ 已建立 `bybit_rest.py` 連接器
3. ✅ API 測試通過，可立即使用

### 中期方案（需設置）
1. 🔧 設置 VPN 連接
2. 🔧 測試 OKX 連接
3. 🔧 建立多交易所並行架構

### 長期方案（架構優化）
1. 📊 實現多交易所資料融合
2. 📊 建立交易所健康度監控
3. 📊 自動切換故障交易所

---

## 🎯 下一步操作

### 選項 A: 立即使用 Bybit
```bash
cd collector-py
python src/connectors/bybit_rest.py  # 測試連接
```

### 選項 B: 設置 VPN 使用 OKX
1. 連接 VPN（香港/新加坡節點）
2. 測試連接：`python test_okx_detailed.py`
3. 如成功，使用 OKX 連接器

### 選項 C: 多交易所並行
修改 `collector-py` 配置，同時使用 Bybit + Kraken

---

**結論**：問題是**網路層級封鎖**，而非 API 請求量過大。建議立即使用 Bybit，或設置 VPN 使用 OKX。
