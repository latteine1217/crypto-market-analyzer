# 資料契約與版本化設計（Data Contract & Versioning）

**任務 ID**: design-improvements-001  
**建立日期**: 2025-12-30  
**狀態**: 設計中  
**優先級**: 高

---

## 問題描述

### 現況
- Collector/Analyzer/Strategy/Report 各層無強制資料契約
- schema/feature/version 資訊未標準化
- 依賴文件規範而非機制保證
- 跨階段資料不一致風險高

### 影響
- 回測結果可能因資料版本不一致而無法重現
- Feature 變更無法追溯影響範圍
- 模型與資料版本綁定鬆散
- 除錯時難以定位資料來源與版本

---

## 設計目標

### 核心原則（基於 AGENTS.md）
1. **Physics Gate 優先**：資料契約需保證量綱一致性
2. **再現性保障**：所有資料必須可追溯版本與來源
3. **觀測性優先**：契約驗證失敗必須有清晰日誌
4. **不破壞 Userspace**：漸進式導入，不影響現有流程

### 驗收標準
- [ ] 資料 schema 變更可被追蹤（schema_version）
- [ ] Feature 計算邏輯變更可被檢測（logic_hash）
- [ ] 回測/報表可驗證輸入資料版本一致性
- [ ] 不相容情況下有明確錯誤訊息
- [ ] 無需修改現有 DB schema（新增 metadata 表）

---

## 階段性實施方案

### Phase 8A: Schema Registry（2-3 天，低風險）

#### 目標
建立集中式資料契約定義，不影響現有流程。

#### 實作內容

**1. 建立 Schema Registry 模組**

