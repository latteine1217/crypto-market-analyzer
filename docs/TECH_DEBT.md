# Technical Debt Tracker

**Last Updated**: 2026-01-15  
**Maintainer**: Development Team

---

## 🎯 Purpose

集中追蹤專案技術債務，確保臨時方案與未完成功能透明化，符合核心哲學「好工程是可辯護的」。

---

## 🔴 Critical Priority

### TD-001: main.py 複雜度過高
**Status**: 🔴 Open  
**Created**: 2026-01-15  
**Impact**: 維護性崩壞風險、違反 Simplicity 原則

**問題描述**：
- 單一檔案 758 行，包含 5 個類別、19 個方法
- 57 個條件分支、24 個異常處理、30+ import
- 職責混雜：初始化、調度、收集、驗證、補資料、監控

**解決方案**：
```
Phase 1: 提取 CollectorOrchestrator (協調各 collector)
Phase 2: 提取 HealthMonitor (健康檢查與監控)
Phase 3: 提取 SchedulerManager (任務調度)
```

**ETA**: 2026-01-20  
**Assigned**: TBD

---

### TD-002: 核心模組測試覆蓋率不足
**Status**: 🔴 Open  
**Created**: 2026-01-15  
**Impact**: 無法驗證假設、回歸風險高

**問題描述**：
- `db_loader.py` (907 行) - 0% 測試
- `quality_checker.py` (622 行) - 0% 測試
- `binance_rest.py` (254 行) - 0% 測試
- 整體 Python 測試覆蓋率：15%
- TypeScript 測試覆蓋率：1%

**解決方案**：
```
Priority 1: db_loader.py 測試 (連接池、事務、錯誤處理)
Priority 2: quality_checker.py 測試 (品質指標計算)
Priority 3: collectors 測試 (API 連接、重試邏輯)
Target: 核心模組 80% 覆蓋率
```

**ETA**: 2026-01-18  
**Assigned**: TBD

---

## 🟡 High Priority

### TD-003: 資料品質量化未落地
**Status**: 🟡 Open  
**Created**: 2026-01-15  
**Impact**: 驗收標準無法驗證（K 線缺失率 ≤ 0.1%）

**問題描述**：
- Migration 013 已建立 `data_quality_metrics` 表
- `quality_checker.py` 計算品質指標但未寫入資料庫
- Dashboard 無法顯示品質趨勢

**解決方案**：
```python
# 在 quality_checker.py 新增：
def record_quality_metrics(self, market_id, timeframe, metrics):
    """將品質指標寫入 data_quality_metrics 表"""
    # Implementation...
```

**ETA**: 2026-01-17  
**Assigned**: TBD

---

### TD-004: 配置檔碎片化
**Status**: 🟡 Open  
**Created**: 2026-01-15  
**Impact**: 配置分散、維護困難

**問題描述**：
- 11 個 YAML 配置檔分散在 4 個目錄
- 只有 1 個 collector 配置（binance_btcusdt_1m.yml）
- 缺少 Bybit、OKX 的配置檔案

**解決方案**：
```
configs/
  ├── app.yml              # 整合應用配置
  ├── collectors/          # 標準化收集器配置
  │   ├── binance.yml
  │   ├── bybit.yml
  │   └── okx.yml
  └── monitoring/          # 監控配置
```

**ETA**: 2026-01-19  
**Assigned**: TBD

---

## 🟢 Medium Priority

### TD-005: Symbol 工具重複實作
**Status**: 🟢 Open  
**Created**: 2026-01-15  
**Impact**: 未來可能不一致

**問題描述**：
- Python 版本：`collector-py/src/utils/symbol_utils.py`
- TypeScript 版本：`data-collector/src/utils/symbolUtils.ts`
- 兩者獨立維護，未來可能偏離

**解決方案**：
```
Short-term: 自動化測試確保兩版本行為一致
Long-term: 評估統一為 TypeScript（容器化後可用 Node.js）
```

**ETA**: 2026-01-22  
**Assigned**: TBD

---

### TD-006: 文檔數據不一致
**Status**: 🟢 Open  
**Created**: 2026-01-15  
**Impact**: 信任度降低

**問題描述**：
```
實際統計: Python 13,788 行 + TypeScript 5,567 行 = 19,355 行
文檔聲稱: 總共 ~8,500 行（減少 48%）
差異:     +10,855 行 (128% 誤差)
```

**解決方案**：
- 更新 SESSION_LOG 與 PROJECT_STATUS_REPORT
- 建立自動化腳本統計代碼行數（排除測試、註解、空行）

**ETA**: 2026-01-16  
**Assigned**: TBD

---

### TD-007: 依賴循環風險
**Status**: 🟢 Open  
**Created**: 2026-01-15  
**Impact**: 模組耦合度高

**問題描述**：
- `main.py` import 11 個模組
- 部分模組互相依賴（quality_checker → db_loader + validator + backfill_scheduler）

**解決方案**：
```python
# 採用依賴注入模式 (DI)
class DataQualityChecker:
    def __init__(self, db: DatabaseLoader, validator: DataValidator):
        self.db = db
        self.validator = validator
```

**ETA**: 2026-01-23  
**Assigned**: TBD

---

## ✅ Completed

### TD-008: 前端效能與類型安全重構
**Status**: ✅ Completed  
**Created**: 2026-01-15  
**Completed**: 2026-01-15

**問題描述**：
- `Providers.tsx` 請求過於頻繁 (5s poll)
- 圖表組件濫用 `any` 且存在記憶體洩漏風險
- 重複依賴 `recharts` 與 `lightweight-charts`

**解決方案**：
- 優化 QueryClient 配置 (staleTime 60s, refetchOff)
- 全面遷移至 `lightweight-charts` 並移除 `recharts`
- 補全 TypeScript 類型定義與 Cleanup 邏輯

### TD-000: 孤兒配置檔案清理
...`

---

## 📝 How to Use This Document

### 新增技術債務
```markdown
### TD-XXX: [簡短描述]
**Status**: 🔴/🟡/🟢 Open
**Created**: YYYY-MM-DD
**Impact**: [對專案的影響]

**問題描述**: [詳細說明]
**解決方案**: [具體步驟]
**ETA**: YYYY-MM-DD
**Assigned**: [負責人]
```

### 更新狀態
- 🔴 Open (Critical)
- 🟡 Open (High)
- 🟢 Open (Medium)
- 🔵 In Progress
- ✅ Completed
- ❌ Cancelled

### 追蹤原則
1. 新增 TODO 註解必須同步更新此文件
2. 完成技術債務後移至 Completed 區段
3. 每週 Review 更新優先級與 ETA

---

**Maintained by**: Development Team  
**Review Frequency**: Weekly
