"""
補資料任務排程器
職責：
1. 檢查資料缺失區段
2. 建立補資料任務
3. 執行補資料任務
4. 更新任務狀態
"""
import psycopg2
from psycopg2.extras import execute_batch
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

from config import settings


class BackfillScheduler:
    """
    補資料任務排程器

    功能：
    - 自動偵測資料缺失
    - 建立補資料任務
    - 管理任務優先級與重試
    """

    def __init__(self, db_conn=None):
        """
        初始化排程器

        Args:
            db_conn: 資料庫連接（可選，若無則自動建立）
        """
        self.conn = db_conn
        self.should_close_conn = False

        if self.conn is None:
            self.conn = psycopg2.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                dbname=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password
            )
            self.should_close_conn = True

        logger.info("BackfillScheduler initialized")

    def check_data_gaps(
        self,
        market_id: int,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        檢查指定時間範圍內的資料缺失

        Args:
            market_id: 市場ID
            timeframe: 時間週期
            start_time: 起始時間
            end_time: 結束時間

        Returns:
            缺失區段列表 [{
                'start_time': datetime,
                'end_time': datetime,
                'missing_count': int
            }]
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT expected_time, has_data
                FROM check_missing_candles(%s, %s, %s, %s)
                """,
                (market_id, timeframe, start_time, end_time)
            )
            results = cur.fetchall()

        # 解析缺失區段
        gaps = []
        gap_start = None
        interval = self._get_interval_delta(timeframe)

        for expected_time, has_data in results:
            if not has_data:
                if gap_start is None:
                    gap_start = expected_time
            else:
                if gap_start is not None:
                    # 計算缺失數量
                    missing_count = int(
                        (expected_time - gap_start).total_seconds() /
                        interval.total_seconds()
                    )
                    gaps.append({
                        'start_time': gap_start,
                        'end_time': expected_time,
                        'missing_count': missing_count
                    })
                    gap_start = None

        # 處理末尾的缺失
        if gap_start is not None:
            missing_count = int(
                (end_time - gap_start).total_seconds() /
                interval.total_seconds()
            ) + 1
            gaps.append({
                'start_time': gap_start,
                'end_time': end_time + interval,
                'missing_count': missing_count
            })

        if gaps:
            total_missing = sum(g['missing_count'] for g in gaps)
            logger.info(
                f"Found {len(gaps)} gaps with {total_missing} missing records "
                f"for market_id={market_id}, timeframe={timeframe}"
            )

        return gaps

    def create_backfill_task(
        self,
        market_id: int,
        data_type: str,
        timeframe: Optional[str],
        start_time: datetime,
        end_time: datetime,
        priority: int = 0,
        expected_records: Optional[int] = None
    ) -> int:
        """
        建立補資料任務

        Args:
            market_id: 市場ID
            data_type: 資料類型 ('ohlcv', 'trades', 'orderbook')
            timeframe: 時間週期（僅對 ohlcv 有效）
            start_time: 起始時間
            end_time: 結束時間
            priority: 優先級（數字越大越優先）
            expected_records: 預期記錄數

        Returns:
            任務ID
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO backfill_tasks (
                    market_id, data_type, timeframe,
                    start_time, end_time, priority, expected_records
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (market_id, data_type, timeframe, start_time, end_time,
                 priority, expected_records)
            )
            task_id = cur.fetchone()[0]
            self.conn.commit()

        logger.info(
            f"Created backfill task #{task_id}: "
            f"market_id={market_id}, {data_type}, {start_time} - {end_time}"
        )
        return task_id

    def create_backfill_tasks_for_gaps(
        self,
        market_id: int,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        priority: int = 5
    ) -> List[int]:
        """
        為檢測到的缺失區段建立補資料任務

        Args:
            market_id: 市場ID
            timeframe: 時間週期
            start_time: 檢查起始時間
            end_time: 檢查結束時間
            priority: 任務優先級

        Returns:
            建立的任務ID列表
        """
        gaps = self.check_data_gaps(market_id, timeframe, start_time, end_time)

        task_ids = []
        for gap in gaps:
            task_id = self.create_backfill_task(
                market_id=market_id,
                data_type='ohlcv',
                timeframe=timeframe,
                start_time=gap['start_time'],
                end_time=gap['end_time'],
                priority=priority,
                expected_records=gap['missing_count']
            )
            task_ids.append(task_id)

        return task_ids

    def get_pending_tasks(
        self,
        limit: int = 10,
        data_type: Optional[str] = None
    ) -> List[Dict]:
        """
        獲取待執行的任務

        Args:
            limit: 最多返回任務數
            data_type: 篩選資料類型（可選）

        Returns:
            任務列表
        """
        with self.conn.cursor() as cur:
            query = """
                SELECT
                    id, market_id, data_type, timeframe,
                    start_time, end_time, priority,
                    retry_count, max_retries, expected_records
                FROM backfill_tasks
                WHERE status = 'pending'
            """

            params = []
            if data_type:
                query += " AND data_type = %s"
                params.append(data_type)

            query += " ORDER BY priority DESC, created_at ASC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            rows = cur.fetchall()

        tasks = []
        for row in rows:
            tasks.append({
                'id': row[0],
                'market_id': row[1],
                'data_type': row[2],
                'timeframe': row[3],
                'start_time': row[4],
                'end_time': row[5],
                'priority': row[6],
                'retry_count': row[7],
                'max_retries': row[8],
                'expected_records': row[9]
            })

        return tasks

    def update_task_status(
        self,
        task_id: int,
        status: str,
        actual_records: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """
        更新任務狀態

        Args:
            task_id: 任務ID
            status: 新狀態 ('pending', 'running', 'completed', 'failed')
            actual_records: 實際獲取的記錄數（完成時提供）
            error_message: 錯誤訊息（失敗時提供）
        """
        with self.conn.cursor() as cur:
            if status == 'running':
                cur.execute(
                    """
                    UPDATE backfill_tasks
                    SET status = %s, started_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    """,
                    (status, task_id)
                )
            elif status == 'completed':
                cur.execute(
                    """
                    UPDATE backfill_tasks
                    SET status = %s, completed_at = NOW(),
                        actual_records = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (status, actual_records, task_id)
                )
            elif status == 'failed':
                cur.execute(
                    """
                    UPDATE backfill_tasks
                    SET status = %s, error_message = %s,
                        retry_count = retry_count + 1, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (status, error_message, task_id)
                )
            else:
                cur.execute(
                    """
                    UPDATE backfill_tasks
                    SET status = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (status, task_id)
                )

            self.conn.commit()

        logger.info(f"Task #{task_id} status updated to '{status}'")

    def retry_failed_tasks(self, max_tasks: int = 5) -> List[int]:
        """
        重試失敗的任務（若未超過最大重試次數）

        Args:
            max_tasks: 最多重試的任務數

        Returns:
            重設為 pending 的任務ID列表
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE backfill_tasks
                SET status = 'pending', updated_at = NOW()
                WHERE status = 'failed'
                  AND retry_count < max_retries
                  AND id IN (
                      SELECT id FROM backfill_tasks
                      WHERE status = 'failed'
                        AND retry_count < max_retries
                      ORDER BY priority DESC, created_at ASC
                      LIMIT %s
                  )
                RETURNING id
                """,
                (max_tasks,)
            )
            task_ids = [row[0] for row in cur.fetchall()]
            self.conn.commit()

        if task_ids:
            logger.info(f"Reset {len(task_ids)} failed tasks to pending")

        return task_ids

    def cleanup_old_completed_tasks(self, days: int = 7) -> int:
        """
        清理舊的已完成任務

        Args:
            days: 保留最近幾天的任務

        Returns:
            刪除的任務數
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM backfill_tasks
                WHERE status = 'completed'
                  AND completed_at < NOW() - INTERVAL '%s days'
                """,
                (days,)
            )
            deleted = cur.rowcount
            self.conn.commit()

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old completed tasks")

        return deleted

    @staticmethod
    def _get_interval_delta(timeframe: str) -> timedelta:
        """取得時間週期對應的 timedelta"""
        interval_map = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        return interval_map.get(timeframe, timedelta(hours=1))

    def close(self):
        """關閉資料庫連接"""
        if self.should_close_conn and self.conn:
            self.conn.close()
            logger.info("BackfillScheduler connection closed")

    def __enter__(self):
        """支援 context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """自動關閉連接"""
        self.close()


# 範例用法
if __name__ == "__main__":
    from datetime import timezone

    scheduler = BackfillScheduler()

    # 檢查 2024-12-01 到現在的資料缺失
    market_id = 1  # BTC/USDT on Binance
    timeframe = "1m"
    start = datetime(2024, 12, 1, tzinfo=timezone.utc)
    end = datetime.now(timezone.utc)

    # 檢查缺失並建立任務
    task_ids = scheduler.create_backfill_tasks_for_gaps(
        market_id, timeframe, start, end
    )

    print(f"Created {len(task_ids)} backfill tasks")

    # 查看待執行任務
    pending = scheduler.get_pending_tasks(limit=5)
    print(f"\nPending tasks: {len(pending)}")
    for task in pending:
        print(f"  Task #{task['id']}: {task['start_time']} - {task['end_time']}")

    scheduler.close()
