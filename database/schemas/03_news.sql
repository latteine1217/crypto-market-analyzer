-- Crypto News 表 (主要來源: CryptoPanic)
CREATE TABLE IF NOT EXISTS news (
    id SERIAL PRIMARY KEY,
    external_id INT UNIQUE,           -- CryptoPanic 的 post ID
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    source_domain TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 情緒與熱度 (CryptoPanic 投票)
    votes_positive INT DEFAULT 0,
    votes_negative INT DEFAULT 0,
    votes_important INT DEFAULT 0,
    votes_liked INT DEFAULT 0,
    votes_disliked INT DEFAULT 0,
    votes_lol INT DEFAULT 0,
    votes_toxic INT DEFAULT 0,
    votes_save INT DEFAULT 0,
    
    -- 元數據
    kind TEXT,                        -- news 或 post
    currencies JSONB,                 -- 關聯的幣種 (e.g., [{"code": "BTC", "title": "Bitcoin"}])
    metadata JSONB,                   -- 原始 API 的其他資訊
    
    -- 全文搜索索引 (可選，視需求啟用)
    search_vector tsvector
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_news_published_at ON news (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_currencies ON news USING GIN (currencies);

-- 建立最新的新聞視圖 (方便 API 調用)
CREATE OR REPLACE VIEW latest_news AS
SELECT 
    id, title, url, source_domain, published_at, 
    votes_positive, votes_negative, votes_important,
    currencies
FROM news
ORDER BY published_at DESC
LIMIT 100;
