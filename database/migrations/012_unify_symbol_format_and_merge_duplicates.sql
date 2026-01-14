-- Migration 012: Unify Symbol Format and Merge Duplicate Markets
-- Purpose: Fix symbol format inconsistency between REST and WebSocket collectors
--          Merge duplicate market entries with different formats (BTC/USDT vs BTCUSDT)
-- Date: 2026-01-15
-- 
-- Background:
--   - REST collectors use CCXT format: BTC/USDT
--   - WebSocket collectors use native format: BTCUSDT
--   - This caused duplicate market entries with wrong base/quote parsing
--   - Example: BTCUSDT was parsed as BTCU/SDT instead of BTC/USDT
--
-- Strategy:
--   1. Identify duplicate markets (same exchange + similar symbol)
--   2. Choose canonical market_id (the one with correct base_asset/quote_asset)
--   3. Migrate all foreign key references to canonical market_id
--   4. Delete duplicate market entries
--   5. Standardize all symbols to native format (no slash)

BEGIN;

-- ============================================
-- Step 1: Create backup table for safety
-- ============================================
CREATE TABLE IF NOT EXISTS markets_backup_20260115 AS
SELECT * FROM markets;

COMMENT ON TABLE markets_backup_20260115 IS 
'Backup before symbol format unification migration (2026-01-15)';

-- ============================================
-- Step 2: Identify and fix duplicate markets
-- ============================================

-- Case 1: Binance BTC/USDT (id=1) vs BTCUSDT (id=1158)
-- Canonical: id=1 (correct base_asset=BTC, quote_asset=USDT, has 19813 OHLCV records)
-- Duplicate: id=1158 (wrong base_asset=BTCU, quote_asset=SDT, no data)

DO $$
DECLARE
    canonical_id INT := 1;
    duplicate_id INT := 1158;
    affected_rows INT;
BEGIN
    -- Check if duplicate exists
    IF EXISTS (SELECT 1 FROM markets WHERE id = duplicate_id) THEN
        RAISE NOTICE 'Merging Binance BTCUSDT (id=%) into BTC/USDT (id=%)', duplicate_id, canonical_id;
        
        -- Migrate OHLCV records
        UPDATE ohlcv SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % OHLCV records', affected_rows;
        
        -- Migrate trades records
        UPDATE trades SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % trades records', affected_rows;
        
        -- Migrate orderbook snapshots
        UPDATE orderbook_snapshots SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % orderbook snapshots', affected_rows;
        
        -- Migrate backfill tasks
        UPDATE backfill_tasks SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % backfill tasks', affected_rows;
        
        -- Migrate data quality summaries
        UPDATE data_quality_summary SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % quality summaries', affected_rows;
        
        -- Delete duplicate market
        DELETE FROM markets WHERE id = duplicate_id;
        RAISE NOTICE '  Deleted duplicate market (id=%)', duplicate_id;
    END IF;
END $$;

-- Case 2: Binance ETH/USDT (id=30) vs ETHUSDT (id=1160)
-- Canonical: id=30 (correct base_asset=ETH, quote_asset=USDT)
-- Duplicate: id=1160 (wrong base_asset=ETHU, quote_asset=SDT, no data)

DO $$
DECLARE
    canonical_id INT := 30;
    duplicate_id INT := 1160;
    affected_rows INT;
BEGIN
    IF EXISTS (SELECT 1 FROM markets WHERE id = duplicate_id) THEN
        RAISE NOTICE 'Merging Binance ETHUSDT (id=%) into ETH/USDT (id=%)', duplicate_id, canonical_id;
        
        UPDATE ohlcv SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % OHLCV records', affected_rows;
        
        UPDATE trades SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % trades records', affected_rows;
        
        UPDATE orderbook_snapshots SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % orderbook snapshots', affected_rows;
        
        UPDATE backfill_tasks SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % backfill tasks', affected_rows;
        
        UPDATE data_quality_summary SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % quality summaries', affected_rows;
        
        DELETE FROM markets WHERE id = duplicate_id;
        RAISE NOTICE '  Deleted duplicate market (id=%)', duplicate_id;
    END IF;
END $$;

-- Case 3: Bybit BTC/USDT (id=15956) vs BTCUSDT (id=43295)
-- Canonical: id=43295 (correct parsing, has 846 OHLCV + 118997 trades)
-- Duplicate: id=15956 (no data)

DO $$
DECLARE
    canonical_id INT := 43295;
    duplicate_id INT := 15956;
    affected_rows INT;
BEGIN
    IF EXISTS (SELECT 1 FROM markets WHERE id = duplicate_id) THEN
        RAISE NOTICE 'Merging Bybit BTC/USDT (id=%) into BTCUSDT (id=%)', duplicate_id, canonical_id;
        
        UPDATE ohlcv SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % OHLCV records', affected_rows;
        
        UPDATE trades SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % trades records', affected_rows;
        
        UPDATE orderbook_snapshots SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % orderbook snapshots', affected_rows;
        
        UPDATE backfill_tasks SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % backfill tasks', affected_rows;
        
        UPDATE data_quality_summary SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % quality summaries', affected_rows;
        
        DELETE FROM markets WHERE id = duplicate_id;
        RAISE NOTICE '  Deleted duplicate market (id=%)', duplicate_id;
    END IF;
