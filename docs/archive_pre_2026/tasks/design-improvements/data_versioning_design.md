# Backfill/品質修正邊界與版本機制設計

**任務 ID**: design-improvements-004  
**建立日期**: 2025-12-30  
**優先級**: 高

---

## 問題描述

### 現況
- 規範說「只標記不刪除」、有 `cleaning_version`
- 但缺少**明確的清洗版本/回溯生效機制**設計
- Backfill 與主流程邊界模糊
- 長期容易出現「同一資料多個版本」爭議

### 影響
- 回測時不確定該用「原始資料」還是「清洗後資料」
- 資料修正後歷史實驗結果失效
- 無法追蹤「這筆資料被修正過幾次」

---

## 設計目標

### 核心原則（基於 AGENTS.md）
1. **Never Break Userspace**：資料修正不破壞現有查詢
2. **再現性保障**：任何版本的資料都可查詢
3. **觀測性優先**：修正歷史可追溯

### 驗收標準
- [ ] 資料有「原始版本」與「清洗版本 v1, v2, ...」
- [ ] 可查詢任意版本的資料（時間旅行）
- [ ] 清洗邏輯變更時自動產生新版本
- [ ] 回測/分析可明確指定資料版本

---

## 實施方案（輕量級）

### Phase 10A: Data Versioning Schema（1 天）

```sql
-- 新增 cleaned_version 欄位（NULL = 原始資料，v1/v2/... = 清洗後）
ALTER TABLE ohlcv ADD COLUMN cleaned_version VARCHAR(10) DEFAULT NULL;
ALTER TABLE trades ADD COLUMN cleaned_version VARCHAR(10) DEFAULT NULL;

-- 建立 cleaning_operations 表（記錄清洗歷史）
CREATE TABLE cleaning_operations (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    version VARCHAR(10) NOT NULL,
    operation_type VARCHAR(50) NOT NULL,  -- 'fill_missing', 'remove_outlier', 'fix_timestamp'
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    affected_rows INT,
    cleaning_logic_hash VARCHAR(32),
    description TEXT
);
```

### Phase 10B: Versioned Data Query Interface（2 天）

```python
# shared/utils/data_version_manager.py

class DataVersionManager:
    """資料版本管理"""
    
    @staticmethod
    def get_data(table: str, version: str = None, **filters):
        """
        取得指定版本的資料
        
        Args:
            table: 表名（如 'ohlcv'）
            version: 資料版本（None=最新, 'raw'=原始, 'v1'=清洗版本1）
            filters: 其他過濾條件（exchange, symbol, timeframe, time_range）
        """
        if version == 'raw':
            # 只取原始資料（cleaned_version IS NULL）
            query = f"SELECT * FROM {table} WHERE cleaned_version IS NULL"
        elif version is None:
            # 預設取最新版本（原始 + 最新清洗）
            latest_version = DataVersionManager.get_latest_version(table)
            query = f"SELECT * FROM {table} WHERE (cleaned_version IS NULL OR cleaned_version = '{latest_version}')"
        else:
            # 取特定版本
            query = f"SELECT * FROM {table} WHERE cleaned_version = '{version}'"
        
        # 加上其他過濾條件
        if filters:
            query += f" AND {build_where_clause(filters)}"
        
        return db.execute(query).fetchall()
    
    @staticmethod
    def apply_cleaning(table: str, new_version: str, cleaning_func, description: str):
        """
        應用清洗邏輯並生成新版本
        
        Args:
            table: 表名
            new_version: 新版本號（如 'v2'）
            cleaning_func: 清洗函數（輸入原始資料，輸出清洗後資料）
            description: 清洗描述
        """
        # 1. 取得原始資料
        raw_data = DataVersionManager.get_data(table, version='raw')
        
        # 2. 應用清洗
        cleaned_data = cleaning_func(raw_data)
        
        # 3. 寫入新版本（INSERT 新記錄，不修改原始資料）
        for row in cleaned_data:
            db.execute(f"""
                INSERT INTO {table} (..., cleaned_version)
                VALUES (..., '{new_version}')
            """)
        
        # 4. 記錄清洗操作
        logic_hash = hashlib.md5(inspect.getsource(cleaning_func).encode()).hexdigest()[:16]
        db.execute("""
            INSERT INTO cleaning_operations (table_name, version, operation_type, affected_rows, cleaning_logic_hash, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (table, new_version, 'custom', len(cleaned_data), logic_hash, description))
```

**使用範例**

```python
# 範例 1：回測時指定資料版本
data_raw = DataVersionManager.get_data('ohlcv', version='raw', symbol='BTC/USDT')
data_v1 = DataVersionManager.get_data('ohlcv', version='v1', symbol='BTC/USDT')

# 範例 2：應用新的清洗邏輯
def remove_outliers(data):
    # 移除價格異常的資料點
    return data[data['close'] < data['close'].quantile(0.99)]

DataVersionManager.apply_cleaning(
    table='ohlcv',
    new_version='v2',
    cleaning_func=remove_outliers,
    description='Remove top 1% price outliers'
)
```

---

### Phase 10C: Backfill 邊界明確化（1 天）

**原則**：
- Backfill **只寫入原始資料**（`cleaned_version = NULL`）
- 不應用任何清洗邏輯
- 清洗由專門的 `data_cleaning_pipeline` 負責

```python
# collector-py/src/schedulers/backfill_scheduler.py

class BackfillScheduler:
    def backfill_ohlcv(self, exchange, symbol, start, end):
        """補資料：只寫入原始資料"""
        data = fetch_historical_data(exchange, symbol, start, end)
        
        for row in data:
            db.execute("""
                INSERT INTO ohlcv (..., cleaned_version)
                VALUES (..., NULL)  -- 原始資料
                ON CONFLICT (exchange, symbol, timestamp, timeframe) DO NOTHING
            """)
```

---

## 驗收標準

- [ ] 可查詢 `raw` 版本（原始資料）和 `v1, v2, ...`（清洗版本）
- [ ] 清洗操作有完整歷史記錄（`cleaning_operations` 表）
- [ ] Backfill 只寫入原始資料（`cleaned_version = NULL`）
- [ ] 回測可明確指定資料版本（在 config 中）

---

**時間估算**: 4 天  
**狀態**: 設計完成，待審查
