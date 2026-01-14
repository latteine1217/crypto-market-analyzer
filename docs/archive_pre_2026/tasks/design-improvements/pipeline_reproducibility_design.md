# Pipeline-Level 再現性機制設計

**任務 ID**: design-improvements-002  
**建立日期**: 2025-12-30  
**狀態**: 設計中  
**優先級**: 高

---

## 問題描述

### 現況
- 有 `results/<exp_id>/meta.json` 記錄部分 metadata
- 缺少 **pipeline-level** 的 seed/依賴版本/資料快照鎖定
- 回測與模型重跑時無法保證完全一致性
- Phase 8 未上線，風險持續存在

### 影響
- 無法 100% 重現歷史實驗結果
- 研究結論可信度受質疑
- 除錯困難（無法確定是程式碼變更還是資料變更導致結果差異）
- 不符合學術/業界標準（reproducible research）

---

## 設計目標

### 核心原則（基於 AGENTS.md）
1. **Physics Gate 優先**：資料快照需保留完整時間戳與量綱資訊
2. **再現性保障**：任何實驗必須可在未來環境 100% 重現
3. **觀測性優先**：重現失敗必須有明確診斷資訊
4. **不破壞 Userspace**：漸進式導入，不影響現有實驗

### 驗收標準
- [ ] 實驗可通過 experiment_id 完全重現（資料+程式碼+環境）
- [ ] Random seed 統一管理（Python/NumPy/PyTorch/TensorFlow）
- [ ] 依賴版本鎖定（pip freeze + conda env export）
- [ ] 資料快照可追溯（DB snapshot 或 DVC）
- [ ] 重現失敗時有明確錯誤訊息（哪個環節不一致）

---

## 階段性實施方案

### Phase 8.1: Seed Management（1 天，低風險）

#### 目標
集中管理所有隨機種子，確保可重現。

#### 實作內容

**1. 建立 Seed Manager**

```python
# shared/utils/seed_manager.py

import random
import numpy as np
import torch
import os
import logging

logger = logging.getLogger(__name__)

class SeedManager:
    """統一管理所有隨機種子，確保可重現性"""
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self._set_all_seeds()
    
    def _set_all_seeds(self):
        """設置所有常用庫的隨機種子"""
        # Python built-in random
        random.seed(self.seed)
        
        # NumPy
        np.random.seed(self.seed)
        
        # PyTorch (if installed)
        try:
            torch.manual_seed(self.seed)
            torch.cuda.manual_seed_all(self.seed)
            # 確保 CUDA 計算可重現（可能影響效能）
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
            logger.info(f"PyTorch seed set to {self.seed}")
        except ImportError:
            pass
        
        # TensorFlow (if installed)
        try:
            import tensorflow as tf
            tf.random.set_seed(self.seed)
            logger.info(f"TensorFlow seed set to {self.seed}")
        except ImportError:
            pass
        
        # 環境變數（某些庫依賴）
        os.environ['PYTHONHASHSEED'] = str(self.seed)
        
        logger.info(f"All random seeds set to {self.seed}")
    
    def get_seed(self) -> int:
        """取得當前 seed"""
        return self.seed
    
    @classmethod
    def from_experiment_config(cls, config: dict):
        """從實驗配置創建"""
        return cls(seed=config.get('random_seed', 42))
```

**2. 整合到實驗流程**

```python
# data-analyzer/src/backtesting/backtest_engine.py

from shared.utils.seed_manager import SeedManager

class BacktestEngine:
    def run(self, strategy, data, config):
        # 1. 初始化 seed（在所有隨機操作之前）
        seed_mgr = SeedManager(seed=config.get('random_seed', 42))
        
        # 2. 記錄 seed 到 manifest
        manifest = PipelineManifest(
            pipeline_id=...,
            random_seed=seed_mgr.get_seed(),
            ...
        )
        
        # 3. 執行回測（所有隨機操作都可重現）
        results = strategy.backtest(data)
        
        return results
```

---

### Phase 8.2: Dependency Lockfile（1 天，低風險）

#### 目標
鎖定所有依賴版本，確保環境可重建。

#### 實作內容

**1. 自動生成依賴鎖定檔**

