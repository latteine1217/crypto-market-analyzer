-- Migration 013: Create data_quality_metrics table
-- Purpose: Quantify data quality for each market/timeframe
-- Date: 2026-01-15

-- Create data_quality_metrics table
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id SERIAL PRIMARY KEY,
    market_id INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    timeframe VARCHAR(10) NOT NULL,
    check_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Time range checked
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    
    -- Quality metrics
    expected_count INT NOT NULL,           -- Expected number of candles
    actual_count INT NOT NULL,             -- Actual number of candles found
    missing_count INT NOT NULL,            -- Number of missing candles
    duplicate_count INT DEFAULT 0,         -- Number of duplicates
    
    -- Rates (0-1)
    missing_rate FLOAT NOT NULL,           -- missing_count / expected_count
    duplicate_rate FLOAT DEFAULT 0,        -- duplicate_count / actual_count
    timestamp_error_rate FLOAT DEFAULT 0,  -- candles with timestamp issues
    
    -- Overall quality score (0-100)
    quality_score FLOAT NOT NULL,
    
    -- Status classification
    status VARCHAR(20) NOT NULL CHECK (status IN ('excellent', 'good', 'acceptable', 'poor', 'critical')),
    
    -- Additional metadata
    issues JSONB DEFAULT '[]'::jsonb,      -- List of specific issues found
    backfill_task_created BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_quality_check UNIQUE (market_id, timeframe, check_time)
);

-- Create indexes
CREATE INDEX idx_quality_market_time ON data_quality_metrics(market_id, timeframe, check_time DESC);
CREATE INDEX idx_quality_status ON data_quality_metrics(status);
CREATE INDEX idx_quality_score ON data_quality_metrics(quality_score);
CREATE INDEX idx_quality_missing_rate ON data_quality_metrics(missing_rate);
CREATE INDEX idx_quality_check_time ON data_quality_metrics(check_time DESC);

-- Note: Hypertable conversion skipped due to unique constraint conflict
-- Can be manually converted later if needed: 
-- ALTER TABLE data_quality_metrics DROP CONSTRAINT unique_quality_check;
-- SELECT create_hypertable('data_quality_metrics', 'check_time');
-- CREATE UNIQUE INDEX unique_quality_check ON data_quality_metrics(market_id, timeframe, check_time);

-- Retention management: Regular table uses partitioning or manual cleanup
-- Keep 30 days of data (to be enforced by application or cron job)

-- Create helper function to calculate quality status
CREATE OR REPLACE FUNCTION calculate_quality_status(missing_rate FLOAT)
RETURNS VARCHAR(20) AS $$
BEGIN
    IF missing_rate = 0 THEN
        RETURN 'excellent';
    ELSIF missing_rate <= 0.001 THEN  -- ≤ 0.1%
        RETURN 'good';
    ELSIF missing_rate <= 0.01 THEN   -- ≤ 1%
        RETURN 'acceptable';
    ELSIF missing_rate <= 0.05 THEN   -- ≤ 5%
        RETURN 'poor';
    ELSE
        RETURN 'critical';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create helper function to calculate quality score (0-100)
CREATE OR REPLACE FUNCTION calculate_quality_score(
    missing_rate FLOAT,
    duplicate_rate FLOAT DEFAULT 0,
    timestamp_error_rate FLOAT DEFAULT 0
)
RETURNS FLOAT AS $$
DECLARE
    score FLOAT;
BEGIN
    -- Start with 100, deduct for each issue
    score := 100.0;
    
    -- Missing data penalty (most critical)
    score := score - (missing_rate * 80);
    
    -- Duplicate penalty
    score := score - (duplicate_rate * 15);
    
    -- Timestamp error penalty
    score := score - (timestamp_error_rate * 5);
    
    -- Ensure score is in [0, 100]
    score := GREATEST(0, LEAST(100, score));
    
    RETURN score;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create view for latest quality metrics per market
CREATE OR REPLACE VIEW latest_data_quality AS
SELECT DISTINCT ON (market_id, timeframe)
    dqm.id,
    m.symbol,
    e.name as exchange,
    dqm.timeframe,
    dqm.check_time,
    dqm.missing_rate,
    dqm.duplicate_rate,
    dqm.quality_score,
    dqm.status,
    dqm.missing_count,
    dqm.expected_count,
    dqm.backfill_task_created
FROM data_quality_metrics dqm
JOIN markets m ON dqm.market_id = m.id
JOIN exchanges e ON m.exchange_id = e.id
ORDER BY market_id, timeframe, check_time DESC;

-- Grant permissions
GRANT SELECT, INSERT ON data_quality_metrics TO crypto;
GRANT USAGE, SELECT ON SEQUENCE data_quality_metrics_id_seq TO crypto;
GRANT SELECT ON latest_data_quality TO crypto;

-- Add comment
COMMENT ON TABLE data_quality_metrics IS 'Quantified data quality metrics for monitoring K-line completeness';
COMMENT ON COLUMN data_quality_metrics.quality_score IS 'Overall quality score: 100 (perfect) to 0 (critical issues)';
COMMENT ON COLUMN data_quality_metrics.missing_rate IS 'Acceptance criteria: ≤ 0.001 (0.1%) per AGENTS.md';
COMMENT ON FUNCTION calculate_quality_status IS 'Classify quality: excellent (0%), good (≤0.1%), acceptable (≤1%), poor (≤5%), critical (>5%)';

-- Migration complete
-- Rollback: DROP TABLE data_quality_metrics CASCADE;
--           DROP VIEW latest_data_quality;
--           DROP FUNCTION calculate_quality_status(FLOAT);
--           DROP FUNCTION calculate_quality_score(FLOAT, FLOAT, FLOAT);
