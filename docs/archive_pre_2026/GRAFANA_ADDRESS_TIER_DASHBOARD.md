# BTC 地址分層追蹤 - Grafana Dashboard 使用指南

## 📊 Dashboard 概覽

此 Dashboard 提供完整的 BTC 地址分層追蹤視覺化，包含：
- 餘額分布趨勢圖
- 地址數量變化
- 每日變動監控
- 巨鯨/散戶行為追蹤

---

## 🚀 快速開始

### 1. 導入 Dashboard

**方法 A: Grafana UI 手動導入**

1. 打開 Grafana：http://localhost:3000
2. 登入（預設: admin / admin）
3. 點擊左側選單 `+` → `Import`
4. 選擇 `Upload JSON file`
5. 上傳檔案：`monitoring/grafana/dashboards/btc_address_tiers.json`
6. 選擇資料源：`TimescaleDB`
7. 點擊 `Import`

**方法 B: 使用 Docker Volume（自動載入）**

如果 Grafana 容器已配置 provisioning，Dashboard 會自動載入。

檢查配置：
```bash
docker exec crypto_grafana ls /etc/grafana/provisioning/dashboards/
```

如果需要手動複製：
```bash
docker cp monitoring/grafana/dashboards/btc_address_tiers.json crypto_grafana:/etc/grafana/provisioning/dashboards/
docker restart crypto_grafana
```

---

## 📈 Dashboard 面板說明

### Panel 1: BTC Balance Distribution by Address Tier
**類型**: 時序圖（Time Series）

**說明**: 顯示各分層持有的 BTC 總量隨時間變化

**顏色編碼**:
- 🟢 綠色: 0-1 BTC（散戶）
- 🟡 黃色: 1-10 BTC（中等持幣者）
- 🟠 橘色: 10-100 BTC（大戶）
- 🔴 紅色: 100+ BTC（巨鯨）

**解讀**:
- 上升趨勢 = 該層級持續買入
- 下降趨勢 = 該層級持續賣出
- 巨鯨層級上升 + 散戶層級下降 = 看漲訊號

---

### Panel 2: Latest Address Tier Distribution
**類型**: 表格（Table）

**說明**: 顯示最新的地址分層統計資料

**欄位**:
- Tier: 分層名稱
- Address Count: 地址數量
- Total Balance (BTC): 總持幣量
- 24h Change: 24小時變動（綠色=增加，紅色=減少）
- % of Total: 佔總流通量百分比
- Source: 資料來源

**用途**: 快速查看當前分布狀態

---

### Panel 3: Daily Balance Changes by Tier
**類型**: 柱狀圖（Bar Chart）

**說明**: 顯示每日各分層的餘額變動

**解讀**:
- 正值（綠色）= 流入
- 負值（紅色）= 流出
- 巨鯨持續流入 → 強烈看漲訊號
- 散戶大量流出 → 恐慌性賣出或築底

---

### Panel 4: Address Count Trends by Tier
**類型**: 時序圖（Time Series）

**說明**: 追蹤各分層地址數量變化

**解讀**:
- 地址數增加 = 新參與者進入該層級
- 地址數減少 = 持有者退出或升級到更高層級

---

### Panel 5: Current Address Distribution
**類型**: 橫向柱狀圖（Bar Gauge）

**說明**: 當前各分層的地址數量對比

**用途**: 直觀了解市場參與者結構

---

### Panel 6-9: 統計指標（Stats）

- **Total BTC Tracked**: 追蹤的 BTC 總量
- **Whale Tier 24h Change**: 巨鯨層級 24 小時變動
  - 綠色 = 流入（看漲）
  - 紅色 = 流出（看跌）
- **Retail Tier 24h Change**: 散戶層級 24 小時變動
  - 綠色 = 持續持有（信心強）
  - 紅色 = 恐慌賣出（信心弱）
- **Data Coverage**: 資料覆蓋天數

---

## 🔍 使用場景

### 場景 1: 識別巨鯨累積期
**觀察指標**:
- Whale Tier (100+) 餘額持續上升
- Retail Tier (0-1) 餘額持續下降
- Daily Balance Changes 顯示巨鯨持續正值