```python
# shared/utils/dependency_manager.py

import subprocess
import json
import os
from pathlib import Path

class DependencyManager:
    """管理依賴版本鎖定"""
    
    @staticmethod
    def capture_environment(output_dir: str):
        """捕獲當前環境的所有依賴"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. pip freeze
        pip_freeze = subprocess.check_output(['pip', 'freeze']).decode('utf-8')
        with open(f"{output_dir}/requirements.lock.txt", 'w') as f:
            f.write(pip_freeze)
        
        # 2. conda env export (if in conda)
        try:
            conda_env = subprocess.check_output(['conda', 'env', 'export']).decode('utf-8')
            with open(f"{output_dir}/conda_env.yml", 'w') as f:
                f.write(conda_env)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # Not in conda environment
        
        # 3. Python version
        python_version = subprocess.check_output(['python', '--version']).decode('utf-8')
        
        # 4. System info
        import platform
        system_info = {
            "python_version": python_version.strip(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }
        
        with open(f"{output_dir}/system_info.json", 'w') as f:
            json.dump(system_info, f, indent=2)
        
        return {
            "pip_freeze": f"{output_dir}/requirements.lock.txt",
            "conda_env": f"{output_dir}/conda_env.yml" if Path(f"{output_dir}/conda_env.yml").exists() else None,
            "system_info": f"{output_dir}/system_info.json"
        }
    
    @staticmethod
    def verify_environment(lockfile_dir: str) -> tuple[bool, list[str]]:
        """驗證當前環境是否與鎖定檔一致"""
        issues = []
        
        # 1. 比對 pip freeze
        lockfile_path = f"{lockfile_dir}/requirements.lock.txt"
        if os.path.exists(lockfile_path):
            with open(lockfile_path) as f:
                expected_packages = set(f.read().strip().split('\n'))
            
            current_packages = set(subprocess.check_output(['pip', 'freeze']).decode('utf-8').strip().split('\n'))
            
            missing = expected_packages - current_packages
            extra = current_packages - expected_packages
            
            if missing:
                issues.append(f"Missing packages: {len(missing)} packages")
            if extra:
                issues.append(f"Extra packages: {len(extra)} packages")
        
        # 2. 檢查 Python 版本
        system_info_path = f"{lockfile_dir}/system_info.json"
        if os.path.exists(system_info_path):
            with open(system_info_path) as f:
                expected_info = json.load(f)
            
            current_python = subprocess.check_output(['python', '--version']).decode('utf-8').strip()
            if expected_info['python_version'] != current_python:
                issues.append(f"Python version mismatch: expected {expected_info['python_version']}, got {current_python}")
        
        return len(issues) == 0, issues
```

**2. 整合到實驗流程**

```python
class BacktestEngine:
    def run(self, strategy, data, config):
        # 1. 捕獲依賴環境
        dep_mgr = DependencyManager()
        dep_files = dep_mgr.capture_environment(f"results/{manifest.pipeline_id}/dependencies")
        
        # 2. 記錄到 manifest
        manifest.dependencies = dep_files
        
        # ...
```

---

### Phase 8.3: Data Snapshot Locking（2-3 天，中風險）

#### 目標
鎖定實驗使用的資料版本，支援時間點查詢。

#### 實作策略

**方案 A: 輕量級 - SQL Snapshot ID（推薦）**

```sql
-- 新增欄位到 ohlcv 等表
ALTER TABLE ohlcv ADD COLUMN data_snapshot_id VARCHAR(32);

-- 建立 snapshot 管理表
CREATE TABLE data_snapshots (
    snapshot_id VARCHAR(32) PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    description TEXT,
    tables JSONB NOT NULL,  -- {"ohlcv": {"min_timestamp": "...", "max_timestamp": "..."}}
    row_counts JSONB NOT NULL,
    checksum VARCHAR(64)
);
```

```python
# shared/utils/data_snapshot_manager.py

import hashlib
from datetime import datetime

class DataSnapshotManager:
    """輕量級資料快照管理（只記錄 metadata，不複製資料）"""
    
    @staticmethod
    def create_snapshot(db, tables: list[str], description: str = "") -> str:
        """創建資料快照（只記錄 metadata）"""
        snapshot_id = hashlib.md5(f"{datetime.now().isoformat()}_{description}".encode()).hexdigest()[:16]
        
        snapshot_meta = {
            "tables": {},
            "row_counts": {}
        }
        
        for table in tables:
            # 記錄時間範圍
            result = db.execute(f"""
                SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
                FROM {table}
            """).fetchone()
            
            snapshot_meta["tables"][table] = {
                "min_timestamp": result[0].isoformat() if result[0] else None,
                "max_timestamp": result[1].isoformat() if result[1] else None
            }
            snapshot_meta["row_counts"][table] = result[2]
        
        # 寫入 snapshot 表
        db.execute("""
            INSERT INTO data_snapshots (snapshot_id, created_at, description, tables, row_counts)
            VALUES (%s, %s, %s, %s, %s)
        """, (snapshot_id, datetime.now(), description, json.dumps(snapshot_meta["tables"]), json.dumps(snapshot_meta["row_counts"])))
        
        return snapshot_id
    
    @staticmethod
    def load_snapshot(db, snapshot_id: str, table: str, time_range: tuple = None):
        """從 snapshot 載入資料（時間範圍查詢）"""
        # 取得 snapshot metadata
        snapshot = db.execute("""
            SELECT tables FROM data_snapshots WHERE snapshot_id = %s
        """, (snapshot_id,)).fetchone()
        
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        table_meta = json.loads(snapshot[0])[table]
        
        # 查詢該時間範圍的資料
        query = f"""
            SELECT * FROM {table}
            WHERE timestamp BETWEEN %s AND %s
            ORDER BY timestamp
        """
        
        return db.execute(query, (table_meta["min_timestamp"], table_meta["max_timestamp"])).fetchall()
```

