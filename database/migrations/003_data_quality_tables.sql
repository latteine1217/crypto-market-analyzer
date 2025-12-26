-- ============================================
-- 資料品質監控表
-- ============================================

-- 資料品質摘要表
CREATE TABLE IF NOT EXISTS data_quality_summary (
    id              SERIAL,
    market_id       INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    data_type       TEXT NOT NULL,              -- 'ohlcv', 'trades', 'orderbook'
    timeframe       TEXT,                       -- 僅對 ohlcv 有效
    check_time      TIMESTAMPTZ NOT NULL,       -- 檢查時間
    time_range_start TIMESTAMPTZ NOT NULL,      -- 資料時間範圍開始
    time_range_end  TIMESTAMPTZ NOT NULL,       -- 資料時間範圍結束
    total_records   INT NOT NULL DEFAULT 0,     -- 總記錄數

    -- 品質指標
    missing_count   INT DEFAULT 0,              -- 缺失記錄數
    duplicate_count INT DEFAULT 0,              -- 重複記錄數
    out_of_order_count INT DEFAULT 0,           -- 時序錯亂數
    price_jump_count INT DEFAULT 0,             -- 價格異常跳動數
    volume_spike_count INT DEFAULT 0,           -- 成交量異常數

    -- 品質分數 (0-100)
    quality_score   FLOAT,

    -- 驗證狀態
    is_valid        BOOLEAN DEFAULT TRUE,       -- 整體是否通過驗證
    validation_errors JSONB,                    -- 錯誤詳情
    validation_warnings JSONB,                  -- 警告詳情

    created_at      TIMESTAMPTZ DEFAULT NOW(),

    -- 複合主鍵包含分區列
    PRIMARY KEY (id, check_time)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_quality_market_type
    ON data_quality_summary(market_id, data_type, check_time DESC);

CREATE INDEX IF NOT EXISTS idx_quality_check_time
    ON data_quality_summary(check_time DESC);

-- 轉換為 Hypertable
SELECT create_hypertable(
    'data_quality_summary',
    'check_time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ============================================
-- 補資料任務表
-- ============================================

CREATE TABLE IF NOT EXISTS backfill_tasks (
    id              SERIAL PRIMARY KEY,
    market_id       INT NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    data_type       TEXT NOT NULL,              -- 'ohlcv', 'trades', 'orderbook'
    timeframe       TEXT,                       -- 僅對 ohlcv 有效
    start_time      TIMESTAMPTZ NOT NULL,       -- 補資料開始時間
    end_time        TIMESTAMPTZ NOT NULL,       -- 補資料結束時間

    -- 任務狀態
    status          TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
    priority        INT DEFAULT 0,              -- 優先級（數字越大越優先）
    retry_count     INT DEFAULT 0,              -- 重試次數
    max_retries     INT DEFAULT 3,              -- 最大重試次數

    -- 執行資訊
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,

    -- 進度追蹤
    expected_records INT,                       -- 預期記錄數
    actual_records  INT DEFAULT 0,              -- 實際獲取數

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_backfill_status
    ON backfill_tasks(status, priority DESC, created_at);

CREATE INDEX IF NOT EXISTS idx_backfill_market
    ON backfill_tasks(market_id, data_type, status);

-- ============================================
-- API 錯誤日誌表
-- ============================================

CREATE TABLE IF NOT EXISTS api_error_logs (
    id              SERIAL,
    exchange_name   TEXT NOT NULL,
    endpoint        TEXT NOT NULL,              -- API 端點
    error_type      TEXT NOT NULL,              -- 'network', 'rate_limit', 'exchange', 'timeout'
    error_code      TEXT,                       -- HTTP 狀態碼或錯誤代碼
    error_message   TEXT,
    request_params  JSONB,                      -- 請求參數
    timestamp       TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    -- 複合主鍵包含分區列
    PRIMARY KEY (id, timestamp)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_api_errors_exchange
    ON api_error_logs(exchange_name, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_api_errors_type
    ON api_error_logs(error_type, timestamp DESC);

-- 轉換為 Hypertable
SELECT create_hypertable(
    'api_error_logs',
    'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ============================================
-- 輔助函數：計算品質分數
-- ============================================

CREATE OR REPLACE FUNCTION calculate_quality_score(
    p_total_records INT,
    p_missing_count INT,
    p_duplicate_count INT,
    p_out_of_order_count INT,
    p_price_jump_count INT,
    p_volume_spike_count INT
) RETURNS FLOAT AS $$
DECLARE
    score FLOAT := 100.0;
    total_issues INT;
BEGIN
    IF p_total_records = 0 THEN
        RETURN 0.0;
    END IF;

    total_issues := p_missing_count + p_duplicate_count + p_out_of_order_count;

    -- 基礎扣分：缺失、重複、時序錯誤
    score := score - (total_issues::FLOAT / p_total_records * 100);

    -- 警告扣分（較輕）：價格跳動、成交量異常
    score := score - ((p_price_jump_count + p_volume_spike_count)::FLOAT / p_total_records * 50);

    -- 確保分數在 0-100 之間
    score := GREATEST(0.0, LEAST(100.0, score));

    RETURN score;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- 輔助函數：自動建立補資料任務
-- ============================================

CREATE OR REPLACE FUNCTION auto_create_backfill_tasks(
    p_market_id INT,
    p_timeframe TEXT,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
) RETURNS INT AS $$
DECLARE
    task_count INT := 0;
    missing_rec RECORD;
    interval_duration INTERVAL;
BEGIN
    -- 確定時間間隔
    interval_duration := CASE p_timeframe
        WHEN '1m' THEN INTERVAL '1 minute'
        WHEN '5m' THEN INTERVAL '5 minutes'
        WHEN '15m' THEN INTERVAL '15 minutes'
        WHEN '1h' THEN INTERVAL '1 hour'
        WHEN '4h' THEN INTERVAL '4 hours'
        WHEN '1d' THEN INTERVAL '1 day'
        ELSE INTERVAL '1 hour'
    END;

    -- 找出缺失區段
    FOR missing_rec IN
        SELECT
            expected_time AS missing_start,
            expected_time + interval_duration AS missing_end
        FROM check_missing_candles(p_market_id, p_timeframe, p_start_time, p_end_time)
        WHERE has_data = FALSE
    LOOP
        -- 插入補資料任務
        INSERT INTO backfill_tasks (
            market_id, data_type, timeframe,
            start_time, end_time, status, priority
        )
        VALUES (
            p_market_id, 'ohlcv', p_timeframe,
            missing_rec.missing_start, missing_rec.missing_end,
            'pending', 10  -- 預設優先級
        )
        ON CONFLICT DO NOTHING;

        task_count := task_count + 1;
    END LOOP;

    RETURN task_count;
END;
$$ LANGUAGE plpgsql;
