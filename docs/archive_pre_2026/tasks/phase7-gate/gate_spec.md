# Phase 7 驗收規範（Gate Specification）

**任務ID**: phase7-gate  
**創建時間**: 2025-12-30 16:50 UTC  
**負責人**: 主 Agent  
**審查者**: exp_planner (待審查)  
**狀態**: 🟡 進行中（Gate 3 已完成）

---

## 📋 任務目標

定義 Phase 7「部署與自動化」的明確驗收標準，確保系統從研究環境過渡至可運營狀態。

### 背景
- Phase 7 當前標註 85% 完成
- 核心基礎設施已就緒，但缺乏長期穩定性證據
- 自動化機制（報表排程、告警通知）已配置但未實測

### 為何需要 Gate？
1. **決策依據**：Phase 8/9 依賴 Phase 7 的穩定性
2. **風險控制**：避免在不穩定系統上建立更多功能
3. **交付標準**：明確「完成」的定義，避免無限優化

---

## 🚪 Gate 架構

### Gate 層級設計
```
Physics Gate ✅ → Debug Gate 🟡 → Performance Gate 🟢 → Reviewer Gate 📌
```

- **Physics Gate**: ✅ 已通過（無物理層涉及）
- **Debug Gate**: 🟡 待驗證（穩定性測試）
- **Performance Gate**: 🟢 可選（效能優化延後至 Phase 8）
- **Reviewer Gate**: 📌 最終審查（需 exp_planner 核可本規範）

---

## 🎯 三大驗收 Gate

### Gate 1: 7×24 穩定性測試 🔴 必過

**目標**: 證明系統可長期穩定運行，無重大故障

#### 目前狀態
- **測試 ID**: stability_perf_test_20251230_165500
- **PID**: 75046
- **啟動時間**: 2025-12-30 16:55 UTC+8
- **預計完成**: 2026-01-06 16:55 UTC+8

#### 驗收標準

| 指標 | 標準值 | 測量方式 | 容忍範圍 |
|------|--------|---------|---------|
| **運行時長** | ≥168 小時（7 天） | 測試開始至結束時間 | 無 |
| **核心服務可用性** | ≥99.5% | (正常運行時間 / 總時間) × 100% | 允許 36 分鐘停機 |
| **資料完整性** | OHLCV 缺失率 <0.1% | (缺失筆數 / 預期筆數) × 100% | 允許 168 筆缺失（7天×24小時） |
| **記憶體穩定性** | 增長率 <1% per day | 線性回歸斜率 | 斜率 p-value <0.05 |
| **磁碟使用** | 線性可預測 | R² >0.95 | - |
| **Retention Jobs** | 成功率 >95% | (成功次數 / 總次數) × 100% | 允許 3 次失敗（7天×24小時/6小時） |
| **自動恢復** | 重啟後 <5 分鐘恢復 | 容器重啟至服務 UP 時間 | - |

#### 測試方法

**啟動測試**:
```bash
cd /Users/latteine/Documents/coding/finance
./scripts/start_long_run_test.sh stability_perf_test_20251230_165500 168
```

**檢查點排程**（每 6 小時）:
- 記錄系統指標快照（記憶體、CPU、磁碟）
- 檢查服務狀態（`docker-compose ps`）
- 驗證資料完整性（`scripts/verify_data.py`）
- 記錄 Prometheus metrics（匯出至 CSV）

**測試中斷條件**（緊急中止）:
- 核心服務崩潰 >3 次/小時
- 資料庫損壞（無法恢復）
- 磁碟空間耗盡（>90%）

**測試完成動作**:
1. 生成驗收報告（`docs/PHASE7_STABILITY_VERIFICATION_REPORT.md`）
2. 包含指標趨勢圖（記憶體、CPU、磁碟、資料量）
3. 失敗事件分析（如有）
4. 通過/失敗決議

#### 驗收決議規則

**✅ 通過條件**: 所有指標達標  
**🟡 條件通過**: 1-2 個次要指標未達標，但有改進計畫  
**❌ 失敗**: 任一核心指標（可用性、資料完整性）未達標

---

### Gate 2: 報表排程驗證 🟡 必過

**目標**: 證明報表系統可自動化運行，產出符合規格

#### 驗收標準

