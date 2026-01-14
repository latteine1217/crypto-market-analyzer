# Migration Guide: v1.x → v2.0.0

**Purpose**: 幫助使用者從 v1.x (ML Platform) 升級至 v2.0.0 (Data Collection + Dashboard)  
**Date**: 2026-01-15  
**Difficulty**: Medium

---

## 🎯 重大變更摘要

### 架構變更
- ❌ **移除**: ML/策略/回測功能 (data-analyzer/)
- ❌ **移除**: Whale Tracker 功能
- ❌ **移除**: 報表排程系統
- ❌ **移除**: Jupyter Lab 服務
- ✅ **保留**: 資料收集 (REST + WebSocket)
- ✅ **保留**: TimescaleDB + Redis
- ✅ **保留**: Dashboard (主要入口)
- ✅ **保留**: Prometheus + Grafana 監控
- ✨ **新增**: Symbol 格式統一機制

### 資料庫變更
- ✅ Symbol 格式統一為原生格式 (BTCUSDT 取代 BTC/USDT)
- ✅ 合併重複 markets (15 → 11)
- ✅ 修正 base/quote 解析錯誤
- ✅ 所有舊資料保留，無需手動遷移

---

## 🔄 升級步驟

### Step 1: 備份現有資料

```bash
# 1. 停止所有服務
docker-compose down

# 2. 備份資料庫
docker run --rm \
  -v finance_db_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/db_backup_$(date +%Y%m%d).tar.gz /data

# 3. 備份 Redis (可選)
docker run --rm \
  -v finance_redis_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/redis_backup_$(date +%Y%m%d).tar.gz /data

# 4. 備份配置文件
cp -r configs configs_backup_$(date +%Y%m%d)
cp .env .env.backup_$(date +%Y%m%d)
```

### Step 2: 更新程式碼

```bash
# 1. 拉取最新程式碼
git fetch origin
git checkout v2.0.0  # 或 main branch

# 2. 檢查變更
git diff v1.x..v2.0.0 --stat
```

### Step 3: 更新 Docker Compose 配置

v2.0.0 移除了以下服務，請更新您的 `docker-compose.override.yml` (如果有):

```yaml
# 移除這些服務 (如果您有自訂配置)
services:
  jupyter:        # ❌ 已移除
  mad-detector:   # ❌ 已移除  
  report-scheduler: # ❌ 已移除
  whale-tracker:  # ❌ 已移除
```

### Step 4: 執行資料庫遷移

```bash
# 1. 啟動資料庫
docker-compose up -d db

# 2. 等待資料庫就緒
sleep 10

# 3. 執行遷移腳本 (自動執行，包含 symbol 統一)
docker exec crypto_timescaledb psql -U crypto -d crypto_db \
  -f /migrations/012_unify_symbol_format_and_merge_duplicates.sql
```

**預期輸出**:
```
BEGIN
NOTICE:  Merging Binance BTCUSDT (id=1158) into BTC/USDT (id=1)
NOTICE:    Migrated 0 OHLCV records
...
NOTICE:  Migration completed successfully!
NOTICE:  Total markets: 11
COMMIT
```

### Step 5: 驗證遷移結果

```bash
# 檢查 markets 表
docker exec crypto_timescaledb psql -U crypto -d crypto_db -c \
  "SELECT id, symbol, base_asset, quote_asset FROM markets ORDER BY id;"
```

**預期結果**: 所有 symbols 應為原生格式 (BTCUSDT, ETHUSDT), base/quote 正確解析

### Step 6: 啟動 v2.0.0 服務

```bash
# 啟動所有服務
docker-compose up -d

# 檢查服務狀態
docker-compose ps

# 應該看到 7 個服務 (移除了 4 個舊服務)
# crypto_timescaledb, crypto_redis, crypto_collector,
# crypto_ws_collector, crypto_dashboard, crypto_prometheus, crypto_grafana
```

### Step 7: 驗證功能

```bash
# 1. 檢查 Dashboard
curl http://localhost:8050
# 應該返回 HTML (200 OK)

# 2. 檢查 Grafana
curl http://localhost:3000
# 應該返回 HTML (200 OK)

# 3. 檢查資料收集
docker-compose logs collector --tail=50
docker-compose logs ws-collector --tail=50
# 應該看到正常的資料收集日誌，無錯誤

# 4. 檢查資料庫資料
docker exec crypto_timescaledb psql -U crypto -d crypto_db -c \
  "SELECT COUNT(*) FROM ohlcv WHERE open_time > NOW() - INTERVAL '1 hour';"
# 應該有新資料
```

---

## 🗑️ 已移除功能說明

### 1. ML/策略/回測 (data-analyzer/)

**為何移除**: 
- 未完成功能占用 8,000 LOC
- 增加維護負擔
- 與 v2.0 專注點不符 (Dashboard)