```python
# shared/utils/data_registry.py

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Literal
from datetime import datetime
import hashlib
import json

# ===== 資料層 Schema 定義 =====

class OHLCVSchema(BaseModel):
    """OHLCV 資料契約 - v1"""
    schema_version: Literal["v1"] = "v1"
    timestamp: datetime
    symbol: str
    exchange: str
    timeframe: str
    open: float = Field(gt=0, description="開盤價（必須 > 0）")
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0, description="成交量（必須 ≥ 0）")
    
    @validator('high')
    def high_gte_low(cls, v, values):
        if 'low' in values and v < values['low']:
            raise ValueError('high 必須 >= low')
        return v
    
    @validator('high')
    def high_gte_open_close(cls, v, values):
        if 'open' in values and 'close' in values:
            if v < values['open'] or v < values['close']:
                raise ValueError('high 必須 >= open 和 close')
        return v

class FeatureVectorSchema(BaseModel):
    """特徵向量契約 - v2"""
    schema_version: Literal["v2"] = "v2"
    feature_set_name: str  # 如 "technical_indicators_v2"
    feature_names: List[str]
    feature_values: List[float]
    computation_hash: str  # 計算邏輯 hash
    source_data_version: str  # 來源資料版本
    timestamp: datetime
    
    @validator('feature_values')
    def check_length_match(cls, v, values):
        if 'feature_names' in values and len(v) != len(values['feature_names']):
            raise ValueError('feature_values 長度必須與 feature_names 一致')
        return v

class ModelPredictionSchema(BaseModel):
    """模型預測輸出契約"""
    model_id: str
    model_version: str
    prediction_type: Literal["classification", "regression"]
    predicted_value: float
    confidence_score: Optional[float]
    feature_version: str  # 使用的 feature 版本
    timestamp: datetime

# ===== Schema 相容性檢查 =====

class SchemaRegistry:
    """Schema 註冊與相容性管理"""
    
    _schemas = {
        "ohlcv": {"v1": OHLCVSchema},
        "features": {"v1": None, "v2": FeatureVectorSchema},  # v1 deprecated
        "predictions": {"v1": ModelPredictionSchema},
    }
    
    @classmethod
    def get_schema(cls, data_type: str, version: str):
        """取得特定版本的 schema"""
        if data_type not in cls._schemas:
            raise ValueError(f"Unknown data type: {data_type}")
        if version not in cls._schemas[data_type]:
            raise ValueError(f"Unknown version {version} for {data_type}")
        return cls._schemas[data_type][version]
    
    @classmethod
    def validate(cls, data: Dict, data_type: str, version: str):
        """驗證資料符合 schema"""
        schema_cls = cls.get_schema(data_type, version)
        if schema_cls is None:
            raise ValueError(f"{data_type} v{version} is deprecated")
        return schema_cls(**data)  # pydantic 自動驗證
    
    @classmethod
    def is_compatible(cls, from_version: str, to_version: str, data_type: str) -> bool:
        """檢查版本相容性（向後相容）"""
        # 實作規則：新版本需支援舊版本欄位（可加欄位但不可刪除）
        # 簡化版：v1 -> v2 相容，v2 -> v1 不相容
        version_order = {"v1": 1, "v2": 2, "v3": 3}
        return version_order.get(from_version, 0) <= version_order.get(to_version, 0)

# ===== Feature Computation Hash =====

def compute_feature_logic_hash(code: str) -> str:
    """計算 feature 計算邏輯的 hash（用於追蹤變更）"""
    return hashlib.sha256(code.encode()).hexdigest()[:16]

# ===== Pipeline Manifest =====

class PipelineManifest(BaseModel):
    """Pipeline 執行時的資料版本清單"""
    pipeline_id: str
    execution_timestamp: datetime
    
    # 資料來源
    data_source: Dict[str, str] = Field(
        description="交易所、交易對、時間框架、schema 版本"
    )
    
    # 特徵資訊
    features: Dict[str, str] = Field(
        description="feature_set_name → version 映射"
    )
    
    # 模型資訊
    model: Optional[Dict[str, str]] = Field(
        description="model_id, version, hyperparams_hash"
    )
    
    # Git 資訊（可選）
    git_commit: Optional[str] = None
    
    def save(self, path: str):
        """儲存為 JSON"""
        with open(path, 'w') as f:
            json.dump(self.dict(), f, indent=2, default=str)
    
    @classmethod
    def load(cls, path: str):
        """從 JSON 載入"""
        with open(path) as f:
            return cls(**json.load(f))
    
    def is_compatible_with(self, other: "PipelineManifest") -> tuple[bool, List[str]]:
        """檢查與另一個 manifest 是否相容"""
        issues = []
        
        # 檢查資料來源
        if self.data_source.get("schema_version") != other.data_source.get("schema_version"):
            issues.append(f"Data schema mismatch: {self.data_source.get('schema_version')} vs {other.data_source.get('schema_version')}")
        
        # 檢查特徵版本
        for feat_name, feat_ver in self.features.items():
            if feat_name in other.features and other.features[feat_name] != feat_ver:
                issues.append(f"Feature '{feat_name}' version mismatch: {feat_ver} vs {other.features[feat_name]}")
        
        return len(issues) == 0, issues
```

**2. 建立 Metadata 表（新增，不影響現有表）**

```sql
-- database/schemas/03_data_versioning.sql

-- Schema 版本記錄
CREATE TABLE IF NOT EXISTS data_schema_versions (
    id SERIAL PRIMARY KEY,
    data_type VARCHAR(50) NOT NULL,  -- 'ohlcv', 'features', 'predictions'
    version VARCHAR(10) NOT NULL,
    schema_definition JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deprecated BOOLEAN DEFAULT FALSE,
    UNIQUE(data_type, version)
);

-- Feature 計算邏輯版本
CREATE TABLE IF NOT EXISTS feature_versions (
    id SERIAL PRIMARY KEY,
    feature_set_name VARCHAR(100) NOT NULL,
    version VARCHAR(10) NOT NULL,
    feature_names TEXT[] NOT NULL,
    computation_logic_hash VARCHAR(32) NOT NULL,
    dependencies JSONB,  -- {"ohlcv_version": "v1", "lookback_period": 20}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deprecated BOOLEAN DEFAULT FALSE,
    UNIQUE(feature_set_name, version)
);

-- Pipeline 執行清單（再現性追蹤）
CREATE TABLE IF NOT EXISTS pipeline_manifests (
    id SERIAL PRIMARY KEY,
    pipeline_id VARCHAR(100) NOT NULL,
    execution_timestamp TIMESTAMPTZ NOT NULL,
    data_source JSONB NOT NULL,
    features JSONB NOT NULL,
    model JSONB,
    git_commit VARCHAR(40),
    manifest_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pipeline_manifests_pipeline_id ON pipeline_manifests(pipeline_id);
CREATE INDEX idx_pipeline_manifests_execution_timestamp ON pipeline_manifests(execution_timestamp);
```

