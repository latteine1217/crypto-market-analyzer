-- =========================================================
-- Crypto Market Dashboard - Consolidated Optimized Schema
-- Goal: High efficiency, unified metrics, automated maintenance
-- Version: 4.0 (Bybit Focused)
-- Date: 2026-01-21
-- =========================================================

-- 1. 基礎設定
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================
-- 模組一：基礎元數據 (Metadata)
-- ============================================

CREATE TABLE IF NOT EXISTS exchanges (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE, -- 'bybit'
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS blockchains (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE, -- 'BTC', 'ETH', 'SOL'
    native_token    TEXT NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS markets (
    id              SERIAL PRIMARY KEY,
    exchange_id     INT REFERENCES exchanges(id),
    blockchain_id   INT REFERENCES blockchains(id), 
    symbol          TEXT NOT NULL,                  -- 統一為 BTCUSDT
    base_asset      TEXT NOT NULL,
    quote_asset     TEXT NOT NULL,
    market_type     TEXT DEFAULT 'spot',            -- 'spot', 'linear_perpetual'
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (exchange_id, symbol)
);

-- ============================================
-- 模組二：核心時序數據 (Market Data)
-- ============================================

-- K線數據
CREATE TABLE IF NOT EXISTS ohlcv (
    market_id   INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    time        TIMESTAMPTZ NOT NULL,
    timeframe   TEXT NOT NULL,         -- '1m', '5m', '1h', '1d'
    open        NUMERIC NOT NULL,
    high        NUMERIC NOT NULL,
    low         NUMERIC NOT NULL,
    close       NUMERIC NOT NULL,
    volume      NUMERIC NOT NULL,
    metadata    JSONB,                 -- 存儲 taker_buy_volume, trade_count 等
    PRIMARY KEY (market_id, time, timeframe)
);

-- 交易流水 (短期保留)
CREATE TABLE IF NOT EXISTS trades (
    market_id   INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    time        TIMESTAMPTZ NOT NULL,
    price       NUMERIC NOT NULL,
    amount      NUMERIC NOT NULL,
    side        TEXT,                  -- 'buy', 'sell'
    trade_id    TEXT,
    PRIMARY KEY (market_id, time, trade_id)
);

-- 市場動態指標 (Funding Rate, Open Interest)
CREATE TABLE IF NOT EXISTS market_metrics (
    market_id   INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    time        TIMESTAMPTZ NOT NULL,
    name        TEXT NOT NULL,         -- 'funding_rate', 'open_interest', 'long_short_ratio'
    value       NUMERIC NOT NULL,
    metadata    JSONB,
    PRIMARY KEY (market_id, time, name)
);

-- 爆倉數據
CREATE TABLE IF NOT EXISTS liquidations (
    time        TIMESTAMPTZ NOT NULL,
    exchange    TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL, -- 'long' or 'short'
    price       NUMERIC(20,8),
    quantity    NUMERIC(20,8),
    value_usd   NUMERIC(20,2),
    PRIMARY KEY (time, exchange, symbol, side, price)
);

-- ============================================
-- 模組三：泛用指標與訊號 (Indicators & Signals)
-- ============================================

-- 整合所有宏觀、情緒、ETF、鏈上指標
CREATE TABLE IF NOT EXISTS global_indicators (
    time            TIMESTAMPTZ NOT NULL,
    category        TEXT NOT NULL,      -- 'sentiment', 'macro', 'etf', 'blockchain'
    name            TEXT NOT NULL,      -- 'fear_greed', 'cpi', 'btc_etf_net_flow', 'active_addresses'
    value           NUMERIC NOT NULL,
    classification  TEXT,               -- 'Extreme Fear', 'High Impact'
    metadata        JSONB,              -- 原始 API 備份
    PRIMARY KEY (time, category, name)
);

-- 市場訊號
CREATE TABLE IF NOT EXISTS market_signals (
    time            TIMESTAMPTZ NOT NULL,
    symbol          TEXT NOT NULL,
    signal_type     TEXT NOT NULL, -- 'oi_spike', 'cvd_divergence', 'funding_extreme', 'liquidation_cascade'
    side            TEXT,          -- 'bullish', 'bearish', 'neutral'
    severity        TEXT,          -- 'info', 'warning', 'critical'
    price_at_signal NUMERIC,
    message         TEXT,
    metadata        JSONB,
    PRIMARY KEY (time, symbol, signal_type)
);

-- ============================================
-- 模組四：區塊鏈特有數據 (Whale & Addresses)
-- ============================================

CREATE TABLE IF NOT EXISTS whale_transactions (
    blockchain_id   INT NOT NULL REFERENCES blockchains(id),
    time            TIMESTAMPTZ NOT NULL,
    tx_hash         TEXT NOT NULL,
    from_addr       TEXT,
    to_addr         TEXT,
    amount_usd      NUMERIC,
    asset           TEXT,
    is_exchange     BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (blockchain_id, time, tx_hash)
);

CREATE TABLE IF NOT EXISTS address_tier_snapshots (
    blockchain_id   INT NOT NULL REFERENCES blockchains(id),
    time            TIMESTAMPTZ NOT NULL,
    tier_name       TEXT NOT NULL,      -- '0-1', '100+'
    address_count   BIGINT,
    total_balance   NUMERIC,
    PRIMARY KEY (blockchain_id, time, tier_name)
);

-- ============================================
-- 模組五：系統日誌、品質與維護 (System & Quality)
-- ============================================

-- 系統日誌
CREATE TABLE IF NOT EXISTS system_logs (
    time        TIMESTAMPTZ NOT NULL,
    module      TEXT NOT NULL,
    level       TEXT NOT NULL,
    message     TEXT,
    value       NUMERIC,
    metadata    JSONB
);

-- API 錯誤日誌
CREATE TABLE IF NOT EXISTS api_error_logs (
    id              SERIAL,
    exchange_name   TEXT NOT NULL,
    endpoint        TEXT NOT NULL,
    error_type      TEXT NOT NULL,              -- 'network', 'rate_limit', 'exchange', 'timeout'
    error_code      TEXT,
    error_message   TEXT,
    request_params  JSONB,
    timestamp       TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- 資料品質摘要
CREATE TABLE IF NOT EXISTS data_quality_summary (
    id              SERIAL,
    market_id       INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    data_type       TEXT NOT NULL,
    timeframe       TEXT,
    check_time      TIMESTAMPTZ NOT NULL,
    time_range_start TIMESTAMPTZ NOT NULL,
    time_range_end  TIMESTAMPTZ NOT NULL,
    total_records   INT NOT NULL DEFAULT 0,
    missing_count   INT DEFAULT 0,
    duplicate_count INT DEFAULT 0,
    out_of_order_count INT DEFAULT 0,
    price_jump_count INT DEFAULT 0,
    volume_spike_count INT DEFAULT 0,
    quality_score   FLOAT,
    is_valid        BOOLEAN DEFAULT TRUE,
    validation_errors JSONB,
    validation_warnings JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, check_time)
);

-- 補資料任務
CREATE TABLE IF NOT EXISTS backfill_tasks (
    id              SERIAL PRIMARY KEY,
    market_id       INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    data_type       TEXT NOT NULL,
    timeframe       TEXT,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    priority        INT DEFAULT 0,
    retry_count     INT DEFAULT 0,
    max_retries     INT DEFAULT 3,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    expected_records INT,
    actual_records  INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 事件與新聞
CREATE TABLE IF NOT EXISTS events (
    id          SERIAL PRIMARY KEY,
    time        TIMESTAMPTZ NOT NULL,
    source      TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    title       TEXT NOT NULL,
    description TEXT,
    impact      TEXT,
    country     TEXT,
    actual      TEXT,
    forecast    TEXT,
    previous    TEXT,
    coins       JSONB,
    url         TEXT,
    metadata    JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT events_unique_source_type_time_title UNIQUE (source, event_type, time, title)
);

CREATE TABLE IF NOT EXISTS news (
    time            TIMESTAMPTZ NOT NULL,
    title           TEXT NOT NULL,
    url             TEXT UNIQUE,
    source          TEXT,
    source_domain   TEXT,
    kind            TEXT,
    votes_positive  INT DEFAULT 0,
    votes_negative  INT DEFAULT 0,
    votes_important INT DEFAULT 0,
    sentiment       NUMERIC,
    currencies      JSONB,
    metadata        JSONB,
    PRIMARY KEY (time, url)
);

-- 價格告警
CREATE TABLE IF NOT EXISTS price_alerts (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    condition TEXT NOT NULL, -- 'above', 'below'
    target_price NUMERIC NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_triggered BOOLEAN DEFAULT FALSE,
    triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 模組六：轉換為 TimescaleDB Hypertables
-- ============================================

SELECT create_hypertable('ohlcv', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
SELECT create_hypertable('trades', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
SELECT create_hypertable('market_metrics', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
SELECT create_hypertable('global_indicators', 'time', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE);
SELECT create_hypertable('whale_transactions', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
SELECT create_hypertable('address_tier_snapshots', 'time', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE);
SELECT create_hypertable('system_logs', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
SELECT create_hypertable('news', 'time', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE);
SELECT create_hypertable('liquidations', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
SELECT create_hypertable('market_signals', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
SELECT create_hypertable('api_error_logs', 'timestamp', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
SELECT create_hypertable('data_quality_summary', 'check_time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);

-- ============================================
-- 模組七：視圖與連續聚合 (Views & Aggregates)
-- ============================================

-- 1分鐘 CVD 連續聚合
CREATE MATERIALIZED VIEW IF NOT EXISTS market_cvd_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    market_id,
    SUM(CASE WHEN side = 'buy' THEN amount ELSE 0 END) AS buy_volume,
    SUM(CASE WHEN side = 'sell' THEN amount ELSE 0 END) AS sell_volume,
    SUM(CASE WHEN side = 'buy' THEN amount ELSE -amount END) AS volume_delta,
    COUNT(*) as trade_count
FROM trades
GROUP BY bucket, market_id
WITH NO DATA;

-- 全網 OI 聚合視圖
CREATE OR REPLACE VIEW aggregated_oi AS
SELECT
    time_bucket('5 minutes', m_metrics.time) AS time,
    m.symbol,
    SUM((m_metrics.metadata->>'open_interest_usd')::NUMERIC) as total_oi_usd,
    COUNT(DISTINCT e.id) as exchange_count,
    jsonb_object_agg(e.name, (m_metrics.metadata->>'open_interest_usd')::NUMERIC) as exchange_breakdown
FROM market_metrics m_metrics
JOIN markets m ON m_metrics.market_id = m.id
JOIN exchanges e ON m.exchange_id = e.id
WHERE m_metrics.name = 'open_interest'
GROUP BY time, m.symbol;

-- Funding Rate 平均視圖
CREATE OR REPLACE VIEW aggregated_funding_rate AS
SELECT
    time_bucket('8 hours', m_metrics.time) AS time,
    m.symbol,
    AVG(m_metrics.value) as avg_funding_rate,
    COUNT(DISTINCT e.id) as exchange_count
FROM market_metrics m_metrics
JOIN markets m ON m_metrics.market_id = m.id
JOIN exchanges e ON m.exchange_id = e.id
WHERE m_metrics.name = 'funding_rate'
GROUP BY time, m.symbol;

-- ============================================
-- 模組八：輔助函數 (Functions)
-- ============================================

-- 檢查缺失 K線
CREATE OR REPLACE FUNCTION check_missing_candles(
    p_market_id INT,
    p_timeframe TEXT,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
)
RETURNS TABLE (expected_time TIMESTAMPTZ, has_data BOOLEAN) AS $$
DECLARE v_interval INTERVAL;
BEGIN
    CASE p_timeframe
        WHEN '1m' THEN v_interval := INTERVAL '1 minute';
        WHEN '5m' THEN v_interval := INTERVAL '5 minutes';
        WHEN '15m' THEN v_interval := INTERVAL '15 minutes';
        WHEN '1h' THEN v_interval := INTERVAL '1 hour';
        WHEN '4h' THEN v_interval := INTERVAL '4 hours';
        WHEN '1d' THEN v_interval := INTERVAL '1 day';
        ELSE v_interval := INTERVAL '1 minute';
    END CASE;
    RETURN QUERY
    WITH time_series AS (SELECT generate_series(p_start_time, p_end_time, v_interval) AS expected_time)
    SELECT ts.expected_time, EXISTS (SELECT 1 FROM ohlcv o WHERE o.market_id = p_market_id AND o.timeframe = p_timeframe AND o.time = ts.expected_time) AS has_data
    FROM time_series ts ORDER BY ts.expected_time ASC;
END;
$$ LANGUAGE plpgsql;

-- 計算品質分數
CREATE OR REPLACE FUNCTION calculate_quality_score(
    p_total_records INT, p_missing_count INT, p_duplicate_count INT, p_out_of_order_count INT, p_price_jump_count INT, p_volume_spike_count INT
) RETURNS FLOAT AS $$
DECLARE score FLOAT := 100.0;
BEGIN
    IF p_total_records = 0 THEN RETURN 0.0; END IF;
    score := score - ((p_missing_count + p_duplicate_count + p_out_of_order_count)::FLOAT / p_total_records * 100);
    score := score - ((p_price_jump_count + p_volume_spike_count)::FLOAT / p_total_records * 50);
    RETURN GREATEST(0.0, LEAST(100.0, score));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- 模組九：索引、保留與壓縮政策 (Policies)
-- ============================================

-- 額外索引
CREATE INDEX IF NOT EXISTS idx_events_time ON events (time DESC);
CREATE INDEX IF NOT EXISTS idx_liquidations_exchange_symbol_time ON liquidations (exchange, symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_market_signals_symbol_time ON market_signals (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_backfill_status ON backfill_tasks(status, priority DESC, created_at);

-- 資料保留 (Retention)
SELECT add_retention_policy('ohlcv', INTERVAL '2 years', if_not_exists => TRUE);
SELECT add_retention_policy('trades', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('market_metrics', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('global_indicators', INTERVAL '5 years', if_not_exists => TRUE);
SELECT add_retention_policy('system_logs', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('market_signals', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('data_quality_summary', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('api_error_logs', INTERVAL '30 days', if_not_exists => TRUE);

-- 壓縮政策 (Compression)
ALTER TABLE ohlcv SET (timescaledb.compress, timescaledb.compress_segmentby = 'market_id');
ALTER TABLE global_indicators SET (timescaledb.compress, timescaledb.compress_segmentby = 'category');
ALTER TABLE market_metrics SET (timescaledb.compress, timescaledb.compress_segmentby = 'market_id');
SELECT add_compression_policy('ohlcv', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_compression_policy('global_indicators', INTERVAL '60 days', if_not_exists => TRUE);

-- CVD 刷新政策
SELECT add_continuous_aggregate_policy('market_cvd_1m',
    start_offset => INTERVAL '3 minutes',
    end_offset => INTERVAL '10 seconds',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE);

-- ============================================
-- 模組十：初始數據 (Initial Data)
-- ============================================

INSERT INTO exchanges (name) VALUES ('bybit') ON CONFLICT DO NOTHING;
INSERT INTO blockchains (name, native_token) VALUES ('BTC', 'BTC'), ('ETH', 'ETH'), ('SOL', 'SOL') ON CONFLICT DO NOTHING;

INSERT INTO markets (exchange_id, symbol, base_asset, quote_asset, market_type)
SELECT id, 'BTCUSDT', 'BTC', 'USDT', 'spot' FROM exchanges WHERE name = 'bybit'
ON CONFLICT DO NOTHING;

INSERT INTO markets (exchange_id, symbol, base_asset, quote_asset, market_type)
SELECT id, 'ETHUSDT', 'ETH', 'USDT', 'spot' FROM exchanges WHERE name = 'bybit'
ON CONFLICT DO NOTHING;