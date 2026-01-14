# 資料保留策略自動化監控系統

## 📋 概述

本系統提供 TimescaleDB 資料保留策略和連續聚合的自動化監控，包含：
- 連續聚合視圖狀態監控
- TimescaleDB Jobs 執行狀態監控
- 資料保留策略執行監控
- 資料完整性檢查
- Prometheus 指標導出與告警

## 🏗️ 架構

```
┌─────────────────────────────────────────────────────────┐
│           Retention Monitor Service                      │
│  ┌──────────────────────────────────────────────────┐  │
│  │  RetentionMonitor (監控核心)                       │  │
│  │  - check_continuous_aggregates()                  │  │
│  │  - check_timescaledb_jobs()                       │  │
│  │  - check_retention_status()                       │  │
│  │  - check_storage_statistics()                     │  │
│  │  - check_data_integrity()                         │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↓                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  RetentionMonitorMetrics (Prometheus指標)         │  │
│  │  - aggregate_last_update_timestamp                │  │
│  │  - job_last_success_timestamp                     │  │
│  │  - data_retention_deviation_days                  │  │
│  │  - table_size_bytes                               │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↓                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  MetricsServer (HTTP :8003)                       │  │
│  │  GET /metrics                                     │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         ↓
           ┌─────────────────────────┐
           │     Prometheus          │
           │  - 收集指標              │
           │  - 評估告警規則          │
           └─────────────────────────┘
                         ↓
           ┌─────────────────────────┐
           │    Alertmanager         │
           │  - 發送告警通知          │
           └─────────────────────────┘
```

## 📊 監控指標

### 連續聚合指標

- `timescaledb_continuous_aggregate_last_update_timestamp` - 聚合視圖最後更新時間
- `timescaledb_continuous_aggregate_record_count` - 聚合視圖記錄數
- `timescaledb_continuous_aggregate_oldest_data_timestamp` - 最舊資料時間戳
- `timescaledb_continuous_aggregate_newest_data_timestamp` - 最新資料時間戳

### TimescaleDB Jobs 指標

- `timescaledb_job_enabled` - Job 啟用狀態 (1=啟用, 0=禁用)
- `timescaledb_job_last_success_timestamp` - 最後成功執行時間
- `timescaledb_job_last_run_timestamp` - 最後執行時間
- `timescaledb_job_next_start_timestamp` - 下次排程執行時間
- `timescaledb_job_total_duration_seconds` - Job 執行時長

### 資料保留指標

- `timescaledb_data_actual_retention_days` - 實際保留天數
- `timescaledb_data_expected_retention_days` - 預期保留天數
- `timescaledb_data_retention_deviation_days` - 保留偏差（實際 - 預期）
- `timescaledb_data_total_records` - 資料記錄總數

### 儲存空間指標

- `timescaledb_table_size_bytes` - 表空間大小
- `timescaledb_index_size_bytes` - 索引空間大小

### 資料完整性指標

- `timescaledb_aggregate_compression_ratio` - 聚合壓縮比
- `timescaledb_data_gap_detected_total` - 資料缺失檢測次數

## 🚨 告警規則

系統包含 15 個預定義告警規則（見 `monitoring/prometheus/rules/retention_alerts.yml`）：

### 連續聚合告警
1. **ContinuousAggregateStale** - 聚合視圖超過 2 小時未更新
2. **ContinuousAggregateRecordCountLow** - 聚合視圖記錄數異常少
3. **ContinuousAggregateDataOutdated** - 聚合視圖資料過時

### TimescaleDB Jobs 告警
4. **TimescaleDBJobDisabled** - Job 被禁用
5. **TimescaleDBJobNotRunning** - Job 超過 2 小時未執行
6. **TimescaleDBJobLastRunFailed** - Job 最後執行失敗
7. **TimescaleDBJobSlowExecution** - Job 執行時間過長

### 資料保留告警
8. **DataRetentionDeviation** - 實際保留期間偏差超過 20%
9. **DataRetentionSevereDeviation** - 實際保留期間偏差超過 50% 🚨
10. **DataLayerRecordCountLow** - 資料層記錄數異常少

### 資料完整性告警
11. **AggregateCompressionRatioAbnormal** - 聚合壓縮比異常

### 儲存空間告警
12. **TableSizeExcessive** - 表空間超過 50GB
13. **IndexSizeExcessive** - 索引空間超過表空間

### 監控服務告警
14. **RetentionMonitorNotChecking** - 監控服務超過 10 分鐘未檢查
15. **RetentionMonitorSlowCheck** - 監控檢查執行時間過長

## 🚀 使用方法

### 1. 安裝依賴

```bash
cd collector-py
pip install prometheus-client psycopg2-binary apscheduler loguru python-dotenv
```

### 2. 配置環境變數

在 `.env` 檔案中添加：

```bash
# 資料保留監控配置
RETENTION_MONITOR_METRICS_PORT=8003
RETENTION_CHECK_INTERVAL_MINUTES=30
LOG_LEVEL=INFO
```

### 3. 啟動監控服務

```bash
# 方法 1: 使用啟動腳本
./scripts/start_retention_monitor.sh

# 方法 2: 直接執行Python腳本
python3 scripts/run_retention_monitor.py
```

### 4. 測試功能

```bash
# 快速測試
python3 test_retention_monitor.py

# 檢查 metrics 端點
curl http://localhost:8003/metrics

# 檢查特定指標
curl http://localhost:8003/metrics | grep timescaledb_
```

### 5. 查看監控指標

