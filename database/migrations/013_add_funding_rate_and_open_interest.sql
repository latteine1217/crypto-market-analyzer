-- Migration 013: Add Funding Rate and Open Interest Tables
-- Purpose: Support perpetual futures market data collection
-- Date: 2026-01-15
--
-- Background:
--   - Funding rates indicate market sentiment (positive = bullish, negative = bearish)
--   - Open interest shows total leverage in the market
--   - Both are critical for derivatives market analysis
--
-- Data Sources:
--   - Binance Futures
--   - Bybit Perpetual
--   - OKX Perpetual

BEGIN;

-- ============================================
-- Funding Rates Table
-- ============================================
-- Tracks funding rate for perpetual futures contracts
-- Funding occurs every 8 hours (00:00, 08:00, 16:00 UTC typically)

CREATE TABLE IF NOT EXISTS funding_rates (
    id                  BIGSERIAL,
    market_id           INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    
    -- Funding rate data
    funding_rate        NUMERIC(12, 8) NOT NULL,      -- Current funding rate (e.g., 0.0001 = 0.01%)
    funding_rate_daily  NUMERIC(12, 8),               -- Annualized daily rate (funding_rate * 3)
    
    -- Timing
    funding_time        TIMESTAMPTZ NOT NULL,         -- When this rate applies
    next_funding_time   TIMESTAMPTZ,                  -- Next funding timestamp
    funding_interval    INT,                          -- Interval in hours (usually 8)
    
    -- Metadata
    mark_price          NUMERIC(20, 8),               -- Mark price at funding time
    index_price         NUMERIC(20, 8),               -- Index price at funding time
    
    -- System fields
    collected_at        TIMESTAMPTZ DEFAULT NOW(),    -- When data was collected
    source              TEXT,                         -- 'binance', 'bybit', 'okx'
    
    -- Constraints
    CONSTRAINT funding_rates_unique UNIQUE (market_id, funding_time)
);