| 檢查項 | 標準 | 驗證方式 |
|--------|------|---------|
| **每日報表生成** | 連續 3 天成功 | 檢查 `reports/daily/` 檔案時間戳 |
| **每週報表生成** | 至少 1 次成功 | 檢查 `reports/weekly/` 檔案 |
| **報表內容完整性** | 包含 K 線圖、巨鯨動向、回測結果 | 手動開啟 HTML 檢視 |
| **日誌記錄** | `report_scheduler.log` 有成功記錄 | 檢查日誌檔案 |
| **檔案格式** | HTML 可正常開啟、圖表可互動 | 瀏覽器測試 |
| **錯誤處理** | 若失敗有錯誤日誌 | 檢查 `logs/` 目錄 |

#### 測試方法

**方案 A：自然觸發（建議）**
- 等待 3-7 天，讓 cron 自動執行
- 每日檢查 `reports/` 目錄更新
- 優點：真實環境驗證
- 缺點：需時較長

**方案 B：人工觸發（快速驗證）**
```bash
cd /Users/latteine/Documents/coding/finance
# 手動觸發每日報表
python scripts/generate_daily_report.py

# 手動觸發每週報表
python scripts/generate_weekly_report.py

# 檢查輸出
ls -lh reports/daily/
ls -lh reports/weekly/
```

**驗證清單**:
- [ ] 檔案已生成（時間戳正確）
- [ ] 檔案大小合理（>10 KB）
- [ ] HTML 可在瀏覽器開啟
- [ ] K 線圖正確顯示（蠟燭圖 + 成交量）
- [ ] 巨鯨動向表格有資料
- [ ] 回測結果圖表存在
- [ ] 無 JavaScript 錯誤（檢查瀏覽器 console）

#### 驗收決議規則

**✅ 通過條件**: 
- 3 次每日報表成功（自然觸發）或 1 次成功（人工觸發）
- 1 次每週報表成功
- 內容完整性檢查全部通過

**❌ 失敗**:
- 連續 2 次排程失敗
- 報表內容缺失關鍵部分（K 線圖或巨鯨動向）

---

### Gate 3: 告警通知驗證 🟢 必過（已完成）

**目標**: 證明告警系統可正常觸發並發送通知

#### 驗收標準

| 檢查項 | 標準 | 驗證方式 |
|--------|------|---------|
| **告警觸發** | 至少 1 次真實或測試告警 | Alertmanager UI 查詢 |
| **郵件發送** | 郵件成功送達配置郵箱 | 檢查收件匣 |
| **告警內容完整性** | 包含時間、服務、指標、閾值 | 檢視郵件內容 |
| **告警恢復通知** | 問題解決後發送恢復郵件 | 檢查收件匣 |
| **Alertmanager 記錄** | UI 有完整告警歷史 | http://localhost:9093 |

#### 測試方法

**方案 A：人工觸發測試告警（建議用於快速驗證）**

```bash
# 方法 1：觸發 PriceStagnant 告警（停止 WS Collector 10 分鐘）
docker stop crypto_ws_collector
sleep 600
docker start crypto_ws_collector

# 方法 2：發送測試告警至 Alertmanager
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning",
      "service": "test"
    },
    "annotations": {
      "summary": "Phase 7 Gate 3 測試告警",
      "description": "這是驗證告警系統的測試訊息"
    },
    "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "endsAt": "'$(date -u -d '+5 minutes' +%Y-%m-%dT%H:%M:%SZ)'"
  }]'
```

**方案 B：等待真實告警（自然觸發）**
- 在 7 天測試期間，可能觸發的告警：
  - `PriceStagnant`（價格停滯 10 分鐘）
  - `DataLayerRecordCountLow`（資料異常少）
  - `IdleInTransactionConnectionsHigh`（連接異常）

**驗證清單**:
- [ ] Alertmanager UI 顯示告警（http://localhost:9093/#/alerts）
- [ ] 郵件已收到（檢查主旨包含 "FIRING" 或 "RESOLVED"）
- [ ] 郵件內容包含：
  - [x] 告警名稱
  - [x] 嚴重級別（warning/critical）
  - [x] 觸發時間
  - [x] 服務/指標名稱
  - [x] 當前值 vs 閾值
  - [x] Grafana 儀表板連結（如有）
- [ ] 告警恢復後收到 RESOLVED 郵件
- [ ] Alertmanager 日誌無錯誤（`docker logs crypto_alertmanager`）

**檢查 SMTP 配置**:
```bash
# 確認環境變數已載入
docker exec crypto_alertmanager cat /etc/alertmanager/alertmanager.yml | grep -A 10 email_configs
```

