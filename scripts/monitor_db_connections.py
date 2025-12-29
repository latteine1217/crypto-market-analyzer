#!/usr/bin/env python3
"""
資料庫連接監控與自動清理腳本

功能：
1. 監控資料庫連接狀態
2. 自動終止殭屍連接（idle in transaction (aborted)）
3. 記錄連接池使用情況
4. 可作為 cron job 或獨立服務運行
"""
import sys
from pathlib import Path
import psycopg2
from datetime import datetime, timedelta
from loguru import logger
from typing import List, Dict

# 添加父目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "collector-py" / "src"))

from config import settings


class DatabaseConnectionMonitor:
    """資料庫連接監控器"""

    def __init__(
        self,
        max_idle_transaction_minutes: int = 30,
        max_idle_minutes: int = 60,
        auto_terminate: bool = True
    ):
        """
        初始化監控器

        Args:
            max_idle_transaction_minutes: 允許的最長 idle in transaction 時間（分鐘）
            max_idle_minutes: 允許的最長 idle 時間（分鐘）
            auto_terminate: 是否自動終止異常連接
        """
        self.max_idle_transaction_minutes = max_idle_transaction_minutes
        self.max_idle_minutes = max_idle_minutes
        self.auto_terminate = auto_terminate
        self.conn = None

    def connect(self):
        """連接到資料庫"""
        try:
            self.conn = psycopg2.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                dbname=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password
            )
            logger.info("Connected to database for monitoring")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def get_connection_stats(self) -> Dict:
        """
        獲取連接統計資訊

        Returns:
            連接統計字典
        """
        if not self.conn:
            self.connect()

        with self.conn.cursor() as cur:
            # 總連接數
            cur.execute("""
                SELECT count(*) as total, state
                FROM pg_stat_activity
                WHERE datname = %s
                GROUP BY state
            """, (settings.postgres_db,))

            stats = {"total": 0, "by_state": {}}
            for row in cur.fetchall():
                count, state = row
                stats["total"] += count
                stats["by_state"][state or "unknown"] = count

            # 獲取資料庫事務統計
            cur.execute("""
                SELECT numbackends, xact_commit, xact_rollback
                FROM pg_stat_database
                WHERE datname = %s
            """, (settings.postgres_db,))

            db_stats = cur.fetchone()
            if db_stats:
                stats["numbackends"] = db_stats[0]
                stats["xact_commit"] = db_stats[1]
                stats["xact_rollback"] = db_stats[2]
                stats["rollback_rate"] = (
                    db_stats[2] / db_stats[1] * 100 if db_stats[1] > 0 else 0
                )

        return stats

    def get_zombie_connections(self) -> List[Dict]:
        """
        獲取殭屍連接列表

        Returns:
            殭屍連接列表
        """
        if not self.conn:
            self.connect()

        zombie_connections = []

        with self.conn.cursor() as cur:
            # 查找 idle in transaction (aborted) 狀態的連接
            cur.execute("""
                SELECT
                    pid,
                    usename,
                    application_name,
                    state,
                    query_start,
                    state_change,
                    NOW() - state_change as idle_duration,
                    left(query, 100) as query
                FROM pg_stat_activity
                WHERE datname = %s
                  AND state = 'idle in transaction (aborted)'
                ORDER BY state_change
            """, (settings.postgres_db,))

            for row in cur.fetchall():
                pid, usename, app_name, state, query_start, state_change, idle_duration, query = row
                zombie_connections.append({
                    "pid": pid,
                    "usename": usename,
                    "application_name": app_name,
                    "state": state,
                    "query_start": query_start,
                    "state_change": state_change,
                    "idle_duration": idle_duration,
                    "query": query
                })

        return zombie_connections

    def get_long_idle_transactions(self) -> List[Dict]:
        """
        獲取長時間 idle in transaction 的連接

        Returns:
            長時間 idle in transaction 連接列表
        """
        if not self.conn:
            self.connect()

        long_idle = []

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT
                    pid,
                    usename,
                    application_name,
                    state,
                    query_start,
                    state_change,
                    NOW() - state_change as idle_duration,
                    left(query, 100) as query
                FROM pg_stat_activity
                WHERE datname = %s
                  AND state = 'idle in transaction'
                  AND NOW() - state_change > interval '%s minutes'
                ORDER BY state_change
            """, (settings.postgres_db, self.max_idle_transaction_minutes))

            for row in cur.fetchall():
                pid, usename, app_name, state, query_start, state_change, idle_duration, query = row
                long_idle.append({
                    "pid": pid,
                    "usename": usename,
                    "application_name": app_name,
                    "state": state,
                    "query_start": query_start,
                    "state_change": state_change,
                    "idle_duration": idle_duration,
                    "query": query
                })

        return long_idle

    def terminate_connection(self, pid: int) -> bool:
        """
        終止指定 PID 的連接

        Args:
            pid: 連接 PID

        Returns:
            是否成功終止
        """
        if not self.conn:
            self.connect()

        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT pg_terminate_backend(%s)", (pid,))
                result = cur.fetchone()[0]
                self.conn.commit()

                if result:
                    logger.info(f"Successfully terminated connection PID {pid}")
                    return True
                else:
                    logger.warning(f"Failed to terminate connection PID {pid}")
                    return False
        except Exception as e:
            logger.error(f"Error terminating connection PID {pid}: {e}")
            return False

    def cleanup(self) -> Dict:
        """
        執行清理操作

        Returns:
            清理結果統計
        """
        results = {
            "zombie_found": 0,
            "zombie_terminated": 0,
            "long_idle_found": 0,
            "long_idle_terminated": 0,
            "errors": []
        }

        # 處理殭屍連接
        zombies = self.get_zombie_connections()
        results["zombie_found"] = len(zombies)

        if zombies:
            logger.warning(f"Found {len(zombies)} zombie connections")
            for conn_info in zombies:
                logger.warning(
                    f"Zombie: PID {conn_info['pid']}, "
                    f"idle for {conn_info['idle_duration']}, "
                    f"query: {conn_info['query']}"
                )

                if self.auto_terminate:
                    if self.terminate_connection(conn_info['pid']):
                        results["zombie_terminated"] += 1
                    else:
                        results["errors"].append(f"Failed to terminate PID {conn_info['pid']}")

        # 處理長時間 idle in transaction
        long_idle = self.get_long_idle_transactions()
        results["long_idle_found"] = len(long_idle)

        if long_idle:
            logger.warning(f"Found {len(long_idle)} long idle in transaction connections")
            for conn_info in long_idle:
                logger.warning(
                    f"Long idle: PID {conn_info['pid']}, "
                    f"idle for {conn_info['idle_duration']}, "
                    f"query: {conn_info['query']}"
                )

                if self.auto_terminate:
                    if self.terminate_connection(conn_info['pid']):
                        results["long_idle_terminated"] += 1
                    else:
                        results["errors"].append(f"Failed to terminate PID {conn_info['pid']}")

        return results

    def run_monitoring_cycle(self):
        """執行一次完整的監控週期"""
        logger.info("=== Database Connection Monitoring Cycle Started ===")

        # 獲取連接統計
        stats = self.get_connection_stats()
        logger.info(f"Total connections: {stats['total']}")
        logger.info(f"Connections by state: {stats['by_state']}")
        logger.info(
            f"Transaction rollback rate: {stats.get('rollback_rate', 0):.2f}%"
        )

        # 執行清理
        cleanup_results = self.cleanup()

        logger.info(f"Cleanup results: {cleanup_results}")
        logger.info("=== Database Connection Monitoring Cycle Completed ===")

        return {
            "stats": stats,
            "cleanup": cleanup_results,
            "timestamp": datetime.now().isoformat()
        }

    def close(self):
        """關閉監控連接"""
        if self.conn:
            self.conn.close()
            logger.info("Monitor connection closed")


def main():
    """主函數"""
    # 配置日誌
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
    )
    logger.add(
        "logs/db_connection_monitor.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )

    monitor = DatabaseConnectionMonitor(
        max_idle_transaction_minutes=30,
        max_idle_minutes=60,
        auto_terminate=True
    )

    try:
        result = monitor.run_monitoring_cycle()
        logger.success("Monitoring cycle completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Monitoring cycle failed: {e}")
        return 1
    finally:
        monitor.close()


if __name__ == "__main__":
    sys.exit(main())
