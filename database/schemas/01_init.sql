-- ============================================
-- Crypto Market Data Schema
-- ============================================

-- 啟用TimescaleDB擴展
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================
-- 基礎表：交易所與市場定義
-- ============================================

-- 交易所資訊
CREATE TABLE exchanges (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,  -- 'binance', 'coinbase', etc.
    api_type    TEXT,                  -- 'ccxt', 'native_rest', 'websocket'
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 市場（交易對）資訊
CREATE TABLE markets (
    id              SERIAL PRIMARY KEY,
    exchange_id     INT REFERENCES exchanges(id) ON DELETE CASCADE,
    symbol          TEXT NOT NULL,          -- 'BTCUSDT', 'BTC/USDT'
    base_asset      TEXT NOT NULL,          -- 'BTC'
    quote_asset     TEXT NOT NULL,          -- 'USDT'
    market_type     TEXT DEFAULT 'spot',    -- 'spot', 'futures', 'swap'
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (exchange_id, symbol)
);

-- ============================================
-- 時序數據表
-- ============================================

-- OHLCV K線數據
CREATE TABLE ohlcv (
    market_id   INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    timeframe   TEXT NOT NULL,              -- '1m', '5m', '15m', '1h', '4h', '1d'
    open_time   TIMESTAMPTZ NOT NULL,       -- K線開始時間
    open        DOUBLE PRECISION NOT NULL,
    high        DOUBLE PRECISION NOT NULL,
    low         DOUBLE PRECISION NOT NULL,
    close       DOUBLE PRECISION NOT NULL,
    volume      DOUBLE PRECISION NOT NULL,
    quote_volume DOUBLE PRECISION,          -- 計價幣種成交量
    trade_count INT,                        -- 成交筆數
    taker_buy_base_volume DOUBLE PRECISION, -- 主動買入量
    taker_buy_quote_volume DOUBLE PRECISION,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (market_id, timeframe, open_time)
);

-- 交易流水（成交明細）
CREATE TABLE trades (
    market_id   INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    trade_id    BIGINT NOT NULL,            -- 交易所原始trade_id
    price       DOUBLE PRECISION NOT NULL,
    quantity    DOUBLE PRECISION NOT NULL,
    quote_qty   DOUBLE PRECISION,           -- 成交金額
    side        TEXT,                       -- 'buy', 'sell'
    is_buyer_maker BOOLEAN,                 -- 買方是否為掛單方
    timestamp   TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (market_id, timestamp, trade_id)
);

-- 訂單簿快照（可選，數據量大時謹慎使用）
CREATE TABLE orderbook_snapshots (
    market_id   INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    timestamp   TIMESTAMPTZ NOT NULL,
    bids        JSONB NOT NULL,             -- [[price, quantity], ...]
    asks        JSONB NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (market_id, timestamp)
);

-- ============================================
-- 轉換為TimescaleDB Hypertable
-- ============================================

SELECT create_hypertable('ohlcv', 'open_time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

SELECT create_hypertable('trades', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT create_hypertable('orderbook_snapshots', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================
-- 索引優化
-- ============================================

-- OHLCV常用查詢索引
CREATE INDEX IF NOT EXISTS idx_ohlcv_market_timeframe
    ON ohlcv (market_id, timeframe, open_time DESC);

-- Trades常用查詢索引
CREATE INDEX IF NOT EXISTS idx_trades_market_time
    ON trades (market_id, timestamp DESC);

-- 市場查詢索引
CREATE INDEX IF NOT EXISTS idx_markets_symbol
    ON markets (symbol);

-- ============================================
-- 數據保留策略（可選）
-- ============================================

-- 1分鐘K線保留90天
SELECT add_retention_policy('ohlcv', INTERVAL '90 days', if_not_exists => TRUE);

-- Trades保留30天
SELECT add_retention_policy('trades', INTERVAL '30 days', if_not_exists => TRUE);

-- ============================================
-- 初始數據：插入Binance交易所
-- ============================================

INSERT INTO exchanges (name, api_type, is_active)
VALUES ('binance', 'ccxt', TRUE)
ON CONFLICT (name) DO NOTHING;

-- 插入BTC/USDT市場
INSERT INTO markets (exchange_id, symbol, base_asset, quote_asset, market_type)
SELECT id, 'BTC/USDT', 'BTC', 'USDT', 'spot'
FROM exchanges WHERE name = 'binance'
ON CONFLICT (exchange_id, symbol) DO NOTHING;

-- ============================================
-- 查詢輔助函數
-- ============================================

-- 取得最新K線時間
CREATE OR REPLACE FUNCTION get_latest_ohlcv_time(
    p_market_id INT,
    p_timeframe TEXT
) RETURNS TIMESTAMPTZ AS $$
    SELECT MAX(open_time)
    FROM ohlcv
    WHERE market_id = p_market_id AND timeframe = p_timeframe;
$$ LANGUAGE SQL STABLE;

-- 檢查數據完整性（缺失K線）
CREATE OR REPLACE FUNCTION check_missing_candles(
    p_market_id INT,
    p_timeframe TEXT,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
) RETURNS TABLE (
    expected_time TIMESTAMPTZ,
    has_data BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH expected_times AS (
        SELECT generate_series(
            p_start_time,
            p_end_time,
            CASE p_timeframe
                WHEN '1m' THEN INTERVAL '1 minute'
                WHEN '5m' THEN INTERVAL '5 minutes'
                WHEN '15m' THEN INTERVAL '15 minutes'
                WHEN '1h' THEN INTERVAL '1 hour'
                WHEN '4h' THEN INTERVAL '4 hours'
                WHEN '1d' THEN INTERVAL '1 day'
                ELSE INTERVAL '1 hour'
            END
        ) AS time
    )
    SELECT
        et.time,
        EXISTS(
            SELECT 1 FROM ohlcv
            WHERE market_id = p_market_id
            AND timeframe = p_timeframe
            AND open_time = et.time
        ) AS has_data
    FROM expected_times et
    ORDER BY et.time;
END;
$$ LANGUAGE plpgsql;
