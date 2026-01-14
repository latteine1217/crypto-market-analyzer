# 📊 BTC 地址分層追蹤 - 快速參考

## 🚀 一鍵啟動

```bash
# 查看 Demo（不需要任何配置）
python3 scripts/demo_address_tiers.py
```

## 📝 設定步驟（5 分鐘）

### 1. 取得 API Key
前往 https://studio.glassnode.com/settings/api → 註冊 → 複製 API Key

### 2. 配置環境
```bash
# 編輯 .env
GLASSNODE_API_KEY=your_api_key_here
```

### 3. 啟動資料庫
```bash
docker-compose up -d timescaledb
```

### 4. 執行 Migration
```bash
docker exec -i crypto_timescaledb psql -U crypto -d crypto_db < database/migrations/011_add_address_tier_tracking.sql
```

### 5. 收集資料
```bash
cd collector-py
python3 collect_address_tiers.py
```

### 6. 查看結果
```bash
python3 scripts/show_address_tiers.py
```

## 📊 地址分層定義

| 分層 | 範圍 | 說明 |
|------|------|------|
| 0-1 | < 1 BTC | 散戶 |
| 1-10 | 1-10 BTC | 中戶 |
| 10-100 | 10-100 BTC | 大戶 |
| 100-1K | 100-1K BTC | 巨鯨 1 |
| 1K-10K | 1K-10K BTC | 巨鯨 2 |
| 10K+ | > 10K BTC | 超級巨鯨 |

## 🔍 分析策略

### 看漲訊號
- ✅ 100+ BTC 層級持續流入（綠色）
- ✅ 0-1 BTC 層級持續流出（紅色）= 散戶恐慌賣出

### 看跌訊號
- ⚠️ 100+ BTC 層級持續流出（紅色）
- ⚠️ 0-1 BTC 層級持續流入（綠色）= FOMO 追高

## 🛠️ 常用指令

```bash
# 查看今日資料
python3 scripts/show_address_tiers.py

# 執行資料收集
python3 collector-py/collect_address_tiers.py

# 設定定時任務（每日 01:00 UTC）
crontab -e
# 添加: 0 1 * * * cd /path/to/finance/collector-py && python3 collect_address_tiers.py
```

## 📊 SQL 查詢

```sql
-- 查詢今日所有分層
SELECT * FROM get_address_tier_distribution('BTC', CURRENT_DATE);

-- 查詢過去 7 天熱力圖資料
SELECT * FROM get_address_tier_heatmap_data('BTC', 7);

-- 檢測異常流動（> 1000 BTC）
SELECT * FROM detect_tier_anomalies('BTC', CURRENT_DATE - 7, CURRENT_DATE, 1000);
```

## 📚 文檔索引

- **完整指南**: `docs/ADDRESS_TIER_TRACKING_GUIDE.md`
- **實作總結**: `docs/ADDRESS_TIER_IMPLEMENTATION_SUMMARY.md`
- **Migration**: `database/migrations/011_add_address_tier_tracking.sql`

## ⚠️ 注意事項

- **API 限制**: 免費帳號 10 requests/min
- **資料延遲**: 1-2 小時（Glassnode）
- **建議頻率**: 每日執行一次即可

---

**狀態**: ✅ 已完成  
**更新**: 2026-01-15
