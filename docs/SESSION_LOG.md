# Crypto Market Analyzer - 開發進度日誌

> **目的**：記錄專案最新進度、重要決策、變更歷史與待辦事項
> **維護者**：開發團隊
> **更新頻率**：每次重大變更或階段完成時更新

---

## 📅 最新進度（2025-12-30 晚上）

### 當前狀態
- **專案版本**：v1.6.0
- **整體完成度**：90% (9/10 階段完成)
- **系統狀態**：✅ 穩定運行，完成 TimescaleDB 資料保留策略自動化監控系統

### 本次更新內容（2025-12-30 晚上）

#### ✅ 已完成：TimescaleDB 資料保留策略自動化監控系統 🎯

**背景**：
用戶詢問資料庫是否有自動降採樣（downsampling）機制。經檢查發現：
- ✅ 資料庫已有完整的 Continuous Aggregates 和 Retention Policies（在 migration 004 中定義）
- ❌ 但沒有自動化監控系統來追蹤這些策略的執行狀態

**實現內容**：
1. **核心監控服務** (`collector-py/src/monitors/retention_monitor.py`)
   - 20 個 Prometheus metrics，5 大監控維度
   - 連續聚合視圖狀態、TimescaleDB Jobs 執行狀態、資料保留策略偏差檢測等

2. **自動化排程** (`collector-py/src/schedulers/retention_monitor_scheduler.py`)
   - 每 30 分鐘執行快速檢查，每小時執行完整檢查

3. **服務部署** - 獨立服務運行在 localhost:8003，導出 108 個指標

4. **告警規則** (`monitoring/prometheus/rules/retention_alerts.yml`) - 15 條預定義告警規則

5. **Prometheus 整合** - 新增 retention-monitor target，成功抓取並評估告警

**部署過程解決的問題**：
1. ✅ 修復 Prometheus `humanizeBytes` 函數不存在問題
2. ✅ 修復 Docker 網路連接問題（改用 host.docker.internal）
3. ✅ 修復 SQL 欄位不存在問題（改用 job_stats 視圖）

**驗證結果**：
```
✅ Retention Monitor: 運行中 (PID: 99746, Port: 8003)
✅ Prometheus Target: UP
✅ Metrics Exported: 108 個
✅ Alert Rules: 15 條已載入
✅ TimescaleDB Jobs: 11/11 正常運行
✅ Continuous Aggregates: 4/4 正常更新
```

**相關文檔**：
- `docs/RETENTION_MONITOR_GUIDE.md` - 使用指南
- `docs/RETENTION_MONITOR_IMPLEMENTATION_REPORT.md` - 實作報告
- `docs/RETENTION_MONITOR_DEPLOYMENT_STATUS.md` - 部署狀態（含完整監控數據）

---

## 📅 最新進度（2025-12-30 下午）

### 當前狀態
- **專案版本**：v1.5.0
- **整體完成度**：85% (8.5/10 階段完成)
- **系統狀態**：穩定運行，新增價格告警與 MAD 異常檢測功能

### 本次更新內容

#### ✅ 已完成（2025-12-30 下午）
1. **實現郵件價格變動告警系統** 📧
   - **新增告警規則**：
     - 價格急劇上漲（5分鐘內 > 3%）
     - 價格急劇下跌（5分鐘內 < -3%）
     - 價格極端波動（5分鐘內 > 5%，嚴重級別）
     - 價格異常停滯（10分鐘內無變化）
   - **告警機制**：通過 Prometheus + Alertmanager 自動觸發郵件通知
   - **結果**：✅ 告警規則已加載，郵件系統已就緒