**如果您需要此功能**:
1. 從備份恢復: `data-analyzer-backup-20260115.tar.gz`
2. 解壓至專案根目錄
3. 自行維護 (不包含在 v2.0 支援範圍)

### 2. Whale Tracker

**為何移除**: 功能未完成，鏈上資料收集需重新設計

**替代方案**: 使用 Dune Analytics 或 Nansen 等專業服務

### 3. 報表排程系統

**為何移除**: Dashboard 已提供即時視覺化，排程報表需求降低

**替代方案**: 
- 使用 Grafana 快照功能
- 手動從 Dashboard 截圖

### 4. Jupyter Lab

**為何移除**: v2.0 不再需要 ad-hoc 分析環境

**替代方案**: 
- 本地安裝 Jupyter
- 使用 `psycopg2` 直接連線 TimescaleDB

---

## 🔄 API 變更

### Symbol 格式

**v1.x**: 混用 `BTC/USDT` 和 `BTCUSDT`  
**v2.0**: 統一使用 `BTCUSDT` (原生格式)

如果您的腳本依賴 symbol 格式，請更新:

```python
# v1.x
symbol = "BTC/USDT"

# v2.0 (推薦)
from utils.symbol_utils import normalize_symbol
symbol = normalize_symbol("BTC/USDT")  # 返回 "BTCUSDT"

# 或直接使用原生格式
symbol = "BTCUSDT"
```

### 資料庫查詢

**v1.x**: 可能有重複 markets  
**v2.0**: 每個 exchange + symbol 唯一

```sql
-- v1.x (可能返回多筆)
SELECT * FROM markets WHERE symbol IN ('BTC/USDT', 'BTCUSDT');

-- v2.0 (唯一結果)
SELECT * FROM markets WHERE symbol = 'BTCUSDT';
```

---

## 🐛 已知問題與解決方案

### 問題 1: 升級後 Dashboard 空白

**原因**: Redis 快取舊資料  
**解決**:
```bash
docker exec -it crypto_redis redis-cli FLUSHALL
docker-compose restart dashboard
```

### 問題 2: Collector 無法連線資料庫

**原因**: Migration 未完成  
**解決**:
```bash
# 檢查 migration 狀態
docker exec crypto_timescaledb psql -U crypto -d crypto_db -c \
  "\dt" | grep markets_backup_20260115

# 如果不存在，手動執行 migration (見 Step 4)
```

### 問題 3: 歷史圖表顯示不正常

**原因**: Symbol 格式變更，前端可能查詢舊格式  
**解決**: 
- 清空瀏覽器快取
- 重啟 Dashboard 服務

---

## 📊 升級檢查清單

在正式切換到 v2.0 之前，請確認:

- [ ] 已備份資料庫與配置 (Step 1)
- [ ] 已更新程式碼至 v2.0.0 (Step 2)
- [ ] 已移除自訂的 v1.x 服務配置 (Step 3)
- [ ] 已執行資料庫遷移 (Step 4)
- [ ] Migration 成功 (看到 "Migration completed successfully") (Step 5)
- [ ] 所有 symbols 已統一格式 (Step 5)
- [ ] 7 個服務全部運行 (Step 6)
- [ ] Dashboard 可訪問 (Step 7)
- [ ] Grafana 可訪問 (Step 7)
- [ ] 有新資料寫入資料庫 (Step 7)

---

## 🆘 回滾方案

如果升級後出現問題，可以回滾至 v1.x:

```bash
# 1. 停止 v2.0 服務
docker-compose down

# 2. 恢復資料庫備份
docker run --rm \
  -v finance_db_data:/data \
  -v $(pwd):/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/db_backup_YYYYMMDD.tar.gz -C /"

# 3. 恢復配置
cp -r configs_backup_YYYYMMDD/* configs/
cp .env.backup_YYYYMMDD .env

# 4. 切換至 v1.x 程式碼
git checkout v1.x  # 或您的舊版本 tag

# 5. 啟動 v1.x 服務
docker-compose up -d
```

---

## 📞 支援

如果在升級過程中遇到問題:

1. **檢查日誌**: `docker-compose logs [service]`
2. **查看已知問題**: 本文「已知問題與解決方案」章節
3. **提交 Issue**: GitHub Issues (包含錯誤日誌與環境資訊)

---

## 📚 延伸閱讀

- **v2.0.0 新功能**: `README.md`
- **Symbol 統一詳情**: `docs/TASK2_SYMBOL_FORMAT_UNIFICATION_REPORT.md`
- **開發進度**: `docs/SESSION_LOG.md`
- **專案狀態**: `docs/PROJECT_STATUS_REPORT.md`

---

**文件版本**: 1.0  
**最後更新**: 2026-01-15  
**維護者**: Development Team
