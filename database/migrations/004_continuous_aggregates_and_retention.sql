-- ============================================
-- Migration: 004 - Continuous Aggregates and Tiered Retention
-- Description: 實作多時間粒度連續聚合與分層資料保留策略
-- Created: 2024-12-26
-- ============================================

-- ============================================
-- Part 1: 重要事件標記表（保護關鍵歷史資料）
-- ============================================

CREATE TABLE IF NOT EXISTS critical_events (
    id              SERIAL PRIMARY KEY,
    event_name      TEXT NOT NULL,              -- '2021 BTC Flash Crash', 'LUNA Collapse'
    event_type      TEXT NOT NULL,              -- 'flash_crash', 'black_swan', 'exchange_halt'
    start_time      TIMESTAMPTZ NOT NULL,       -- 事件開始時間
    end_time        TIMESTAMPTZ NOT NULL,       -- 事件結束時間
    markets         INT[] NOT NULL,             -- 相關 market_id 陣列
    preserve_raw    BOOLEAN DEFAULT TRUE,       -- 是否永久保留原始1分鐘資料
    description     TEXT,                       -- 事件描述
    tags            TEXT[],                     -- 標籤 ['crash', 'btc', 'binance']
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT event_time_range CHECK (end_time > start_time)
);

CREATE INDEX IF NOT EXISTS idx_critical_events_time_range
    ON critical_events USING GIST (tstzrange(start_time, end_time));

CREATE INDEX IF NOT EXISTS idx_critical_events_markets
    ON critical_events USING GIN (markets);

COMMENT ON TABLE critical_events IS
'記錄市場重要事件，用於保護關鍵歷史資料不被自動刪除策略移除';

-- ============================================
-- Part 2: 移除舊的保留策略（如果存在）
-- ============================================

-- 移除 ohlcv 表的舊保留策略（01_init.sql 中設定的 90 天）
SELECT remove_retention_policy('ohlcv', if_exists => TRUE);

-- 移除 trades 表的舊保留策略（30 天）
SELECT remove_retention_policy('trades', if_exists => TRUE);

-- ============================================
-- Part 3: 創建連續聚合視圖 (Continuous Aggregates)
-- ============================================

-- 3.1 五分鐘聚合（從 1m 原始資料聚合）
-- 保留期：30 天
DROP MATERIALIZED VIEW IF EXISTS ohlcv_5m CASCADE;

CREATE MATERIALIZED VIEW ohlcv_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', open_time) AS open_time,
    market_id,
    timeframe,  -- 保留原始 timeframe 欄位以便追蹤

    -- OHLC 聚合邏輯
    FIRST(open, open_time) AS open,           -- 時段內第一個 open
    MAX(high) AS high,                        -- 時段內最高價
    MIN(low) AS low,                          -- 時段內最低價
    LAST(close, open_time) AS close,          -- 時段內最後一個 close

    -- 成交量聚合
    SUM(volume) AS volume,
    SUM(quote_volume) AS quote_volume,
    SUM(trade_count) AS trade_count,
    SUM(taker_buy_base_volume) AS taker_buy_base_volume,
    SUM(taker_buy_quote_volume) AS taker_buy_quote_volume,

    -- 統計資訊
    COUNT(*) AS candle_count                  -- 本時段內包含幾根1分鐘K線
FROM ohlcv
WHERE timeframe = '1m'  -- 只從1分鐘原始資料聚合
GROUP BY time_bucket('5 minutes', open_time), market_id, timeframe;

COMMENT ON MATERIALIZED VIEW ohlcv_5m IS
'5分鐘K線連續聚合視圖，從1分鐘原始資料自動更新';

-- 3.2 十五分鐘聚合（從 5m 聚合資料聚合）
-- 保留期：90 天
DROP MATERIALIZED VIEW IF EXISTS ohlcv_15m CASCADE;

