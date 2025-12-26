-- ============================================
-- 報表生成記錄表
-- ============================================

-- 報表生成日誌表
CREATE TABLE IF NOT EXISTS report_generation_logs (
    id              SERIAL,
    report_type     TEXT NOT NULL,          -- 'daily', 'weekly', 'monthly', 'backtest', 'quality'
    report_name     TEXT,                   -- 報表名稱
    generated_at    TIMESTAMPTZ NOT NULL,   -- 生成時間
    start_date      TIMESTAMPTZ,            -- 報表資料起始日期
    end_date        TIMESTAMPTZ,            -- 報表資料結束日期

    -- 輸出檔案
    html_path       TEXT,                   -- HTML 檔案路徑
    pdf_path        TEXT,                   -- PDF 檔案路徑
    json_path       TEXT,                   -- JSON 資料路徑

    -- 統計資訊
    quality_records INT DEFAULT 0,          -- 資料品質記錄數
    strategies_count INT DEFAULT 0,         -- 策略數
    models_count    INT DEFAULT 0,          -- 模型數

    -- 郵件發送記錄
    email_sent      BOOLEAN DEFAULT FALSE,  -- 是否已發送郵件
    email_recipients TEXT[],                -- 郵件收件人列表
    email_sent_at   TIMESTAMPTZ,            -- 郵件發送時間

    -- 狀態
    status          TEXT DEFAULT 'success', -- 'success', 'failed', 'partial'
    error_message   TEXT,                   -- 錯誤訊息
    generation_time FLOAT,                  -- 生成耗時（秒）

    created_at      TIMESTAMPTZ DEFAULT NOW(),

    -- 複合主鍵包含分區列
    PRIMARY KEY (id, generated_at)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_report_logs_type_time
    ON report_generation_logs(report_type, generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_report_logs_generated_at
    ON report_generation_logs(generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_report_logs_status
    ON report_generation_logs(status, generated_at DESC);

-- 轉換為 Hypertable
SELECT create_hypertable(
    'report_generation_logs',
    'generated_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ============================================
-- 郵件發送記錄表
-- ============================================

CREATE TABLE IF NOT EXISTS email_send_logs (
    id              SERIAL PRIMARY KEY,
    report_log_id   INT,                    -- 關聯 report_generation_logs.id
    recipients      TEXT[] NOT NULL,        -- 收件人列表
    subject         TEXT NOT NULL,          -- 郵件主旨
    sent_at         TIMESTAMPTZ NOT NULL,   -- 發送時間
    status          TEXT NOT NULL,          -- 'success', 'failed'
    error_message   TEXT,                   -- 錯誤訊息
    attachment_count INT DEFAULT 0,         -- 附件數量
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at
    ON email_send_logs(sent_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_logs_status
    ON email_send_logs(status, sent_at DESC);

-- ============================================
-- 輔助函數：記錄報表生成
-- ============================================

CREATE OR REPLACE FUNCTION log_report_generation(
    p_report_type TEXT,
    p_report_name TEXT,
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ,
    p_html_path TEXT,
    p_pdf_path TEXT,
    p_json_path TEXT,
    p_quality_records INT,
    p_strategies_count INT,
    p_models_count INT,
    p_generation_time FLOAT
) RETURNS INT AS $$
DECLARE
    new_id INT;
BEGIN
    INSERT INTO report_generation_logs (
        report_type,
        report_name,
        generated_at,
        start_date,
        end_date,
        html_path,
        pdf_path,
        json_path,
        quality_records,
        strategies_count,
        models_count,
        status,
        generation_time
    )
    VALUES (
        p_report_type,
        p_report_name,
        NOW(),
        p_start_date,
        p_end_date,
        p_html_path,
        p_pdf_path,
        p_json_path,
        p_quality_records,
        p_strategies_count,
        p_models_count,
        'success',
        p_generation_time
    )
    RETURNING id INTO new_id;

    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 查詢輔助視圖
-- ============================================

-- 最近的報表生成摘要
CREATE OR REPLACE VIEW recent_reports AS
SELECT
    id,
    report_type,
    report_name,
    generated_at,
    EXTRACT(EPOCH FROM (end_date - start_date)) / 3600 AS report_hours,
    quality_records,
    strategies_count,
    models_count,
    email_sent,
    status,
    generation_time
FROM report_generation_logs
WHERE generated_at >= NOW() - INTERVAL '30 days'
ORDER BY generated_at DESC;

-- 報表生成統計（按類型）
CREATE OR REPLACE VIEW report_stats_by_type AS
SELECT
    report_type,
    COUNT(*) AS total_reports,
    COUNT(CASE WHEN status = 'success' THEN 1 END) AS success_count,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed_count,
    AVG(generation_time) AS avg_generation_time,
    COUNT(CASE WHEN email_sent = TRUE THEN 1 END) AS emails_sent
FROM report_generation_logs
WHERE generated_at >= NOW() - INTERVAL '30 days'
GROUP BY report_type;
