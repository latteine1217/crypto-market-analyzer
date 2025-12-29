# 文檔管理建議

## 📋 目的
本文檔提供 docs/ 目錄的文檔管理建議，確保文檔結構清晰、避免冗餘。

---

## 📁 當前文檔狀態（12 份）

### ✅ 保留文檔（核心與指南）

#### 活躍文檔（持續更新）
1. **SESSION_LOG.md** 🆕
   - 最新進度日誌
   - 決策記錄
   - 待辦事項
   - **更新頻率**：每次重大變更

2. **PROJECT_STATUS_REPORT.md**
   - 專案整體狀態
   - 完成度統計
   - 技術債務
   - **更新頻率**：每階段完成時

#### 技術指南（穩定文檔）
3. **ENGINEERING_MANUAL.md**
   - 系統功能總覽
   - 技術棧說明
   - 重要文件索引

4. **LONG_RUN_TEST_GUIDE.md**
   - 長期測試操作指南
   - 監控指標說明
   - 故障排除

5. **GRAFANA_DASHBOARDS_GUIDE.md**
   - Dashboard 使用說明
   - 變數配置
   - 面板說明

6. **EMAIL_SETUP_GUIDE.md**
   - SMTP 配置指南
   - 報表郵件設定

#### 參考文檔（歷史記錄）
7. **PROJECT_DOC_SUMMARY.md**
   - 所有文檔彙整
   - 快速索引

---

## 🗂️ 建議歸檔（移至 archive/）

這些文檔是重要的歷史記錄，但不需要在主目錄：

### Phase 6 測試相關（3 份）
- `PHASE6_TEST_REPORT.md` → `archive/phase6/`
- `PHASE6_METRICS_FIX_REPORT.md` → `archive/phase6/`
- `PHASE6_METRICS_TEST_RESULTS.md` → `archive/phase6/`

**原因**：
- Phase 6 已完成，測試報告屬於歷史記錄
- 重要資訊已整合到 PROJECT_STATUS_REPORT.md
- 保留作為參考，但不需要在主文檔目錄

### 穩定性驗證相關（2 份）
- `STABILITY_VERIFICATION_REPORT.md` → `archive/stability_tests/`
- `WS_COLLECTOR_HEALTHCHECK_INVESTIGATION.md` → `archive/stability_tests/`

**原因**：
- 階段性驗證報告
- 關鍵結論已記錄在 SESSION_LOG.md
- 作為歷史參考保留

---

## 📂 建議目錄結構

```
docs/
├── SESSION_LOG.md                    # 🔥 最新進度日誌
├── PROJECT_STATUS_REPORT.md          # 專案狀態總覽
├── PROJECT_DOC_SUMMARY.md            # 文檔索引
├── ENGINEERING_MANUAL.md             # 工程手冊
├── LONG_RUN_TEST_GUIDE.md           # 測試指南
├── GRAFANA_DASHBOARDS_GUIDE.md      # Grafana 使用
├── EMAIL_SETUP_GUIDE.md             # 郵件配置
│
└── archive/                          # 歷史文檔歸檔
    ├── phase6/                       # Phase 6 測試記錄
    │   ├── PHASE6_TEST_REPORT.md
    │   ├── PHASE6_METRICS_FIX_REPORT.md
    │   └── PHASE6_METRICS_TEST_RESULTS.md
    │
    └── stability_tests/              # 穩定性測試記錄
        ├── STABILITY_VERIFICATION_REPORT.md
        └── WS_COLLECTOR_HEALTHCHECK_INVESTIGATION.md
```

---

## 🎯 文檔生命週期管理

### 文檔類型定義

#### 1. 活躍文檔（Active）
- 持續更新
- 反映當前狀態
- 位於 `docs/` 根目錄

**示例**：
- SESSION_LOG.md
- PROJECT_STATUS_REPORT.md

#### 2. 穩定文檔（Stable）
- 內容基本確定
- 偶爾更新
- 位於 `docs/` 根目錄

**示例**：
- ENGINEERING_MANUAL.md
- LONG_RUN_TEST_GUIDE.md

#### 3. 歷史文檔（Archived）
- 已完成的階段報告
- 不再更新
- 移至 `docs/archive/`

**示例**：
- Phase 測試報告
- 階段性驗證報告

### 歸檔規則

**何時歸檔？**
1. 階段完成且不再更新
2. 重要資訊已整合到活躍文檔
3. 僅作為歷史參考

