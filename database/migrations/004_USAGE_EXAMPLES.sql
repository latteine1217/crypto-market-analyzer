-- ============================================
-- Migration 004 使用範例
-- ============================================
-- 此文件包含常用查詢範例，展示如何使用新的連續聚合與保留功能
-- ============================================

-- ============================================
-- 範例 1: 查詢資料保留狀態
-- ============================================

-- 查看所有層級的資料保留狀態
SELECT * FROM v_retention_status;

-- 預期輸出：
-- layer        | retention_period | oldest_data | newest_data | actual_retention | total_records
-- -------------|------------------|-------------|-------------|------------------|---------------
-- ohlcv (1m)   | 7 days          | ...         | ...         | ...              | ...
-- ohlcv_5m     | 30 days         | ...         | ...         | ...              | ...
-- ...


-- ============================================
-- 範例 2: 智能查詢最佳粒度資料
-- ============================================

-- 2.1 查詢最近 6 小時（自動使用 1 分鐘資料）
SELECT *
FROM get_optimal_ohlcv(
    p_market_id := 1,
    p_start_time := NOW() - INTERVAL '6 hours',
    p_end_time := NOW(),
    p_max_points := 1000
)
LIMIT 10;

-- 2.2 查詢最近 7 天（自動使用 5 分鐘聚合）
SELECT *
FROM get_optimal_ohlcv(
    p_market_id := 1,
    p_start_time := NOW() - INTERVAL '7 days',
    p_end_time := NOW(),
    p_max_points := 2000
)
ORDER BY open_time DESC
LIMIT 10;

-- 2.3 查詢最近 3 個月（自動使用 1 小時聚合）
SELECT *
FROM get_optimal_ohlcv(
    p_market_id := 1,
    p_start_time := NOW() - INTERVAL '3 months',
    p_end_time := NOW()
)
ORDER BY open_time
LIMIT 10;


-- ============================================
-- 範例 3: 檢查資料可用性
-- ============================================

-- 檢查特定時間範圍內各粒度資料的可用性
SELECT *
FROM check_data_availability(
    p_market_id := 1,
    p_start_time := '2024-01-01 00:00:00+00',
    p_end_time := '2024-12-31 23:59:59+00'
);

-- 預期輸出：
-- timeframe | available | start_time | end_time | record_count
-- ----------|-----------|------------|----------|-------------
-- 1m        | true/false| ...        | ...      | ...
-- 5m        | true      | ...        | ...      | ...
-- ...


-- ============================================
-- 範例 4: 直接查詢不同粒度的聚合資料
-- ============================================

-- 4.1 查詢 5 分鐘 K 線
SELECT
    open_time,
    open,
    high,
    low,
    close,
    volume,
    candle_count  -- 顯示此5分鐘包含幾根1分鐘K線
FROM ohlcv_5m
WHERE market_id = 1
AND open_time >= NOW() - INTERVAL '1 day'
ORDER BY open_time DESC
LIMIT 20;

-- 4.2 查詢 1 小時 K 線
SELECT
    open_time,
    open,
    high,
    low,
    close,
    volume,
    ROUND((close - open) / open * 100, 2) AS price_change_pct
FROM ohlcv_1h
WHERE market_id = 1
AND open_time >= NOW() - INTERVAL '30 days'
ORDER BY open_time DESC;

-- 4.3 查詢日 K 線（長期趨勢分析）
SELECT
    DATE(open_time) AS date,
    open,
    high,
    low,
    close,
    volume,
    candle_count AS total_candles
FROM ohlcv_1d
WHERE market_id = 1
AND open_time >= NOW() - INTERVAL '1 year'
ORDER BY open_time;


-- ============================================
-- 範例 5: 重要事件管理
-- ============================================

-- 5.1 查看所有重要事件
SELECT
    id,
    event_name,
    event_type,
    TO_CHAR(start_time, 'YYYY-MM-DD HH24:MI') AS start,
    TO_CHAR(end_time, 'YYYY-MM-DD HH24:MI') AS end,
    preserve_raw,
    array_length(markets, 1) AS affected_markets,
    tags
