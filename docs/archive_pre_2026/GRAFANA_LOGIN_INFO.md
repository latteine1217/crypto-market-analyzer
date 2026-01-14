# Grafana 登入資訊

## 🔐 預設登入憑證

**URL**: http://localhost:3000

**帳號**: `admin`  
**密碼**: `admin`

---

## 📝 首次登入流程

1. **打開瀏覽器** 訪問: http://localhost:3000
2. **輸入帳密**:
   - Username: `admin`
   - Password: `admin`
3. **（可選）修改密碼**:
   - 首次登入時 Grafana 會提示你修改密碼
   - 你可以選擇「Skip」跳過，繼續使用 admin/admin
   - 或設定新密碼以提高安全性

---

## 🔄 修改密碼（建議）

### 方法 1: 通過 Grafana UI

1. 登入 Grafana
2. 點擊左下角頭像 → `Preferences`
3. 切換到 `Change Password` 頁籤
4. 輸入：
   - Old password: `admin`
   - New password: `你的新密碼`
   - Confirm password: `你的新密碼`
5. 點擊 `Change Password`

### 方法 2: 通過環境變數（永久修改）

編輯 `docker-compose.yml`:

```yaml
grafana:
  environment:
    GF_SECURITY_ADMIN_USER: admin
    GF_SECURITY_ADMIN_PASSWORD: 你的新密碼  # 修改這裡
```

然後重啟容器:
```bash
docker-compose restart grafana
```

### 方法 3: 通過 Grafana CLI（重置密碼）

如果忘記密碼，可以重置:

```bash
# 重置 admin 密碼為 admin
docker exec crypto_grafana grafana-cli admin reset-admin-password admin

# 或設定為其他密碼
docker exec crypto_grafana grafana-cli admin reset-admin-password 你的新密碼
```

---

## 👥 建立新用戶（多人使用）

### 通過 UI 建立

1. 登入 Grafana（使用 admin 帳號）
2. 左側選單 → `Configuration` (⚙️) → `Users`
3. 點擊 `New user`
4. 填寫資訊:
   - Name: 使用者名稱
   - Email: 電子郵件
   - Username: 登入帳號
   - Password: 登入密碼
5. 選擇角色:
   - **Admin**: 完全控制權限（可管理用戶、資料源、Dashboard）
   - **Editor**: 可編輯 Dashboard 與 Alerts
   - **Viewer**: 僅可查看 Dashboard（適合只看報表的使用者）
6. 點擊 `Create user`

### 推薦的使用者架構

```
admin (Admin)           → 你自己（管理員）
analyst (Editor)        → 分析師（可編輯 Dashboard）
viewer (Viewer)         → 其他人（只能查看）
```

---

## 🔒 安全性建議

### ⚠️ 開發環境（目前設定）
```
✅ 使用預設 admin/admin
✅ 僅 localhost 可存取
✅ 快速開發測試
```

### 🔐 生產環境（建議調整）

1. **修改管理員密碼**
   ```bash
   # 在 docker-compose.yml 中設定強密碼
   GF_SECURITY_ADMIN_PASSWORD: "複雜的密碼123!@#"
   ```

2. **啟用 HTTPS**（如果需要外網存取）
   ```yaml
   grafana:
     environment:
       GF_SERVER_PROTOCOL: https
       GF_SERVER_CERT_FILE: /etc/grafana/ssl/cert.pem
       GF_SERVER_CERT_KEY: /etc/grafana/ssl/key.pem
   ```

3. **限制存取 IP**（使用防火牆或 Nginx 反向代理）
   ```nginx
   # 只允許內網存取
   allow 192.168.0.0/16;
   deny all;
   ```

4. **啟用匿名存取控制**
   ```yaml
   GF_AUTH_ANONYMOUS_ENABLED: "false"  # 預設已禁用
   ```