#### 驗收決議規則

**✅ 通過條件**: 
- 至少 1 次告警成功觸發（真實或測試）
- 郵件成功送達且內容完整
- Alertmanager 有記錄可查詢

**❌ 失敗**:
- 告警觸發但郵件未送達（SMTP 配置問題）
- 郵件內容缺失關鍵資訊

---

## 📊 整體驗收矩陣

| Gate | 權重 | 狀態 | 通過條件 | 當前進度 |
|------|------|------|---------|---------|
| **Gate 1: 7×24 穩定性** | 50% | 🟡 進行中 | 所有指標達標 | 測試進行中（168h） |
| **Gate 2: 報表排程** | 25% | ⏳ 待驗證 | 3 天每日 + 1 次週報 | 等待排程觸發 |
| **Gate 3: 告警通知** | 25% | ✅ 已通過 | 1 次成功觸發 | 25/25（100%） |

### 最終決議規則

**✅ Phase 7 完全通過**:
- 所有 3 個 Gate 均達標

**🟡 Phase 7 條件通過**:
- Gate 1 必須通過
- Gate 2 或 Gate 3 其中一個未達標，但有改進計畫

**❌ Phase 7 失敗**:
- Gate 1 未通過
- Gate 2 和 Gate 3 均未通過

---

## 🔄 測試時間表

### 建議排程（2025-12-30 啟動）

| 日期 | 任務 | 負責人 | 檢查點 |
|------|------|--------|--------|
| **2025-12-30** | 啟動 7 天測試 | 主 Agent | ✅ 測試開始記錄 |
| **2025-12-30** | 觸發告警測試 | 主 Agent | ✅ 郵件驗證 |
| **2025-12-31** | 第 1 次檢查點（24h） | 主 Agent | 指標快照 |
| **2026-01-01** | 驗證每日報表（第 1 天） | 主 Agent | 檢查檔案生成 |
| **2026-01-02** | 第 2 次檢查點（72h） | 主 Agent | 指標快照 |
| **2026-01-02** | 驗證每日報表（第 2 天） | 主 Agent | 檢查檔案生成 |
| **2026-01-03** | 驗證每日報表（第 3 天） | 主 Agent | ✅ Gate 2 決議 |
| **2026-01-04** | 第 3 次檢查點（120h） | 主 Agent | 指標快照 |
| **2026-01-05** | 驗證每週報表（週一） | 主 Agent | ✅ Gate 2 最終驗證 |
| **2026-01-06** | 第 4 次檢查點（168h） | 主 Agent | ✅ 測試結束 |
| **2026-01-06** | 生成驗收報告 | 主 Agent | ✅ Gate 1 決議 |
| **2026-01-07** | Reviewer 最終審查 | exp_planner | 🚪 Phase 7 最終決議 |

---

## 📋 驗收報告模板

測試完成後需生成報告：`docs/PHASE7_STABILITY_VERIFICATION_REPORT.md`

### 報告結構
```markdown
# Phase 7 穩定性驗收報告

## 測試摘要
- 測試期間：YYYY-MM-DD HH:MM ~ YYYY-MM-DD HH:MM
- 總時長：XXX 小時
- 系統版本：v1.7.0

## Gate 1: 7×24 穩定性測試
- 核心服務可用性：XX.X%（目標：≥99.5%）✅/❌
- 資料完整性：缺失率 X.XX%（目標：<0.1%）✅/❌
- 記憶體穩定性：增長率 X.X% per day（目標：<1%）✅/❌
- Retention Jobs 成功率：XX%（目標：>95%）✅/❌
- [指標趨勢圖]
- [失敗事件分析]

## Gate 2: 報表排程驗證
- 每日報表：X/3 成功 ✅/❌
- 每週報表：X/1 成功 ✅/❌
- 內容完整性：✅/❌
- [報表截圖]

## Gate 3: 告警通知驗證
- 告警觸發：X 次 ✅/❌
- 郵件送達：X/X 成功 ✅/❌
- [告警截圖]

## 最終決議
- [ ] ✅ Phase 7 完全通過
- [ ] 🟡 Phase 7 條件通過（改進計畫：...）
- [ ] ❌ Phase 7 失敗（原因：...）

## 建議
- 下一步行動：...
- 風險項目：...
```

---

## 🚨 風險與緩解措施

