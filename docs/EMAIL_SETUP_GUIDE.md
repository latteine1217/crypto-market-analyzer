# 📧 郵件功能啟用指南

## 快速開始（推薦）

使用自動化設定腳本，一鍵完成所有配置：

```bash
bash scripts/setup_email.sh
```

腳本會引導您：
1. ✅ 自動建立/更新 .env 檔案
2. ✅ 互動式輸入 Gmail 和應用程式密碼
3. ✅ 自動重啟容器
4. ✅ 自動測試郵件發送

---

## 手動設定（進階）

### 步驟 1: 取得 Gmail 應用程式專用密碼

#### 1.1 啟用兩步驟驗證

1. 前往 [Google 帳戶安全設定](https://myaccount.google.com/security)
2. 找到「登入 Google」區塊
3. 點擊「**兩步驟驗證**」
4. 如果未啟用，點擊「開始使用」並完成設定

#### 1.2 建立應用程式專用密碼

1. 在「兩步驟驗證」頁面，向下捲動
2. 找到「**應用程式密碼**」（App passwords）
3. 點擊進入
   > 💡 如果看不到此選項，代表兩步驟驗證未完全啟用
4. 在下拉選單中：
   - 選擇應用程式：**郵件**
   - 選擇裝置：**其他（自訂名稱）**
5. 輸入名稱：`Crypto Market Analyzer`
6. 點擊「**產生**」
7. 🔑 **複製顯示的 16 碼密碼**
   - 格式：`xxxx xxxx xxxx xxxx`
   - 使用時移除空格：`xxxxxxxxxxxxxxxx`
   - ⚠️ 此密碼只會顯示一次，請立即保存！

---

### 步驟 2: 配置環境變數

#### 2.1 建立 .env 檔案

```bash
# 如果 .env 不存在，從範本建立
cp .env.example .env
```

#### 2.2 編輯 .env 檔案

```bash
# 使用您喜歡的編輯器
nano .env
# 或
vim .env
```

#### 2.3 填寫 SMTP 設定

找到 SMTP 區塊並填入以下資訊：

```bash
# ============================================
# SMTP 郵件設定
# ============================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com          # ← 您的 Gmail 地址
SMTP_PASSWORD=xxxxxxxxxxxxxxxx          # ← 應用程式專用密碼（16碼）
SMTP_FROM=your-email@gmail.com           # ← 寄件人（通常同 SMTP_USER）
SMTP_TO=recipient@example.com            # ← 預設收件人
```

#### 配置說明：

| 參數 | 說明 | 範例 |
|------|------|------|
| `SMTP_HOST` | SMTP 伺服器地址 | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP 埠號 | `587` (TLS) 或 `465` (SSL) |
| `SMTP_USER` | Gmail 完整地址 | `user@gmail.com` |
| `SMTP_PASSWORD` | 應用程式專用密碼 | `abcdabcdabcdabcd` |
| `SMTP_FROM` | 寄件人地址 | 通常同 `SMTP_USER` |
| `SMTP_TO` | 預設收件人 | 可用逗號分隔多個：`a@gmail.com,b@gmail.com` |

---

### 步驟 3: 重啟報表排程容器

```bash
# 方法 1: 僅重啟 report-scheduler
docker-compose restart report-scheduler

# 方法 2: 完整重啟（確保環境變數載入）
docker-compose down
docker-compose up -d
```

---

### 步驟 4: 驗證配置

#### 4.1 檢查環境變數是否載入

```bash
docker exec crypto_report_scheduler env | grep SMTP
```

預期輸出：
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxxxxxxxxxxxxxx
SMTP_FROM=your-email@gmail.com
SMTP_TO=recipient@example.com
```

#### 4.2 測試郵件發送

```bash
python3 scripts/test_email.py
```

測試腳本會：
1. ✅ 驗證 SMTP 配置完整性
2. ✅ 測試 SMTP 連接
3. ✅ 發送測試郵件（含 HTML 格式）
4. ✅ 顯示測試結果

成功輸出範例：
```
[測試 1: SMTP 連接測試]
✓ SMTP_USER: user@gmail.com
✓ SMTP_FROM: user@gmail.com
✓ SMTP_TO: recipient@example.com
✓ SMTP_PASSWORD: **************** (已設定)

發送測試郵件...
✅ 測試郵件發送成功！
   請檢查收件匣：recipient@example.com
```

---

## 自動報表排程

郵件功能啟用後，系統會自動發送報表：

| 報表類型 | 排程時間 | 說明 |
|---------|---------|------|
| **每日報表** | 每天 08:00 (台北時間) | 前一日市場摘要、策略績效 |
| **每週報表** | 每週一 09:00 (台北時間) | 週報、模型比較、深度分析 |

### 查看排程器狀態

```bash
# 查看排程器日誌
docker logs crypto_report_scheduler -f

# 查看最近 50 行日誌
docker logs crypto_report_scheduler --tail 50
```

---

## 手動觸發報表

不等排程時間，立即生成並發送報表：

### 每日報表

```bash
python3 scripts/generate_daily_report.py
```

### 每週報表

```bash
python3 scripts/generate_weekly_report.py
```

---

## 常見問題 (FAQ)

### ❓ 測試郵件發送失敗

**可能原因 1：應用程式密碼錯誤**
```
解決方案：
1. 重新檢查應用程式密碼（16碼，不含空格）
2. 如果遺失，刪除舊密碼並重新產生
3. 更新 .env 檔案並重啟容器
```

**可能原因 2：兩步驟驗證未啟用**
```
解決方案：
1. 前往 Google 帳戶安全設定
2. 確認兩步驟驗證已啟用
3. 完成手機驗證
```

**可能原因 3：網路防火牆阻擋**
```
解決方案：
1. 確認可連接 smtp.gmail.com:587
2. 測試指令：telnet smtp.gmail.com 587
3. 檢查公司/學校防火牆設定
```

---

### ❓ 收不到郵件

**檢查清單：**
- [ ] 檢查垃圾郵件資料夾
- [ ] 確認收件人地址正確
- [ ] 檢查 Gmail 「已寄出」資料夾
- [ ] 查看容器日誌：`docker logs crypto_report_scheduler`

---

### ❓ 排程時間如何修改？

編輯 `scripts/report_scheduler.py`：

```python
# 修改每日報表時間（預設 08:00）
schedule.every().day.at("08:00").do(self.generate_daily_report)

# 修改為 09:30
schedule.every().day.at("09:30").do(self.generate_daily_report)

# 修改每週報表時間（預設週一 09:00）
schedule.every().monday.at("09:00").do(self.generate_weekly_report)
```

修改後重啟容器：
```bash
docker-compose restart report-scheduler
```

---

### ❓ 如何發送給多個收件人？

在 .env 中使用逗號分隔：

```bash
SMTP_TO=user1@gmail.com,user2@gmail.com,user3@gmail.com
```

或在手動觸發時指定：

```python
from reports.email_sender import EmailSender

sender = EmailSender(...)
sender.send_report(
    to_addresses=['user1@gmail.com', 'user2@gmail.com'],
    subject='報表標題',
    html_content='...'
)
```

---

### ❓ 郵件內容如何自訂？

報表內容由 `data-analyzer/src/reports/html_generator.py` 生成，您可以：

1. 修改 HTML 模板
2. 調整圖表樣式
3. 新增/移除報表區塊

範例：自訂標題顏色
```python
# html_generator.py
COLORS = {
    'primary': '#1a1a2e',    # 修改為您喜歡的顏色
    'success': '#28a745',
    'warning': '#ffc107',
}
```

---

## 安全性建議

🔒 **保護您的憑證：**

1. **不要提交 .env 到 Git**
   ```bash
   # 確認 .gitignore 包含
   echo ".env" >> .gitignore
   ```

2. **定期更換應用程式密碼**
   - 建議每 3-6 個月更換一次
   - 如果懷疑洩露，立即刪除並重新產生

3. **限制容器權限**
   - report-scheduler 容器僅需 SMTP 訪問權限
   - 不需要 root 權限

4. **監控郵件發送日誌**
   ```bash
   # 檢查異常發送
   docker logs crypto_report_scheduler | grep "send_report"
   ```

---

## 進階配置

### 使用其他 SMTP 服務

#### Outlook / Hotmail
```bash
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
```

#### Yahoo Mail
```bash
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USER=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

#### 企業 SMTP
```bash
SMTP_HOST=smtp.your-company.com
SMTP_PORT=587
SMTP_USER=your-username
SMTP_PASSWORD=your-password
```

---

## 疑難排解

### 除錯模式

啟用詳細日誌：

```bash
# 編輯 docker-compose.yml
services:
  report-scheduler:
    environment:
      - LOG_LEVEL=DEBUG  # 新增此行
```

重啟並查看日誌：
```bash
docker-compose restart report-scheduler
docker logs crypto_report_scheduler -f
```

### 測試 SMTP 連接

```bash
# 使用 telnet 測試
telnet smtp.gmail.com 587

# 預期輸出
220 smtp.gmail.com ESMTP ...
```

---

## 相關文件

- [報表系統使用指南](../data-analyzer/REPORT_USAGE.md)
- [排程器配置說明](../scripts/report_scheduler.py)
- [郵件發送 API 文檔](../data-analyzer/src/reports/email_sender.py)

---

## 支援

遇到問題？

1. 📖 查看本文檔的常見問題區塊
2. 📝 檢查容器日誌
3. 🧪 執行測試腳本診斷
4. 💬 提交 Issue 或聯繫管理員

---

**最後更新**：2025-12-29
**版本**：1.0.0