2. **部署 MAD 異常檢測服務** 🔍
   - **實現內容**：
     - 創建 `mad_detector.py`：完整的 MAD 算法實現
       - `MADDetector`：批次異常檢測
       - `RealtimeMADDetector`：即時流式檢測
     - 創建 `mad_service.py`：獨立監控服務
       - 每 30 秒檢測 BTC/USDT、ETH/USDT 價格異常
       - 導出 Prometheus metrics（8002 端口）
   - **技術細節**：
     - 異常閾值：3.0（警告）、5.0（嚴重）
     - 滑動窗口：100 個資料點
     - MAD 公式：`median(|X_i - median(X)|)`
   - **監控指標**：
     - `mad_anomaly_score`：當前異常分數
     - `mad_anomaly_detected_total`：累計異常次數
     - `price_current`：當前價格
     - `mad_price_median`：價格中位數
     - `mad_value`：MAD 值
     - `mad_detection_latency_seconds`：檢測延遲
   - **告警規則**（5 條）：
     - MAD 檢測到異常（分數 > 3）
     - MAD 檢測到嚴重異常（分數 > 5）
     - 異常檢測率過高（1小時 > 10%）
     - MAD 服務停止運行
     - 檢測延遲過高（P99 > 5s）
   - **Grafana 儀表板**：
     - MAD 異常分數趨勢圖
     - 當前價格 vs 中位數對比
     - 異常檢測數量儀表
     - 檢測延遲監控
     - MAD 值趨勢（波動度）
     - 異常檢測事件時間線
     - 當前異常狀態總覽表
   - **結果**：
     - ✅ MAD 服務正常運行（容器：crypto_mad_detector）
     - ✅ Prometheus 正常採集 metrics
     - ✅ 告警規則已加載
     - ✅ Grafana 儀表板已創建

3. **系統架構升級**
   - 新增服務：`mad-detector` (8002 端口)
   - 更新 Prometheus 配置：新增 mad-detector 抓取目標
   - 更新 docker-compose.yml：新增 MAD 服務定義
   - 支援的交易對：BTC/USDT、ETH/USDT

### 上次更新內容（2025-12-30 上午）

#### ✅ 已完成
1. **成功從 Binance 切換至 Bybit WebSocket** 🎯
   - **背景**：Binance WebSocket 連接被網路環境封鎖（TLS 握手失敗）
   - **解決方案**：
     - 建立完整的 `BybitWSClient.ts` 實現（支援 Bybit V5 API）
     - 修改 `index.ts` 支援動態交易所選擇（透過 `EXCHANGE` 環境變數）
     - 移除所有硬編碼的 'binance' 字串，改用 `this.exchange` 動態屬性
   - **技術細節**：
     - Bybit WebSocket URL: `wss://stream.bybit.com/v5/public/spot`
     - 訂閱格式：`publicTrade.{symbol}`, `orderbook.50.{symbol}`
     - Ping 間隔：20 秒（Bybit 要求）
   - **驗證結果**：
     - ✅ 90 秒內收到 4,828 條訊息
     - ✅ 已寫入 869 筆交易至資料庫（標記為 'bybit'）
     - ✅ 訂單簿快照正確標記交易所來源
     - ✅ 無重連、無錯誤

2. **修復 Alertmanager 郵件通知系統**
   - **問題**：環境變數未被替換（`${SMTP_PORT}` 保持原樣）
   - **原因**：Alpine Linux 容器內無 `envsubst` 命令
   - **解決方案**：
     - 重寫 `entrypoint.sh` 使用 `sed` 替換環境變數
     - 修改 `docker-compose.yml` 新增 entrypoint 配置
   - **結果**：✅ 環境變數正確替換

3. **修復資料庫健康檢查錯誤**
   - **問題**：每 10 秒報錯 `database "crypto" does not exist`
   - **原因**：pg_isready 預設使用使用者名稱作為資料庫名稱
   - **解決方案**：明確指定資料庫名稱 `pg_isready -U crypto -d crypto_db`
   - **結果**：✅ 健康檢查正常，無錯誤日誌

4. **更新監控腳本相容性**
   - **問題**：`long_run_monitor.py` 查詢過時的表名（klines_1m, klines_1h）
   - **解決方案**：更新為當前 schema（ohlcv）
   - **結果**：✅ 監控腳本正常運行

5. **修復 Collector 資料庫連接問題**
   - **問題**：資料庫重啟後 Collector 連接失效
   - **解決方案**：重啟 Collector 服務
   - **結果**：✅ 連接恢復正常

### 上次更新內容（2025-12-29）

#### ✅ 已完成
1. **README.md 全面更新**
   - 重新組織專案結構，增加詳細說明
   - 新增系統架構圖（多層次資料流）
   - 新增快速訪問連結表格（8 個服務端口）
   - 擴展「常見問題」章節（15+ Q&A）
   - 新增「專案狀態」儀表板區塊
   - 更新路線圖（11 個階段清單）
   - 完善文檔索引（16 份關鍵文檔）

2. **穩定性驗證完成**
   - 6+ 小時連續運行測試通過
   - 11/13 服務穩定運行（核心服務 100%）
   - 資料持久化驗證通過（235 MB）
   - 容器重啟恢復機制驗證通過

