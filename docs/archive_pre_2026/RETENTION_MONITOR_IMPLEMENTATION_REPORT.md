# 資料保留策略自動化監控系統 - 實作完成報告

## ✅ 已完成項目

### 1. 核心監控模組

#### 📄 `collector-py/src/monitors/retention_monitor.py`
**功能**：資料保留策略監控核心邏輯

**包含類別**：
- `RetentionMonitorMetrics`: Prometheus 指標定義類（37 個指標）
- `RetentionMonitor`: 監控執行類

**監控項目**：
1. ✅ 連續聚合狀態 (`check_continuous_aggregates`)
   - 檢查 ohlcv_5m, ohlcv_15m, ohlcv_1h, ohlcv_1d
   - 記錄數、時間範圍、最後更新時間

2. ✅ TimescaleDB Jobs 狀態 (`check_timescaledb_jobs`)
   - Job 啟用狀態
   - 最後執行時間
   - 執行成功/失敗次數
   - 下次排程時間
   - 執行時長

3. ✅ 資料保留狀態 (`check_retention_status`)
   - 實際保留期間 vs 預期保留期間
   - 偏差計算與警告
   - 記錄數統計

4. ✅ 儲存空間統計 (`check_storage_statistics`)
   - 表空間大小
   - 索引空間大小

5. ✅ 資料完整性檢查 (`check_data_integrity`)
   - 壓縮比檢查（1m vs 5m，預期 ~5:1）

---

### 2. 排程器模組

#### 📄 `collector-py/src/schedulers/retention_monitor_scheduler.py`
**功能**：定期執行監控檢查

**排程策略**：
- ⏱️ 快速檢查：每 N 分鐘執行一次（可配置，預設 30 分鐘）
- ⏱️ 完整檢查：每小時第 5 分鐘執行一次

**特性**：
- 使用 APScheduler 背景排程
- 支援優雅關閉
- 防止重複執行（max_instances=1）

---

### 3. 服務啟動腳本

#### 📄 `scripts/run_retention_monitor.py`
**功能**：Python 服務主程式

**特性**：
- 啟動 Prometheus metrics server（預設端口 8003）
- 初始化並啟動監控排程器
- 信號處理（SIGINT, SIGTERM）
- 日誌配置（console + file）

#### 📄 `scripts/start_retention_monitor.sh`
**功能**：Shell 啟動腳本

**特性**：
- 環境變數檢查與載入
- PYTHONPATH 設定
- 日誌目錄自動創建
- 配置資訊顯示

---

### 4. Prometheus 整合

#### 📄 `monitoring/prometheus/prometheus.yml`
**更新內容**：
- ✅ 新增 `retention-monitor` job（端口 8003）
- ✅ 配置 scrape 間隔與標籤

#### 📄 `monitoring/prometheus/rules/retention_alerts.yml`
**功能**：15 個預定義告警規則

**告警類別**：

**連續聚合告警（3 個）**：
1. `ContinuousAggregateStale` - 超過 2 小時未更新
2. `ContinuousAggregateRecordCountLow` - 記錄數異常少
3. `ContinuousAggregateDataOutdated` - 資料過時

**TimescaleDB Jobs 告警（4 個）**：
4. `TimescaleDBJobDisabled` - Job 被禁用
5. `TimescaleDBJobNotRunning` - 超過 2 小時未執行
6. `TimescaleDBJobLastRunFailed` - 最後執行失敗
7. `TimescaleDBJobSlowExecution` - 執行時間過長

**資料保留告警（3 個）**：
8. `DataRetentionDeviation` - 偏差超過 20%（警告）
9. `DataRetentionSevereDeviation` - 偏差超過 50%（嚴重）
10. `DataLayerRecordCountLow` - 記錄數異常少

**資料完整性告警（1 個）**：
11. `AggregateCompressionRatioAbnormal` - 壓縮比異常

**儲存空間告警（2 個）**：
12. `TableSizeExcessive` - 表空間超過 50GB
13. `IndexSizeExcessive` - 索引空間超過表空間

**監控服務告警（2 個）**：
14. `RetentionMonitorNotChecking` - 超過 10 分鐘未檢查
15. `RetentionMonitorSlowCheck` - 檢查執行時間過長

---

### 5. 測試與文檔

#### 📄 `test_retention_monitor.py`
**功能**：快速測試腳本

**測試項目**：
- 資料庫連接
- 監控檢查執行
- 指標收集驗證

#### 📄 `docs/RETENTION_MONITOR_GUIDE.md`
**功能**：完整使用指南

**內容包含**：
- 系統架構圖
- 所有監控指標說明
- 告警規則詳細說明
- 使用方法（安裝、配置、啟動、測試）
- 故障排除指南
- 維護建議
- Grafana Dashboard 建議

#### 📄 `.env.example`（更新）
**新增配置項**：
```bash
RETENTION_MONITOR_METRICS_PORT=8003
RETENTION_CHECK_INTERVAL_MINUTES=30
RETENTION_DEVIATION_WARNING_PERCENT=20
RETENTION_DEVIATION_CRITICAL_PERCENT=50
AGGREGATE_STALE_HOURS=2
JOB_NOT_RUNNING_HOURS=2
CHECK_COMPRESSION_RATIO=true
EXPECTED_5M_RATIO=5.0
COMPRESSION_RATIO_TOLERANCE=1.5
```

---

## 📊 導出的 Prometheus 指標總覽

