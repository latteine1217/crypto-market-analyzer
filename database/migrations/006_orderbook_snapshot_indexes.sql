-- ============================================
-- Migration: 006 - Orderbook Snapshot Indexes
-- Description: 修正並補齊 orderbook_snapshots 索引
-- ============================================

CREATE INDEX IF NOT EXISTS idx_orderbook_snapshots_market_timestamp
ON orderbook_snapshots (market_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_orderbook_snapshots_timestamp
ON orderbook_snapshots (timestamp DESC);