**3. 使用範例**

```python
# 範例 1：Collector 寫入資料時驗證
from shared.utils.data_registry import SchemaRegistry, OHLCVSchema

def save_ohlcv(data: dict):
    # 驗證資料符合 schema
    try:
        validated = SchemaRegistry.validate(data, "ohlcv", "v1")
        # 寫入 DB
        db.execute("INSERT INTO ohlcv ...")
    except ValidationError as e:
        logger.error(f"OHLCV schema validation failed: {e}")
        # 寫入錯誤表
        db.execute("INSERT INTO data_quality_issues ...")

# 範例 2：Analyzer 生成 feature 時記錄版本
from shared.utils.data_registry import compute_feature_logic_hash

def generate_features(ohlcv_data):
    # 計算 features
    features = technical_indicators.compute(ohlcv_data)
    
    # 記錄 feature 版本
    logic_code = inspect.getsource(technical_indicators.compute)
    logic_hash = compute_feature_logic_hash(logic_code)
    
    db.execute("""
        INSERT INTO feature_versions (feature_set_name, version, feature_names, computation_logic_hash)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (feature_set_name, version) DO NOTHING
    """, ("technical_indicators_v2", "v2", list(features.keys()), logic_hash))
    
    return features

# 範例 3：Strategy 回測時檢查 manifest 相容性
from shared.utils.data_registry import PipelineManifest

def run_backtest(strategy, start_date, end_date):
    # 載入訓練時的 manifest
    train_manifest = PipelineManifest.load("results/exp_001/manifest.json")
    
    # 生成當前 manifest
    current_manifest = PipelineManifest(
        pipeline_id="backtest_20251230",
        execution_timestamp=datetime.now(),
        data_source={"exchange": "bybit", "schema_version": "v1"},
        features={"technical_indicators_v2": "v2"},
        model={"model_id": "xgboost_001", "version": "v1"}
    )
    
    # 檢查相容性
    compatible, issues = current_manifest.is_compatible_with(train_manifest)
    if not compatible:
        raise IncompatiblePipelineError(f"Pipeline不相容: {issues}")
    
    # 執行回測
    results = strategy.backtest(...)
    
    # 儲存 manifest
    current_manifest.save("results/backtest_20251230/manifest.json")
```

---

### Phase 8B: Versioned Feature Store（3-4 天，中風險）

#### 目標
將 feature 版本資訊與資料綁定，確保可追溯。

#### 實作內容

**1. 修改 Analyzer 輸出介面**

```python
# data-analyzer/src/features/feature_engine.py

class FeatureEngine:
    def __init__(self, feature_set_name: str, version: str):
        self.feature_set_name = feature_set_name
        self.version = version
        self._register_version()
    
    def _register_version(self):
        """註冊 feature 版本到 DB"""
        logic_hash = compute_feature_logic_hash(inspect.getsource(self.compute))
        db.execute("""
            INSERT INTO feature_versions (...)
            ON CONFLICT DO NOTHING
        """)
    
    def compute(self, ohlcv_data) -> pd.DataFrame:
        """計算 features，並附加 metadata"""
        features_df = self._compute_features(ohlcv_data)
        
        # 附加版本資訊（作為 DataFrame metadata）
        features_df.attrs['feature_set_name'] = self.feature_set_name
        features_df.attrs['version'] = self.version
        features_df.attrs['computation_hash'] = self._get_logic_hash()
        features_df.attrs['source_data_version'] = ohlcv_data.attrs.get('schema_version', 'unknown')
        
        return features_df
```

**2. 修改 Strategy 讀取介面**

