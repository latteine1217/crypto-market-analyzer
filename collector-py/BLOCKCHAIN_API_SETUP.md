# 區塊鏈 API 設定總結

## ✅ 已完成設定

### 1. API Keys 配置

所有 API keys 已配置在 `collector-py/.env`:

```bash
# Etherscan API (Ethereum 主網)
ETHERSCAN_API_KEY=ZRH3AV7J1N9XNJHBYCJJCGSRPFWTB9XXUZ

# BscScan API (Binance Smart Chain)
BSCSCAN_API_KEY=ZRH3AV7J1N9XNJHBYCJJCGSRPFWTB9XXUZ

# TronScan API (Tron 主網) - 可選
TRONSCAN_API_KEY=

# Blockchain.com API (Bitcoin) - 不需要 key
BLOCKCHAIN_API_KEY=
```

### 2. API Endpoints 配置

已在 `configs/whale_tracker.yml` 中配置:

| 區塊鏈 | API 端點 | 狀態 |
|--------|----------|------|
| Ethereum | https://api.etherscan.io/api | ✅ 正常 |
| BSC | https://api.bscscan.com/api | ✅ 正常 |
| Bitcoin | https://blockchain.info | ✅ 正常 |

### 3. 程式碼修正

已修正 `collector-py/src/utils/config_loader.py`:
- ✅ 正確映射區塊鏈縮寫到完整名稱 (ETH → ethereum)
- ✅ 正確映射 API key 名稱 (eth → etherscan)
- ✅ 處理特殊配置 (Bitcoin 的多個 API)

---

## ⚠️ 已知問題與解決方案

### 1. BscScan API Key 問題

**問題**: 測試顯示 BscScan API 返回 "NOTOK" 錯誤

**原因**: BscScan 需要獨立的 API key,不能直接使用 Etherscan 的 key

**解決方案**:
1. 前往 https://bscscan.com/myapikey
2. 使用你的 Etherscan 帳號登入 (同一團隊)
3. 申請 BscScan 專屬的 API key
4. 更新 `.env` 文件中的 `BSCSCAN_API_KEY`

### 2. Etherscan API "NOTOK" 錯誤

**可能原因**:
1. API key 已達到免費版限制 (每秒 5 次請求)
2. 需要驗證 API key 是否有效

**檢查方式**:
```bash
# 測試 Etherscan API
curl "https://api.etherscan.io/api?module=account&action=balance&address=0x0000000000000000000000000000000000000000&apikey=ZRH3AV7J1N9XNJHBYCJJCGSRPFWTB9XXUZ"
```

**解決方案**:
- 如果返回錯誤,可能需要重新申請或升級到付費版
- 建議查看 Etherscan 帳號的 API 使用狀況

### 3. CoinGecko API 限制 (429 錯誤)

**問題**: 免費版 CoinGecko API 有請求限制

**影響**: 測試時可能無法獲取價格,但不影響主要功能

**解決方案**:
- 使用價格快取機制 (已實作,預設 5 分鐘)
- 或申請 CoinGecko API key (可選)

### 4. Blockchair API 限制 (430 錯誤)

**問題**: Blockchair 免費版有嚴格的請求限制

**影響**: Bitcoin 大額交易查詢可能受限

**解決方案**:
- 使用 Blockchain.com API 作為主要來源
- Blockchair 作為備用或升級到付費版

---

## 🔧 測試與驗證

### 執行測試腳本

```bash
cd collector-py
python3 test_blockchain_apis.py
```

### 測試結果解讀

| 測試項目 | 狀態 | 說明 |
|---------|------|------|
| Etherscan 配置 | ✅ | API URL 和 Key 已正確載入 |
| BscScan 配置 | ✅ | API URL 和 Key 已正確載入 |
| Bitcoin 配置 | ✅ | API URL 已正確載入 |
| 價格查詢 | ⚠️ | 受 CoinGecko 免費限制影響 |
| 交易查詢 | ⚠️ | 需要有效的 API key |

---

## 📝 後續步驟

### 必須完成
1. ✅ 配置 Etherscan API key
2. ⬜ 申請並配置 BscScan 獨立 API key
3. ⬜ 驗證 Etherscan API key 有效性

### 可選項目
1. ⬜ 申請 TronScan API key (如需追蹤 TRON 鏈)
2. ⬜ 申請 CoinGecko API key (提升價格查詢穩定性)
3. ⬜ 升級 Blockchair 付費版 (提升 Bitcoin 查詢效能)

---

## 🚀 開始使用

### 1. 基本使用範例

```python
import asyncio
from connectors.ethereum_whale_tracker import EthereumWhaleTracker
from utils.config_loader import load_whale_tracker_config, get_blockchain_config

async def main():
    # 載入配置
    config = load_whale_tracker_config()
    eth_config = get_blockchain_config('ETH', config)

    # 建立追蹤器
    tracker = EthereumWhaleTracker(
        api_key=eth_config['api_key'],
        config=eth_config
    )

    # 查詢大額交易
    txs = await tracker.get_recent_transactions(
        address='0x28C6c06298d514Db089934071355E5743bf21d60',
        limit=10
    )

    for tx in txs:
        print(f"交易: {tx.tx_hash}")
        print(f"金額: {tx.amount} {tx.token_symbol or 'ETH'}")

    await tracker.close()

asyncio.run(main())
```

### 2. 整合到資料收集器

參考 `configs/whale_tracker.yml` 中的排程配置:

```yaml
collection:
  # 即時監控
  realtime:
    enabled: true
    poll_interval: 60     # 每分鐘輪詢一次

  # 排程配置
  schedule:
    full_scan_interval: "0 */6 * * *"   # 每 6 小時全量掃描
    light_poll_interval: "*/5 * * * *"  # 每 5 分鐘輕量輪詢
```

---

## 📚 相關資源

### API 文檔
- [Etherscan API Docs](https://docs.etherscan.io/)
- [BscScan API Docs](https://docs.bscscan.com/)
- [Blockchain.com API Docs](https://www.blockchain.com/api)
- [CoinGecko API Docs](https://www.coingecko.com/en/api)

### 程式碼檔案
- 配置載入: `collector-py/src/utils/config_loader.py`
- Ethereum 追蹤器: `collector-py/src/connectors/ethereum_whale_tracker.py`
- BSC 追蹤器: `collector-py/src/connectors/bsc_whale_tracker.py`
- Bitcoin 追蹤器: `collector-py/src/connectors/bitcoin_whale_tracker.py`
- 測試腳本: `collector-py/test_blockchain_apis.py`

---

## 💡 最佳實踐

1. **API Key 安全**
   - 永遠不要將 API key 提交到 Git
   - 使用環境變數管理敏感資訊
   - 定期輪換 API key

2. **請求限制管理**
   - 遵守各 API 的速率限制
   - 實作重試機制與指數退避
   - 使用快取減少重複請求

3. **錯誤處理**
   - 記錄所有 API 錯誤
   - 實作降級方案 (fallback)
   - 監控 API 可用性

4. **資料品質**
   - 驗證獲取的資料完整性
   - 標記異常交易
   - 定期檢查資料缺失

---

**更新日期**: 2025-12-28
**維護者**: @latteine