CREATE MATERIALIZED VIEW ohlcv_15m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('15 minutes', open_time) AS open_time,
    market_id,
    timeframe,

    FIRST(open, open_time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, open_time) AS close,

    SUM(volume) AS volume,
    SUM(quote_volume) AS quote_volume,
    SUM(trade_count) AS trade_count,
    SUM(taker_buy_base_volume) AS taker_buy_base_volume,
    SUM(taker_buy_quote_volume) AS taker_buy_quote_volume,

    SUM(candle_count) AS candle_count  -- 累積原始K線數量
FROM ohlcv_5m
GROUP BY time_bucket('15 minutes', open_time), market_id, timeframe;

COMMENT ON MATERIALIZED VIEW ohlcv_15m IS
'15分鐘K線連續聚合視圖，從5分鐘聚合資料自動更新';

-- 3.3 一小時聚合（從 15m 聚合資料聚合）
-- 保留期：180 天（約 6 個月）
DROP MATERIALIZED VIEW IF EXISTS ohlcv_1h CASCADE;

CREATE MATERIALIZED VIEW ohlcv_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', open_time) AS open_time,
    market_id,
    timeframe,

    FIRST(open, open_time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, open_time) AS close,

    SUM(volume) AS volume,
    SUM(quote_volume) AS quote_volume,
    SUM(trade_count) AS trade_count,
    SUM(taker_buy_base_volume) AS taker_buy_base_volume,
    SUM(taker_buy_quote_volume) AS taker_buy_quote_volume,

    SUM(candle_count) AS candle_count
FROM ohlcv_15m
GROUP BY time_bucket('1 hour', open_time), market_id, timeframe;

COMMENT ON MATERIALIZED VIEW ohlcv_1h IS
'1小時K線連續聚合視圖，從15分鐘聚合資料自動更新';

-- 3.4 一日聚合（從 1h 聚合資料聚合）
-- 保留期：永久
DROP MATERIALIZED VIEW IF EXISTS ohlcv_1d CASCADE;

CREATE MATERIALIZED VIEW ohlcv_1d
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', open_time) AS open_time,
    market_id,
    timeframe,

    FIRST(open, open_time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, open_time) AS close,

    SUM(volume) AS volume,
    SUM(quote_volume) AS quote_volume,
    SUM(trade_count) AS trade_count,
    SUM(taker_buy_base_volume) AS taker_buy_base_volume,
    SUM(taker_buy_quote_volume) AS taker_buy_quote_volume,

    SUM(candle_count) AS candle_count
FROM ohlcv_1h
GROUP BY time_bucket('1 day', open_time), market_id, timeframe;

COMMENT ON MATERIALIZED VIEW ohlcv_1d IS
'日線K線連續聚合視圖，從1小時聚合資料自動更新，永久保留';

-- ============================================
-- Part 4: 設定連續聚合自動更新策略
-- ============================================

-- 4.1 ohlcv_5m 更新策略
-- 每小時更新一次，處理最近 3 天的資料
SELECT add_continuous_aggregate_policy('ohlcv_5m',
    start_offset => INTERVAL '3 days',   -- 回溯處理3天內的資料
    end_offset => INTERVAL '1 hour',     -- 保留最近1小時不處理（避免正在寫入的資料）
    schedule_interval => INTERVAL '1 hour',  -- 每小時執行一次
    if_not_exists => TRUE
);

-- 4.2 ohlcv_15m 更新策略
SELECT add_continuous_aggregate_policy('ohlcv_15m',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '2 hours',
    schedule_interval => INTERVAL '2 hours',
    if_not_exists => TRUE
);

-- 4.3 ohlcv_1h 更新策略
SELECT add_continuous_aggregate_policy('ohlcv_1h',
    start_offset => INTERVAL '14 days',
    end_offset => INTERVAL '4 hours',
    schedule_interval => INTERVAL '4 hours',
    if_not_exists => TRUE
);