```python
# data-analyzer/src/strategies/base_strategy.py

class BaseStrategy:
    def __init__(self, required_features: Dict[str, str]):
        """
        required_features: {"technical_indicators_v2": "v2"}
        """
        self.required_features = required_features
    
    def validate_features(self, features_df: pd.DataFrame):
        """驗證 features 版本"""
        actual_feature_set = features_df.attrs.get('feature_set_name')
        actual_version = features_df.attrs.get('version')
        
        for feat_name, required_version in self.required_features.items():
            if actual_feature_set != feat_name:
                raise ValueError(f"Expected {feat_name}, got {actual_feature_set}")
            if actual_version != required_version:
                raise ValueError(f"Feature version mismatch: expected {required_version}, got {actual_version}")
```

---

### Phase 8C: Pipeline Manifest 強制檢查（1-2 天，低風險）

#### 目標
回測/報表執行時強制生成與檢查 manifest。

#### 實作內容

```python
# data-analyzer/src/backtesting/backtest_engine.py

class BacktestEngine:
    def run(self, strategy, data, config):
        # 1. 生成 manifest
        manifest = PipelineManifest(
            pipeline_id=f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            execution_timestamp=datetime.now(),
            data_source={
                "exchange": config.exchange,
                "symbols": config.symbols,
                "timeframe": config.timeframe,
                "schema_version": data.attrs.get('schema_version', 'v1')
            },
            features={
                data.attrs.get('feature_set_name'): data.attrs.get('version')
            },
            model=None  # 策略回測不一定用模型
        )
        
        # 2. 檢查是否有參考 manifest（如訓練時的）
        if config.reference_manifest_path:
            ref_manifest = PipelineManifest.load(config.reference_manifest_path)
            compatible, issues = manifest.is_compatible_with(ref_manifest)
            if not compatible:
                logger.error(f"Pipeline不相容: {issues}")
                raise IncompatiblePipelineError(issues)
        
        # 3. 執行回測
        results = strategy.backtest(data)
        
        # 4. 儲存 manifest
        output_dir = f"results/{manifest.pipeline_id}"
        os.makedirs(output_dir, exist_ok=True)
        manifest.save(f"{output_dir}/manifest.json")
        
        return results
```

---

## 驗收標準

### Phase 8A 驗收
- [ ] SchemaRegistry 模組可正確驗證 OHLCV/Feature 資料
- [ ] 不符合 schema 的資料會拋出明確 ValidationError
- [ ] 新增的 3 張 metadata 表 migration 成功
- [ ] 無需修改現有 Collector/Analyzer 程式碼即可測試

### Phase 8B 驗收
- [ ] FeatureEngine 計算時自動寫入 feature_versions 表
- [ ] Feature DataFrame 包含 attrs metadata
- [ ] Strategy 可驗證 feature 版本不一致時拋出錯誤
- [ ] 現有回測流程可正常運行（向後相容）

### Phase 8C 驗收
- [ ] 每次回測自動生成 manifest.json
- [ ] 不相容 manifest 會阻止回測執行
- [ ] manifest 包含完整 data_source/features/model 資訊
- [ ] 可通過 manifest 完全重現回測條件

---

## 風險評估

| 風險 | 機率 | 影響 | 緩解措施 |
|------|------|------|---------|
| pydantic 驗證影響效能 | 中 | 低 | 只在寫入時驗證，讀取時跳過 |
| DataFrame attrs 在某些操作中遺失 | 高 | 中 | 文檔明確說明保留 attrs 的操作方式 |
| 現有程式碼需大幅修改 | 低 | 高 | Phase 8A 完全不影響現有程式碼 |
| Manifest 檢查過於嚴格導致無法執行 | 中 | 中 | 提供 `--skip-manifest-check` 選項 |

---

## 時間估算

- **Phase 8A**: 2-3 天（Schema Registry + Migration）
- **Phase 8B**: 3-4 天（Feature Store 整合）
- **Phase 8C**: 1-2 天（Manifest 強制檢查）
- **總計**: 6-9 天

---

## 後續擴展

### Phase 8D（可選）
- 整合 DVC (Data Version Control) 管理大型資料集版本
- 建立 Feature Store UI 查看所有 feature 版本
- 自動檢測 feature 計算邏輯變更（Git pre-commit hook）

---

**最後更新**: 2025-12-30  
**狀態**: 設計完成，待 Reviewer 審查
