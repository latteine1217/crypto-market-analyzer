#!/bin/bash
# 即時查看測試狀態

TEST_ID="stability_24h_20251229"
METRICS_FILE="monitoring/test_results/${TEST_ID}/metrics_latest.json"

while true; do
    clear
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║        24小時穩定性測試 - 即時監控                   ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo ""

    if [ -f "${METRICS_FILE}" ]; then
        python3 << 'EOF'
import json, sys
from datetime import datetime

with open('monitoring/test_results/stability_24h_20251229/metrics_latest.json') as f:
    data = json.load(f)

# 時間
print(f"更新時間: {data['timestamp']}")
print("")

# 系統資源
sr = data['system_resources']
print("═══ 系統資源 ═══")
print(f"CPU:      {sr['cpu']['percent_avg']:6.2f}%  {'✅' if sr['cpu']['percent_avg'] < 80 else '⚠️'}")
print(f"記憶體:   {sr['memory']['percent']:6.2f}%  {'✅' if sr['memory']['percent'] < 85 else '⚠️'}")
print(f"磁碟:     {sr['disk']['percent']:6.2f}%  {'✅' if sr['disk']['percent'] < 90 else '⚠️'}")
print("")

# Docker 容器
containers = data['docker_containers']['containers']
running = sum(1 for c in containers if c['State'] == 'running')
print(f"═══ Docker 容器 ═══")
print(f"運行中: {running}/{len(containers)}")
print("")

# 資料庫
if 'database_status' in data:
    db = data['database_status']
    if 'connections' in db:
        print(f"═══ 資料庫 ═══")
        print(f"連線數: {db['connections']}")
        if 'row_counts' in db:
            for table, count in db['row_counts'].items():
                if count > 0:
                    print(f"{table}: {count:,} rows")
print("")

# Redis
if 'redis_status' in data and 'used_memory_human' in data['redis_status']:
    redis = data['redis_status']
    print(f"═══ Redis ═══")
    print(f"記憶體: {redis['used_memory_human']}")
    print(f"連線數: {redis.get('connected_clients', 'N/A')}")

EOF
    else
        echo "等待數據採集..."
    fi

    echo ""
    echo "按 Ctrl+C 退出 | 每 10 秒刷新"
    sleep 10
done
