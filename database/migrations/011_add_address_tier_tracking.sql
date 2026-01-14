-- ============================================
-- Migration 011: BTC 地址分層追蹤功能
-- ============================================
-- 目的：追蹤不同持幣量級別地址的分布與每日變動
-- 資料來源：Glassnode API
-- 支援區塊鏈：BTC（架構支援未來擴展）

-- ============================================
-- 1. 地址分層定義表
-- ============================================

CREATE TABLE IF NOT EXISTS address_tiers (
    id              SERIAL PRIMARY KEY,
    tier_name       TEXT NOT NULL UNIQUE,       -- '0-1', '1-10', '10-100', '100-1K', '1K-10K', '10K+'
    min_balance     NUMERIC(30, 8) NOT NULL,    -- 最小持幣量（含）
    max_balance     NUMERIC(30, 8),             -- 最大持幣量（不含，NULL 表示無上限）
    display_order   INT NOT NULL,               -- 顯示順序
    description     TEXT,                       -- 描述
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 插入 BTC 常用分層（簡化版：4 層）
INSERT INTO address_tiers (tier_name, min_balance, max_balance, display_order, description) VALUES
    ('0-1', 0, 1, 1, 'Small holders (< 1 BTC)'),
    ('1-10', 1, 10, 2, 'Medium holders (1-10 BTC)'),
    ('10-100', 10, 100, 3, 'Large holders (10-100 BTC)'),
    ('100+', 100, NULL, 4, 'Whales (100+ BTC)')
ON CONFLICT (tier_name) DO NOTHING;

-- ============================================
-- 2. 地址分層快照表（時序數據）
-- ============================================

CREATE TABLE IF NOT EXISTS address_tier_snapshots (
    id                  BIGSERIAL,
    snapshot_date       TIMESTAMPTZ NOT NULL,       -- 快照日期（UTC 00:00）
    blockchain_id       INT NOT NULL REFERENCES blockchains(id) ON DELETE CASCADE,
    tier_id             INT NOT NULL REFERENCES address_tiers(id),
    
    -- 地址統計
    address_count       BIGINT NOT NULL DEFAULT 0,  -- 該層級地址數量
    
    -- 餘額統計
    total_balance       NUMERIC(30, 8) NOT NULL DEFAULT 0,  -- 該層級總持幣量
    avg_balance         NUMERIC(30, 8),             -- 平均持幣量
    
    -- 每日變動
    balance_change_24h  NUMERIC(30, 8),             -- 24小時持幣量變動
    address_change_24h  BIGINT,                     -- 24小時地址數量變動
    
    -- 百分比統計
    balance_pct         NUMERIC(5, 2),              -- 佔總流通量百分比
    address_pct         NUMERIC(5, 2),              -- 佔總地址數百分比
    
    -- 資料來源
    data_source         TEXT DEFAULT 'glassnode',   -- 'glassnode', 'blockchain.com', 'calculated'
    data_quality        TEXT DEFAULT 'normal',      -- 'normal', 'estimated', 'verified'
    
    -- 元數據
    metadata            JSONB,                      -- 額外資訊（API response, etc.）
    
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (blockchain_id, snapshot_date, tier_id)
);

-- 轉換為 TimescaleDB Hypertable（按日分區）
SELECT create_hypertable(
    'address_tier_snapshots',
    'snapshot_date',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

-- ============================================
-- 3. 索引優化
-- ============================================

-- 查詢特定區塊鏈特定日期範圍
CREATE INDEX IF NOT EXISTS idx_tier_snapshots_blockchain_date
    ON address_tier_snapshots (blockchain_id, snapshot_date DESC);

-- 查詢特定分層的歷史趨勢
CREATE INDEX IF NOT EXISTS idx_tier_snapshots_tier_date
    ON address_tier_snapshots (tier_id, snapshot_date DESC);

-- 查詢最大變動（異常檢測）
CREATE INDEX IF NOT EXISTS idx_tier_snapshots_balance_change
    ON address_tier_snapshots (blockchain_id, ABS(balance_change_24h) DESC NULLS LAST);

-- ============================================
-- 4. 連續聚合視圖（每週統計）
-- ============================================

CREATE MATERIALIZED VIEW IF NOT EXISTS address_tier_weekly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('7 days', snapshot_date) AS week_start,
    blockchain_id,
    tier_id,
    
    -- 週統計
    AVG(address_count) AS avg_address_count,
    AVG(total_balance) AS avg_total_balance,
    SUM(balance_change_24h) AS net_balance_change_week,
    
    -- 週極值
    MAX(total_balance) AS max_balance_week,
    MIN(total_balance) AS min_balance_week
    
FROM address_tier_snapshots
GROUP BY week_start, blockchain_id, tier_id
WITH NO DATA;

-- 設定連續聚合刷新策略（每天刷新）
SELECT add_continuous_aggregate_policy(
    'address_tier_weekly',
    start_offset => INTERVAL '14 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================
-- 5. 資料保留策略
-- ============================================

-- 保留 365 天的每日快照（1 年歷史）
SELECT add_retention_policy(
    'address_tier_snapshots',
    INTERVAL '365 days',
    if_not_exists => TRUE
);

-- ============================================
-- 6. 查詢輔助函數
-- ============================================

-- 取得特定日期的地址分層分布（用於終端輸出）
CREATE OR REPLACE FUNCTION get_address_tier_distribution(
    p_blockchain_name TEXT,
    p_date DATE DEFAULT CURRENT_DATE
) RETURNS TABLE (
    tier_name TEXT,
    address_count BIGINT,
    total_balance NUMERIC,
    balance_change_24h NUMERIC,
    balance_pct NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        at.tier_name,
        ats.address_count,
        ats.total_balance,
        ats.balance_change_24h,
        ats.balance_pct
    FROM address_tier_snapshots ats
    JOIN blockchains b ON ats.blockchain_id = b.id
    JOIN address_tiers at ON ats.tier_id = at.id
    WHERE b.name = p_blockchain_name
      AND DATE(ats.snapshot_date) = p_date
    ORDER BY at.display_order;
END;
$$ LANGUAGE plpgsql;

-- 取得最近 N 天的地址分層變動（用於熱力圖）
CREATE OR REPLACE FUNCTION get_address_tier_heatmap_data(
    p_blockchain_name TEXT,
    p_days INT DEFAULT 7
) RETURNS TABLE (
    snapshot_date DATE,
    tier_name TEXT,
    balance_change_24h NUMERIC,
    display_order INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        DATE(ats.snapshot_date) AS snapshot_date,
        at.tier_name,
        ats.balance_change_24h,
        at.display_order
    FROM address_tier_snapshots ats
    JOIN blockchains b ON ats.blockchain_id = b.id
    JOIN address_tiers at ON ats.tier_id = at.id
    WHERE b.name = p_blockchain_name
      AND ats.snapshot_date >= NOW() - (p_days || ' days')::INTERVAL
    ORDER BY ats.snapshot_date DESC, at.display_order;
END;
$$ LANGUAGE plpgsql;

-- 檢測異常流入流出（單日變動超過閾值）
CREATE OR REPLACE FUNCTION detect_tier_anomalies(
    p_blockchain_name TEXT,
    p_start_date DATE,
    p_end_date DATE,
    p_threshold_btc NUMERIC DEFAULT 1000
) RETURNS TABLE (
    snapshot_date DATE,
    tier_name TEXT,
    balance_change_24h NUMERIC,
    severity TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        DATE(ats.snapshot_date) AS snapshot_date,
        at.tier_name,
        ats.balance_change_24h,
        CASE
            WHEN ABS(ats.balance_change_24h) >= p_threshold_btc * 5 THEN 'critical'
            WHEN ABS(ats.balance_change_24h) >= p_threshold_btc * 2 THEN 'high'
            WHEN ABS(ats.balance_change_24h) >= p_threshold_btc THEN 'medium'
            ELSE 'low'
        END AS severity
    FROM address_tier_snapshots ats
    JOIN blockchains b ON ats.blockchain_id = b.id
    JOIN address_tiers at ON ats.tier_id = at.id
    WHERE b.name = p_blockchain_name
      AND DATE(ats.snapshot_date) BETWEEN p_start_date AND p_end_date
      AND ABS(ats.balance_change_24h) >= p_threshold_btc
    ORDER BY ABS(ats.balance_change_24h) DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 7. 觸發器：自動更新 updated_at
-- ============================================

CREATE TRIGGER update_address_tier_snapshots_updated_at
    BEFORE UPDATE ON address_tier_snapshots
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 8. 初始驗證查詢（測試用）
-- ============================================

-- 驗證 schema 是否正確創建
DO $$
BEGIN
    -- 檢查 hypertable
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables 
        WHERE hypertable_name = 'address_tier_snapshots'
    ) THEN
        RAISE EXCEPTION 'address_tier_snapshots hypertable 未成功創建';
    END IF;
    
    -- 檢查連續聚合
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.continuous_aggregates 
        WHERE view_name = 'address_tier_weekly'
    ) THEN
        RAISE WARNING 'address_tier_weekly 連續聚合未成功創建';
    END IF;
    
    -- 檢查函數
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'get_address_tier_distribution'
    ) THEN
        RAISE EXCEPTION 'get_address_tier_distribution 函數未成功創建';
    END IF;
    
    RAISE NOTICE '✅ Migration 011 驗證通過';
END $$;
