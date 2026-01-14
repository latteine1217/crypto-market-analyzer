# BTC 地址分層追蹤功能 - 完整使用指南

> **狀態**: ✅ 已實作完成  
> **版本**: v1.0  
> **更新時間**: 2026-01-15

---

## 📋 功能概述

追蹤 Bitcoin 鏈上不同持幣量級別地址的分布與每日變動，提供類似 YouTube 頻道「東一獨家鏈上數據」的可視化輸出。

### 核心功能

1. **資料收集**: 從 Glassnode API 收集 BTC 地址分層分布資料
2. **資料庫儲存**: 儲存至 TimescaleDB，支援時序查詢與聚合
3. **終端輸出**: 彩色表格即時查看地址變動（類似圖片風格）
4. **報表整合**: HTML 熱力圖整合進每日/每週報表

### 地址分層定義

| 分層 | 持幣量範圍 | 描述 |
|------|-----------|------|
| 0-1 Coins | < 1 BTC | 小額持有者（散戶） |
| 1-10 Coins | 1-10 BTC | 中額持有者 |
| 10-100 Coins | 10-100 BTC | 大戶 |
| 100-1K Coins | 100-1,000 BTC | 巨鯨層級 1 |
| 1K-10K Coins | 1,000-10,000 BTC | 巨鯨層級 2 |
| 10K+ Coins | > 10,000 BTC | 超級巨鯨 |

---

## 🚀 快速開始

### 1. 環境準備

#### 1.1 安裝依賴

```bash
cd /Users/latteine/Documents/coding/finance

# Python 依賴
pip install aiohttp asyncpg loguru rich pandas plotly

# 或使用 requirements.txt
pip install -r collector-py/requirements.txt
```

#### 1.2 取得 Glassnode API Key