| 風險 | 機率 | 影響 | 緩解措施 | 負責人 |
|------|------|------|---------|--------|
| 7 天測試中發現記憶體洩漏 | 中 | 高 | 監控指標 + 自動重啟 + 事後修復 | Debug Engineer |
| 報表排程未觸發（cron 問題） | 低 | 中 | 手動觸發驗證 + 修復 cron 配置 | 主 Agent |
| 告警郵件無法送達（SMTP） | 低 | 中 | SMTP 配置已驗證（v1.5.0），備用：Slack | 主 Agent |
| 測試期間用戶要求中斷 | 低 | 高 | 保存檢查點，可恢復測試 | 主 Agent |
| 容器崩潰無法恢復 | 低 | 高 | Docker restart policy + 人工介入 | 主 Agent |

---

## ✅ 審查檢查清單

本規範需經過以下審查：

### exp_planner 審查（實驗規劃層）
- [ ] 測試時長（7 天）是否足夠？
- [ ] 驗收標準（99.5% 可用性）是否合理？
- [ ] 檢查點間隔（6 小時）是否適當？
- [ ] 資料完整性閾值（<0.1%）是否可達？
- [ ] 失敗條件是否明確？
- [ ] 測試中斷條件是否安全？

### Reviewer 審查（最終決議層）
- [ ] 三個 Gate 是否涵蓋關鍵驗收點？
- [ ] 驗收矩陣權重分配是否合理？
- [ ] 報告模板是否完整？
- [ ] 風險登記是否全面？

---

## 📎 相關文件

- **長期測試指南**: `docs/LONG_RUN_TEST_GUIDE.md`
- **當前系統狀態**: `docs/PROJECT_STATUS_REPORT.md`
- **Session 上下文**: `context/context_session_20251230_163012.md`
- **決策日誌**: `context/decisions_log.md`
- **穩定性驗證報告範本**: `docs/STABILITY_VERIFICATION_REPORT.md`（待生成）

---

**文件版本**: v1.0 (草案)  
**最後更新**: 2025-12-30 16:50 UTC  
**下次審查**: exp_planner 審查後  
**狀態**: ⏳ 待審查

---

## 📊 Gate Completion Status Update

### Gate 3: Alert Notification Verification ✅ **COMPLETED**

**Completion Date**: 2025-12-30 16:50 UTC+8  
**Status**: 🟢 **PASSED**  
**Result**: EXCELLENT

#### Completion Details

**Timeline**:
- 16:25 - Issue discovered (emails not being sent due to webhook routing)
- 16:35 - Root cause identified (entrypoint.sh overwrites config)
- 16:45 - Fix applied to alertmanager.yml.template
- 16:46 - Test alerts sent (Phase7Gate3EmailTest, Phase7CriticalEmailTest)
- 16:50 - User confirmed email receipt ✅

**Tests Passed**:
- ✅ SMTP connectivity (smtp.gmail.com:587)
- ✅ Email receiver routing (critical/warning/notifications)
- ✅ Alert grouping and timing
- ✅ HTML email rendering (Chinese characters)
- ✅ End-to-end delivery (Prometheus → Alertmanager → SMTP → Gmail)

**Metrics**:
- **Email Delivery Time**: <5 minutes from alert trigger
- **Alerts Tested**: 5 (2 test + 3 system alerts)
- **Success Rate**: 100% (all emails delivered)
- **Configuration Issues**: 1 (resolved within 25 minutes)

**Files Modified**:
- `monitoring/alertmanager/alertmanager.yml.template` (routing fix)
- `context/gate3_email_verification_20251230_164806.md` (verification report)
- `context/decisions_log.md` (Decision D004 logged)

**Weight**: 25%  
**Score**: 25/25 (100%)

---

### Updated Phase 7 Completion Score

| Gate | Weight | Status | Score | Notes |
|------|--------|--------|-------|-------|
| Gate 1: 7-Day Stability | 50% | 🟡 IN PROGRESS | TBD | 0.5h / 168h completed |
| Gate 2: Report Scheduling | 25% | ⏳ PENDING | TBD | Waiting for cron triggers |
| Gate 3: Alert Notifications | 25% | ✅ **PASSED** | **25/25** | Email delivery confirmed |
| **TOTAL** | 100% | 🟡 IN PROGRESS | **25/100** | **25% Complete** |

**Next Milestone**: Gate 1 checkpoint at 24h (2025-12-31 16:36 UTC+8)