### 連續聚合指標（4 個）
- `timescaledb_continuous_aggregate_last_update_timestamp`
- `timescaledb_continuous_aggregate_record_count`
- `timescaledb_continuous_aggregate_oldest_data_timestamp`
- `timescaledb_continuous_aggregate_newest_data_timestamp`

### TimescaleDB Jobs 指標（5 個）
- `timescaledb_job_enabled`
- `timescaledb_job_last_success_timestamp`
- `timescaledb_job_last_run_timestamp`
- `timescaledb_job_next_start_timestamp`
- `timescaledb_job_total_duration_seconds`

### 資料保留指標（4 個）
- `timescaledb_data_actual_retention_days`
- `timescaledb_data_expected_retention_days`
- `timescaledb_data_retention_deviation_days`
- `timescaledb_data_total_records`

### 儲存空間指標（2 個）
- `timescaledb_table_size_bytes`
- `timescaledb_index_size_bytes`

### 資料完整性指標（2 個）
- `timescaledb_aggregate_compression_ratio`
- `timescaledb_data_gap_detected_total`

### 監控服務指標（3 個）
- `timescaledb_retention_monitor_last_check_timestamp`
- `timescaledb_retention_monitor_check_duration_seconds`
- `timescaledb_retention_monitor` (Info)

**總計：20 個指標**

---

## 🚀 快速開始

### 1. 安裝依賴
```bash
cd collector-py
pip install prometheus-client psycopg2-binary apscheduler loguru python-dotenv
```

### 2. 配置環境變數
```bash
# 複製 .env.example 為 .env
cp .env.example .env

# 編輯 .env，確保資料庫配置正確
# 特別注意以下配置：
# - POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB
# - RETENTION_MONITOR_METRICS_PORT=8003
# - RETENTION_CHECK_INTERVAL_MINUTES=30
```

### 3. 啟動服務
```bash
# 使用 Shell 腳本啟動
./scripts/start_retention_monitor.sh

# 或直接使用 Python
python3 scripts/run_retention_monitor.py
```

### 4. 驗證運行
```bash
# 測試監控功能
python3 test_retention_monitor.py

# 檢查 metrics 端點
curl http://localhost:8003/metrics

# 檢查特定指標
curl http://localhost:8003/metrics | grep timescaledb_data_retention
```

### 5. 整合到 Docker Compose（可選）
在 `docker-compose.yml` 中添加：
```yaml
  retention-monitor:
    build:
      context: ./collector-py
      dockerfile: Dockerfile
    container_name: crypto_retention_monitor
    command: python3 /app/scripts/run_retention_monitor.py
    environment:
      - RETENTION_MONITOR_METRICS_PORT=8003
      - RETENTION_CHECK_INTERVAL_MINUTES=30
    ports:
      - "8003:8003"
    depends_on:
      - timescaledb
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

---

## 📈 預期效果

### 自動監控
- ✅ 每 30 分鐘自動檢查一次資料保留狀態
- ✅ 每小時執行一次完整檢查
- ✅ 所有指標自動導出到 Prometheus

### 主動告警
- ⚠️ 當資料保留期間偏差超過 20% 時發出警告
- 🚨 當資料保留期間偏差超過 50% 時發出嚴重警告
- ⚠️ 當 TimescaleDB Job 執行失敗時立即告警
- ⚠️ 當連續聚合超過 2 小時未更新時告警

### 可觀測性
- 📊 所有指標可在 Prometheus 查詢
- 📈 可基於指標創建 Grafana Dashboard
- 📝 完整的日誌記錄（logs/retention_monitor.log）

---

## 🔄 下一步建議

### 短期（已完成）
- ✅ 核心監控邏輯實作
- ✅ Prometheus 指標導出
- ✅ 告警規則定義
- ✅ 啟動腳本與測試

### 中期（建議實作）
- 📊 建立 Grafana Dashboard
- 📧 配置 Alertmanager 通知渠道（Email、Slack）
- 🔍 添加更多資料完整性檢查（資料缺失偵測）
- 📈 添加趨勢預測（預測何時需要擴充容量）

### 長期（未來規劃）
- 🤖 自動化修復機制（當發現異常時自動觸發修復）
- 📊 歷史數據分析（保留策略效果分析）
- 🔄 動態調整保留策略（基於使用模式）

---

## ⚠️ 注意事項

1. **資料庫連接**：確保監控服務有足夠權限查詢 `timescaledb_information` schema
2. **端口衝突**：預設使用 8003 端口，確保未被佔用
3. **檢查頻率**：根據資料量調整檢查間隔，避免對資料庫造成過大負載
4. **日誌輪替**：定期清理 `logs/retention_monitor.log`
5. **告警疲勞**：初期可能會有較多告警，根據實際情況調整閾值

---

## 📞 相關文檔

- 📖 [使用指南](docs/RETENTION_MONITOR_GUIDE.md) - 完整的使用說明
- 📖 [Migration 004](database/migrations/004_continuous_aggregates_and_retention.sql) - 資料庫設定
- 📖 [手動檢查腳本](scripts/check_retention_status.sh) - 手動驗證工具
- 📖 [Prometheus 配置](monitoring/prometheus/prometheus.yml) - 監控配置
- 📖 [告警規則](monitoring/prometheus/rules/retention_alerts.yml) - 告警定義

---

**實作日期**: 2025-12-30  
**狀態**: ✅ 核心功能完成，可投入測試使用  
**下一步**: 啟動服務並驗證告警規則
