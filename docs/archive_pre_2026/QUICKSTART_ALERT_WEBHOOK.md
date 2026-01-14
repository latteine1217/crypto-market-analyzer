# 🎯 快速啟動：Alert Webhook Handler (K線圖告警)

## 📦 已實作的功能

✅ **Alert Chart Generator** (`alert_chart_generator.py`)
   - 從資料庫查詢 OHLCV 資料
   - 生成蠟燭圖（Candlestick）
   - 生成價格對比圖（Price Comparison）
   - 自動清理舊圖表

✅ **Alert Webhook Handler** (`alert_webhook_handler.py`)
   - 接收 Alertmanager webhook
   - 智能判斷是否需要生成圖表
   - 生成 HTML 郵件（帶附件）
   - 發送郵件給指定收件人
   - 記錄告警日誌

✅ **Alertmanager 配置更新**
   - 價格告警自動路由至 webhook
   - MAD 異常檢測告警路由至 webhook
   - 其他告警繼續使用原有郵件系統

✅ **測試腳本**
   - 圖表生成測試
   - 郵件發送測試
   - Webhook 端點測試

✅ **完整文檔**
   - 使用指南（ALERT_WEBHOOK_HANDLER_GUIDE.md）
   - 故障排除指南
   - 最佳實踐建議

---

## 🚀 快速啟動步驟

### 1. 安裝依賴
```bash
cd /Users/latteine/Documents/coding/finance/collector-py
pip install mplfinance matplotlib flask
```

### 2. 配置環境變數
確認 `.env` 已設定：
```bash
# 資料庫（必須）
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crypto_db
DB_USER=crypto
DB_PASSWORD=crypto123

# SMTP（必須，用於發送郵件）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_TO=your-email@gmail.com

# Webhook（可選）
ALERT_WEBHOOK_PORT=9100
ALERT_CHART_DIR=/tmp/alert_charts
ALERT_LOG_DIR=/tmp/alert_logs
```

### 3. 測試圖表生成
```bash
cd /Users/latteine/Documents/coding/finance
python3 scripts/test_alert_webhook.py
```

預期輸出：
```
✓ Candlestick chart generated: /tmp/alert_charts_test/BTCUSDT_1h_*.png
✓ Price comparison chart generated: /tmp/alert_charts_test/BTCUSDT_price_comparison_*.png
✓ All chart generation tests passed
```

### 4. 啟動 Webhook Handler
```bash
./scripts/start_alert_webhook.sh
```

或者：
```bash
python3 collector-py/src/monitors/alert_webhook_handler.py
```

預期輸出：
```
Alert Webhook Handler starting...
Chart output: /tmp/alert_charts
Alert logs: /tmp/alert_logs
Email configured: True
 * Running on http://0.0.0.0:9100
```

### 5. 測試 Webhook 端點
```bash
curl http://localhost:9100/health
```

預期響應：
```json
{
  "status": "healthy",
  "email_configured": true,
  "chart_dir": "/tmp/alert_charts",
  "log_dir": "/tmp/alert_logs"
}
```

### 6. 重啟 Alertmanager
```bash
docker-compose restart alertmanager
```

---

## 📧 測試郵件發送（可選）

```bash
TEST_EMAIL_SEND=true python3 scripts/test_alert_webhook.py
```

這會：
1. 生成測試圖表
2. 發送郵件至 `SMTP_USER` 信箱
3. 附上 2 張 K 線圖

---

## 🧪 手動觸發告警測試

### 方法 1: 使用 Alertmanager API
```bash
curl -X POST http://localhost:9093/api/v1/alerts \
-H "Content-Type: application/json" \
-d '[{
  "labels": {
    "alertname": "PriceSpike",
    "symbol": "BTCUSDT",
    "severity": "warning"
  },
  "annotations": {
    "summary": "TEST: BTC價格急劇上漲",
    "description": "TEST: BTCUSDT 在 5 分鐘內上漲 3.5%"
  }
}]'
```

