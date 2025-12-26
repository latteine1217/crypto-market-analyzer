-- ============================================
-- Migration: 002 - Add Performance Indexes
-- Description: 為常用查詢添加索引以提升性能
-- ============================================

-- OHLCV 表索引
CREATE INDEX IF NOT EXISTS idx_ohlcv_market_timeframe_time
ON ohlcv (market_id, timeframe, open_time DESC);

CREATE INDEX IF NOT EXISTS idx_ohlcv_open_time
ON ohlcv (open_time DESC);

-- Trades 表索引
CREATE INDEX IF NOT EXISTS idx_trades_market_timestamp
ON trades (market_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_trades_timestamp
ON trades (timestamp DESC);

-- Order Book 表索引（如果存在）
CREATE INDEX IF NOT EXISTS idx_orderbook_market_timestamp
ON order_book (market_id, timestamp DESC);

-- Markets 表索引
CREATE INDEX IF NOT EXISTS idx_markets_symbol
ON markets (symbol);

CREATE INDEX IF NOT EXISTS idx_markets_exchange_symbol
ON markets (exchange_id, symbol);

COMMENT ON INDEX idx_ohlcv_market_timeframe_time IS
'Fast lookup for OHLCV data by market, timeframe, and time range';

COMMENT ON INDEX idx_trades_market_timestamp IS
'Fast lookup for trades by market and timestamp';
