#!/usr/bin/env python3
"""
長期運行測試監控腳本
定期收集系統狀態、資源使用、資料品質指標
"""

import os
import sys
import json
import time
import psutil
import subprocess
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

# 配置
MONITOR_INTERVAL = 300  # 5分鐘
OUTPUT_DIR = Path("/Users/latteine/Documents/coding/finance/monitoring/test_results")
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "crypto_db",
    "user": "crypto",
    "password": "crypto_pass"
}


def get_timestamp():
    """取得時間戳"""
    return datetime.now().isoformat()


def check_docker_containers():
    """檢查 Docker 容器狀態"""
    try:
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            cwd="/Users/latteine/Documents/coding/finance"
        )
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                containers.append(json.loads(line))

        return {
            "timestamp": get_timestamp(),
            "containers": containers,
            "total": len(containers),
            "running": sum(1 for c in containers if c.get("State") == "running"),
            "unhealthy": [c for c in containers if "unhealthy" in c.get("Health", "").lower()]
        }
    except Exception as e:
        return {"error": str(e), "timestamp": get_timestamp()}


def check_system_resources():
    """檢查系統資源使用"""
    cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    return {
        "timestamp": get_timestamp(),
        "cpu": {
            "percent_per_core": cpu_percent,
            "percent_avg": sum(cpu_percent) / len(cpu_percent),
            "count": psutil.cpu_count()
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent": memory.percent,
            "available_gb": round(memory.available / (1024**3), 2)
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent
        }
    }


def check_docker_stats():
    """檢查 Docker 容器資源使用"""
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format",
             "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"],
            capture_output=True,
            text=True
        )

        stats = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                stats.append({
                    "name": parts[0],
                    "cpu": parts[1],
                    "memory": parts[2],
                    "network": parts[3],
                    "block_io": parts[4]
                })

        return {
            "timestamp": get_timestamp(),
            "containers": stats
        }
    except Exception as e:
        return {"error": str(e), "timestamp": get_timestamp()}


def check_database_status():
    """檢查資料庫狀態與資料量"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 資料表大小
        cursor.execute("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY size_bytes DESC
            LIMIT 20;
        """)
        table_sizes = cursor.fetchall()

        # 資料筆數統計
        tables = ['klines_1m', 'klines_1h', 'trades', 'orderbook_snapshots']
        row_counts = {}
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table};")
                result = cursor.fetchone()
                row_counts[table] = result['count'] if result else 0
            except:
                row_counts[table] = -1

        # 連接數
        cursor.execute("SELECT count(*) as connections FROM pg_stat_activity;")
        connections = cursor.fetchone()['connections']

        # 資料庫大小
        cursor.execute("""
            SELECT pg_size_pretty(pg_database_size('crypto_db')) as db_size,
                   pg_database_size('crypto_db') as db_size_bytes;
        """)
        db_size = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            "timestamp": get_timestamp(),
            "database_size": db_size,
            "connections": connections,
            "table_sizes": [dict(row) for row in table_sizes],
            "row_counts": row_counts
        }
    except Exception as e:
        return {"error": str(e), "timestamp": get_timestamp()}


def check_redis_status():
    """檢查 Redis 狀態"""
    try:
        result = subprocess.run(
            ["docker", "exec", "crypto_redis", "redis-cli", "INFO"],
            capture_output=True,
            text=True
        )

        info = {}
        for line in result.stdout.split('\n'):
            if ':' in line and not line.startswith('#'):
                key, value = line.strip().split(':', 1)
                info[key] = value

        # 關鍵指標
        return {
            "timestamp": get_timestamp(),
            "used_memory_human": info.get("used_memory_human"),
            "used_memory_peak_human": info.get("used_memory_peak_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec"),
            "keyspace": {k: v for k, v in info.items() if k.startswith("db")}
        }
    except Exception as e:
        return {"error": str(e), "timestamp": get_timestamp()}


def check_log_sizes():
    """檢查日誌檔案大小"""
    log_dirs = [
        "/Users/latteine/Documents/coding/finance/collector-py/logs",
        "/Users/latteine/Documents/coding/finance/data-collector/logs",
        "/Users/latteine/Documents/coding/finance/data-analyzer/logs"
    ]

    log_info = {}
    for log_dir in log_dirs:
        if os.path.exists(log_dir):
            files = []
            total_size = 0
            for f in os.listdir(log_dir):
                path = os.path.join(log_dir, f)
                if os.path.isfile(path):
                    size = os.path.getsize(path)
                    total_size += size
                    files.append({
                        "name": f,
                        "size_mb": round(size / (1024**2), 2),
                        "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
                    })

            log_info[log_dir] = {
                "total_size_mb": round(total_size / (1024**2), 2),
                "file_count": len(files),
                "files": sorted(files, key=lambda x: x['size_mb'], reverse=True)[:10]
            }

    return {
        "timestamp": get_timestamp(),
        "directories": log_info
    }