**解讀**: 機構/大戶正在累積，可能預示價格上漲

---

### 場景 2: 偵測散戶恐慌拋售
**觀察指標**:
- Retail Tier 24h Change 大幅負值
- Address Count Trends 顯示散戶地址數減少
- Whale Tier 同時流入

**解讀**: 散戶在低點恐慌拋售，巨鯨在接盤（築底訊號）

---

### 場景 3: 監控鯨魚分布
**觀察指標**:
- Balance Distribution 巨鯨層級突然下降
- Daily Changes 巨鯨層級大幅負值

**解讀**: 巨鯨可能在獲利了結，需警惕價格回調

---

## ⚙️ 自訂設定

### 調整時間範圍
- 預設: 最近 7 天
- 點擊右上角時間選擇器可調整
- 建議範圍:
  - 短期分析: 7 天
  - 中期分析: 30 天
  - 長期分析: 90 天

### 調整刷新頻率
- 預設: 1 分鐘自動刷新
- 點擊右上角刷新圖示可調整
- 建議設定: 5-10 分鐘（資料每日更新一次）

### 匯出資料
1. 點擊面板標題 → `Inspect` → `Data`
2. 點擊 `Download CSV` 或 `Download Excel`

---

## 🔔 設定告警（Alert）

### 巨鯨異動告警
```
Panel: Whale Tier 24h Change
Condition: value < -1000 OR value > 1000
Alert: Send notification when whale tier changes more than 1000 BTC in 24h
```

### 散戶恐慌告警
```
Panel: Retail Tier 24h Change
Condition: value < -500
Alert: Retail panic selling detected
```

**設定步驟**:
1. 編輯面板 → `Alert` tab
2. 設定條件與閾值
3. 選擇通知管道（Email / Slack / Telegram）

---

## 📊 Dashboard 連結

- **Dashboard URL**: http://localhost:3000/d/btc-address-tiers
- **直接存取**: Grafana → Dashboards → BTC Address Tier Tracking

---

## 🐛 故障排除

### 問題 1: Dashboard 無資料顯示

**檢查步驟**:
```bash
# 1. 確認資料庫有資料
docker exec crypto_timescaledb psql -U crypto -d crypto_db -c "
    SELECT COUNT(*) FROM address_tier_snapshots WHERE blockchain_id = 1;
"

# 2. 確認 TimescaleDB 資料源已設定
# Grafana → Configuration → Data Sources → TimescaleDB

# 3. 測試 SQL 查詢
# Dashboard → Panel → Edit → Query Inspector
```

### 問題 2: Dashboard 導入失敗

**可能原因**:
- JSON 格式錯誤
- 資料源名稱不匹配

**解決方法**:
1. 確認 TimescaleDB 資料源名稱
2. 編輯 JSON 檔案，搜尋 `"datasource"` 並替換為正確名稱
3. 重新導入

### 問題 3: 圖表顯示異常

**檢查**:
- 時間範圍是否包含資料
- 是否有足夠資料點（至少 2-3 天）
- SQL 查詢是否有錯誤（Query Inspector）

---

## 📝 維護建議

### 每日檢查
- 查看 Whale/Retail 24h Change 指標
- 檢查資料更新是否正常（Data Coverage 面板）

### 每週檢查
- 回顧 Balance Distribution 趨勢
- 分析 Address Count Trends 變化
- 匯出資料進行深度分析

### 每月檢查
- 檢視長期趨勢（90 天）
- 評估告警規則有效性
- 調整閾值與通知設定

---

## 🔗 相關資源

- **資料收集腳本**: `collector-py/collect_address_tiers.py`
- **終端顯示工具**: `scripts/show_address_tiers.py`
- **Demo 腳本**: `scripts/demo_address_tiers.py`
- **資料庫 Schema**: `database/migrations/011_add_address_tier_tracking.sql`

---

## 📧 支援

遇到問題？
1. 檢查日誌: `logs/address_tiers/cron.log`
2. 執行測試: `scripts/test_address_tier_cron.sh`
3. 手動收集: `python3 collector-py/collect_address_tiers.py`

---

**最後更新**: 2026-01-15  
**Dashboard 版本**: v1.0
