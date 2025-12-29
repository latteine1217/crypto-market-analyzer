-- ============================================
-- 區塊鏈巨鯨追蹤 Schema
-- ============================================
-- 用於追蹤 Bitcoin, Ethereum, BSC, Tron 等區塊鏈上的大額交易

-- ============================================
-- 區塊鏈定義表
-- ============================================

-- 支援的區塊鏈
CREATE TABLE IF NOT EXISTS blockchains (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,       -- 'BTC', 'ETH', 'BSC', 'TRX'
    full_name       TEXT NOT NULL,              -- 'Bitcoin', 'Ethereum', etc.
    chain_id        INT,                        -- EVM 鏈的 chain_id (非 EVM 為 NULL)
    native_token    TEXT NOT NULL,              -- 'BTC', 'ETH', 'BNB', 'TRX'
    block_time      INT,                        -- 平均出塊時間（秒）
    api_endpoint    TEXT,                       -- 主要 API 端點
    explorer_url    TEXT,                       -- 區塊瀏覽器 URL
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 巨鯨地址追蹤
-- ============================================

-- 巨鯨地址或交易所地址
CREATE TABLE IF NOT EXISTS whale_addresses (
    id              SERIAL PRIMARY KEY,
    blockchain_id   INT NOT NULL REFERENCES blockchains(id) ON DELETE CASCADE,
    address         TEXT NOT NULL,              -- 區塊鏈地址
    label           TEXT,                       -- 地址標籤 (Binance Hot Wallet, etc.)
    address_type    TEXT,                       -- 'exchange', 'whale', 'contract', 'unknown'
    is_exchange     BOOLEAN DEFAULT FALSE,      -- 是否為交易所地址
    exchange_name   TEXT,                       -- 交易所名稱 (Binance, Coinbase, etc.)

    -- 統計資訊 (由系統定期更新)
    total_tx_count      INT DEFAULT 0,          -- 總交易數
    total_inflow        NUMERIC(30, 8) DEFAULT 0,  -- 總流入量
    total_outflow       NUMERIC(30, 8) DEFAULT 0,  -- 總流出量
    current_balance     NUMERIC(30, 8),         -- 當前餘額

    -- 時間戳
    first_seen      TIMESTAMPTZ,                -- 首次發現時間
    last_active     TIMESTAMPTZ,                -- 最後活躍時間
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (blockchain_id, address)
);

-- ============================================
-- 大額交易追蹤 (時序數據)
-- ============================================

-- 巨鯨大額交易
CREATE TABLE IF NOT EXISTS whale_transactions (
    id              BIGSERIAL,
    blockchain_id   INT NOT NULL REFERENCES blockchains(id) ON DELETE CASCADE,

    -- 交易基本資訊
    tx_hash         TEXT NOT NULL,              -- 交易哈希
    block_number    BIGINT,                     -- 區塊高度
    tx_timestamp    TIMESTAMPTZ NOT NULL,       -- 交易時間

    -- 交易方
    from_address    TEXT NOT NULL,              -- 發送地址
    to_address      TEXT NOT NULL,              -- 接收地址
    from_address_id INT REFERENCES whale_addresses(id),  -- 關聯地址 ID
    to_address_id   INT REFERENCES whale_addresses(id),  -- 關聯地址 ID

    -- 金額資訊
    amount          NUMERIC(30, 8) NOT NULL,    -- 原始金額
    amount_usd      NUMERIC(20, 2),             -- 美元價值
    token_symbol    TEXT,                       -- 代幣符號 (NULL 為主幣)
    token_contract  TEXT,                       -- 代幣合約地址 (ERC20/BEP20)
    token_decimal   INT DEFAULT 18,             -- 代幣精度

    -- 交易所標記
    is_exchange_inflow  BOOLEAN DEFAULT FALSE,  -- 流入交易所
    is_exchange_outflow BOOLEAN DEFAULT FALSE,  -- 流出交易所
    exchange_name   TEXT,                       -- 相關交易所名稱
    direction       TEXT,                       -- 'inflow', 'outflow', 'neutral'

    -- 分類標籤
    is_whale        BOOLEAN DEFAULT TRUE,       -- 是否為巨鯨交易
    is_anomaly      BOOLEAN DEFAULT FALSE,      -- 是否為異常超大額

    -- Gas 資訊 (EVM 鏈)
    gas_used        BIGINT,                     -- Gas 使用量
    gas_price       BIGINT,                     -- Gas 價格 (wei)
    tx_fee          NUMERIC(30, 8),             -- 交易手續費

    -- 元數據
    metadata        JSONB,                      -- 額外資訊 (JSON)

    -- 資料來源與品質
    data_source     TEXT,                       -- 'etherscan', 'bscscan', 'blockchain.com'
    data_quality    TEXT DEFAULT 'normal',      -- 'normal', 'suspicious', 'verified'

    -- 時間戳
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (blockchain_id, tx_timestamp, tx_hash)
);

-- ============================================
-- 代幣追蹤表 (ERC20/BEP20/TRC20)
-- ============================================

-- 熱門代幣資訊
CREATE TABLE IF NOT EXISTS tracked_tokens (
    id              SERIAL PRIMARY KEY,
    blockchain_id   INT NOT NULL REFERENCES blockchains(id) ON DELETE CASCADE,
    contract_address TEXT NOT NULL,             -- 合約地址
    symbol          TEXT NOT NULL,              -- 代幣符號
    name            TEXT,                       -- 代幣名稱
    decimals        INT DEFAULT 18,             -- 精度
    total_supply    NUMERIC(30, 8),             -- 總供應量
    is_stablecoin   BOOLEAN DEFAULT FALSE,      -- 是否為穩定幣
    is_active       BOOLEAN DEFAULT TRUE,       -- 是否追蹤
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (blockchain_id, contract_address)
);

-- ============================================
-- 轉換為 TimescaleDB Hypertable
-- ============================================

-- whale_transactions 設為 hypertable (按時間分區)
SELECT create_hypertable(
    'whale_transactions',
    'tx_timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ============================================
-- 索引優化
-- ============================================

-- whale_transactions 查詢索引
CREATE INDEX IF NOT EXISTS idx_whale_tx_blockchain_time
    ON whale_transactions (blockchain_id, tx_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_whale_tx_hash
    ON whale_transactions (tx_hash);

CREATE INDEX IF NOT EXISTS idx_whale_tx_from_address
    ON whale_transactions (from_address);

CREATE INDEX IF NOT EXISTS idx_whale_tx_to_address
    ON whale_transactions (to_address);

CREATE INDEX IF NOT EXISTS idx_whale_tx_amount_usd
    ON whale_transactions (amount_usd DESC) WHERE amount_usd IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_whale_tx_exchange_flow
    ON whale_transactions (blockchain_id, is_exchange_inflow, is_exchange_outflow, tx_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_whale_tx_anomaly
    ON whale_transactions (blockchain_id, is_anomaly, tx_timestamp DESC) WHERE is_anomaly = TRUE;

-- whale_addresses 查詢索引
CREATE INDEX IF NOT EXISTS idx_whale_addr_blockchain_address
    ON whale_addresses (blockchain_id, address);

CREATE INDEX IF NOT EXISTS idx_whale_addr_type
    ON whale_addresses (blockchain_id, address_type);

CREATE INDEX IF NOT EXISTS idx_whale_addr_exchange
    ON whale_addresses (blockchain_id, is_exchange) WHERE is_exchange = TRUE;

-- tracked_tokens 查詢索引
CREATE INDEX IF NOT EXISTS idx_tracked_tokens_symbol
    ON tracked_tokens (blockchain_id, symbol);

-- ============================================
-- 資料保留策略
-- ============================================

-- 保留 180 天的巨鯨交易資料 (可根據需求調整)
SELECT add_retention_policy(
    'whale_transactions',
    INTERVAL '180 days',
    if_not_exists => TRUE
);

-- ============================================
-- 查詢輔助函數
-- ============================================

-- 取得特定區塊鏈的最新交易時間
CREATE OR REPLACE FUNCTION get_latest_whale_tx_time(
    p_blockchain_id INT
) RETURNS TIMESTAMPTZ AS $$
    SELECT MAX(tx_timestamp)
    FROM whale_transactions
    WHERE blockchain_id = p_blockchain_id;
$$ LANGUAGE SQL STABLE;

-- 計算時間區間內的交易所流入/流出統計
CREATE OR REPLACE FUNCTION get_exchange_flow_stats(
    p_blockchain_id INT,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
) RETURNS TABLE (
    exchange_name TEXT,
    inflow_count BIGINT,
    inflow_amount NUMERIC,
    outflow_count BIGINT,
    outflow_amount NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        wt.exchange_name,
        COUNT(*) FILTER (WHERE wt.is_exchange_inflow) AS inflow_count,
        SUM(wt.amount_usd) FILTER (WHERE wt.is_exchange_inflow) AS inflow_amount,
        COUNT(*) FILTER (WHERE wt.is_exchange_outflow) AS outflow_count,
        SUM(wt.amount_usd) FILTER (WHERE wt.is_exchange_outflow) AS outflow_amount
    FROM whale_transactions wt
    WHERE wt.blockchain_id = p_blockchain_id
      AND wt.tx_timestamp >= p_start_time
      AND wt.tx_timestamp <= p_end_time
      AND wt.exchange_name IS NOT NULL
    GROUP BY wt.exchange_name
    ORDER BY (COALESCE(SUM(wt.amount_usd) FILTER (WHERE wt.is_exchange_inflow), 0) +
              COALESCE(SUM(wt.amount_usd) FILTER (WHERE wt.is_exchange_outflow), 0)) DESC;
END;
$$ LANGUAGE plpgsql;

-- 查詢異常大額交易
CREATE OR REPLACE FUNCTION get_anomaly_transactions(
    p_blockchain_id INT,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ,
    p_limit INT DEFAULT 100
) RETURNS TABLE (
    tx_hash TEXT,
    tx_timestamp TIMESTAMPTZ,
    from_address TEXT,
    to_address TEXT,
    amount NUMERIC,
    amount_usd NUMERIC,
    token_symbol TEXT,
    direction TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        wt.tx_hash,
        wt.tx_timestamp,
        wt.from_address,
        wt.to_address,
        wt.amount,
        wt.amount_usd,
        wt.token_symbol,
        wt.direction
    FROM whale_transactions wt
    WHERE wt.blockchain_id = p_blockchain_id
      AND wt.tx_timestamp >= p_start_time
      AND wt.tx_timestamp <= p_end_time
      AND wt.is_anomaly = TRUE
    ORDER BY wt.amount_usd DESC NULLS LAST, wt.tx_timestamp DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 初始數據：插入支援的區塊鏈
-- ============================================

INSERT INTO blockchains (name, full_name, chain_id, native_token, block_time, explorer_url)
VALUES
    ('BTC', 'Bitcoin', NULL, 'BTC', 600, 'https://www.blockchain.com/explorer'),
    ('ETH', 'Ethereum', 1, 'ETH', 12, 'https://etherscan.io'),
    ('BSC', 'Binance Smart Chain', 56, 'BNB', 3, 'https://bscscan.com'),
    ('TRX', 'Tron', NULL, 'TRX', 3, 'https://tronscan.org')
ON CONFLICT (name) DO NOTHING;

-- 插入常見代幣
INSERT INTO tracked_tokens (blockchain_id, contract_address, symbol, name, decimals, is_stablecoin)
SELECT b.id, '0xdac17f958d2ee523a2206206994597c13d831ec7', 'USDT', 'Tether USD', 6, TRUE
FROM blockchains b WHERE b.name = 'ETH'
ON CONFLICT (blockchain_id, contract_address) DO NOTHING;

INSERT INTO tracked_tokens (blockchain_id, contract_address, symbol, name, decimals, is_stablecoin)
SELECT b.id, '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48', 'USDC', 'USD Coin', 6, TRUE
FROM blockchains b WHERE b.name = 'ETH'
ON CONFLICT (blockchain_id, contract_address) DO NOTHING;

-- BSC USDT
INSERT INTO tracked_tokens (blockchain_id, contract_address, symbol, name, decimals, is_stablecoin)
SELECT b.id, '0x55d398326f99059ff775485246999027b3197955', 'USDT', 'Tether USD', 18, TRUE
FROM blockchains b WHERE b.name = 'BSC'
ON CONFLICT (blockchain_id, contract_address) DO NOTHING;

-- ============================================
-- 觸發器：自動更新 updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_whale_addresses_updated_at
    BEFORE UPDATE ON whale_addresses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_whale_transactions_updated_at
    BEFORE UPDATE ON whale_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tracked_tokens_updated_at
    BEFORE UPDATE ON tracked_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_blockchains_updated_at
    BEFORE UPDATE ON blockchains
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