3. **監控系統完善**
   - Prometheus + Grafana + Alertmanager 全棧運行
   - 50+ metrics 實時監控
   - 2 個預配置 Grafana Dashboards
   - Postgres/Redis Exporters 正常採集

4. **報表系統自動化**
   - Report Scheduler 配置完成
   - 每日報表（08:00 UTC）
   - 每週報表（週一 09:00 UTC）

---

## 🎯 當前優先級任務

### 高優先級（本週）
- [ ] **監控 MAD 異常檢測效果**
  - 觀察異常檢測準確性
  - 調整閾值參數（如需要）
  - 驗證郵件告警觸發
  - 檢視 Grafana 儀表板數據

- [ ] **執行 72 小時長期穩定性測試（Bybit + MAD）**
  - 使用 `./scripts/start_long_run_test.sh`
  - 監控 Bybit WebSocket 穩定性
  - 監控 MAD 服務穩定性
  - 驗證資料完整性與品質
  - 驗證價格告警與 MAD 告警觸發
  - 生成完整測試報告

- [ ] **驗證報表自動生成**
  - 等待每日報表實際產出（08:00 UTC）
  - 檢查報表日誌記錄
  - 驗證郵件發送功能

- [ ] **驗證 Bybit 資料品質**
  - 對比 Bybit vs Binance 歷史資料（如有）
  - 檢查價格、成交量合理性
  - 驗證訂單簿深度與價差

### 中優先級（本月）
- [ ] **MLflow 整合**
  - 安裝 MLflow（SQLite backend）
  - 整合模型訓練流程
  - 記錄實驗 metadata

- [ ] **LSTM 模型優化**
  - 特徵工程改進
  - 架構調整
  - 超參數搜尋

- [ ] **文檔清理**
  - 合併重複文檔
  - 建立文檔生命週期管理

### 低優先級（下月）
- [ ] Coinbase 連接器開發
- [ ] 鏈上數據完整整合
- [ ] Paper Trading 環境建立

---

## 📝 重要決策記錄

### 2025-12-30 下午
**決策 #6**：實現 MAD 異常檢測服務 ⭐
- **原因**：需要自動化的價格異常檢測，減少人工監控負擔
- **方案**：
  - 採用 MAD (Median Absolute Deviation) 算法
    - 比標準差更穩健，不易受極端值影響
    - 公式：`MAD = median(|X_i - median(X)|)`
  - 實現雙模式檢測器：
    - `MADDetector`：批次歷史資料分析
    - `RealtimeMADDetector`：即時流式檢測
  - 獨立微服務架構（mad-detector 容器）
  - 導出 Prometheus metrics 整合現有監控系統
- **參數選擇**：
  - 異常閾值：3.0（警告級別）、5.0（嚴重級別）
  - 滑動窗口：100 個資料點
  - 檢查間隔：30 秒
- **結果**：✅ 服務正常運行，metrics 正常導出
- **優勢**：
  - 自動化異常檢測，7x24 小時監控
  - 可擴展至更多交易對
  - 可調整參數適應不同市場條件
- **未來改進**：
  - 支援動態閾值調整（根據市場波動度）
  - 增加更多檢測算法（Z-Score, IQR）
  - 機器學習模型輔助

**決策 #7**：實現郵件價格變動告警
- **原因**：需要即時通知價格劇烈波動，避免錯失交易機會或風險
- **方案**：
  - 在 Prometheus 告警規則中添加 4 條價格告警：
    - 急劇上漲（5分鐘 > 3%）
    - 急劇下跌（5分鐘 < -3%）
    - 極端波動（5分鐘 > 5%，嚴重）
    - 異常停滯（10分鐘無變化）
  - 利用現有 Alertmanager 郵件系統
  - 分級告警：warning 和 critical
- **結果**：✅ 告警規則已加載
- **整合**：與 MAD 異常檢測形成雙層監控機制

### 2025-12-30 上午
**決策 #1**：從 Binance 切換至 Bybit WebSocket ⭐
- **原因**：Binance WebSocket 端口 9443 被網路環境封鎖，無法建立 TLS 連接
- **影響**：所有 WebSocket 實時資料收集（trades, orderbook）
- **方案**：
  - 實現 Bybit V5 WebSocket 客戶端
  - 重構 index.ts 支援多交易所動態切換
  - 透過 `EXCHANGE` 環境變數控制交易所選擇
