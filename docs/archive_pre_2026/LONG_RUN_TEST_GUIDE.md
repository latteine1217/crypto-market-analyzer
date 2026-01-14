# 長期運行測試指南

## 概述

本測試方案用於驗證 Crypto Market Analyzer 系統的長期穩定性與性能表現。測試將持續 72 小時（可配置），全程監控系統資源使用、容器狀態、資料品質與告警事件。

## 測試目標

### 1. 全面穩定性測試
- ✅ 所有容器持續運行不崩潰
- ✅ 資料收集無中斷
- ✅ 自動重連機制驗證
- ✅ 錯誤處理與日誌記錄
- ✅ 資料庫持久化驗證

### 2. 性能與資源測試
- ✅ CPU 使用率趨勢分析
- ✅ 記憶體使用與洩漏檢測
- ✅ 磁碟空間增長率
- ✅ 資料庫寫入效能
- ✅ Redis 佇列堆積監控
- ✅ 網路 I/O 效能

## 測試架構

```
┌─────────────────────────────────────────────────────────────┐
│                    Long Run Test System                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Prometheus  │───▶│  Grafana     │    │  Alertmanager│ │
│  │  (Metrics)   │    │  (Dashboard) │    │  (Alerts)    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                                        │          │
│         │                                        ▼          │
│         │                              ┌──────────────┐    │
│         │                              │Alert Webhook │    │
│         │                              │  (Logger)    │    │
│         │                              └──────────────┘    │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Monitor Script (Python)                      │  │
│  │  • 每 5 分鐘採集系統指標                              │  │
│  │  • Docker 容器狀態                                   │  │
│  │  • 資料庫 & Redis 狀態                               │  │
│  │  • 日誌檔案大小                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Test Results & Reports                       │  │
│  │  • 時序監控數據 (JSONL)                              │  │
│  │  • 告警事件日誌                                      │  │
│  │  • 系統快照                                          │  │
│  │  • HTML 測試報告                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 快速開始

### 前置條件

1. **系統已運行**
   ```bash
   docker-compose up -d
   ```

2. **安裝 Python 依賴**
   ```bash
   pip install psutil matplotlib flask psycopg2-binary
   ```

3. **確認容器狀態**
   ```bash
   docker-compose ps
   ```
   確保所有容器都是 `Up` 狀態。

### 啟動測試

**預設 72 小時測試**
```bash
./scripts/start_long_run_test.sh
```

**自訂測試 ID 和時長**
```bash
./scripts/start_long_run_test.sh my_test_001 48
# 測試 ID: my_test_001
# 時長: 48 小時
```

### 測試期間監控

#### 1. Grafana 儀表板
打開瀏覽器訪問：http://localhost:3000
- 用戶名：`admin`
- 密碼：`admin`
- 導入儀表板：`monitoring/grafana/dashboards/long_run_test.json`

#### 2. 即時監控日誌
```bash
# 監控數據採集日誌
tail -f monitoring/test_results/<test_id>/monitor.log

# 告警事件日誌
tail -f monitoring/test_results/alerts/webhook.log

# 查看最新系統狀態
cat monitoring/test_results/<test_id>/metrics_latest.json | jq
```

#### 3. 中期報告生成
```bash
# 在測試期間任何時候都可以生成當前報告
python3 scripts/generate_test_report.py <test_id>
open monitoring/test_results/<test_id>/test_report.html
```

### 停止測試

```bash
./scripts/stop_long_run_test.sh <test_id>
```

此命令將：
1. 停止監控數據採集
2. 停止告警 Webhook 服務器
3. 執行測試後系統快照
4. 自動生成最終測試報告

## 監控指標

### 系統資源
| 指標 | 採集間隔 | 告警閾值 |
|------|---------|---------|
| CPU 使用率 | 5 分鐘 | > 80% (15 分鐘) |
| 記憶體使用率 | 5 分鐘 | > 85% (10 分鐘) |
| 磁碟使用率 | 5 分鐘 | > 90% (5 分鐘) |
| 網路 I/O | 5 分鐘 | - |

### Docker 容器
| 指標 | 採集間隔 | 告警條件 |
|------|---------|---------|
| 容器狀態 | 5 分鐘 | 容器停止 > 3 分鐘 |
| 容器重啟 | 5 分鐘 | 任何重啟事件 |
| 資源使用 | 5 分鐘 | - |

### 資料庫
| 指標 | 採集間隔 | 告警閾值 |
|------|---------|---------|
| 連線數 | 5 分鐘 | > 80 |
| 資料庫大小 | 5 分鐘 | - |
| 寫入速率 | 5 分鐘 | < 100 rows/sec (15 分鐘) |
| 資料表大小 | 5 分鐘 | - |

### Redis
| 指標 | 採集間隔 | 告警閾值 |
|------|---------|---------|
| 記憶體使用 | 5 分鐘 | > 90% |
| 連線數 | 5 分鐘 | - |
| 操作速率 | 5 分鐘 | - |

### 資料品質
| 指標 | 採集間隔 | 告警條件 |
|------|---------|---------|
| API 錯誤率 | 1 分鐘 | > 10% (10 分鐘) |
| 資料缺失率 | 1 分鐘 | > 5% (10 分鐘) |
| 時間戳倒退 | 即時 | 任何倒退事件 |

## 告警分類

### Critical (嚴重)
- 容器停止運行
- 資料庫/Redis 連線中斷
- 資料收集中斷 > 30 分鐘
- 磁碟空間 < 10%
- 時間戳倒退

### Warning (警告)
- 容器重啟
- 高 CPU/記憶體使用
- API 錯誤率過高
- 資料缺失率過高
- 資料庫連線數過多

### Info (資訊)
- 交易量異常
- 性能建議

## 測試報告

### 報告內容

測試報告包含以下部分：

1. **測試摘要**
   - 測試 ID、開始/結束時間、持續時間
   - 資料採集點數量
   - 關鍵指標統計

2. **資源使用統計**
   - CPU/記憶體/磁碟使用率（最小/最大/平均）
   - 時序圖表
   - 合格/不合格判定

3. **告警摘要**
   - 按類別統計
   - 按嚴重程度統計
   - 詳細事件列表

4. **測試結果**
   - 穩定性測試結果
   - 性能測試結果
   - 資料品質測試結果

### 判定標準

| 測試項目 | 標準 | 結果 |
|---------|------|------|
| 穩定性 | 無 Critical 告警 | PASS/FAIL |
| CPU 性能 | 最大值 < 80% | PASS/FAIL |
| 記憶體性能 | 最大值 < 85% | PASS/FAIL |
| 磁碟性能 | 最大值 < 90% | PASS/FAIL |
| 測試時長 | 達到目標時長 | PASS |

## 故障排除

### 問題：監控採集未啟動

**症狀**：monitor.log 沒有輸出

**解決**：
```bash
# 檢查進程
ps aux | grep long_run_monitor

