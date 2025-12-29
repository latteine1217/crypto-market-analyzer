#!/bin/bash
# 系統狀態快照腳本
# 用於測試前後的系統狀態對比

SNAPSHOT_DIR="monitoring/test_results/snapshots"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAPSHOT_FILE="${SNAPSHOT_DIR}/snapshot_${TIMESTAMP}.txt"

mkdir -p "${SNAPSHOT_DIR}"

echo "=== 系統狀態快照 ===" | tee "${SNAPSHOT_FILE}"
echo "時間: $(date)" | tee -a "${SNAPSHOT_FILE}"
echo "測試 ID: $1" | tee -a "${SNAPSHOT_FILE}"
echo "" | tee -a "${SNAPSHOT_FILE}"

# Docker 容器狀態
echo "=== Docker 容器狀態 ===" | tee -a "${SNAPSHOT_FILE}"
docker-compose ps | tee -a "${SNAPSHOT_FILE}"
echo "" | tee -a "${SNAPSHOT_FILE}"

# 系統資源
echo "=== 系統資源 ===" | tee -a "${SNAPSHOT_FILE}"
echo "CPU 核心數: $(sysctl -n hw.ncpu)" | tee -a "${SNAPSHOT_FILE}"
echo "記憶體總量: $(sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 " GB"}')" | tee -a "${SNAPSHOT_FILE}"
echo "磁碟使用:" | tee -a "${SNAPSHOT_FILE}"
df -h / | tee -a "${SNAPSHOT_FILE}"
echo "" | tee -a "${SNAPSHOT_FILE}"

# Docker 資源使用
echo "=== Docker 容器資源使用 ===" | tee -a "${SNAPSHOT_FILE}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" | tee -a "${SNAPSHOT_FILE}"
echo "" | tee -a "${SNAPSHOT_FILE}"

# 資料庫狀態
echo "=== TimescaleDB 狀態 ===" | tee -a "${SNAPSHOT_FILE}"
docker exec crypto_timescaledb psql -U crypto -d crypto_db -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;" 2>&1 | tee -a "${SNAPSHOT_FILE}"
echo "" | tee -a "${SNAPSHOT_FILE}"

# Redis 狀態
echo "=== Redis 狀態 ===" | tee -a "${SNAPSHOT_FILE}"
docker exec crypto_redis redis-cli INFO | grep -E "used_memory_human|connected_clients|total_commands_processed|keyspace" | tee -a "${SNAPSHOT_FILE}"
echo "" | tee -a "${SNAPSHOT_FILE}"

# 日誌檔案大小
echo "=== 日誌檔案大小 ===" | tee -a "${SNAPSHOT_FILE}"
du -sh collector-py/logs/* 2>/dev/null | tee -a "${SNAPSHOT_FILE}"
echo "" | tee -a "${SNAPSHOT_FILE}"

# Docker volumes
echo "=== Docker Volumes ===" | tee -a "${SNAPSHOT_FILE}"
docker volume ls | grep crypto | tee -a "${SNAPSHOT_FILE}"
echo "" | tee -a "${SNAPSHOT_FILE}"
docker volume inspect crypto_postgres_data crypto_redis_data 2>&1 | tee -a "${SNAPSHOT_FILE}"
echo "" | tee -a "${SNAPSHOT_FILE}"

echo "快照已儲存至: ${SNAPSHOT_FILE}"