1. 前往 [Glassnode Studio](https://studio.glassnode.com/settings/api)
2. 註冊帳號並生成 API Key
3. 複製 API Key

#### 1.3 配置環境變數

編輯 `.env` 文件，添加：

```bash
# Glassnode API
GLASSNODE_API_KEY=your_glassnode_api_key_here

# 資料庫配置（如已存在，確認正確）
DB_HOST=localhost
DB_PORT=5432
DB_USER=crypto
DB_PASSWORD=crypto_pass
DB_NAME=crypto_db
```

### 2. 資料庫初始化

#### 2.1 啟動 Docker 服務

```bash
docker-compose up -d timescaledb
```

#### 2.2 執行 Migration

```bash
docker exec -i crypto_timescaledb psql -U crypto -d crypto_db < database/migrations/011_add_address_tier_tracking.sql
```

**驗證成功**：應看到以下訊息

```
CREATE TABLE
...
✅ Migration 011 驗證通過
```

---

## 📊 使用方式

### 方式一：終端即時查看（推薦）

#### 執行 Demo（模擬資料）

```bash
python3 scripts/demo_address_tiers.py
```

**輸出範例**：

```
 ▶   YouTube東一獨家鏈上數據                     注: 排除非行為性噪聲樣本

             BTC鏈上數據                           10:25            
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓
┃ BTC Address  ┃  BTC held  ┃  01/15  ┃  01/14  ┃  01/13  ┃
┃ Tiers        ┃            ┃         ┃         ┃         ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━┩
│ (0-1)Coins   │  1,387,528 │  +309   │  +518   │  -543   │
│              │            │   BTC   │   BTC   │   BTC   │
│ (10K+)Coins  │ 12,008,116 │  +183   │ +2645   │ +1392   │
│              │            │   BTC   │   BTC   │   BTC   │
└──────────────┴────────────┴─────────┴─────────┴─────────┘

🔍 重點觀察
  • 綠色 = 流入/增加（買入訊號）
  • 紅色 = 流出/減少（賣出訊號）
  • 巨鯨層級 (100+) 持續流入 → 看漲訊號
```

#### 執行真實資料查詢（需先收集資料）

```bash
python3 scripts/show_address_tiers.py
```

### 方式二：資料收集與儲存

#### 手動執行單次收集

```bash
cd collector-py
python3 collect_address_tiers.py
```

**執行流程**：

```
[步驟 1] 收集最新地址分層分布...
  0-1       :   1,387,528.00 BTC |   48,500,000 addresses (24h: -842 BTC)
  1-10      :   2,089,601.00 BTC |      850,000 addresses (24h: -1222 BTC)
  10-100    :   4,302,751.00 BTC |      145,000 addresses (24h: -3244 BTC)
  100-1K    :   5,500,000.00 BTC |       15,000 addresses (24h: +5221 BTC)
  1K-10K    :   4,200,000.00 BTC |        1,200 addresses (24h: +3350 BTC)
  10K+      :  12,008,116.00 BTC |          150 addresses (24h: +1010 BTC)

[步驟 2] 準備資料...
[步驟 3] 寫入資料庫...
✅ 成功寫入 6/6 筆資料

[步驟 4] 更新統計資訊...
✅ 統計資訊已更新
```

#### 設定定時任務（每日自動收集）

編輯 `crontab` 添加排程：

```bash
crontab -e
```

添加以下行（每天 UTC 00:00 執行）：

```bash
0 0 * * * cd /Users/latteine/Documents/coding/finance/collector-py && /usr/bin/python3 collect_address_tiers.py >> /tmp/address_tiers_collector.log 2>&1
```

---

## 📈 報表整合

### 在報表中顯示地址分層熱力圖

編輯 `data-analyzer/src/reports/data_collector.py`，添加方法：

```python
async def collect_address_tier_data(
    self,
    blockchain: str = 'BTC',
    days: int = 7
) -> Dict[str, Any]:
    """收集地址分層資料（用於報表）"""
    query = """
    SELECT 
        DATE(ats.snapshot_date) AS date,
        at.tier_name,
        at.display_order,
        ats.balance_change_24h
    FROM address_tier_snapshots ats
    JOIN blockchains b ON ats.blockchain_id = b.id
    JOIN address_tiers at ON ats.tier_id = at.id
    WHERE b.name = $1
      AND ats.snapshot_date >= NOW() - INTERVAL '1 day' * $2
    ORDER BY ats.snapshot_date DESC, at.display_order
    """
    
    rows = await self.conn.fetch(query, blockchain, days)
    
    # 轉換為 DataFrame
    import pandas as pd
    df = pd.DataFrame([dict(row) for row in rows])
    
    return {'tier_data': df}
```

在 `html_generator.py` 中使用：

```python
# 生成熱力圖
tier_data = report_data.get('address_tier_data', {}).get('tier_data')
if tier_data is not None and not tier_data.empty:
    heatmap_html = chart_gen.generate_address_tier_heatmap(
        tier_data,
        title="BTC 地址分層流動熱力圖（過去 7 天）"
    )
    
    if heatmap_html:
        html_content += f"""
        <h2>🔗 鏈上數據追蹤</h2>
        <div class="chart-container">
            {heatmap_html}
        </div>
        """
```

---

## 📊 資料查詢範例

### SQL 查詢

#### 查詢今日所有分層資料

```sql
SELECT * 
FROM get_address_tier_distribution('BTC', CURRENT_DATE);
```

#### 查詢過去 7 天熱力圖資料

```sql
SELECT * 
FROM get_address_tier_heatmap_data('BTC', 7);
```

#### 檢測異常流動（單日變動 > 1000 BTC）

```sql
SELECT * 
FROM detect_tier_anomalies('BTC', CURRENT_DATE - 7, CURRENT_DATE, 1000);
```

### Python 查詢

```python
import asyncpg
import pandas as pd

async def query_tier_data():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='crypto',
        password='crypto_pass',
        database='crypto_db'
    )
    
    # 查詢今日資料
    rows = await conn.fetch(
        "SELECT * FROM get_address_tier_distribution('BTC', CURRENT_DATE)"
    )
    
    df = pd.DataFrame([dict(row) for row in rows])
    print(df)
    
    await conn.close()
```

---

## 🔧 進階配置

### 自訂分層定義

如需新增自訂分層，編輯 `database/migrations/011_add_address_tier_tracking.sql`：

```sql
INSERT INTO address_tiers (tier_name, min_balance, max_balance, display_order, description) VALUES
    ('50-100', 50, 100, 7, 'Custom tier (50-100 BTC)');
```

### 調整資料保留期限

預設保留 365 天，修改 retention policy：

```sql
SELECT remove_retention_policy('address_tier_snapshots');
SELECT add_retention_policy('address_tier_snapshots', INTERVAL '180 days');
```

### API 速率限制

Glassnode 免費帳號限制：**10 requests/min**

在 `glassnode_collector.py` 中調整：

```python
collector = GlassnodeCollector(
    api_key=api_key,
    blockchain='BTC',
    rate_limit=5  # 降低為 5 requests/min（更保守）
)
```

---

## 📝 資料庫 Schema

### 主要資料表

#### `address_tiers`（分層定義）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | SERIAL | 主鍵 |
| tier_name | TEXT | 分層名稱（'0-1', '1-10', ...） |
| min_balance | NUMERIC | 最小持幣量（含） |
| max_balance | NUMERIC | 最大持幣量（不含） |
| display_order | INT | 顯示順序 |

#### `address_tier_snapshots`（時序資料）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | BIGSERIAL | 主鍵 |
| snapshot_date | TIMESTAMPTZ | 快照日期 |
| blockchain_id | INT | 區塊鏈 ID（外鍵） |
| tier_id | INT | 分層 ID（外鍵） |
| address_count | BIGINT | 地址數量 |
| total_balance | NUMERIC | 總持幣量 |
| balance_change_24h | NUMERIC | 24小時變動 |
| balance_pct | NUMERIC | 佔總流通量百分比 |
| data_source | TEXT | 資料來源（'glassnode'） |

---

## ⚠️ 注意事項

### API 配額

- **免費帳號**: 10 requests/min, 有限歷史資料
- **付費帳號**: 更高速率限制，完整歷史資料
- **建議**: 每日執行一次收集即可，避免超過配額

### 資料延遲

- Glassnode 資料通常有 **1-2 小時延遲**
- 建議在 UTC 01:00 後收集前一日資料

### 錯誤處理

如遇到 API 錯誤：

1. **403 Forbidden**: API key 無效或配額用盡
2. **429 Too Many Requests**: 速率限制超過，自動等待 60 秒重試
3. **404 Not Found**: 端點不存在，檢查 Glassnode 文檔

---

## 🔍 故障排除

### 問題 1: 無法連接資料庫

**症狀**: `connection refused`

**解決方案**:

```bash
# 檢查 Docker 服務
docker-compose ps

# 重啟資料庫
docker-compose restart timescaledb
```

### 問題 2: Migration 執行失敗

**症狀**: `relation already exists`

**解決方案**:

```bash
# 檢查是否已執行過
docker exec crypto_timescaledb psql -U crypto -d crypto_db -c "\dt address_tier*"

# 如已存在，跳過 migration
```

### 問題 3: API 無回應資料

**症狀**: `未收集到任何資料`

**可能原因**:

1. API key 無效 → 檢查 `.env` 配置
2. 免費帳號權限不足 → 升級為付費帳號
3. 網路問題 → 檢查防火牆設定

---

## 📚 相關文檔

- [Glassnode API 文檔](https://docs.glassnode.com/)
- [TimescaleDB 文檔](https://docs.timescale.com/)
- [Rich CLI 文檔](https://rich.readthedocs.io/)
- [Plotly Python 文檔](https://plotly.com/python/)

---

## 🎯 下一步計劃

### Phase 2 功能擴展

- [ ] 支援 Ethereum (ETH) 地址分層追蹤
- [ ] 支援 Binance Smart Chain (BSC)
- [ ] 新增地址分層「流動速度」指標
- [ ] 整合 Telegram 告警（異常流動時推送通知）
- [ ] 建立 Grafana Dashboard（即時監控）

---

**最後更新**: 2026-01-15  
**維護者**: 開發團隊  
**版本**: v1.0
