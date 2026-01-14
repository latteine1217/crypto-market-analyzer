-- Migration 010: 設定 idle_in_transaction_session_timeout
-- Purpose: 防止長時間 idle in transaction 連接阻塞 retention jobs
-- Date: 2025-12-30
-- Issue: https://github.com/project/issues/retention-policy-failures
--
-- 問題背景：
-- - Job 1006/1010/1011 在 2025-12-27 至 2025-12-28 期間失敗率高達 88.5%
-- - 根因：idle in transaction 連接持有未提交的事務，阻塞 retention jobs
-- - 當前設定：idle_in_transaction_session_timeout = 0（無限期等待）
--
-- 解決方案：
-- - 設定 10 分鐘超時（足夠長以容納正常事務，但防止長時間阻塞）
-- - 此設定會自動終止超過 10 分鐘的 idle in transaction 連接

-- 設定全域參數（需要重啟生效，但我們會在下方設定當前 session）
ALTER SYSTEM SET idle_in_transaction_session_timeout = '10min';

-- 讓設定立即生效於新連接（無需重啟）
SELECT pg_reload_conf();

-- 驗證設定
SHOW idle_in_transaction_session_timeout;

-- 顯示當前 idle in transaction 連接數（供記錄）
SELECT 
    count(*) as idle_in_transaction_count,
    max(now() - state_change) as max_duration
FROM pg_stat_activity 
WHERE state = 'idle in transaction';

-- 建議：定期檢查長時間 idle in transaction 連接
-- SELECT pid, usename, application_name, state, 
--        now() - state_change as duration, 
--        query 
-- FROM pg_stat_activity 
-- WHERE state = 'idle in transaction' 
--   AND now() - state_change > interval '5 minutes'
-- ORDER BY duration DESC;

-- 建議：如需手動終止長時間連接（謹慎使用）
-- SELECT pg_terminate_backend(pid)
-- FROM pg_stat_activity
-- WHERE state = 'idle in transaction'
--   AND now() - state_change > interval '10 minutes';
