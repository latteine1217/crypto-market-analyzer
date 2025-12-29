-- ============================================================================
-- Migration: 004 - 創建區塊鏈巨鯨追蹤表
--
-- 功能：
-- 1. whale_transactions - 儲存大額區塊鏈交易
-- 2. whale_addresses - 追蹤活躍巨鯨地址
-- 3. exchange_addresses - 已知交易所地址標記
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. 大額交易表 (Whale Transactions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS whale_transactions (
    id BIGSERIAL PRIMARY KEY,

    -- 基本資訊
    blockchain VARCHAR(20) NOT NULL,           -- BTC, ETH, BSC, TRX
    tx_hash VARCHAR(100) UNIQUE NOT NULL,      -- 交易哈希
    block_number BIGINT,                        -- 區塊高度
    timestamp TIMESTAMPTZ NOT NULL,             -- 交易時間

    -- 交易方
    from_address VARCHAR(100) NOT NULL,         -- 發送地址
    to_address VARCHAR(100) NOT NULL,           -- 接收地址

    -- 金額資訊
    amount DECIMAL(30, 10) NOT NULL,            -- 原始金額
    amount_usd DECIMAL(20, 2),                  -- 美元價值（當時）
    token_symbol VARCHAR(20),                   -- 代幣符號（NULL 表示主幣）
    token_contract VARCHAR(100),                -- 代幣合約地址

    -- 交易所標記
    is_exchange_inflow BOOLEAN DEFAULT FALSE,   -- 是否流入交易所
    is_exchange_outflow BOOLEAN DEFAULT FALSE,  -- 是否流出交易所
    exchange_name VARCHAR(50),                  -- 關聯的交易所名稱

    -- 分類標籤
    is_whale BOOLEAN DEFAULT TRUE,              -- 是否為巨鯨交易
    is_anomaly BOOLEAN DEFAULT FALSE,           -- 是否為異常交易（超大額）

    -- 元數據
    gas_used BIGINT,                            -- Gas 使用量（ETH/BSC）
    gas_price BIGINT,                           -- Gas 價格
    tx_fee DECIMAL(20, 10),                     -- 交易手續費

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引優化
CREATE INDEX idx_whale_tx_blockchain_time ON whale_transactions(blockchain, timestamp DESC);
CREATE INDEX idx_whale_tx_hash ON whale_transactions(tx_hash);
CREATE INDEX idx_whale_tx_from ON whale_transactions(from_address);
CREATE INDEX idx_whale_tx_to ON whale_transactions(to_address);
CREATE INDEX idx_whale_tx_exchange_inflow ON whale_transactions(blockchain, is_exchange_inflow, timestamp DESC)
    WHERE is_exchange_inflow = TRUE;
CREATE INDEX idx_whale_tx_exchange_outflow ON whale_transactions(blockchain, is_exchange_outflow, timestamp DESC)
    WHERE is_exchange_outflow = TRUE;
CREATE INDEX idx_whale_tx_anomaly ON whale_transactions(blockchain, is_anomaly, timestamp DESC)
    WHERE is_anomaly = TRUE;

-- 註解
COMMENT ON TABLE whale_transactions IS '區塊鏈大額交易記錄表';
COMMENT ON COLUMN whale_transactions.blockchain IS '區塊鏈類型: BTC, ETH, BSC, TRX';
COMMENT ON COLUMN whale_transactions.is_exchange_inflow IS '資金是否流入交易所';
COMMENT ON COLUMN whale_transactions.is_exchange_outflow IS '資金是否流出交易所';
COMMENT ON COLUMN whale_transactions.is_anomaly IS '是否為異常超大額交易';


-- ============================================================================
-- 2. 巨鯨地址表 (Whale Addresses)
-- ============================================================================
CREATE TABLE IF NOT EXISTS whale_addresses (
    id SERIAL PRIMARY KEY,

    -- 基本資訊
    blockchain VARCHAR(20) NOT NULL,            -- 區塊鏈類型
    address VARCHAR(100) NOT NULL,              -- 地址

    -- 標籤與分類
    label VARCHAR(200),                         -- 自定義標籤
    address_type VARCHAR(50),                   -- 類型: exchange, whale, contract, etc.

    -- 交易所標記
    is_exchange BOOLEAN DEFAULT FALSE,          -- 是否為交易所地址
    exchange_name VARCHAR(50),                  -- 交易所名稱

    -- 統計資訊
    first_seen TIMESTAMPTZ,                     -- 首次發現時間
    last_active TIMESTAMPTZ,                    -- 最後活躍時間
    total_tx_count INTEGER DEFAULT 0,           -- 總交易次數
    total_inflow DECIMAL(30, 10) DEFAULT 0,     -- 總流入金額
    total_outflow DECIMAL(30, 10) DEFAULT 0,    -- 總流出金額
    current_balance DECIMAL(30, 10),            -- 當前餘額（如果可查）

    -- 活躍度指標
    tx_count_24h INTEGER DEFAULT 0,             -- 24小時交易次數
    tx_count_7d INTEGER DEFAULT 0,              -- 7天交易次數
    last_updated TIMESTAMPTZ,                   -- 最後更新時間

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(blockchain, address)
);

-- 索引
CREATE INDEX idx_whale_addr_blockchain ON whale_addresses(blockchain, address);
CREATE INDEX idx_whale_addr_exchange ON whale_addresses(blockchain, is_exchange)
    WHERE is_exchange = TRUE;
CREATE INDEX idx_whale_addr_active ON whale_addresses(blockchain, last_active DESC);
CREATE INDEX idx_whale_addr_balance ON whale_addresses(blockchain, current_balance DESC)
    WHERE current_balance IS NOT NULL;

-- 註解
COMMENT ON TABLE whale_addresses IS '巨鯨地址追蹤表';
COMMENT ON COLUMN whale_addresses.address_type IS '地址類型: exchange, whale, contract, miner, etc.';


-- ============================================================================
-- 3. 交易所地址表 (Exchange Addresses)
-- ============================================================================
CREATE TABLE IF NOT EXISTS exchange_addresses (
    id SERIAL PRIMARY KEY,

    -- 基本資訊
    blockchain VARCHAR(20) NOT NULL,            -- 區塊鏈類型
    address VARCHAR(100) NOT NULL,              -- 地址
    exchange_name VARCHAR(50) NOT NULL,         -- 交易所名稱

    -- 地址分類
    wallet_type VARCHAR(50),                    -- hot_wallet, cold_wallet, deposit_wallet
    label VARCHAR(100),                         -- 額外標籤

    -- 驗證狀態
    is_verified BOOLEAN DEFAULT FALSE,          -- 是否經過驗證
    source VARCHAR(200),                        -- 資料來源（如官方公告、社群確認等）

    -- 時間戳
    added_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ,

    UNIQUE(blockchain, address)
);

-- 索引
CREATE INDEX idx_exchange_addr_blockchain ON exchange_addresses(blockchain, exchange_name);
CREATE INDEX idx_exchange_addr_verified ON exchange_addresses(blockchain, is_verified)
    WHERE is_verified = TRUE;

-- 註解
COMMENT ON TABLE exchange_addresses IS '已知交易所地址列表';
COMMENT ON COLUMN exchange_addresses.wallet_type IS '錢包類型: hot_wallet（熱錢包）, cold_wallet（冷錢包）, deposit_wallet（充值錢包）';
COMMENT ON COLUMN exchange_addresses.is_verified IS '是否經過官方或可靠來源驗證';


-- ============================================================================
-- 4. 創建物化視圖：交易所資金流向摘要
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS exchange_flow_summary AS
SELECT
    blockchain,
    exchange_name,
    DATE_TRUNC('hour', timestamp) as hour,

    -- 流入統計
    COUNT(*) FILTER (WHERE is_exchange_inflow = TRUE) as inflow_count,
    COALESCE(SUM(amount_usd) FILTER (WHERE is_exchange_inflow = TRUE), 0) as inflow_usd,

    -- 流出統計
    COUNT(*) FILTER (WHERE is_exchange_outflow = TRUE) as outflow_count,
    COALESCE(SUM(amount_usd) FILTER (WHERE is_exchange_outflow = TRUE), 0) as outflow_usd,

    -- 淨流向
    COALESCE(SUM(amount_usd) FILTER (WHERE is_exchange_inflow = TRUE), 0) -
    COALESCE(SUM(amount_usd) FILTER (WHERE is_exchange_outflow = TRUE), 0) as net_flow_usd

FROM whale_transactions
WHERE exchange_name IS NOT NULL
GROUP BY blockchain, exchange_name, DATE_TRUNC('hour', timestamp);

-- 物化視圖索引
CREATE INDEX idx_exchange_flow_blockchain_time ON exchange_flow_summary(blockchain, hour DESC);
CREATE INDEX idx_exchange_flow_exchange ON exchange_flow_summary(exchange_name, hour DESC);

-- 註解
COMMENT ON MATERIALIZED VIEW exchange_flow_summary IS '交易所資金流向小時級別摘要';


-- ============================================================================
-- 5. 創建更新函數
-- ============================================================================

-- 自動更新 whale_addresses 統計的觸發函數
CREATE OR REPLACE FUNCTION update_whale_address_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- 更新發送地址統計
    INSERT INTO whale_addresses (blockchain, address, first_seen, last_active, total_tx_count, total_outflow)
    VALUES (NEW.blockchain, NEW.from_address, NEW.timestamp, NEW.timestamp, 1, NEW.amount)
    ON CONFLICT (blockchain, address)
    DO UPDATE SET
        last_active = GREATEST(whale_addresses.last_active, NEW.timestamp),
        total_tx_count = whale_addresses.total_tx_count + 1,
        total_outflow = whale_addresses.total_outflow + NEW.amount,
        last_updated = NOW();

    -- 更新接收地址統計
    INSERT INTO whale_addresses (blockchain, address, first_seen, last_active, total_tx_count, total_inflow)
    VALUES (NEW.blockchain, NEW.to_address, NEW.timestamp, NEW.timestamp, 1, NEW.amount)
    ON CONFLICT (blockchain, address)
    DO UPDATE SET
        last_active = GREATEST(whale_addresses.last_active, NEW.timestamp),
        total_tx_count = whale_addresses.total_tx_count + 1,
        total_inflow = whale_addresses.total_inflow + NEW.amount,
        last_updated = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 創建觸發器
DROP TRIGGER IF EXISTS trigger_update_whale_stats ON whale_transactions;
CREATE TRIGGER trigger_update_whale_stats
    AFTER INSERT ON whale_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_whale_address_stats();

COMMENT ON FUNCTION update_whale_address_stats() IS '自動更新巨鯨地址統計資訊';


-- ============================================================================
-- 6. 預先載入知名交易所地址（範例數據）
-- ============================================================================

-- 注意：這裡只是示範，實際使用時需要從可靠來源獲取最新的交易所地址
INSERT INTO exchange_addresses (blockchain, address, exchange_name, wallet_type, is_verified, source) VALUES
    -- Binance (ETH)
    ('ETH', '0x28C6c06298d514Db089934071355E5743bf21d60', 'Binance', 'hot_wallet', TRUE, 'Official Binance announcement'),
    ('ETH', '0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549', 'Binance', 'hot_wallet', TRUE, 'Official Binance announcement'),
    ('ETH', '0xDFd5293D8e347dFe59E90eFd55b2956a1343963d', 'Binance', 'hot_wallet', TRUE, 'Official Binance announcement'),

    -- Coinbase (ETH)
    ('ETH', '0x71660c4005BA85c37ccec55d0C4493E66Fe775d3', 'Coinbase', 'hot_wallet', TRUE, 'Known exchange wallet'),
    ('ETH', '0x503828976D22510aad0201ac7EC88293211D23Da', 'Coinbase', 'hot_wallet', TRUE, 'Known exchange wallet'),

    -- Kraken (ETH)
    ('ETH', '0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2', 'Kraken', 'hot_wallet', TRUE, 'Known exchange wallet'),
    ('ETH', '0x0A869d79a7052C7f1b55a8EbAbbEa3420F0D1E13', 'Kraken', 'hot_wallet', TRUE, 'Known exchange wallet')
ON CONFLICT (blockchain, address) DO NOTHING;

COMMIT;

-- ============================================================================
-- 驗證
-- ============================================================================
SELECT 'Migration 004 completed successfully!' as status;
SELECT 'Tables created:' as info,
       COUNT(*) FILTER (WHERE table_name IN ('whale_transactions', 'whale_addresses', 'exchange_addresses')) as count
FROM information_schema.tables
WHERE table_schema = 'public';