訪問 Prometheus UI：
- URL: http://localhost:9090
- 查詢範例：`timescaledb_data_retention_deviation_days`

### 6. 查看告警

訪問 Alertmanager UI：
- URL: http://localhost:9093
- 查看當前觸發的告警

## 📁 檔案結構

```
collector-py/src/
├── monitors/
│   ├── __init__.py
│   └── retention_monitor.py          # 監控核心邏輯
├── schedulers/
│   └── retention_monitor_scheduler.py # 排程器

scripts/
├── run_retention_monitor.py          # 服務啟動腳本
└── start_retention_monitor.sh        # Shell 啟動腳本

monitoring/prometheus/
└── rules/
    └── retention_alerts.yml          # Prometheus 告警規則

test_retention_monitor.py             # 快速測試腳本
```

## ⚙️ 配置選項

### 檢查間隔

預設每 30 分鐘執行一次快速檢查，每小時執行一次完整檢查。

修改檢查間隔：
```bash
export RETENTION_CHECK_INTERVAL_MINUTES=15  # 改為每 15 分鐘檢查一次
```

### 預期保留期間

在 `retention_monitor.py` 中的 `EXPECTED_RETENTION` 字典定義：

```python
EXPECTED_RETENTION = {
    'ohlcv (1m)': 7,      # 7 天
    'ohlcv_5m': 30,       # 30 天
    'ohlcv_15m': 90,      # 90 天
    'ohlcv_1h': 180,      # 180 天
    'ohlcv_1d': None,     # 永久保留
    'trades': 7,
    'orderbook_snapshots': 3
}
```

### 告警閾值

在 `.env` 中配置：

```bash
RETENTION_DEVIATION_WARNING_PERCENT=20   # 警告閾值
RETENTION_DEVIATION_CRITICAL_PERCENT=50  # 嚴重閾值
AGGREGATE_STALE_HOURS=2
JOB_NOT_RUNNING_HOURS=2
```

## 🔍 監控檢查項目

### 1. 連續聚合檢查 (`check_continuous_aggregates`)
- 檢查 `ohlcv_5m`, `ohlcv_15m`, `ohlcv_1h`, `ohlcv_1d` 的記錄數
- 檢查資料時間範圍（最舊/最新）
- 檢查最後更新時間

### 2. TimescaleDB Jobs 檢查 (`check_timescaledb_jobs`)
- 查詢 `timescaledb_information.jobs`
- 檢查 Job 啟用狀態
- 檢查最後執行時間
- 檢查執行失敗次數
- 檢查下次排程時間

### 3. 資料保留狀態檢查 (`check_retention_status`)
- 使用 `v_retention_status` 視圖
- 計算實際保留期間
- 比對預期保留期間
- 計算偏差並告警

### 4. 儲存空間統計 (`check_storage_statistics`)
- 查詢各表的空間使用情況
- 監控表空間與索引空間比例

### 5. 資料完整性檢查 (`check_data_integrity`)
- 檢查 1m vs 5m 壓縮比（預期 ~5:1）
- 檢測異常壓縮比

## 📈 Grafana Dashboard 整合

可以基於這些 metrics 創建 Grafana Dashboard：

### 推薦面板

1. **資料保留狀態概覽**
   - 顯示各層級實際保留期間 vs 預期
   - 使用 Gauge 圖表顯示偏差百分比

2. **TimescaleDB Jobs 狀態**
   - 顯示所有 Jobs 的執行狀態
   - 最後成功執行時間
   - 下次排程時間

3. **連續聚合更新狀態**
   - 各聚合視圖的最後更新時間
   - 記錄數趨勢圖

4. **儲存空間使用趨勢**
   - 各表空間使用量時間序列圖
   - 預測未來空間需求

## 🐛 故障排除

### 問題：監控服務無法連接資料庫

**解決方案**：
1. 檢查 `.env` 中的資料庫配置
2. 確認資料庫服務正在運行
3. 檢查防火牆規則

### 問題：指標端點無回應

**解決方案**：
1. 檢查服務是否正常啟動：`ps aux | grep retention_monitor`
2. 檢查端口是否被佔用：`netstat -an | grep 8003`
3. 查看日誌：`tail -f logs/retention_monitor.log`

### 問題：告警未觸發

**解決方案**：
1. 確認 Prometheus 已載入告警規則：訪問 http://localhost:9090/rules
2. 檢查指標是否正常收集：http://localhost:9090/targets
3. 檢查 Alertmanager 配置

## 📝 維護建議

### 定期檢查項目

1. **每日**：查看 Grafana Dashboard，確認無異常告警
2. **每週**：檢視 `v_retention_status` 視圖，確認保留策略正常運行
3. **每月**：分析儲存空間趨勢，規劃容量擴充

### 日誌管理

監控服務日誌位於 `logs/retention_monitor.log`，建議：
- 保留 30 天
- 每日輪替
- 定期檢視錯誤日誌

### 效能優化

如果監控檢查執行時間過長：
1. 增加檢查間隔
2. 優化資料庫查詢（添加索引）
3. 分離檢查任務（部分檢查降低頻率）

## 📞 相關資源

- **資料庫 Migration**: `database/migrations/004_continuous_aggregates_and_retention.sql`
- **手動檢查腳本**: `scripts/check_retention_status.sh`
- **Prometheus 配置**: `monitoring/prometheus/prometheus.yml`
- **告警規則**: `monitoring/prometheus/rules/retention_alerts.yml`

---

**建立日期**: 2025-12-30
**維護者**: Crypto Market Analyzer Team