### 方法 2: 直接發送 webhook
```bash
curl -X POST http://localhost:9100/webhook/alerts \
-H "Content-Type: application/json" \
-d '{
  "groupLabels": {"alertname": "PriceSpike"},
  "alerts": [{
    "status": "firing",
    "labels": {
      "alertname": "PriceSpike",
      "symbol": "BTCUSDT",
      "severity": "warning"
    },
    "annotations": {
      "summary": "TEST: BTC價格急劇上漲",
      "description": "TEST: BTCUSDT 在 5 分鐘內上漲 3.5%"
    },
    "startsAt": "2025-12-30T08:00:00Z"
  }]
}'
```

---

## 📊 查看結果

### 1. 檢查圖表檔案
```bash
ls -lh /tmp/alert_charts/
```

### 2. 檢查告警日誌
```bash
tail -f /tmp/alert_logs/alerts_$(date +%Y%m%d).jsonl
```

### 3. 檢查郵件
登入您的郵箱，應該會收到：
- 主旨：`[⚠️ WARNING] Crypto Analyzer - PriceSpike`
- 內容：HTML 格式，包含告警詳情
- 附件：2 張 PNG 圖表

---

## 🔍 故障排除

### 問題 1: "No data to plot"
**原因**: 資料庫無資料或交易對名稱錯誤

**解決**:
```sql
-- 檢查資料
SELECT COUNT(*), symbol, exchange FROM ohlcv 
GROUP BY symbol, exchange;

-- 確認有 BTCUSDT/bybit 的資料
```

### 問題 2: ImportError: No module named 'mplfinance'
**解決**:
```bash
pip install mplfinance
```

### 問題 3: 郵件發送失敗
**解決**:
```bash
# 測試 SMTP 連接
python3 scripts/test_email.py
```

### 問題 4: Webhook handler 無法啟動
**檢查**:
```bash
# 端口是否被佔用
lsof -i :9100

# 查看詳細錯誤
python3 collector-py/src/monitors/alert_webhook_handler.py
```

---

## 📁 檔案清單

已創建/修改的檔案：

```
collector-py/src/monitors/
├── alert_chart_generator.py          # ✅ 新建 - 圖表生成器
└── alert_webhook_handler.py          # ✅ 新建 - Webhook 處理器

scripts/
├── start_alert_webhook.sh            # ✅ 新建 - 啟動腳本
└── test_alert_webhook.py             # ✅ 新建 - 測試腳本

monitoring/alertmanager/
└── alertmanager.yml.template         # ✅ 修改 - 添加 webhook 路由

collector-py/
└── requirements.txt                  # ✅ 修改 - 添加依賴

docs/
├── ALERT_WEBHOOK_HANDLER_GUIDE.md    # ✅ 新建 - 完整指南
└── QUICKSTART_ALERT_WEBHOOK.md       # ✅ 新建 - 本檔案
```

---

## 🎯 下一步

1. **安裝依賴並測試** - 確保圖表能正確生成
2. **配置 SMTP** - 確保郵件能正常發送
3. **啟動 webhook handler** - 讓它在背景運行
4. **重啟 Alertmanager** - 應用新配置
5. **等待真實告警** - 或手動觸發測試告警
6. **查看郵件** - 確認收到帶圖表的郵件

---

## ✅ 驗收標準

- [ ] 圖表生成測試通過
- [ ] 測試郵件收到（帶 2 張圖表附件）
- [ ] Webhook handler 健康檢查通過
- [ ] Alertmanager 配置已更新並重啟
- [ ] 收到真實告警郵件（帶 K 線圖）

---

## 📞 需要幫助？

查看完整文檔：`docs/ALERT_WEBHOOK_HANDLER_GUIDE.md`

或查看日誌：
```bash
# Webhook handler 日誌
tail -f /tmp/alert_logs/alerts_*.jsonl

# Alertmanager 日誌
docker-compose logs -f alertmanager
```

---

**建立時間**: 2025-12-30  
**狀態**: ✅ 就緒
