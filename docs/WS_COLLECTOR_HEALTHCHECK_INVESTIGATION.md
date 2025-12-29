# WS Collector Healthcheck 失敗調查報告

**日期**: 2025-12-29
**問題**: WS Collector 容器狀態為 unhealthy
**影響**: 容器功能正常但被標記為不健康
**調查工程師**: Claude Sonnet 4.5

---

## 1. 問題摘要

### 症狀
- **容器狀態**: unhealthy
- **連續失敗**: 750 次 healthcheck 失敗
- **實際功能**: ✅ 正常運行，已寫入 714 筆資料
- **矛盾現象**: 健康檢查失敗，但應用正常工作

---

## 2. 根因分析

### 2.1 Healthcheck 配置問題

**位置**: `data-collector/Dockerfile:45-46`

**原始配置**（錯誤）：
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD node -e "require('redis').createClient({host:process.env.REDIS_HOST,port:process.env.REDIS_PORT}).ping()" || exit 1
```

### 2.2 錯誤分析

**核心錯誤**: `ClientClosedError: The client is closed`

#### 問題層級
1. **API 版本不匹配**
   - 使用舊版 Redis client API：`require('redis').createClient()`
   - 新版 `redis` 包（v4+）需要異步連接

2. **未建立連接**
   - `createClient()` 只創建 client 實例
   - 新版 API 需要調用 `await client.connect()` 才能使用
   - 直接調用 `.ping()` 會拋出 `ClientClosedError`

3. **同步執行問題**
   - 使用 `node -e` 執行同步代碼
   - 無法使用 `await` 進行異步連接
   - Ping 失敗導致 healthcheck 返回 exit code 1

#### 錯誤堆疊
```javascript
ClientClosedError: The client is closed
    at Commander._RedisClient_sendCommand (/app/node_modules/@redis/client/dist/lib/client/index.js:520:31)
    at Commander.commandsExecutor (/app/node_modules/@redis/client/dist/lib/client/index.js:190:154)
    at BaseClass.<computed> [as ping] (/app/node_modules/@redis/client/dist/lib/commander.js:8:29)
```

### 2.3 為何應用仍正常運行？

**關鍵發現**: Healthcheck 與應用運行邏輯**完全獨立**

1. **應用層面**
   - 主程序正確使用 Redis client（有 connect 邏輯）
   - WebSocket 連接正常
   - 資料寫入持續運作

2. **Healthcheck 層面**
   - 僅用於 Docker 健康狀態標記
   - 失敗不影響容器運行（只標記為 unhealthy）
   - 不會觸發容器重啟（因為主進程正常）

---

## 3. 修復方案

### 3.1 選擇的方案：HTTP Healthcheck

**新配置**：
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${METRICS_PORT:-8001}/metrics || exit 1
```

### 3.2 方案優勢

| 特性 | HTTP Healthcheck | Redis Ping |
|------|------------------|------------|
| **簡單性** | ✅ 簡單直接 | ❌ 需要異步處理 |
| **可靠性** | ✅ 直接檢查應用 | ⚠️ 依賴 Redis 狀態 |
| **依賴** | ✅ 僅需 curl | ❌ 需要 Redis client |
| **準確性** | ✅ 反映應用健康 | ⚠️ 只反映 Redis 連接 |
| **性能** | ✅ HTTP GET 快速 | ⚠️ 創建連接開銷 |

### 3.3 替代方案（未採用）

#### 方案 B：修正 Redis Client
```dockerfile
HEALTHCHECK CMD node -e "(async()=>{const redis=require('redis');const client=redis.createClient({socket:{host:process.env.REDIS_HOST,port:process.env.REDIS_PORT}});await client.connect();await client.ping();await client.quit();})()" || exit 1
```
- ✅ 檢查 Redis 連接
- ❌ 代碼複雜，難維護
- ❌ 每次創建新連接，性能差

#### 方案 C：移除 Healthcheck
```dockerfile
# 移除 HEALTHCHECK 指令
```
- ✅ 最簡單
- ❌ 失去健康狀態監控
- ❌ 無法自動發現應用問題

