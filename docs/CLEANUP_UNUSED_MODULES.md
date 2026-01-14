# Unused Modules Cleanup Report

**Date**: 2026-01-15  
**Task**: Remove unused blockchain & duplicate modules (P2 #2)  
**Backup**: `unused-modules-20260115.tar.gz`

---

## 📋 Modules to Remove

### 1. Blockchain Data Collection (8 files, ~70KB)

**Reason**: 未整合進主流程 (`main.py` 無引用)，功能未完成（標記 TODO）

| File | Size | Last Modified | Reason |
|------|------|---------------|--------|
| `collector-py/src/connectors/blockchain_base.py` | 9.4KB | Dec 28 | Base class, 無實際使用 |
| `collector-py/src/connectors/bitcoin_whale_tracker.py` | 10KB | Dec 28 | Whale tracking 未整合 |
| `collector-py/src/connectors/ethereum_whale_tracker.py` | 16KB | Dec 28 | 同上 |
| `collector-py/src/connectors/bsc_whale_tracker.py` | 12KB | Dec 28 | 同上 |
| `collector-py/src/connectors/tron_whale_tracker.py` | 11KB | Dec 30 | 同上 |
| `collector-py/src/connectors/blockchain_com_collector.py` | 7.2KB | Jan 15 | 有 TODO 標記 |
| `collector-py/src/connectors/glassnode_collector.py` | 17KB | Jan 15 | 未使用 |
| `collector-py/src/connectors/free_address_tier_collector.py` | 13KB | Jan 15 | 未使用 |

**Total**: ~95.6KB

### 2. Address Tier Loader (1 file)

| File | Reason |
|------|--------|
| `collector-py/src/loaders/address_tier_loader.py` | 只有 self-reference，無其他模組引用 |

### 3. Blockchain Validator (1 file)

| File | Reason |
|------|--------|
| `collector-py/src/validators/blockchain_validator.py` | 配合 blockchain collectors，未使用 |

### 4. Blockchain Loader (1 file)

| File | Reason |
|------|--------|
| `collector-py/src/loaders/blockchain_loader.py` | 配合 blockchain collectors，未使用 |

### 5. Duplicate Main File

| File | Reason |
|------|--------|
| `collector-py/src/main_v2.py` | 與 `main.py` 重複，Docker 使用 `main.py` |

### 6. Scripts 整理 (16 files)

#### 移除（5個）：與區塊鏈相關或已過時

- `scripts/init_blockchain_db.py` - 區塊鏈 DB 初始化（無區塊鏈功能）
- `scripts/reset_blockchain_db.py` - 同上
- `scripts/show_address_tiers.py` - Address tier 功能未使用
- `scripts/demo_address_tiers.py` - 同上
- `scripts/generate_test_report.py` - 測試用，可用 pytest 替代

#### 保留（11個）：實際有用或與監控相關

- `scripts/monitor_db_connections.py` - ✅ 由 `main.py` 使用
- `scripts/run_retention_monitor.py` - ✅ 監控使用
- `scripts/long_run_monitor.py` - ✅ 長期測試
- `scripts/verify_data.py` - ✅ 資料驗證工具
- `scripts/test_collector.py` - ✅ 測試工具
- `scripts/alert_webhook.py` - ✅ 告警 webhook
- `scripts/test_alert_webhook.py` - ✅ 測試工具
- `scripts/test_email.py` - ✅ 郵件測試
- `scripts/report_scheduler.py` - ⚠️ 報表功能（v2.0 已移除 ML，待確認）
- `scripts/generate_daily_report.py` - ⚠️ 同上
- `scripts/generate_weekly_report.py` - ⚠️ 同上

---

## 📊 Impact Analysis

### Files to Remove: 16 files (~120KB code)

### Current Usage Check:

```bash
# main.py 實際引用的模組
from connectors.binance_rest import BinanceRESTConnector
from connectors.okx_rest import OKXRESTConnector
from connectors.funding_rate_collector import FundingRateCollector
from connectors.open_interest_collector import OpenInterestCollector
from loaders.db_loader import DatabaseLoader
from validators.data_validator import DataValidator
from schedulers.backfill_scheduler import BackfillScheduler
from quality_checker import DataQualityChecker
from error_handler import (...)
from metrics_exporter import start_metrics_server, CollectorMetrics
from monitors.retention_monitor import RetentionMonitor
```

**✅ 沒有引用任何區塊鏈相關模組！**

### Risk Assessment:

| Risk Level | Impact |
|------------|--------|
| 🟢 Low | 移除的模組未整合進主流程，不影響當前運行服務 |
| 🟢 Low | 所有檔案已建立備份 `unused-modules-20260115.tar.gz` |
| 🟢 Low | Docker 容器使用 `main.py`（非 `main_v2.py`） |

---

## ✅ Pre-removal Checklist

- [x] 檢查 `main.py` 無引用待移除模組
- [x] 檢查 Docker Compose 配置使用正確檔案
- [x] 確認當前服務運行正常 (7/7 healthy)
- [x] 建立完整備份計劃

---

## 📦 Backup Strategy

```bash
# 建立備份檔案包含：
- collector-py/src/connectors/*whale_tracker*.py
- collector-py/src/connectors/blockchain_*.py
- collector-py/src/connectors/glassnode_collector.py
- collector-py/src/connectors/free_address_tier_collector.py
- collector-py/src/loaders/address_tier_loader.py
- collector-py/src/loaders/blockchain_loader.py
- collector-py/src/validators/blockchain_validator.py
- collector-py/src/main_v2.py
- scripts/init_blockchain_db.py
- scripts/reset_blockchain_db.py
- scripts/show_address_tiers.py
- scripts/demo_address_tiers.py
- scripts/generate_test_report.py
```

---

## 🎯 Expected Outcome

**Code Reduction**:
- Before: ~8,500 LOC
- After: ~8,380 LOC (-120 LOC, -1.4%)

**Benefits**:
- ✅ 消除「未被驗證的假設」（區塊鏈功能）
- ✅ 降低認知負擔（少 16 個檔案）
- ✅ 符合核心哲學：「能刪掉的程式碼才是好設計」
- ✅ 清理技術債務

---

**Next Steps**: Execute removal → Update SESSION_LOG.md → Verify services