FROM critical_events
ORDER BY start_time DESC;

-- 5.2 新增自定義重要事件
INSERT INTO critical_events (
    event_name,
    event_type,
    start_time,
    end_time,
    markets,
    preserve_raw,
    description,
    tags
) VALUES (
    '2024 BTC Halving',
    'scheduled_event',
    '2024-04-19 00:00:00+00',
    '2024-04-21 00:00:00+00',
    ARRAY(SELECT id FROM markets WHERE base_asset = 'BTC'),
    TRUE,
    'Bitcoin 第四次減半事件',
    ARRAY['btc', 'halving', 'supply']
);

-- 5.3 檢查特定時間是否屬於重要事件期間
SELECT
    is_critical_event_period(
        p_market_id := 1,
        p_timestamp := '2021-05-19 12:00:00+00'
    ) AS is_protected;

-- 5.4 查詢某個市場的所有受保護時段
SELECT
    event_name,
    event_type,
    tstzrange(start_time, end_time) AS time_range,
    description
FROM critical_events
WHERE 1 = ANY(markets)  -- market_id = 1
AND preserve_raw = TRUE
ORDER BY start_time;


-- ============================================
-- 範例 6: 儲存空間監控
-- ============================================

-- 6.1 查看各表的儲存空間使用情況
SELECT * FROM get_storage_statistics();

-- 6.2 計算壓縮比（原始資料 vs 聚合資料）
SELECT
    '1m vs 5m' AS comparison,
    ROUND(
        (SELECT COUNT(*) FROM ohlcv WHERE timeframe = '1m')::NUMERIC /
        NULLIF((SELECT COUNT(*) FROM ohlcv_5m), 0),
        2
    ) AS compression_ratio;

-- 6.3 查看 TimescaleDB chunk 資訊
SELECT
    hypertable_name,
    chunk_name,
    range_start,
    range_end,
    pg_size_pretty(total_bytes) AS total_size
FROM timescaledb_information.chunks
WHERE hypertable_name IN ('ohlcv', 'ohlcv_5m', 'ohlcv_15m', 'ohlcv_1h', 'ohlcv_1d')
ORDER BY hypertable_name, range_start DESC
LIMIT 20;


-- ============================================
-- 範例 7: 效能比較查詢
-- ============================================

-- 7.1 比較查詢同樣時間範圍，不同粒度的效能差異
-- (需要有實際資料才能看出差異)

-- 使用 1 分鐘原始資料（慢）
EXPLAIN ANALYZE
SELECT COUNT(*)
FROM ohlcv
WHERE market_id = 1
AND timeframe = '1m'
AND open_time >= NOW() - INTERVAL '7 days';

-- 使用 5 分鐘聚合（快）
EXPLAIN ANALYZE
SELECT COUNT(*)
FROM ohlcv_5m
WHERE market_id = 1
AND open_time >= NOW() - INTERVAL '7 days';


-- ============================================
-- 範例 8: 資料完整性檢查
-- ============================================

-- 8.1 檢查最近 1 天的 1 分鐘資料是否完整
SELECT
    COUNT(*) FILTER (WHERE has_data = FALSE) AS missing_candles,
    COUNT(*) AS total_expected,
    ROUND(
        COUNT(*) FILTER (WHERE has_data = TRUE)::NUMERIC / COUNT(*) * 100,
        2
    ) AS completeness_pct
FROM check_missing_candles(
    p_market_id := 1,
    p_timeframe := '1m',
    p_start_time := NOW() - INTERVAL '1 day',
    p_end_time := NOW()
);

-- 8.2 找出缺失的具體時段
SELECT
    expected_time,
    expected_time + INTERVAL '1 minute' AS expected_end
FROM check_missing_candles(
    p_market_id := 1,
    p_timeframe := '1m',
    p_start_time := NOW() - INTERVAL '1 day',
    p_end_time := NOW()
)
WHERE has_data = FALSE
ORDER BY expected_time
LIMIT 20;


-- ============================================
-- 範例 9: 連續聚合手動刷新（通常不需要）
-- ============================================