END $$;

-- Case 4: Bybit ETH/USDT (id=15959) vs ETHUSDT (id=43294)
-- Canonical: id=43294 (correct parsing, has 847 OHLCV + 71560 trades)
-- Duplicate: id=15959 (no data)

DO $$
DECLARE
    canonical_id INT := 43294;
    duplicate_id INT := 15959;
    affected_rows INT;
BEGIN
    IF EXISTS (SELECT 1 FROM markets WHERE id = duplicate_id) THEN
        RAISE NOTICE 'Merging Bybit ETH/USDT (id=%) into ETHUSDT (id=%)', duplicate_id, canonical_id;
        
        UPDATE ohlcv SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % OHLCV records', affected_rows;
        
        UPDATE trades SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % trades records', affected_rows;
        
        UPDATE orderbook_snapshots SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % orderbook snapshots', affected_rows;
        
        UPDATE backfill_tasks SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % backfill tasks', affected_rows;
        
        UPDATE data_quality_summary SET market_id = canonical_id WHERE market_id = duplicate_id;
        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        RAISE NOTICE '  Migrated % quality summaries', affected_rows;
        
        DELETE FROM markets WHERE id = duplicate_id;
        RAISE NOTICE '  Deleted duplicate market (id=%)', duplicate_id;
    END IF;
END $$;

-- ============================================
-- Step 3: Standardize all symbol formats to native format (no slash)
-- ============================================

-- Update symbols to native format (without creating duplicates)
UPDATE markets SET symbol = 'BTCUSDT' WHERE symbol = 'BTC/USDT' AND NOT EXISTS (
    SELECT 1 FROM markets m2 WHERE m2.exchange_id = markets.exchange_id AND m2.symbol = 'BTCUSDT'
);

UPDATE markets SET symbol = 'ETHUSDT' WHERE symbol = 'ETH/USDT' AND NOT EXISTS (
    SELECT 1 FROM markets m2 WHERE m2.exchange_id = markets.exchange_id AND m2.symbol = 'ETHUSDT'
);

UPDATE markets SET symbol = 'ETHBTC' WHERE symbol = 'ETH/BTC' AND NOT EXISTS (
    SELECT 1 FROM markets m2 WHERE m2.exchange_id = markets.exchange_id AND m2.symbol = 'ETHBTC'
);

UPDATE markets SET symbol = 'SOLUSDT' WHERE symbol = 'SOL/USDT' AND NOT EXISTS (
    SELECT 1 FROM markets m2 WHERE m2.exchange_id = markets.exchange_id AND m2.symbol = 'SOLUSDT'
);

-- ============================================
-- Step 4: Fix any remaining incorrectly parsed base/quote assets
-- ============================================

-- Fix BTCU/SDT → BTC/USDT
UPDATE markets 
SET base_asset = 'BTC', quote_asset = 'USDT'
WHERE base_asset = 'BTCU' AND quote_asset = 'SDT';

-- Fix ETHU/SDT → ETH/USDT
UPDATE markets 
SET base_asset = 'ETH', quote_asset = 'USDT'
WHERE base_asset = 'ETHU' AND quote_asset = 'SDT';

-- ============================================
-- Step 5: Verification queries
-- ============================================

DO $$
DECLARE
    total_markets INT;
    total_ohlcv INT;
    total_trades INT;
    total_orderbook INT;
BEGIN
    SELECT COUNT(*) INTO total_markets FROM markets;
    SELECT COUNT(*) INTO total_ohlcv FROM ohlcv;
    SELECT COUNT(*) INTO total_trades FROM trades;
    SELECT COUNT(*) INTO total_orderbook FROM orderbook_snapshots;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total markets: %', total_markets;
    RAISE NOTICE 'Total OHLCV records: %', total_ohlcv;
    RAISE NOTICE 'Total trades: %', total_trades;
    RAISE NOTICE 'Total orderbook snapshots: %', total_orderbook;
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Backup table: markets_backup_20260115';
    RAISE NOTICE 'To rollback: See rollback script';
    RAISE NOTICE '========================================';
END $$;

-- Show final market state
SELECT 
    m.id,
    e.name as exchange,
    m.symbol,
    m.base_asset,
    m.quote_asset,
    (SELECT COUNT(*) FROM ohlcv WHERE market_id = m.id) as ohlcv_count,
    (SELECT COUNT(*) FROM trades WHERE market_id = m.id) as trades_count
FROM markets m
JOIN exchanges e ON m.exchange_id = e.id
ORDER BY e.name, m.symbol;

COMMIT;

-- ============================================
-- Rollback script (DO NOT RUN - for reference only)
-- ============================================
-- BEGIN;
-- DROP TABLE IF EXISTS markets CASCADE;
-- CREATE TABLE markets AS SELECT * FROM markets_backup_20260115;
-- -- Note: This will break foreign key constraints
-- -- Full recovery requires restoring from database backup
-- ROLLBACK;