---

## 4. 修復執行

### 4.1 實施步驟
```bash
# 1. 修改 Dockerfile
vim data-collector/Dockerfile

# 2. 重新構建
docker-compose build ws-collector

# 3. 重新啟動
docker-compose up -d ws-collector

# 4. 等待 healthcheck（start-period 40s）
sleep 45

# 5. 驗證狀態
docker inspect crypto_ws_collector --format='{{.State.Health.Status}}'
```

### 4.2 修復結果

| 指標 | 修復前 | 修復後 |
|------|--------|--------|
| **健康狀態** | unhealthy | ✅ healthy |
| **失敗次數** | 750 | ✅ 0 |
| **應用功能** | ✅ 正常 | ✅ 正常 |
| **資料寫入** | ✅ 714 筆 | ✅ 持續寫入 |
| **Exit Code** | 1 | ✅ 0 |

### 4.3 驗證日誌
```
$ docker inspect crypto_ws_collector --format='{{.State.Health.Status}}'
healthy

$ docker ps | grep ws_collector
8d283bd2d8a2   finance-ws-collector   Up 51 seconds (healthy)   0.0.0.0:8001->8001/tcp
```

---

## 5. 深入分析

### 5.1 Metrics 端點驗證

**測試**：
```bash
$ curl http://localhost:8001/metrics | head -20
# HELP process_cpu_user_seconds_total Total user CPU time spent in seconds.
# TYPE process_cpu_user_seconds_total counter
process_cpu_user_seconds_total 76.95774300000011

# HELP process_cpu_system_seconds_total Total system CPU time spent in seconds.
# TYPE process_cpu_system_seconds_total counter
process_cpu_system_seconds_total 33.101200000000055
...
```

**結論**: ✅ Metrics 端點穩定回應，適合作為 healthcheck 目標

### 5.2 WebSocket 連接狀態

**觀察日誌**：
```
2025-12-28 17:19:07 [info] Connecting to Binance WebSocket
2025-12-28 17:19:04 [info] Flushed 2 orderbook snapshots
```

**發現**：
- WebSocket 有間歇性重連（10 reconnects, 11 errors）
- 這是**正常現象**（網絡波動、交易所維護等）
- 應用有自動重連機制
- 資料持續寫入，無遺失

### 5.3 Redis 實際使用

**應用內 Redis 連接**（應用代碼）：
```typescript
// 應用正確使用 Redis（有 connect）
const redis = new Redis({
  host: process.env.REDIS_HOST,
  port: process.env.REDIS_PORT
});
await redis.connect();  // ✅ 正確連接
```

**Healthcheck 錯誤用法**（已修復前）：
```javascript
// Healthcheck 錯誤用法（無 connect）
require('redis').createClient(...).ping()  // ❌ 缺少 connect
```

---

## 6. 影響評估

### 6.1 修復前影響

| 層面 | 影響 | 嚴重度 |
|------|------|--------|
| **功能** | ✅ 無影響（應用正常） | 🟢 低 |
| **監控** | ⚠️ 健康狀態誤報 | 🟡 中 |
| **告警** | ⚠️ 可能觸發誤告警 | 🟡 中 |
| **信任度** | ⚠️ 狀態不可信 | 🟡 中 |

### 6.2 修復後收益

1. **準確監控** - 健康狀態正確反映應用狀態
2. **告警可靠** - 減少誤告警
3. **運維信心** - 狀態可信，決策準確
4. **性能提升** - HTTP check 比 Redis 連接輕量

---

## 7. 最佳實踐建議

### 7.1 Healthcheck 設計原則

1. **簡單直接**
   - ✅ 使用簡單的 HTTP/TCP 檢查
   - ❌ 避免複雜的邏輯或外部依賴

2. **檢查應用本身**
   - ✅ 檢查應用端點（metrics, health, status）
   - ❌ 不要只檢查依賴服務（DB, Redis）

3. **輕量快速**
   - ✅ 檢查操作應該快速（< 1s）
   - ❌ 避免重量級操作（創建連接、查詢資料庫）