-- Convert to hypertable (time-series optimization)
SELECT create_hypertable(
    'funding_rates', 
    'funding_time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_funding_rates_market_time 
    ON funding_rates (market_id, funding_time DESC);

CREATE INDEX IF NOT EXISTS idx_funding_rates_collected 
    ON funding_rates (collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_funding_rates_rate 
    ON funding_rates (funding_rate DESC) 
    WHERE funding_rate IS NOT NULL;

-- Retention policy: Keep 90 days of funding rate history
SELECT add_retention_policy(
    'funding_rates',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

COMMENT ON TABLE funding_rates IS 
'Funding rates for perpetual futures contracts. Updated every 8 hours.';

COMMENT ON COLUMN funding_rates.funding_rate IS 
'Funding rate as decimal (0.0001 = 0.01%). Positive = longs pay shorts. Negative = shorts pay longs.';

COMMENT ON COLUMN funding_rates.funding_rate_daily IS 
'Daily annualized rate (funding_rate * 3 funding periods per day)';

-- ============================================
-- Open Interest Table
-- ============================================
-- Tracks total open interest for perpetual futures
-- Updated more frequently than funding rates (typically every minute)

CREATE TABLE IF NOT EXISTS open_interest (
    id                  BIGSERIAL,
    market_id           INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    
    -- Open interest data
    open_interest       NUMERIC(30, 8) NOT NULL,      -- Total OI in base currency (e.g., BTC)
    open_interest_usd   NUMERIC(30, 2),               -- Total OI in USD value
    
    -- Additional metrics
    open_interest_change_24h NUMERIC(30, 8),          -- 24h change in OI
    open_interest_change_pct NUMERIC(10, 4),          -- 24h change percentage
    
    -- Context data
    price               NUMERIC(20, 8),               -- Price at snapshot time
    volume_24h          NUMERIC(30, 8),               -- 24h trading volume
    
    -- System fields
    timestamp           TIMESTAMPTZ NOT NULL,         -- Snapshot time
    collected_at        TIMESTAMPTZ DEFAULT NOW(),    -- Collection time
    source              TEXT,                         -- 'binance', 'bybit', 'okx'
    
    -- Constraints
    CONSTRAINT open_interest_unique UNIQUE (market_id, timestamp)
);

-- Convert to hypertable
SELECT create_hypertable(
    'open_interest', 
    'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_open_interest_market_time 
    ON open_interest (market_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_open_interest_collected 
    ON open_interest (collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_open_interest_value 
    ON open_interest (open_interest_usd DESC NULLS LAST);

-- Retention policy: Keep 180 days of OI history
SELECT add_retention_policy(
    'open_interest',
    INTERVAL '180 days',
    if_not_exists => TRUE
);

COMMENT ON TABLE open_interest IS 
'Open interest for perpetual futures. Indicates total leverage in market.';

COMMENT ON COLUMN open_interest.open_interest IS 
'Total open positions in base currency (e.g., total BTC in all open BTC/USDT positions)';

COMMENT ON COLUMN open_interest.open_interest_usd IS 
'USD value of total open positions (OI * price)';

-- ============================================
-- Continuous Aggregates for Analytics
-- ============================================

-- Hourly funding rate summary
CREATE MATERIALIZED VIEW IF NOT EXISTS funding_rates_hourly
WITH (timescaledb.continuous) AS
SELECT 
    market_id,
    time_bucket('1 hour', funding_time) AS bucket,
    AVG(funding_rate) AS avg_funding_rate,
    MAX(funding_rate) AS max_funding_rate,
    MIN(funding_rate) AS min_funding_rate,
    AVG(funding_rate_daily) AS avg_funding_rate_daily,
    COUNT(*) AS data_points
FROM funding_rates
GROUP BY market_id, bucket
WITH NO DATA;

-- Refresh policy for hourly view
SELECT add_continuous_aggregate_policy(
    'funding_rates_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Hourly open interest summary
CREATE MATERIALIZED VIEW IF NOT EXISTS open_interest_hourly
WITH (timescaledb.continuous) AS
SELECT 
    market_id,
    time_bucket('1 hour', timestamp) AS bucket,
    AVG(open_interest) AS avg_open_interest,
    MAX(open_interest) AS max_open_interest,
    MIN(open_interest) AS min_open_interest,
    AVG(open_interest_usd) AS avg_open_interest_usd,
    FIRST(open_interest, timestamp) AS open_oi,
    LAST(open_interest, timestamp) AS close_oi,
    COUNT(*) AS data_points
FROM open_interest
GROUP BY market_id, bucket
WITH NO DATA;

-- Refresh policy for OI hourly view
SELECT add_continuous_aggregate_policy(
    'open_interest_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ============================================
-- Helper Functions
-- ============================================

-- Calculate funding rate sentiment
CREATE OR REPLACE FUNCTION funding_rate_sentiment(rate NUMERIC)
RETURNS TEXT AS $$
BEGIN
    IF rate IS NULL THEN
        RETURN 'unknown';
    ELSIF rate > 0.001 THEN
        RETURN 'very_bullish';  -- > 0.1% = very bullish (longs pay shorts heavily)
    ELSIF rate > 0.0003 THEN
        RETURN 'bullish';       -- > 0.03% = bullish
    ELSIF rate > -0.0003 THEN
        RETURN 'neutral';       -- -0.03% to 0.03% = neutral
    ELSIF rate > -0.001 THEN
        RETURN 'bearish';       -- < -0.03% = bearish
    ELSE
        RETURN 'very_bearish';  -- < -0.1% = very bearish (shorts pay longs heavily)
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION funding_rate_sentiment IS 
'Categorize funding rate into sentiment: very_bullish, bullish, neutral, bearish, very_bearish';

-- ============================================
-- Verification Queries
-- ============================================

DO $$
DECLARE
    funding_table_exists BOOLEAN;
    oi_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'funding_rates'
    ) INTO funding_table_exists;
    
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'open_interest'
    ) INTO oi_table_exists;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 013 completed successfully!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Funding Rates table: %', CASE WHEN funding_table_exists THEN '✓ Created' ELSE '✗ Failed' END;
    RAISE NOTICE 'Open Interest table: %', CASE WHEN oi_table_exists THEN '✓ Created' ELSE '✗ Failed' END;
    RAISE NOTICE 'Continuous aggregates: ✓ Created';
    RAISE NOTICE 'Retention policies: ✓ Applied';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Update collector to fetch funding rates';
    RAISE NOTICE '2. Update collector to fetch open interest';
    RAISE NOTICE '3. Add Dashboard visualizations';
    RAISE NOTICE '========================================';
END $$;

COMMIT;

-- ============================================
-- Sample Queries (for reference)
-- ============================================
-- Get latest funding rate for all markets
-- SELECT m.symbol, fr.funding_rate, fr.funding_rate_daily, fr.funding_time
-- FROM funding_rates fr
-- JOIN markets m ON fr.market_id = m.id
-- WHERE fr.funding_time = (
--     SELECT MAX(funding_time) FROM funding_rates WHERE market_id = fr.market_id
-- )
-- ORDER BY fr.funding_rate DESC;

-- Get funding rate trend for BTCUSDT
-- SELECT funding_time, funding_rate, funding_rate_sentiment(funding_rate) as sentiment
-- FROM funding_rates
-- WHERE market_id = (SELECT id FROM markets WHERE symbol = 'BTCUSDT' LIMIT 1)
-- ORDER BY funding_time DESC
-- LIMIT 20;

-- Get OI changes
-- SELECT m.symbol, 
--        oi.open_interest, 
--        oi.open_interest_usd,
--        oi.open_interest_change_24h,
--        oi.open_interest_change_pct
-- FROM open_interest oi
-- JOIN markets m ON oi.market_id = m.id
-- WHERE oi.timestamp > NOW() - INTERVAL '1 hour'
-- ORDER BY oi.open_interest_usd DESC NULLS LAST;