5. **設定 Session 過期時間**
   ```yaml
   GF_AUTH_LOGIN_COOKIE_NAME: grafana_session
   GF_AUTH_LOGIN_MAXIMUM_LIFETIME_DURATION: 24h
   ```

---

## 🔑 完整環境變數列表

當前 Grafana 容器使用的環境變數:

```bash
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin
GF_INSTALL_PLUGINS=
GF_PATHS_CONFIG=/etc/grafana/grafana.ini
GF_PATHS_DATA=/var/lib/grafana
GF_PATHS_HOME=/usr/share/grafana
GF_PATHS_LOGS=/var/log/grafana
GF_PATHS_PLUGINS=/var/lib/grafana/plugins
GF_PATHS_PROVISIONING=/etc/grafana/provisioning
```

---

## 🆘 常見問題

### Q1: 登入後顯示「Invalid username or password」

**解決方法**:
1. 確認帳密是否正確（注意大小寫）
2. 檢查容器環境變數:
   ```bash
   docker exec crypto_grafana env | grep GF_SECURITY
   ```
3. 重置密碼:
   ```bash
   docker exec crypto_grafana grafana-cli admin reset-admin-password admin
   ```

### Q2: 忘記密碼怎麼辦？

**解決方法**:
```bash
# 重置為 admin
docker exec crypto_grafana grafana-cli admin reset-admin-password admin

# 或重啟容器（會重新載入 docker-compose.yml 設定）
docker-compose restart grafana
```

### Q3: 想要多人使用不同帳號

**解決方法**:
參考上方「建立新用戶」章節，為每個使用者建立獨立帳號與權限。

### Q4: 如何查看目前有哪些用戶？

**解決方法**:
1. Grafana UI: `Configuration` → `Users`
2. 或直接查詢資料庫:
   ```bash
   docker exec crypto_grafana sqlite3 /var/lib/grafana/grafana.db "SELECT id, login, email, is_admin FROM user;"
   ```

### Q5: 不小心把 admin 帳號刪了怎麼辦？

**解決方法**:
```bash
# 重新建立 admin 帳號
docker exec crypto_grafana grafana-cli admin reset-admin-password admin

# 或完全重置 Grafana（會清空所有資料）
docker-compose down
docker volume rm crypto_grafana_data
docker-compose up -d grafana
```

---

## 📊 快速存取連結

### BTC 地址分層追蹤 Dashboard
- **URL**: http://localhost:3000/d/btc-address-tiers
- **需要登入**: 是（admin/admin）

### Grafana 主頁
- **URL**: http://localhost:3000
- **登入**: admin / admin

### 其他 Dashboards
- **Long Run Test**: http://localhost:3000/d/long_run_test
- **MAD Anomaly Detection**: http://localhost:3000/d/mad_anomaly_detection
- **Redis Queue Monitor**: http://localhost:3000/d/redis_queue_monitor

---

## 🔧 進階設定

### 自訂 Grafana 配置檔

如果需要更多客製化設定，可以掛載自訂的 `grafana.ini`:

1. 建立配置檔:
   ```bash
   touch monitoring/grafana/grafana.ini
   ```

2. 修改 `docker-compose.yml`:
   ```yaml
   grafana:
     volumes:
       - ./monitoring/grafana/grafana.ini:/etc/grafana/grafana.ini
   ```

3. 參考官方文檔編輯配置:
   https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/

---

## 📝 總結

**預設登入資訊**:
```
URL: http://localhost:3000
帳號: admin
密碼: admin
```

**建議設定**:
- ✅ 開發環境: 保持 admin/admin（快速測試）
- 🔐 生產環境: 修改為強密碼
- 👥 多人使用: 建立不同角色的帳號

**修改密碼後記得更新**:
- `docker-compose.yml` 中的 `GF_SECURITY_ADMIN_PASSWORD`
- 或通過 Grafana UI 直接修改

---

**最後更新**: 2026-01-15  
**Grafana 版本**: latest