# 手動啟動
python3 scripts/long_run_monitor.py <test_id> 72
```

### 問題：告警未記錄

**症狀**：alerts/ 目錄沒有日誌

**解決**：
```bash
# 檢查 Webhook 服務器
curl http://localhost:9099/health

# 重啟 Webhook
kill $(cat monitoring/test_results/alerts/webhook.pid)
python3 scripts/alert_webhook.py
```

### 問題：Grafana 無法訪問

**症狀**：http://localhost:3000 無法打開

**解決**：
```bash
# 檢查 Grafana 容器
docker logs crypto_grafana

# 重啟 Grafana
docker-compose restart grafana
```

### 問題：報告生成失敗

**症狀**：generate_test_report.py 報錯

**解決**：
```bash
# 檢查數據檔案
ls -lh monitoring/test_results/<test_id>/

# 檢查 Python 依賴
pip install matplotlib psycopg2-binary

# 重新生成
python3 scripts/generate_test_report.py <test_id>
```

## 最佳實踐

### 1. 測試前準備
- ✅ 確保磁碟空間充足（建議 > 50GB 可用）
- ✅ 檢查所有容器健康狀態
- ✅ 清理舊的測試數據
- ✅ 備份重要配置

### 2. 測試期間
- ✅ 定期檢查 Grafana 儀表板
- ✅ 關注 Critical 告警
- ✅ 每 12 小時生成中期報告
- ✅ 監控磁碟空間使用

### 3. 測試後分析
- ✅ 對比測試前後快照
- ✅ 分析資源使用趨勢
- ✅ 檢討告警事件
- ✅ 記錄優化建議

## 附錄

### 測試檔案結構

```
monitoring/test_results/
├── <test_id>/
│   ├── metrics_timeseries.jsonl  # 時序監控數據
│   ├── metrics_latest.json       # 最新狀態
│   ├── summary.json              # 統計摘要
│   ├── monitor.log               # 監控日誌
│   ├── test_report.html          # HTML 報告
│   ├── cpu_usage.png            # CPU 圖表
│   ├── memory_usage.png         # 記憶體圖表
│   └── disk_usage.png           # 磁碟圖表
├── alerts/
│   ├── alerts_general.jsonl     # 一般告警
│   ├── alerts_critical.jsonl    # 嚴重告警
│   ├── alerts_stability.jsonl   # 穩定性告警
│   ├── alerts_performance.jsonl # 性能告警
│   ├── alerts_data_quality.jsonl # 資料品質告警
│   ├── alert_summary.json       # 告警統計
│   └── webhook.log              # Webhook 日誌
└── snapshots/
    ├── snapshot_<timestamp>.txt      # 測試前快照
    └── snapshot_<test_id>_end.txt   # 測試後快照
```

### 相關腳本

| 腳本 | 用途 |
|-----|------|
| `start_long_run_test.sh` | 啟動測試 |
| `stop_long_run_test.sh` | 停止測試並生成報告 |
| `long_run_monitor.py` | 監控數據採集 |
| `alert_webhook.py` | 告警記錄服務器 |
| `generate_test_report.py` | 生成測試報告 |
| `system_snapshot.sh` | 系統狀態快照 |

### 參考資料

- Prometheus 配置：`monitoring/prometheus/prometheus.yml`
- 告警規則：`monitoring/prometheus/rules/long_run_alerts.yml`
- Grafana 儀表板：`monitoring/grafana/dashboards/long_run_test.json`
- Alertmanager 配置：`monitoring/alertmanager/test_config.yml`
