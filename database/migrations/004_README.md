# Migration 004: 連續聚合與分層資料保留

## 📋 概述

此 migration 實作了 TimescaleDB 的連續聚合（Continuous Aggregates）與分層資料保留策略，用於優化長期資料儲存與查詢效能。

## 🎯 主要功能

### 1. 多時間粒度連續聚合

自動從原始資料生成並維護不同時間粒度的聚合視圖：

| 粒度 | 來源 | 保留期限 | 更新頻率 | 用途 |
|------|------|----------|----------|------|
| 1m (原始) | Collector | 7 天 | 實時 | 短期精細分析、高頻策略 |
| 5m | 1m | 30 天 | 每小時 | 日內分析、中頻策略 |
| 15m | 5m | 90 天 | 每 2 小時 | 週內趨勢分析 |
| 1h | 15m | 180 天 | 每 4 小時 | 月度趨勢、中期回測 |
| 1d | 1h | 永久 | 每天 | 長期趨勢、基本面分析 |

### 2. 重要事件保護機制

透過 `critical_events` 表標記的市場重要事件期間，原始 1 分鐘資料將永久保留，不受保留策略影響。

預設已標記的事件：
- 2021-05-19: BTC Flash Crash
- 2022-05-09~13: LUNA Collapse
- 2022-11-06~12: FTX Collapse

### 3. 智能查詢函數

**`get_optimal_ohlcv()`**
根據查詢時間範圍自動選擇最佳資料粒度：
- ≤ 12 小時 → 使用 1m 資料
- ≤ 3 天 → 使用 5m 聚合
- ≤ 30 天 → 使用 15m 聚合
- ≤ 180 天 → 使用 1h 聚合
- > 180 天 → 使用 1d 聚合

**`check_data_availability()`**
檢查指定時間範圍內各粒度資料的可用性

**`get_storage_statistics()`**
查詢各表的儲存空間使用情況

## 🚀 執行 Migration

### 前置條件

- PostgreSQL 12+ with TimescaleDB 2.0+
- 已執行 migrations 001-003
- 資料庫中已有 `ohlcv` 表和資料

### 執行步驟

```bash
# 1. 執行 migration
./scripts/apply_migration_004.sh

# 2. 驗證執行結果
./scripts/verify_migration_004.sh

# 3. 查看資料保留狀態
./scripts/check_retention_status.sh
```

### 手動執行（可選）

```bash
psql -h localhost -U postgres -d crypto_market \
  -f database/migrations/004_continuous_aggregates_and_retention.sql
```

## 📊 儲存空間估算

假設單一交易對（如 BTCUSDT）：

| 粒度 | 每年記錄數 | 單筆大小 | 年度空間 | 保留期限 | 穩態空間 |
|------|-----------|---------|---------|---------|----------|
| 1m | 525,600 | ~200B | 100 MB | 7 天 | ~2 MB |
| 5m | 105,120 | ~250B | 25 MB | 30 天 | ~2 MB |
| 15m | 35,040 | ~250B | 8.4 MB | 90 天 | ~2 MB |
| 1h | 8,760 | ~250B | 2.1 MB | 180 天 | ~1 MB |
| 1d | 365 | ~250B | 89 KB | 永久 | 累積 |

**10 個交易對穩態總空間**：約 70 MB（不含日線歷史累積）

相較於原始方案（90 天保留所有 1m 資料 ≈ 1.2 GB），節省約 **94% 儲存空間**。

## 📖 使用範例

### 查詢最近 7 天資料（自動選擇 5m 聚合）

```sql
SELECT *
FROM get_optimal_ohlcv(
    p_market_id := 1,
    p_start_time := NOW() - INTERVAL '7 days',
    p_end_time := NOW()
)
ORDER BY open_time DESC;
```

### 查詢資料保留狀態

```sql
SELECT * FROM v_retention_status;
```

### 新增自定義重要事件

```sql
INSERT INTO critical_events (
    event_name, event_type, start_time, end_time, markets,
    preserve_raw, description, tags
) VALUES (
    '2024 BTC ETF Approval',
    'regulatory',
    '2024-01-10 00:00:00+00',
    '2024-01-12 00:00:00+00',
    ARRAY(SELECT id FROM markets WHERE base_asset = 'BTC'),
    TRUE,
    'BTC 現貨 ETF 獲批准上市',
    ARRAY['btc', 'etf', 'institutional']
);
```

### 直接查詢特定粒度

```sql
-- 查詢最近 30 天的小時線
SELECT
    open_time,
    close,
    volume,
    ROUND((close - LAG(close) OVER (ORDER BY open_time)) / LAG(close) OVER (ORDER BY open_time) * 100, 2) AS change_pct
FROM ohlcv_1h
WHERE market_id = 1
AND open_time >= NOW() - INTERVAL '30 days'
ORDER BY open_time;
```

更多範例請參考 [`004_USAGE_EXAMPLES.sql`](./004_USAGE_EXAMPLES.sql)

## 🔧 維護操作

### 查看連續聚合狀態

```sql
SELECT
    view_name,
    materialization_hypertable_name,
    materialized_only
FROM timescaledb_information.continuous_aggregates;
```

### 手動刷新聚合（故障恢復時使用）

