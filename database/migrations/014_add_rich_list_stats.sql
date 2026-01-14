-- ============================================
-- Migration 014: Rich List Stats (Top N Holders)
-- ============================================

CREATE TABLE IF NOT EXISTS rich_list_stats (
    id                  BIGSERIAL,
    snapshot_date       TIMESTAMPTZ NOT NULL,
    blockchain_id       INT NOT NULL REFERENCES blockchains(id) ON DELETE CASCADE,
    symbol              TEXT NOT NULL,              -- 'BTC', etc.
    
    -- 分組 (e.g., 'Top 10', 'Top 100', 'Top 1000')
    rank_group          TEXT NOT NULL,
    
    -- 統計數據
    address_count       BIGINT,                     -- 該組地址數 (e.g. 10, 90, 900) - Note: BitInfoCharts distincts ranges
    total_balance       NUMERIC(30, 8),             -- 總持倉量
    total_balance_usd   NUMERIC(30, 2),             -- 總美元價值
    percentage_of_supply NUMERIC(10, 4),            -- 佔總供應量百分比
    
    -- 變動數據 (從來源獲取或計算)
    balance_change_24h  NUMERIC(30, 8),
    
    -- 元數據
    data_source         TEXT DEFAULT 'bitinfocharts',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (blockchain_id, snapshot_date, rank_group)
);

-- 轉換為 TimescaleDB Hypertable
SELECT create_hypertable(
    'rich_list_stats',
    'snapshot_date',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_rich_list_lookup 
    ON rich_list_stats (blockchain_id, symbol, rank_group, snapshot_date DESC);