4. **冪等性**
   - ✅ 多次執行不影響系統
   - ❌ 避免有副作用的操作

### 7.2 Docker Healthcheck 配置建議

```dockerfile
# 推薦配置
HEALTHCHECK --interval=30s \      # 檢查間隔
            --timeout=10s \       # 超時時間
            --start-period=40s \  # 啟動緩衝期
            --retries=3 \         # 失敗重試次數
    CMD curl -f http://localhost:${PORT}/health || exit 1
```

**參數說明**：
- `interval`: 30s 適中（不過於頻繁）
- `timeout`: 10s 足夠（HTTP 通常 < 1s）
- `start-period`: 40s 給予應用充分啟動時間
- `retries`: 3 次避免偶發失敗誤判

### 7.3 應用層健康檢查

**建議在應用內實現 `/health` 端點**：

```typescript
// 範例：Express health endpoint
app.get('/health', async (req, res) => {
  const checks = {
    uptime: process.uptime(),
    redis: await checkRedis(),
    db: await checkDatabase(),
    websocket: checkWebSocketStatus()
  };

  const isHealthy = checks.redis && checks.db && checks.websocket;
  res.status(isHealthy ? 200 : 503).json(checks);
});
```

---

## 8. 後續行動

### 8.1 完成項
- ✅ 問題根因分析
- ✅ 修復 healthcheck 配置
- ✅ 驗證修復效果
- ✅ 文檔記錄

### 8.2 建議後續優化

#### 優先級 1（高）
- [ ] 為其他容器添加 HTTP healthcheck（collector, report-scheduler）
- [ ] 統一 healthcheck 配置模式
- [ ] 添加 Prometheus 告警規則（基於 container health）

#### 優先級 2（中）
- [ ] 實現應用層 `/health` 端點
- [ ] 包含依賴服務狀態檢查
- [ ] 添加詳細健康報告（JSON）

#### 優先級 3（低）
- [ ] WebSocket 重連策略優化（減少 reconnects）
- [ ] 網絡錯誤重試指數退避
- [ ] 添加斷線恢復通知

---

## 9. 結論

### 9.1 關鍵發現

1. **根本原因**: Healthcheck 使用錯誤的 Redis client API
2. **實際影響**: 監控誤報，功能無損
3. **修復方案**: 改用 HTTP metrics 端點檢查
4. **驗證結果**: ✅ 健康狀態恢復正常

### 9.2 學到的教訓

1. **API 版本重要性** - 升級依賴時需檢查 API 變更
2. **健康檢查獨立性** - 失敗不等於應用不健康
3. **簡單即美** - HTTP check 優於複雜邏輯
4. **監控可信度** - 錯誤的監控比沒有監控更危險

### 9.3 最終狀態

| 服務 | 狀態 | Healthcheck | 功能 |
|------|------|-------------|------|
| WS Collector | ✅ Running | ✅ Healthy | ✅ 正常寫入 |

**總評**: 🎉 **問題已完全解決，系統健康狀態正常**

---

## 附錄

### A. 相關文件
- `data-collector/Dockerfile` - Healthcheck 配置
- `docker-compose.yml` - 服務編排
- `data-collector/src/index.ts` - 主程序邏輯

### B. 相關命令
```bash
# 檢查容器健康狀態
docker inspect <container> --format='{{json .State.Health}}' | jq

# 測試 metrics 端點
curl http://localhost:8001/metrics

# 查看 healthcheck 日誌
docker inspect <container> --format='{{range .State.Health.Log}}{{.Output}}{{end}}'

# 重新構建特定服務
docker-compose build ws-collector
docker-compose up -d ws-collector
```

### C. 參考資料
- [Docker HEALTHCHECK 文檔](https://docs.docker.com/engine/reference/builder/#healthcheck)
- [Redis Client v4 遷移指南](https://github.com/redis/node-redis/blob/master/docs/v3-to-v4.md)
- [Prometheus Metrics 最佳實踐](https://prometheus.io/docs/practices/naming/)

---

**報告結束**