def collect_all_metrics():
    """收集所有監控指標"""
    return {
        "timestamp": get_timestamp(),
        "docker_containers": check_docker_containers(),
        "system_resources": check_system_resources(),
        "docker_stats": check_docker_stats(),
        "database_status": check_database_status(),
        "redis_status": check_redis_status(),
        "log_sizes": check_log_sizes()
    }


def save_metrics(metrics, test_id):
    """儲存監控指標"""
    output_dir = OUTPUT_DIR / test_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # 時間序列檔案
    ts_file = output_dir / "metrics_timeseries.jsonl"
    with open(ts_file, 'a') as f:
        f.write(json.dumps(metrics) + '\n')

    # 最新狀態
    latest_file = output_dir / "metrics_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"[{metrics['timestamp']}] 指標已儲存")


def generate_summary(test_id):
    """生成測試摘要"""
    ts_file = OUTPUT_DIR / test_id / "metrics_timeseries.jsonl"

    if not ts_file.exists():
        return None

    metrics_list = []
    with open(ts_file, 'r') as f:
        for line in f:
            metrics_list.append(json.loads(line))

    if not metrics_list:
        return None

    # 計算統計
    cpu_usage = [m['system_resources']['cpu']['percent_avg'] for m in metrics_list]
    mem_usage = [m['system_resources']['memory']['percent'] for m in metrics_list]
    disk_usage = [m['system_resources']['disk']['percent'] for m in metrics_list]

    summary = {
        "test_id": test_id,
        "start_time": metrics_list[0]['timestamp'],
        "end_time": metrics_list[-1]['timestamp'],
        "duration_hours": (
            datetime.fromisoformat(metrics_list[-1]['timestamp']) -
            datetime.fromisoformat(metrics_list[0]['timestamp'])
        ).total_seconds() / 3600,
        "data_points": len(metrics_list),
        "resource_stats": {
            "cpu_percent": {
                "min": min(cpu_usage),
                "max": max(cpu_usage),
                "avg": sum(cpu_usage) / len(cpu_usage)
            },
            "memory_percent": {
                "min": min(mem_usage),
                "max": max(mem_usage),
                "avg": sum(mem_usage) / len(mem_usage)
            },
            "disk_percent": {
                "min": min(disk_usage),
                "max": max(disk_usage),
                "avg": sum(disk_usage) / len(disk_usage)
            }
        },
        "container_restarts": [],  # TODO: 分析容器重啟
        "errors": []  # TODO: 從日誌提取錯誤
    }

    summary_file = OUTPUT_DIR / test_id / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    return summary


def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("使用方式: python long_run_monitor.py <test_id> [duration_hours]")
        print("範例: python long_run_monitor.py stability_test_001 72")
        sys.exit(1)

    test_id = sys.argv[1]
    duration_hours = float(sys.argv[2]) if len(sys.argv) > 2 else 72

    print(f"=== 長期運行測試監控 ===")
    print(f"測試 ID: {test_id}")
    print(f"持續時間: {duration_hours} 小時")
    print(f"監控間隔: {MONITOR_INTERVAL} 秒")
    print(f"輸出目錄: {OUTPUT_DIR / test_id}")
    print("=" * 50)

    start_time = time.time()
    end_time = start_time + (duration_hours * 3600)

    iteration = 0
    try:
        while time.time() < end_time:
            iteration += 1
            print(f"\n--- 第 {iteration} 次採集 ---")

            metrics = collect_all_metrics()
            save_metrics(metrics, test_id)

            # 每小時生成一次摘要
            if iteration % 12 == 0:
                summary = generate_summary(test_id)
                if summary:
                    print(f"\n已運行: {summary['duration_hours']:.2f} 小時")
                    print(f"CPU 平均: {summary['resource_stats']['cpu_percent']['avg']:.2f}%")
                    print(f"記憶體平均: {summary['resource_stats']['memory_percent']['avg']:.2f}%")

            time.sleep(MONITOR_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n測試被中斷，生成最終摘要...")
        summary = generate_summary(test_id)
        if summary:
            print(json.dumps(summary, indent=2))

    print("\n測試完成！")


if __name__ == "__main__":
    main()