**方案 B: 重量級 - DVC (Data Version Control)（可選）**

```bash
# 安裝 DVC
pip install dvc dvc-s3

# 初始化 DVC
cd data-analyzer
dvc init

# 追蹤大型資料檔案
dvc add results/exp_001/features.parquet
git add results/exp_001/features.parquet.dvc

# 版本綁定
git commit -m "Experiment 001: Add features dataset"
git tag exp-001

# 未來重現
git checkout exp-001
dvc pull
```

**整合到實驗流程**

```python
class BacktestEngine:
    def run(self, strategy, data, config):
        # 方案 A: 創建輕量級 snapshot
        snapshot_mgr = DataSnapshotManager()
        snapshot_id = snapshot_mgr.create_snapshot(
            db=self.db,
            tables=["ohlcv", "trades"],
            description=f"Backtest {manifest.pipeline_id}"
        )
        
        # 記錄到 manifest
        manifest.data_snapshot_id = snapshot_id
        
        # 執行回測（使用 snapshot 的資料）
        data = snapshot_mgr.load_snapshot(self.db, snapshot_id, "ohlcv")
        results = strategy.backtest(data)
        
        return results
```

---

### Phase 8.4: Git Integration（1 天，低風險）

#### 目標
記錄實驗執行時的 Git commit，確保程式碼可追溯。

#### 實作內容

```python
# shared/utils/git_manager.py

import subprocess
import os

class GitManager:
    """Git 資訊管理"""
    
    @staticmethod
    def get_current_commit() -> str:
        """取得當前 Git commit hash"""
        try:
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
            return commit
        except subprocess.CalledProcessError:
            return "unknown"
    
    @staticmethod
    def is_dirty() -> bool:
        """檢查是否有未提交變更"""
        try:
            result = subprocess.check_output(['git', 'status', '--porcelain']).decode('utf-8')
            return len(result.strip()) > 0
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def get_git_info() -> dict:
        """取得完整 Git 資訊"""
        return {
            "commit_hash": GitManager.get_current_commit(),
            "is_dirty": GitManager.is_dirty(),
            "branch": subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode('utf-8').strip()
        }
```

**整合到 PipelineManifest**

```python
class PipelineManifest(BaseModel):
    # ... existing fields ...
    
    git_info: Optional[Dict[str, str]] = None
    
    @classmethod
    def create(cls, ...):
        # 自動捕獲 Git 資訊
        git_info = GitManager.get_git_info()
        
        if git_info['is_dirty']:
            logger.warning("⚠️ Git working directory is dirty! Results may not be reproducible.")
        
        return cls(
            ...,
            git_info=git_info
        )
```

---

### Phase 8.5: Reproducibility Verification（1 天，低風險）

#### 目標
提供工具驗證實驗是否可重現。

#### 實作內容

```python
# scripts/verify_reproducibility.py

import argparse
import json
from pathlib import Path
from shared.utils.data_snapshot_manager import DataSnapshotManager
from shared.utils.dependency_manager import DependencyManager
from shared.utils.git_manager import GitManager

def verify_experiment_reproducibility(exp_id: str):
    """驗證實驗是否可重現"""
    exp_dir = Path(f"results/{exp_id}")
    
    # 1. 載入 manifest
    manifest_path = exp_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"❌ Manifest not found: {manifest_path}")
        return False
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    issues = []
    
    # 2. 驗證 Git commit
    current_commit = GitManager.get_current_commit()
    if manifest.get('git_info', {}).get('commit_hash') != current_commit:
        issues.append(f"Git commit mismatch: expected {manifest['git_info']['commit_hash']}, current {current_commit}")
    
    # 3. 驗證依賴環境
    dep_dir = exp_dir / "dependencies"
    if dep_dir.exists():
        dep_ok, dep_issues = DependencyManager.verify_environment(str(dep_dir))
        if not dep_ok:
            issues.extend(dep_issues)
    
    # 4. 驗證資料 snapshot（檢查是否存在）
    snapshot_id = manifest.get('data_snapshot_id')
    if snapshot_id:
        # 檢查 DB 是否有該 snapshot
        from shared.utils.db_manager import get_db_connection
        db = get_db_connection()
        snapshot_exists = db.execute("SELECT 1 FROM data_snapshots WHERE snapshot_id = %s", (snapshot_id,)).fetchone()
        if not snapshot_exists:
            issues.append(f"Data snapshot not found: {snapshot_id}")
    
    # 5. 輸出驗證結果
    if issues:
        print(f"❌ Experiment {exp_id} is NOT reproducible:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print(f"✅ Experiment {exp_id} is reproducible")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("exp_id", help="Experiment ID to verify")
    args = parser.parse_args()
    
    verify_experiment_reproducibility(args.exp_id)
```