**如何歸檔？**
```bash
# 建立歸檔目錄
mkdir -p docs/archive/phase6
mkdir -p docs/archive/stability_tests

# 移動文檔
mv docs/PHASE6_*.md docs/archive/phase6/
mv docs/STABILITY_*.md docs/archive/stability_tests/
mv docs/WS_COLLECTOR_*.md docs/archive/stability_tests/

# 更新 README.md 中的連結（如有）
```

---

## 📝 文檔命名規範

### 建議格式
- 活躍文檔：`大寫_英文.md`（如 `SESSION_LOG.md`）
- 指南文檔：`主題_GUIDE.md`（如 `SETUP_GUIDE.md`）
- 階段報告：`PHASE數字_主題.md`（如 `PHASE6_REPORT.md`）
- 測試報告：`測試類型_TEST_REPORT.md`

### 避免
- 過長的檔名（>40 字元）
- 空格或特殊符號
- 版本號在檔名中（使用 git 管理版本）

---

## 🔄 維護檢查清單

### 每週檢查
- [ ] 更新 SESSION_LOG.md（如有重大變更）
- [ ] 檢查待辦事項完成狀態

### 每月檢查
- [ ] 更新 PROJECT_STATUS_REPORT.md
- [ ] 檢查是否有文檔需要歸檔
- [ ] 清理過時資訊

### 每階段完成時
- [ ] 生成階段完成報告
- [ ] 歸檔階段測試文檔
- [ ] 更新 PROJECT_DOC_SUMMARY.md

---

## 🎬 執行歸檔（可選）

如果同意以上建議，可以執行以下命令：

```bash
# 建立歸檔目錄
mkdir -p docs/archive/phase6
mkdir -p docs/archive/stability_tests

# 移動 Phase 6 文檔
git mv docs/PHASE6_TEST_REPORT.md docs/archive/phase6/
git mv docs/PHASE6_METRICS_FIX_REPORT.md docs/archive/phase6/
git mv docs/PHASE6_METRICS_TEST_RESULTS.md docs/archive/phase6/

# 移動穩定性測試文檔
git mv docs/STABILITY_VERIFICATION_REPORT.md docs/archive/stability_tests/
git mv docs/WS_COLLECTOR_HEALTHCHECK_INVESTIGATION.md docs/archive/stability_tests/

# 提交變更
git add docs/
git commit -m "docs: 歸檔 Phase 6 與穩定性測試報告"
```

**注意**：歸檔後這些文檔仍然可以通過 git 歷史訪問，只是不會出現在主文檔列表中。

---

## 📊 歸檔前後對比

### 歸檔前（12 份文檔）
```
docs/
├── EMAIL_SETUP_GUIDE.md
├── ENGINEERING_MANUAL.md
├── GRAFANA_DASHBOARDS_GUIDE.md
├── LONG_RUN_TEST_GUIDE.md
├── PHASE6_METRICS_FIX_REPORT.md        ← 可歸檔
├── PHASE6_METRICS_TEST_RESULTS.md      ← 可歸檔
├── PHASE6_TEST_REPORT.md               ← 可歸檔
├── PROJECT_DOC_SUMMARY.md
├── PROJECT_STATUS_REPORT.md
├── SESSION_LOG.md
├── STABILITY_VERIFICATION_REPORT.md    ← 可歸檔
└── WS_COLLECTOR_HEALTHCHECK_INVESTIGATION.md  ← 可歸檔
```

### 歸檔後（7 份核心文檔）
```
docs/
├── SESSION_LOG.md                    # 🔥 最新進度
├── PROJECT_STATUS_REPORT.md          # 專案狀態
├── PROJECT_DOC_SUMMARY.md            # 文檔索引
├── ENGINEERING_MANUAL.md             # 工程手冊
├── LONG_RUN_TEST_GUIDE.md           # 測試指南
├── GRAFANA_DASHBOARDS_GUIDE.md      # Grafana 使用
├── EMAIL_SETUP_GUIDE.md             # 郵件配置
│
└── archive/                          # 歷史歸檔（5 份）
    ├── phase6/ (3 份)
    └── stability_tests/ (2 份)
```

**效果**：主文檔目錄從 12 份減少到 7 份，更加清晰易讀。

---

**建議狀態**：待執行（可選）  
**預期效果**：文檔結構更清晰，減少認知負擔  
**風險**：無（使用 git mv 可保留歷史）