- **結果**：✅ 成功，Bybit 連接穩定，資料正常收集
- **可逆性**：可透過設置 `EXCHANGE=binance` 切換回 Binance（需網路支援）
- **未來擴展**：架構已支援輕鬆新增其他交易所（OKX, Coinbase 等）

### 2025-12-29
**決策 #2**：升級至 Python 3.13
- **原因**：pandas-ta 依賴需求（>=3.12）
- **影響**：Analyzer、Jupyter、Report Scheduler
- **結果**：✅ 成功，依賴衝突解決

**決策 #3**：暫時禁用 PDF 報表生成
- **原因**：weasyprint 需要系統依賴（較複雜）
- **影響**：PDF 功能暫不可用
- **計劃**：後續評估需求再處理

**決策 #4**：Node Exporter 在 macOS 不啟用
- **原因**：macOS Docker Desktop 架構限制
- **影響**：無法收集主機系統指標
- **解決方案**：生產環境使用 Linux

### 2025-12-28
**決策 #5**：實施資料庫連接池優化
- **原因**：修復 "connection already closed" 錯誤
- **方案**：ThreadedConnectionPool (min=2, max=10)
- **結果**：✅ 穩定性大幅提升

---

## 🐛 已知問題與解決方案

### 問題 #1：WS Collector Binance 連接失敗 ✅ 已解決
- **狀態**：✅ 已解決（切換至 Bybit）
- **現象**：10 reconnects, 11 errors（TLS 連接失敗）
- **根因**：Binance WebSocket 端口 9443 被網路環境封鎖
- **解決方案**：
  - 實現 Bybit WebSocket 客戶端
  - 重構支援多交易所動態切換
  - 透過 `EXCHANGE=bybit` 環境變數控制
- **結果**：
  - ✅ Bybit 連接穩定（0 reconnects, 0 errors）
  - ✅ 資料正常收集（90 秒內 4,828 條訊息）
  - ✅ 架構可擴展至其他交易所

### 問題 #2：LSTM 模型效果不佳 ⚠️
- **狀態**：待優化
- **現象**：方向準確率接近隨機（~50%）
- **原因**：特徵工程或架構問題
- **計劃**：重新設計特徵 + 架構調優

### 問題 #3：PDF 報表功能禁用 ℹ️
- **狀態**：暫時接受
- **原因**：weasyprint 安裝複雜
- **替代方案**：使用 HTML 報表
- **計劃**：按需啟用

---

## 📊 系統健康度指標

### 最新監控數據（2025-12-30 12:40 UTC）
| 指標 | 當前值 | 目標 | 狀態 |
|------|--------|------|------|
| 服務可用性 | 100% (14/14) | 100% | ✅ 優秀 |
| 核心服務可用性 | 100% (3/3) | 100% | ✅ 優秀 |
| WS Collector 狀態 | ✅ 穩定（Bybit） | 穩定 | ✅ 優秀 |
| MAD Detector 狀態 | ✅ 運行中 | 穩定 | ✅ 優秀 |
| MAD 異常分數 | BTC: 0.0, ETH: 0.0 | < 3.0 | ✅ 正常 |
| 當前價格 | BTC: 87,312 USDT<br>ETH: 2,939 USDT | N/A | ✅ 正常 |
| WS 訊息接收 | >3000/分鐘 | >1000/分鐘 | ✅ 優秀 |
| WS 重連次數 | 0 | <5/小時 | ✅ 優秀 |
| WS 錯誤次數 | 0 | <10/小時 | ✅ 優秀 |
| 資料庫寫入 | >500/分鐘 | >100/分鐘 | ✅ 優秀 |
| Prometheus targets | 7/7 健康 | 100% | ✅ 優秀 |
| 告警規則 | 16 條已加載 | N/A | ✅ 正常 |
| Grafana 儀表板 | 3 個（含 MAD） | N/A | ✅ 正常 |
| 資料庫大小 | ~250 MB | N/A | ✅ 正常 |
| 日誌累積 | <20 MB | <100 MB | ✅ 正常 |

### 新增服務（v1.5.0）
- **MAD Detector**：異常檢測服務（端口 8002）
  - 監控交易對：BTC/USDT, ETH/USDT
  - 檢查間隔：30 秒
  - Metrics 導出：正常

### 資源使用
- **CPU**：平均 <35%（Docker 所有容器，含 MAD 服務）
- **記憶體**：約 4.2GB / 8GB
- **磁碟**：約 500MB / 50GB

---

## 🔄 下次更新計劃

### 預計更新時間：2025-12-31 或 MAD 異常檢測驗證完成後