**使用範例**

```bash
# 驗證實驗是否可重現
python scripts/verify_reproducibility.py backtest_20251230_165500

# 輸出：
# ✅ Experiment backtest_20251230_165500 is reproducible
#    - Git commit: a1b2c3d (clean)
#    - Dependencies: 50/50 packages match
#    - Data snapshot: snapshot_abc123 exists
```

---

## 完整實驗流程範例

```python
# 範例：執行一個可重現的回測實驗

from shared.utils.seed_manager import SeedManager
from shared.utils.dependency_manager import DependencyManager
from shared.utils.data_snapshot_manager import DataSnapshotManager
from shared.utils.git_manager import GitManager
from data_registry import PipelineManifest

def run_reproducible_backtest(strategy, config):
    # 1. 設置隨機種子
    seed_mgr = SeedManager(seed=config['random_seed'])
    
    # 2. 創建資料 snapshot
    snapshot_mgr = DataSnapshotManager()
    snapshot_id = snapshot_mgr.create_snapshot(
        db=get_db_connection(),
        tables=["ohlcv", "features"],
        description=f"Backtest {config['strategy_name']}"
    )
    
    # 3. 捕獲 Git 資訊
    git_info = GitManager.get_git_info()
    if git_info['is_dirty']:
        raise RuntimeError("⚠️ Git working directory is dirty! Commit changes first.")
    
    # 4. 捕獲依賴環境
    dep_mgr = DependencyManager()
    exp_id = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    dep_files = dep_mgr.capture_environment(f"results/{exp_id}/dependencies")
    
    # 5. 創建 manifest
    manifest = PipelineManifest(
        pipeline_id=exp_id,
        execution_timestamp=datetime.now(),
        random_seed=seed_mgr.get_seed(),
        data_snapshot_id=snapshot_id,
        git_info=git_info,
        dependencies=dep_files,
        data_source={"exchange": "bybit", "schema_version": "v1"},
        features={"technical_indicators_v2": "v2"}
    )
    
    # 6. 執行回測
    data = snapshot_mgr.load_snapshot(get_db_connection(), snapshot_id, "ohlcv")
    results = strategy.backtest(data)
    
    # 7. 儲存 manifest
    manifest.save(f"results/{exp_id}/manifest.json")
    
    # 8. 驗證可重現性
    verify_experiment_reproducibility(exp_id)
    
    return results
```

---

## 驗收標準

### Phase 8.1-8.4 完成後
- [ ] 任何實驗自動生成完整 manifest（seed/git/deps/snapshot）
- [ ] 可透過 `verify_reproducibility.py` 驗證任何歷史實驗
- [ ] Git dirty 狀態會阻止實驗執行（或至少警告）
- [ ] 所有隨機操作使用統一 seed

### 重現性測試
- [ ] 選擇一個歷史實驗，重新執行應得到**相同結果**（誤差 < 1e-6）
- [ ] 在不同機器上重現（只要依賴環境一致）

---

## 風險評估

| 風險 | 機率 | 影響 | 緩解措施 |
|------|------|------|---------|
| Snapshot 機制影響查詢效能 | 中 | 低 | 使用輕量級方案 A（只記錄 metadata） |
| 依賴鎖定過於嚴格 | 低 | 中 | 提供 `--skip-dep-check` 選項 |
| Git dirty 阻斷研發流程 | 高 | 低 | 改為警告而非錯誤 |
| 不同平台 PyTorch/TF 結果仍有差異 | 中 | 中 | 文檔說明跨平台限制 |

---

## 時間估算

- **Phase 8.1**: 1 天（Seed Manager）
- **Phase 8.2**: 1 天（Dependency Lockfile）
- **Phase 8.3**: 2-3 天（Data Snapshot，選擇方案 A）
- **Phase 8.4**: 1 天（Git Integration）
- **Phase 8.5**: 1 天（Verification Tool）
- **總計**: 6-8 天

---

## 後續擴展

### Phase 8.6（可選）
- 整合 MLflow Tracking（替代自建 manifest）
- 建立實驗比較 UI（視覺化 diff manifests）
- 自動化重現測試（CI/CD pipeline）

---

**最後更新**: 2025-12-30  
**狀態**: 設計完成，待 Reviewer 審查
