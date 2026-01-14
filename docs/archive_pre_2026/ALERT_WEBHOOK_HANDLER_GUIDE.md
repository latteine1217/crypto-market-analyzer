# Alert Webhook Handler - 使用指南

## 📋 功能概述

Alert Webhook Handler 是一個增強型告警通知系統，它接收來自 Prometheus Alertmanager 的 webhook，自動生成相關的 K 線圖表，並通過郵件發送帶圖表附件的告警通知。

### 核心功能
1. **接收 Alertmanager webhook** - 處理所有告警事件
2. **智能圖表生成** - 根據告警類型自動生成對應的 K 線圖
3. **郵件通知增強** - 發送帶圖表附件的 HTML 郵件
4. **歷史記錄** - 保存告警日誌和圖表檔案

### 支援的告警類型
- **價格告警**：PriceSpike, PriceDrop, ExtremePriceVolatility, PriceStagnant
- **異常檢測**：MADAnomalyDetected, MADSevereAnomaly
- **系統告警**：RetentionMonitorNotChecking 等（僅文字郵件）

---

## 🚀 快速開始

### 1. 安裝依賴

```bash
cd collector-py
pip install -r requirements.txt
```

新增的依賴：
- `mplfinance` - K 線圖生成
- `matplotlib` - 圖表繪製
- `flask` - Webhook HTTP 服務器

### 2. 配置環境變數

在 `.env` 檔案中添加（如果尚未配置）：

```bash
# 資料庫配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crypto_db
DB_USER=crypto
DB_PASSWORD=crypto123

# SMTP 郵件配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
ALERT_EMAIL_TO=recipient@example.com

# Alert Webhook 配置（可選）
ALERT_WEBHOOK_PORT=9100
ALERT_CHART_DIR=/tmp/alert_charts
ALERT_LOG_DIR=/tmp/alert_logs
```

### 3. 啟動服務

```bash
# 方法 1: 使用啟動腳本
./scripts/start_alert_webhook.sh

# 方法 2: 直接運行
python3 collector-py/src/monitors/alert_webhook_handler.py
```

服務啟動後會監聽 `http://localhost:9100`

### 4. 測試功能

```bash
# 測試圖表生成
python3 scripts/test_alert_webhook.py

# 測試郵件發送（需配置 SMTP）
TEST_EMAIL_SEND=true python3 scripts/test_alert_webhook.py
```

### 5. 更新 Alertmanager 配置

Alertmanager 配置已更新（`monitoring/alertmanager/alertmanager.yml.template`），會自動路由告警至 webhook：

```yaml
route:
  receiver: 'webhook-with-charts'
  routes:
    # 價格相關告警 → webhook（生成 K 線圖）
    - match_re:
        alertname: '(PriceSpike|PriceDrop|ExtremePriceVolatility|...'
      receiver: 'webhook-with-charts'
```

重啟 Alertmanager 以應用新配置：

```bash
docker-compose restart alertmanager
```

---

## 📊 圖表類型

### 1. Candlestick Chart (蠟燭圖)
- **時間範圍**：過去 24 小時
- **時間框架**：1 小時
- **特徵**：
  - 蠟燭圖顯示 OHLC 價格
  - 移動平均線（MA7, MA25）
  - 成交量柱狀圖
  - 告警標註（黃色標籤）

### 2. Price Comparison Chart (價格對比圖)
- **時間範圍**：過去 48 小時
- **時間框架**：5 分鐘
- **特徵**：
  - 價格折線圖
  - 突出顯示最近 1 小時（紅色）
  - 當前價格標記
  - 移動平均線
  - 成交量柱狀圖（彩色：綠漲紅跌）

---

## 📧 郵件格式

### 郵件主旨
```
[🚨 CRITICAL] Crypto Analyzer - ExtremePriceVolatility
[⚠️ WARNING] Crypto Analyzer - PriceSpike
```

### 郵件內容
- **告警摘要**：Firing/Resolved 數量、時間
- **告警詳情**：每個告警的描述、標籤、狀態、時間
- **圖表說明**：附件列表和查看提示
- **視覺化告警**：色彩編碼、emoji 圖示

### 附件
- 1-2 張 PNG 圖表（根據告警類型）
- 檔案大小：約 100-200 KB / 張
- 解析度：1400x800 px（適合螢幕和列印）

---

## 🗂️ 檔案結構

```
collector-py/src/monitors/
├── alert_chart_generator.py       # 圖表生成器
└── alert_webhook_handler.py       # Webhook 處理器

scripts/
├── start_alert_webhook.sh         # 啟動腳本
└── test_alert_webhook.py          # 測試腳本

/tmp/alert_charts/                 # 圖表輸出目錄
├── BTCUSDT_1h_20251230_123456.png
└── BTCUSDT_price_comparison_20251230_123456.png

/tmp/alert_logs/                   # 告警日誌目錄
└── alerts_20251230.jsonl
```

---

## 🔧 進階配置

### 自訂圖表參數

編輯 `alert_webhook_handler.py` 中的 `generate_alert_charts()` 函數：

```python
# 修改時間範圍
hours_back=48  # 查詢 48 小時的資料

# 修改時間框架
timeframe='4h'  # 使用 4 小時 K 線

# 修改突出顯示時間
highlight_recent_hours=2  # 突出最近 2 小時
```

### 添加更多告警類型

在 `should_generate_chart()` 函數中添加：

```python
price_related = [
    'PriceSpike', 'PriceDrop', 'ExtremePriceVolatility',
    'YourCustomAlert'  # 添加自訂告警
]
```

### 自訂郵件模板

修改 `format_alert_email_html()` 函數以自訂 HTML 樣式和內容。