-- 9.1 手動刷新特定時間範圍的聚合（僅在故障恢復時使用）
CALL refresh_continuous_aggregate(
    'ohlcv_5m',
    NOW() - INTERVAL '1 day',
    NOW()
);

-- 9.2 查看連續聚合的更新策略
SELECT
    view_name,
    schedule_interval,
    config,
    next_start
FROM timescaledb_information.jobs j
JOIN timescaledb_information.continuous_aggregates ca
    ON j.hypertable_name = ca.materialization_hypertable_name
WHERE view_name LIKE 'ohlcv_%';


-- ============================================
-- 範例 10: 進階分析查詢
-- ============================================

-- 10.1 使用日線資料計算移動平均線
WITH daily_prices AS (
    SELECT
        open_time::DATE AS date,
        close,
        volume
    FROM ohlcv_1d
    WHERE market_id = 1
    ORDER BY open_time
)
SELECT
    date,
    close,
    AVG(close) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma7,
    AVG(close) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS ma30
FROM daily_prices
ORDER BY date DESC
LIMIT 30;

-- 10.2 計算各時間粒度的波動率
SELECT
    '1h' AS timeframe,
    STDDEV(close) AS price_stddev,
    AVG(close) AS avg_price,
    ROUND(STDDEV(close) / NULLIF(AVG(close), 0) * 100, 2) AS cv_percent
FROM ohlcv_1h
WHERE market_id = 1
AND open_time >= NOW() - INTERVAL '30 days'

UNION ALL

SELECT
    '1d' AS timeframe,
    STDDEV(close),
    AVG(close),
    ROUND(STDDEV(close) / NULLIF(AVG(close), 0) * 100, 2)
FROM ohlcv_1d
WHERE market_id = 1
AND open_time >= NOW() - INTERVAL '1 year';

-- 10.3 識別價格異常波動日（使用日線資料）
SELECT
    open_time::DATE AS date,
    open,
    high,
    low,
    close,
    ROUND(((high - low) / low * 100)::NUMERIC, 2) AS intraday_range_pct,
    volume
FROM ohlcv_1d
WHERE market_id = 1
AND (high - low) / low > 0.05  -- 當日波動超過 5%
ORDER BY (high - low) / low DESC
LIMIT 20;


-- ============================================
-- 範例 11: 備份與還原建議
-- ============================================

-- 11.1 僅備份重要事件期間的原始資料
/*
pg_dump \
    --host=localhost \
    --dbname=crypto_market \
    --table=ohlcv \
    --where="market_id = 1 AND timeframe = '1m' AND open_time >= '2021-05-19' AND open_time < '2021-05-21'" \
    > btc_flash_crash_2021_backup.sql
*/

-- 11.2 匯出聚合資料用於外部分析
COPY (
    SELECT * FROM ohlcv_1d
    WHERE market_id = 1
    ORDER BY open_time
) TO '/tmp/btc_daily_export.csv' WITH CSV HEADER;


-- ============================================
-- 範例 12: 監控與告警查詢
-- ============================================

-- 12.1 檢查聚合視圖是否正常更新
SELECT
    view_name,
    materialization_hypertable_name,
    view_definition IS NOT NULL AS is_valid
FROM timescaledb_information.continuous_aggregates
WHERE view_name LIKE 'ohlcv_%';

-- 12.2 檢查保留策略是否正常執行
SELECT
    hypertable_name,
    job_id,
    last_run_status,
    last_successful_finish,
    next_scheduled_run
FROM timescaledb_information.jobs
WHERE proc_name = 'policy_retention'
ORDER BY hypertable_name;

-- 12.3 檢查是否有資料即將被刪除（保留策略預警）
SELECT
    'ohlcv' AS table_name,
    '7 days' AS retention,
    MIN(open_time) AS oldest_data,
    NOW() - MIN(open_time) AS age,
    CASE
        WHEN NOW() - MIN(open_time) > INTERVAL '6.5 days' THEN '⚠️  即將刪除'
        ELSE '✅ 正常'
    END AS status
FROM ohlcv
WHERE timeframe = '1m';