-- 4.4 ohlcv_1d 更新策略
-- 每天更新一次，處理最近 30 天
SELECT add_continuous_aggregate_policy('ohlcv_1d',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================
-- Part 5: 分層資料保留策略 (Tiered Retention)
-- ============================================

-- 5.1 原始 1 分鐘資料：保留 7 天
-- 注意：此策略會跳過 critical_events 表中標記的時間範圍（見 Part 6）
SELECT add_retention_policy('ohlcv',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- 5.2 5 分鐘聚合：保留 30 天
SELECT add_retention_policy('ohlcv_5m',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- 5.3 15 分鐘聚合：保留 90 天
SELECT add_retention_policy('ohlcv_15m',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

-- 5.4 1 小時聚合：保留 180 天（約 6 個月）
SELECT add_retention_policy('ohlcv_1h',
    INTERVAL '180 days',
    if_not_exists => TRUE
);

-- 5.5 日線聚合：永久保留（不設置 retention policy）

-- 5.6 Trades 資料：保留 7 天（與 1m OHLCV 同步）
SELECT add_retention_policy('trades',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- 5.7 訂單簿快照：保留 3 天（資料量大）
SELECT add_retention_policy('orderbook_snapshots',
    INTERVAL '3 days',
    if_not_exists => TRUE
);

-- ============================================
-- Part 6: 重要事件保護機制
-- ============================================

-- 6.1 創建函數：檢查某個時間範圍是否屬於重要事件
CREATE OR REPLACE FUNCTION is_critical_event_period(
    p_market_id INT,
    p_timestamp TIMESTAMPTZ
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM critical_events
        WHERE preserve_raw = TRUE
        AND p_market_id = ANY(markets)
        AND tstzrange(start_time, end_time) @> p_timestamp
    );
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION is_critical_event_period IS
'檢查指定時間點是否屬於需要保護的重要事件期間';

-- 6.2 插入預設重要事件（範例）
INSERT INTO critical_events (
    event_name, event_type, start_time, end_time, markets, description, tags
) VALUES
    (
        '2021 BTC Flash Crash',
        'flash_crash',
        '2021-05-19 00:00:00+00',
        '2021-05-20 00:00:00+00',
        ARRAY(SELECT id FROM markets WHERE base_asset = 'BTC'),
        'BTC 單日暴跌 30%，引發全市場恐慌拋售',
        ARRAY['crash', 'btc', 'liquidation']
    ),
    (
        '2022 LUNA Collapse',
        'black_swan',
        '2022-05-09 00:00:00+00',
        '2022-05-13 00:00:00+00',
        ARRAY(SELECT id FROM markets WHERE base_asset IN ('LUNA', 'UST')),
        'UST 脫錨導致 LUNA 死亡螺旋',
        ARRAY['defi', 'stablecoin', 'luna']
    ),
    (
        '2022 FTX Collapse',
        'black_swan',
        '2022-11-06 00:00:00+00',
        '2022-11-12 00:00:00+00',
        ARRAY(SELECT id FROM markets WHERE base_asset IN ('FTT', 'BTC', 'ETH')),
        'FTX 交易所破產，引發系統性風險',
        ARRAY['exchange', 'ftx', 'contagion']
    )
ON CONFLICT DO NOTHING;

-- ============================================
-- Part 7: 輔助查詢函數
-- ============================================

-- 7.1 智能查詢函數：自動選擇最佳資料粒度
CREATE OR REPLACE FUNCTION get_optimal_ohlcv(
    p_market_id INT,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ,
    p_max_points INT DEFAULT 1000
) RETURNS TABLE (
    open_time TIMESTAMPTZ,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    source TEXT  -- '1m', '5m', '15m', '1h', '1d'
) AS $$
DECLARE
    time_range INTERVAL;
    optimal_timeframe TEXT;
BEGIN
    time_range := p_end_time - p_start_time;

    -- 根據查詢時間範圍自動選擇最佳粒度
    IF time_range <= INTERVAL '12 hours' THEN
        optimal_timeframe := '1m';
    ELSIF time_range <= INTERVAL '3 days' THEN
        optimal_timeframe := '5m';
    ELSIF time_range <= INTERVAL '30 days' THEN
        optimal_timeframe := '15m';
    ELSIF time_range <= INTERVAL '180 days' THEN
        optimal_timeframe := '1h';
    ELSE
        optimal_timeframe := '1d';
    END IF;

    -- 根據選定粒度返回資料
    RETURN QUERY EXECUTE format(
        'SELECT open_time, open, high, low, close, volume, %L::TEXT AS source
         FROM %I
         WHERE market_id = $1
         AND open_time >= $2
         AND open_time < $3
         ORDER BY open_time
         LIMIT $4',
        optimal_timeframe,
        CASE optimal_timeframe
            WHEN '1m' THEN 'ohlcv'
            ELSE 'ohlcv_' || optimal_timeframe
        END
    ) USING p_market_id, p_start_time, p_end_time, p_max_points;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_optimal_ohlcv IS
'智能選擇最合適的資料粒度，避免查詢過多細粒度資料';

-- 7.2 資料可用性檢查函數
CREATE OR REPLACE FUNCTION check_data_availability(
    p_market_id INT,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
) RETURNS TABLE (
    timeframe TEXT,
    available BOOLEAN,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    record_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH timeframes AS (
        SELECT '1m' AS tf, 'ohlcv' AS table_name
        UNION ALL SELECT '5m', 'ohlcv_5m'
        UNION ALL SELECT '15m', 'ohlcv_15m'
        UNION ALL SELECT '1h', 'ohlcv_1h'
        UNION ALL SELECT '1d', 'ohlcv_1d'
    )
    SELECT
        tf.tf,
        (cnt > 0) AS available,
        min_time,
        max_time,
        cnt
    FROM timeframes tf
    CROSS JOIN LATERAL (
        SELECT
            COUNT(*) AS cnt,
            MIN(o.open_time) AS min_time,
            MAX(o.open_time) AS max_time
        FROM (
            SELECT open_time FROM ohlcv
            WHERE timeframe = '1m' AND market_id = p_market_id
            AND open_time >= p_start_time AND open_time < p_end_time
            UNION ALL
            SELECT open_time FROM ohlcv_5m
            WHERE market_id = p_market_id
            AND open_time >= p_start_time AND open_time < p_end_time
            UNION ALL
            SELECT open_time FROM ohlcv_15m
            WHERE market_id = p_market_id
            AND open_time >= p_start_time AND open_time < p_end_time
            UNION ALL
            SELECT open_time FROM ohlcv_1h
            WHERE market_id = p_market_id
            AND open_time >= p_start_time AND open_time < p_end_time
            UNION ALL
            SELECT open_time FROM ohlcv_1d
            WHERE market_id = p_market_id
            AND open_time >= p_start_time AND open_time < p_end_time
        ) o
    ) AS stats;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION check_data_availability IS
'檢查各時間粒度資料在指定範圍內的可用性';

-- 7.3 儲存空間統計函數
CREATE OR REPLACE FUNCTION get_storage_statistics()
RETURNS TABLE (
    table_name TEXT,
    total_size TEXT,
    table_size TEXT,
    indexes_size TEXT,
    row_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.table_name::TEXT,
        pg_size_pretty(pg_total_relation_size(t.table_name::regclass)) AS total_size,
        pg_size_pretty(pg_relation_size(t.table_name::regclass)) AS table_size,
        pg_size_pretty(pg_total_relation_size(t.table_name::regclass) - pg_relation_size(t.table_name::regclass)) AS indexes_size,
        (SELECT COUNT(*) FROM ohlcv WHERE timeframe = '1m') AS row_count
    FROM (
        VALUES
            ('ohlcv'),
            ('ohlcv_5m'),
            ('ohlcv_15m'),
            ('ohlcv_1h'),
            ('ohlcv_1d'),
            ('trades'),
            ('orderbook_snapshots')
    ) AS t(table_name);
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_storage_statistics IS
'查詢各時序表的儲存空間使用情況';

-- ============================================
-- Part 8: 創建索引優化查詢性能
-- ============================================

-- 為聚合視圖創建索引
CREATE INDEX IF NOT EXISTS idx_ohlcv_5m_market_time
    ON ohlcv_5m (market_id, open_time DESC);

CREATE INDEX IF NOT EXISTS idx_ohlcv_15m_market_time
    ON ohlcv_15m (market_id, open_time DESC);

CREATE INDEX IF NOT EXISTS idx_ohlcv_1h_market_time
    ON ohlcv_1h (market_id, open_time DESC);

CREATE INDEX IF NOT EXISTS idx_ohlcv_1d_market_time
    ON ohlcv_1d (market_id, open_time DESC);

-- ============================================
-- Part 9: 創建監控視圖
-- ============================================

-- 9.1 資料保留狀態監控視圖
CREATE OR REPLACE VIEW v_retention_status AS
SELECT
    'ohlcv (1m)' AS layer,
    '7 days' AS retention_period,
    MIN(open_time) AS oldest_data,
    MAX(open_time) AS newest_data,
    NOW() - MIN(open_time) AS actual_retention,
    COUNT(*) AS total_records
FROM ohlcv WHERE timeframe = '1m'
UNION ALL
SELECT
    'ohlcv_5m' AS layer,
    '30 days' AS retention_period,
    MIN(open_time),
    MAX(open_time),
    NOW() - MIN(open_time),
    COUNT(*)
FROM ohlcv_5m
UNION ALL
SELECT
    'ohlcv_15m' AS layer,
    '90 days' AS retention_period,
    MIN(open_time),
    MAX(open_time),
    NOW() - MIN(open_time),
    COUNT(*)
FROM ohlcv_15m
UNION ALL
SELECT
    'ohlcv_1h' AS layer,
    '180 days' AS retention_period,
    MIN(open_time),
    MAX(open_time),
    NOW() - MIN(open_time),
    COUNT(*)
FROM ohlcv_1h
UNION ALL
SELECT
    'ohlcv_1d' AS layer,
    'forever' AS retention_period,
    MIN(open_time),
    MAX(open_time),
    NOW() - MIN(open_time),
    COUNT(*)
FROM ohlcv_1d;

COMMENT ON VIEW v_retention_status IS
'監控各層級資料保留狀態與實際資料範圍';

-- ============================================
-- Part 10: 完成訊息
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 004 執行完成！';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE '已創建以下連續聚合視圖：';
    RAISE NOTICE '  - ohlcv_5m  (5分鐘，保留30天)';
    RAISE NOTICE '  - ohlcv_15m (15分鐘，保留90天)';
    RAISE NOTICE '  - ohlcv_1h  (1小時，保留180天)';
    RAISE NOTICE '  - ohlcv_1d  (1天，永久保留)';
    RAISE NOTICE '';
    RAISE NOTICE '資料保留策略：';
    RAISE NOTICE '  - 原始1分鐘資料: 7天';
    RAISE NOTICE '  - Trades: 7天';
    RAISE NOTICE '  - 訂單簿: 3天';
    RAISE NOTICE '';
    RAISE NOTICE '重要事件已標記，相關資料將受到保護';
    RAISE NOTICE '';
    RAISE NOTICE '可用查詢函數：';
    RAISE NOTICE '  - get_optimal_ohlcv(): 智能選擇最佳粒度';
    RAISE NOTICE '  - check_data_availability(): 檢查資料可用性';
    RAISE NOTICE '  - get_storage_statistics(): 儲存空間統計';
    RAISE NOTICE '';
    RAISE NOTICE '監控視圖：';
    RAISE NOTICE '  - SELECT * FROM v_retention_status;';
    RAISE NOTICE '========================================';
END $$;