---

## 🐛 故障排除

### 問題 1: 圖表生成失敗
**症狀**：日誌顯示 "No data to plot"

**解決方案**：
1. 檢查資料庫是否有資料：
   ```sql
   SELECT COUNT(*) FROM ohlcv WHERE symbol='BTCUSDT' AND exchange='bybit';
   ```
2. 確認 symbol 名稱正確（如 `BTCUSDT` 而非 `BTC/USDT`）
3. 確認 exchange 名稱正確（如 `bybit` 而非 `Bybit`）

### 問題 2: 郵件發送失敗
**症狀**：日誌顯示 "SMTP authentication failed"

**解決方案**：
1. 確認使用 **應用專用密碼**（不是 Gmail 登入密碼）
2. 檢查 Gmail「較不安全的應用程式存取權」設定
3. 測試 SMTP 連接：
   ```bash
   python3 scripts/test_email.py
   ```

### 問題 3: Webhook 未收到告警
**症狀**：Alertmanager 顯示告警，但 webhook 無日誌

**解決方案**：
1. 確認 webhook 服務運行：
   ```bash
   curl http://localhost:9100/health
   ```
2. 檢查 Alertmanager 配置：
   ```bash
   docker-compose logs alertmanager | grep webhook
   ```
3. 確認 `host.docker.internal` 可訪問（macOS/Windows Docker Desktop）

### 問題 4: 圖表檔案累積過多
**症狀**：`/tmp/alert_charts/` 目錄佔用大量空間

**解決方案**：
- 自動清理功能已內建（保留 24 小時）
- 手動清理：
  ```bash
  find /tmp/alert_charts -name "*.png" -mtime +1 -delete
  ```

---

## 📈 性能指標

### 資源使用
- **記憶體**：約 100-150 MB（含 matplotlib）
- **CPU**：生成圖表時峰值 20-30%
- **磁碟**：每張圖表 100-200 KB

### 處理速度
- **圖表生成**：2-5 秒 / 張
- **郵件發送**：3-10 秒（含附件）
- **總處理時間**：5-15 秒 / 告警

### 並發能力
- 單執行緒處理（Flask 預設）
- 適合中低頻告警（< 10 次 / 分鐘）
- 高頻場景建議使用 gunicorn 多進程模式

---

## 🔄 與現有系統整合

### 1. Prometheus → Alertmanager → Webhook → Email

```
[Prometheus]
    ↓ (評估告警規則)
[Alertmanager]
    ↓ (路由告警)
[Alert Webhook Handler] ← 接收 webhook
    ↓ (生成圖表)
    ↓ (格式化郵件)
[Email Server] → [User]
```

### 2. 告警流程

1. **Prometheus** 檢測到告警條件（如價格波動）
2. **Alertmanager** 接收告警並路由至 webhook
3. **Webhook Handler** 處理：
   - 解析告警資訊
   - 從資料庫查詢 OHLCV 資料
   - 生成 K 線圖（1-2 張）
   - 格式化 HTML 郵件
   - 發送郵件（帶附件）
4. **使用者** 收到郵件，查看圖表，採取行動

---

## 🎯 最佳實踐

### 1. 告警設計
- 為價格相關告警添加 `symbol` label
- 設定合理的 `for` 持續時間（避免誤報）
- 使用分級告警（warning / critical）

### 2. 圖表優化
- 選擇合適的時間範圍（不要太長或太短）
- 使用較粗的時間框架（1h-4h）以提高清晰度
- 限制移動平均線數量（2-3 條）

### 3. 郵件管理
- 設定 `repeat_interval`（避免郵件轟炸）
- 使用 `group_by` 合併相似告警
- 設定郵件過濾規則（重要告警標星號）

### 4. 維護
- 定期檢查圖表目錄（清理舊檔案）
- 監控 webhook 服務健康度
- 定期測試郵件發送功能

---

## 📝 範例告警郵件

### 範例：價格急劇下跌告警

**主旨**：`[⚠️ WARNING] Crypto Analyzer - PriceDrop`

**內容**：
```
🔔 Crypto Analyzer Alert
Alert: PriceDrop | Severity: WARNING

📊 Alert Summary
Firing: 1 | Resolved: 0 | Time: 2025-12-30 08:00:00 UTC

Alert #1 - FIRING
Summary: BTCUSDT 價格急劇下跌
Description: BTCUSDT 在 5 分鐘內下跌 3.25%（當前價格：93,500）

Labels: alertname: PriceDrop | symbol: BTCUSDT | severity: warning

Started: 2025-12-30T08:00:15Z

📈 Attached Charts: 2 chart(s) attached to this email
- BTCUSDT_1h_20251230_080045.png
- BTCUSDT_price_comparison_20251230_080045.png

Please check the attachments to view the K-line charts.
```

**附件**：
1. 24 小時蠟燭圖（顯示價格走勢）
2. 48 小時價格對比圖（突出最近 1 小時）

---

## 🆕 更新日誌

### v1.0.0 (2025-12-30)
- ✅ 初始版本發布
- ✅ 支援價格告警圖表生成
- ✅ 支援 MAD 異常檢測告警
- ✅ HTML 郵件模板
- ✅ 自動清理舊圖表
- ✅ 健康檢查端點

---

## 📚 相關文檔

- [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md) - 郵件配置指南
- [GRAFANA_DASHBOARDS_GUIDE.md](GRAFANA_DASHBOARDS_GUIDE.md) - Grafana 告警設定
- [SESSION_LOG.md](SESSION_LOG.md) - 專案進度日誌

---

**最後更新**：2025-12-30  
**維護者**：開發團隊  
**狀態**：✅ 穩定運行