### 預期達成目標
1. MAD 異常檢測效果驗證（24 小時運行）
2. 價格告警郵件觸發驗證
3. MAD 告警郵件觸發驗證
4. Grafana MAD 儀表板數據可視化驗證
5. 完成 72 小時穩定性測試（含 MAD 服務）
6. 獲得第一份自動產出的每日報表

### 需要檢查的項目
- [ ] MAD 異常檢測準確性
- [ ] 價格告警是否正確觸發
- [ ] MAD 告警是否正確觸發
- [ ] 郵件通知是否正常發送
- [ ] Grafana 儀表板數據是否正常顯示
- [ ] MAD 服務穩定性
- [ ] 報表日誌是否正確寫入
- [ ] 資源使用是否穩定
- [ ] 有無記憶體洩漏
- [ ] 磁碟空間增長率

---

## 📚 相關文檔快速連結

### 核心文檔
- [README.md](../README.md) - 專案總覽（已更新 v1.4.0）
- [PROJECT_STATUS_REPORT.md](PROJECT_STATUS_REPORT.md) - 詳細狀態報告
- [STABILITY_VERIFICATION_REPORT.md](STABILITY_VERIFICATION_REPORT.md) - 穩定性驗證
- [PROJECT_DOC_SUMMARY.md](PROJECT_DOC_SUMMARY.md) - 文檔彙整

### 操作指南
- [LONG_RUN_TEST_GUIDE.md](LONG_RUN_TEST_GUIDE.md) - 長期測試指南
- [GRAFANA_DASHBOARDS_GUIDE.md](GRAFANA_DASHBOARDS_GUIDE.md) - Grafana 使用
- [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md) - 郵件配置

### 技術文檔
- [ENGINEERING_MANUAL.md](ENGINEERING_MANUAL.md) - 工程手冊
- [CLAUDE.md](../CLAUDE.md) - 開發指南
- [AGENTS.md](../AGENTS.md) - Agent 規範

---

## 💡 改進建議與想法

### 技術改進
1. **實施 log rotation**：防止日誌檔案過大
2. **添加 CI/CD pipeline**：自動化測試與部署
3. **資料庫備份策略**：定期備份重要資料
4. **告警通知整合**：接入 Slack/Telegram

### 功能擴展
1. **實時 Dashboard**：Web 介面即時監控
2. **移動端告警**：推送通知到手機
3. **A/B 測試框架**：策略對比測試
4. **風險管理模組**：交易風控系統

### 文檔優化
1. **API 文檔生成**：自動化 API 文檔
2. **視頻教學**：錄製操作示範
3. **最佳實踐指南**：經驗總結
4. **故障排除手冊**：常見問題解決

---

## 🏆 里程碑

### 已達成
- ✅ **2025-12-27**: Phase 1-6 完成（資料收集、品質、分析、回測、報表、監控）
- ✅ **2025-12-28**: 資料庫連接池優化完成
- ✅ **2025-12-29**: 6+ 小時穩定性驗證通過
- ✅ **2025-12-29**: README.md 全面更新完成
- ✅ **2025-12-30 上午**: 成功從 Binance 遷移至 Bybit WebSocket
- ✅ **2025-12-30 上午**: 多交易所架構重構完成（支援動態切換）
- ✅ **2025-12-30 上午**: 修復 Alertmanager、DB healthcheck、監控腳本等多項問題
- ✅ **2025-12-30 下午**: 實現郵件價格變動告警系統（4 條告警規則）
- ✅ **2025-12-30 下午**: 部署 MAD 異常檢測服務（v1.5.0）
- ✅ **2025-12-30 下午**: 創建 MAD Grafana 儀表板

### 待達成
- ⏳ **2025-12-31**: MAD 異常檢測效果驗證（24 小時）
- ⏳ **2025-12-31**: 價格 & MAD 告警郵件觸發驗證
- ⏳ **2025-12-31**: 72 小時長期穩定性測試通過（含 MAD）
- ⏳ **2026-01-05**: MLflow 實驗管理系統上線
- ⏳ **2026-01-15**: 鏈上數據完整整合
- ⏳ **2026-01-31**: Paper Trading 環境建立

---

**最後更新**：2025-12-30 12:45 UTC
**下次檢查**：2025-12-31 或 MAD 異常檢測驗證完成後
**維護者**：開發團隊
**重要變更**：✅ v1.5.0 發布 - 新增價格告警與 MAD 異常檢測功能