```sql
CALL refresh_continuous_aggregate(
    'ohlcv_5m',
    NOW() - INTERVAL '1 day',
    NOW()
);
```

### 暫時停用保留策略

```sql
-- 停用 ohlcv 表的自動刪除（緊急情況）
SELECT alter_job(
    (SELECT job_id FROM timescaledb_information.jobs
     WHERE hypertable_name = 'ohlcv'
     AND proc_name = 'policy_retention'),
    scheduled => false
);
```

### 恢復保留策略

```sql
SELECT alter_job(
    (SELECT job_id FROM timescaledb_information.jobs
     WHERE hypertable_name = 'ohlcv'
     AND proc_name = 'policy_retention'),
    scheduled => true
);
```

## ⚠️ 注意事項

1. **資料丟失風險**
   - 保留策略啟用後，超過期限的資料將**永久刪除**
   - 確保重要事件已正確標記在 `critical_events` 表中

2. **首次執行**
   - 如果已有大量歷史資料，聚合視圖的初次建立可能需要數分鐘
   - 建議在低峰時段執行

3. **連續聚合限制**
   - 聚合視圖只包含 `timeframe = '1m'` 的資料
   - 如果有其他 timeframe 的原始資料，需要另外處理

4. **查詢兼容性**
   - 現有查詢 `ohlcv` 表的程式碼仍可正常運作
   - 建議逐步遷移到使用 `get_optimal_ohlcv()` 函數

## 🔄 回滾方案

如需回滾此 migration：

```sql
-- 1. 移除保留策略
SELECT remove_retention_policy('ohlcv', if_exists => TRUE);
SELECT remove_retention_policy('ohlcv_5m', if_exists => TRUE);
SELECT remove_retention_policy('ohlcv_15m', if_exists => TRUE);
SELECT remove_retention_policy('ohlcv_1h', if_exists => TRUE);
SELECT remove_retention_policy('trades', if_exists => TRUE);
SELECT remove_retention_policy('orderbook_snapshots', if_exists => TRUE);

-- 2. 刪除連續聚合視圖
DROP MATERIALIZED VIEW IF EXISTS ohlcv_1d CASCADE;
DROP MATERIALIZED VIEW IF EXISTS ohlcv_1h CASCADE;
DROP MATERIALIZED VIEW IF EXISTS ohlcv_15m CASCADE;
DROP MATERIALIZED VIEW IF EXISTS ohlcv_5m CASCADE;

-- 3. 刪除輔助表與函數
DROP TABLE IF EXISTS critical_events CASCADE;
DROP FUNCTION IF EXISTS get_optimal_ohlcv;
DROP FUNCTION IF EXISTS check_data_availability;
DROP FUNCTION IF EXISTS get_storage_statistics;
DROP FUNCTION IF EXISTS is_critical_event_period;
DROP VIEW IF EXISTS v_retention_status;

-- 4. 恢復原始保留策略（可選）
SELECT add_retention_policy('ohlcv', INTERVAL '90 days');
SELECT add_retention_policy('trades', INTERVAL '30 days');
```

## 📚 相關文件

- [TimescaleDB Continuous Aggregates 文檔](https://docs.timescale.com/use-timescale/latest/continuous-aggregates/)
- [TimescaleDB Data Retention 文檔](https://docs.timescale.com/use-timescale/latest/data-retention/)
- 專案架構文件：`CLAUDE.md`
- 資料庫 Schema：`database/schemas/01_init.sql`

## 🐛 故障排除

### 問題：聚合視圖沒有資料

**可能原因**：
- 原始 `ohlcv` 表中沒有 `timeframe = '1m'` 的資料
- 聚合策略尚未執行

**解決方案**：
```sql
-- 檢查原始資料
SELECT COUNT(*), MIN(open_time), MAX(open_time)
FROM ohlcv WHERE timeframe = '1m';

-- 手動觸發聚合
CALL refresh_continuous_aggregate('ohlcv_5m', NULL, NULL);
```

### 問題：查詢效能沒有改善

**可能原因**：
- 查詢時間範圍太小，仍在使用原始資料
- 索引未正確建立

**解決方案**：
```sql
-- 檢查查詢計畫
EXPLAIN ANALYZE
SELECT * FROM get_optimal_ohlcv(1, NOW() - INTERVAL '7 days', NOW());

-- 確認索引存在
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename LIKE 'ohlcv%';
```

### 問題：儲存空間沒有減少

**可能原因**：
- 保留策略尚未執行（需等待排程）
- PostgreSQL 需要手動 VACUUM 回收空間

**解決方案**：
```sql
-- 手動觸發保留策略（謹慎使用）
-- CALL run_job((SELECT job_id FROM timescaledb_information.jobs
--               WHERE proc_name = 'policy_retention'
--               AND hypertable_name = 'ohlcv'));

-- 回收已刪除資料的空間
VACUUM FULL ohlcv;
```

## 📞 支援

如有問題或建議，請：
1. 查看 `004_USAGE_EXAMPLES.sql` 中的範例
2. 執行 `./scripts/verify_migration_004.sh` 檢查系統狀態
3. 檢查 TimescaleDB 日誌：`SELECT * FROM timescaledb_information.job_stats;`
