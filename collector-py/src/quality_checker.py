"""
資料品質檢查任務
職責：
1. 定期檢查已收集的資料品質
2. 發現缺失區段並建立補資料任務
3. 記錄品質摘要到資料庫
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from loguru import logger

from loaders.db_loader import DatabaseLoader
from validators.data_validator import DataValidator
from schedulers.backfill_scheduler import BackfillScheduler


class DataQualityChecker:
    """
    資料品質檢查器

    功能：
    - 檢查指定市場與時間週期的資料品質
    - 自動建立補資料任務
    - 記錄品質報告
    """

    def __init__(
        self,
        db_loader: Optional[DatabaseLoader] = None,
        validator: Optional[DataValidator] = None,
        backfill_scheduler: Optional[BackfillScheduler] = None
    ):
        """
        初始化品質檢查器

        Args:
            db_loader: 資料庫載入器
            validator: 資料驗證器
            backfill_scheduler: 補資料排程器
        """
        self.db = db_loader or DatabaseLoader()
        self.validator = validator or DataValidator()
        # BackfillScheduler 會建立自己的連接
        self.backfill_scheduler = backfill_scheduler or BackfillScheduler()

        logger.info("DataQualityChecker initialized")

    def check_ohlcv_quality(
        self,
        market_id: int,
        timeframe: str,
        lookback_hours: int = 24,
        create_backfill_tasks: bool = True
    ) -> Dict:
        """
        檢查 OHLCV 資料品質

        Args:
            market_id: 市場ID
            timeframe: 時間週期
            lookback_hours: 往回檢查的小時數
            create_backfill_tasks: 是否自動建立補資料任務

        Returns:
            品質檢查結果字典
        """
        logger.info(
            f"Checking OHLCV quality: market_id={market_id}, "
            f"timeframe={timeframe}, lookback={lookback_hours}h"
        )

        # 確定檢查時間範圍
        check_time = datetime.now(timezone.utc)
        end_time = check_time
        start_time = end_time - timedelta(hours=lookback_hours)

        # 串流驗證以降低記憶體使用
        row_iter = self._iter_ohlcv_from_db(
            market_id, timeframe, start_time, end_time
        )
        validation_result = self.validator.validate_ohlcv_stream(
            row_iter, timeframe, check_missing_intervals=False
        )

        actual_count = validation_result.get('total_records', 0)
        
        # 計算預期記錄數（無論是否有資料都要計算）
        expected_count = self._calculate_expected_count(
            start_time, end_time, timeframe
        )
        
        if actual_count == 0:
            logger.warning(
                f"No OHLCV data found for quality check "
                f"(expected {expected_count} records)"
            )
            
            # 當沒有資料時，自動建立補資料任務
            backfill_created = False
            if expected_count > 0:
                try:
                    task_id = self.backfill_scheduler.create_backfill_task(
                        market_id=market_id,
                        data_type='ohlcv',
                        timeframe=timeframe,
                        start_time=start_time,
                        end_time=end_time,
                        priority=2,  # 高優先級
                        expected_records=expected_count
                    )
                    backfill_created = True
                    logger.info(
                        f"Created backfill task (task_id={task_id}) for "
                        f"market_id={market_id}, timeframe={timeframe}, "
                        f"range: {start_time} to {end_time}"
                    )
                except Exception as e:
                    logger.error(f"Failed to create backfill task: {e}")
            
            # 寫入品質指標（無資料情況）
            self.db.insert_quality_metrics(
                market_id=market_id,
                timeframe=timeframe,
                check_time=check_time,
                start_time=start_time,
                end_time=end_time,
                expected_count=expected_count,
                actual_count=0,
                missing_count=expected_count,
                missing_rate=1.0,  # 100% 缺失
                issues=[{
                    'type': 'no_data',
                    'message': f'No data in time range (expected {expected_count} records)'
                }],
                backfill_task_created=backfill_created
            )
            return {
                'market_id': market_id,
                'timeframe': timeframe,
                'total_records': 0,
                'valid': False,
                'errors': [{'type': 'no_data', 'message': 'No data in range'}],
                'warnings': []
            }

        # 檢查缺失區間
        missing_intervals = self._fetch_missing_intervals_sql(
            market_id, timeframe, start_time, end_time
        )
        
        missing_count = 0
        if missing_intervals:
            warnings = validation_result.get('warnings', [])
            warnings.append({
                'type': 'missing_interval',
                'count': len(missing_intervals),
                'details': missing_intervals[:10]
            })
            validation_result['warnings'] = warnings
            
            # 計算總缺失數
            missing_count_from_gaps = sum(gap['missing_count'] for gap in missing_intervals)
        else:
            missing_count_from_gaps = 0

        # 計算最終缺失數
        # 取 "中間斷層缺失" 與 "總量預期缺失" 的較大值，以涵蓋頭尾缺失的情況
        # 注意：由於資料庫有唯一約束，actual_count 不會包含重複時間戳
        missing_count = max(missing_count_from_gaps, expected_count - actual_count)
        missing_count = max(0, missing_count)  # 確保不為負數

        # 計算缺失率
        missing_rate = missing_count / expected_count if expected_count > 0 else 0.0

        # 統計其他錯誤類型
        duplicate_count = 0
        timestamp_error_count = 0
        issues = []

        for error in validation_result.get('errors', []):
            if error['type'] == 'out_of_order_timestamp':
                timestamp_error_count = error.get('count', 1)
                issues.append({
                    'type': 'timestamp_order',
                    'severity': 'error',
                    'count': timestamp_error_count,
                    'message': error.get('message', 'Timestamps not in order')
                })

        for warning in validation_result.get('warnings', []):
            if warning['type'] == 'missing_interval':
                for gap in warning.get('details', [])[:5]:  # 只記錄前5個
                    issues.append({
                        'type': 'missing_data',
                        'severity': 'warning',
                        'start_time': gap['start_time'].isoformat() if isinstance(gap['start_time'], datetime) else str(gap['start_time']),
                        'end_time': gap['end_time'].isoformat() if isinstance(gap['end_time'], datetime) else str(gap['end_time']),
                        'missing_count': gap['missing_count']
                    })
            elif warning['type'] == 'price_jump':
                issues.append({
                    'type': 'price_anomaly',
                    'severity': 'warning',
                    'count': warning.get('count', 1),
                    'message': 'Abnormal price jumps detected'
                })
            elif warning['type'] == 'volume_spike':
                issues.append({
                    'type': 'volume_anomaly',
                    'severity': 'warning',
                    'count': warning.get('count', 1),
                    'message': 'Abnormal volume spikes detected'
                })

        # 決定是否建立補資料任務（當缺失率超過 3% 時）
        should_create_backfill = create_backfill_tasks and missing_rate > 0.03
        
        if should_create_backfill:
            self._create_backfill_tasks_from_validation(
                market_id, timeframe, validation_result
            )

        # 寫入新的品質指標表
        self.db.insert_quality_metrics(
            market_id=market_id,
            timeframe=timeframe,
            check_time=check_time,
            start_time=start_time,
            end_time=end_time,
            expected_count=expected_count,
            actual_count=actual_count,
            missing_count=missing_count,
            missing_rate=missing_rate,
            duplicate_count=duplicate_count,
            timestamp_error_count=timestamp_error_count,
            issues=issues,
            backfill_task_created=should_create_backfill
        )

        logger.info(
            f"Quality check completed: "
            f"records={actual_count}/{expected_count}, "
            f"missing_rate={missing_rate*100:.2f}%, "
            f"valid={validation_result['valid']}, "
            f"errors={len(validation_result['errors'])}, "
            f"warnings={len(validation_result['warnings'])}"
        )

        return validation_result

    def check_all_active_markets(
        self,
        timeframe: str = "1m",
        lookback_hours: int = 24,
        create_backfill_tasks: bool = True
    ) -> List[Dict]:
        """
        檢查所有活躍市場的資料品質

        Args:
            timeframe: 時間週期
            lookback_hours: 往回檢查的小時數
            create_backfill_tasks: 是否自動建立補資料任務

        Returns:
            所有市場的品質檢查結果列表
        """
        logger.info(f"Checking quality for all active markets: timeframe={timeframe}")

        # 取得所有活躍市場
        active_markets = self._get_active_markets()

        results = []
        for market in active_markets:
            market_id = market['id']
            symbol = market['symbol']

            try:
                result = self.check_ohlcv_quality(
                    market_id=market_id,
                    timeframe=timeframe,
                    lookback_hours=lookback_hours,
                    create_backfill_tasks=create_backfill_tasks
                )
                result['symbol'] = symbol
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to check quality for {symbol}: {e}")
                results.append({
                    'market_id': market_id,
                    'symbol': symbol,
                    'error': str(e)
                })

        logger.info(f"Completed quality check for {len(results)} markets")
        return results

    def _fetch_ohlcv_from_db(
        self,
        market_id: int,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[List]:
        """
        從資料庫抓取 OHLCV 資料

        Args:
            market_id: 市場ID
            timeframe: 時間週期
            start_time: 起始時間
            end_time: 結束時間

        Returns:
            OHLCV 資料列表 [[timestamp_ms, open, high, low, close, volume], ...]
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        EXTRACT(EPOCH FROM time) * 1000,
                        open, high, low, close, volume
                    FROM ohlcv
                    WHERE market_id = %s
                      AND timeframe = %s
                      AND time >= %s
                      AND time < %s
                    ORDER BY time ASC
                    """,
                    (market_id, timeframe, start_time, end_time)
                )
                rows = cur.fetchall()

        return [list(row) for row in rows]

    def _fetch_missing_intervals_sql(
        self,
        market_id: int,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        使用 SQL 端計算缺失區間，避免搬運大量資料到應用層
        """
        interval_map = {
            '1m': '1 minute',
            '5m': '5 minutes',
            '15m': '15 minutes',
            '1h': '1 hour',
            '4h': '4 hours',
            '1d': '1 day'
        }
        interval_literal = interval_map.get(timeframe, '1 minute')

        query = f"""
            WITH ordered AS (
                SELECT
                    time,
                    LAG(time) OVER (ORDER BY time) AS prev_time
                FROM ohlcv
                WHERE market_id = %s
                  AND timeframe = %s
                  AND time >= %s
                  AND time < %s
            )
            SELECT
                prev_time AS start_time,
                time AS end_time,
                (EXTRACT(EPOCH FROM (time - prev_time))
                 / EXTRACT(EPOCH FROM INTERVAL '{interval_literal}'))::int - 1
                 AS missing_count,
                (time - prev_time) AS actual_interval
            FROM ordered
            WHERE prev_time IS NOT NULL
              AND time - prev_time > INTERVAL '{interval_literal}' * 1.5
            ORDER BY start_time
        """

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (market_id, timeframe, start_time, end_time)
                )
                rows = cur.fetchall()

        return [
            {
                'start_time': row[0],
                'end_time': row[1],
                'missing_count': row[2],
                'actual_interval': row[3]
            }
            for row in rows
        ]

    def _iter_ohlcv_from_db(
        self,
        market_id: int,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ):
        """
        串流取得 OHLCV 資料，避免一次載入記憶體

        Returns:
            iterator yielding [timestamp_ms, open, high, low, close, volume]
        """
        with self.db.get_connection() as conn:
            with conn.cursor(name='ohlcv_stream') as cur:
                cur.itersize = 10000
                cur.execute(
                    """
                    SELECT
                        EXTRACT(EPOCH FROM time) * 1000,
                        open, high, low, close, volume
                    FROM ohlcv
                    WHERE market_id = %s
                      AND timeframe = %s
                      AND time >= %s
                      AND time < %s
                    ORDER BY time ASC
                    """,
                    (market_id, timeframe, start_time, end_time)
                )
                for row in cur:
                    # 轉換 Decimal timestamp 為 int
                    yield [int(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])]

    def _get_active_markets(self) -> List[Dict]:
        """
        取得所有活躍市場

        Returns:
            市場列表 [{'id': int, 'symbol': str, 'exchange': str}, ...]
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT m.id, m.symbol, e.name AS exchange
                    FROM markets m
                    JOIN exchanges e ON m.exchange_id = e.id
                    WHERE m.is_active = TRUE
                    ORDER BY m.id
                    """
                )
                rows = cur.fetchall()

        return [
            {'id': row[0], 'symbol': row[1], 'exchange': row[2]}
            for row in rows
        ]

    def _calculate_expected_count(
        self,
        start_time: datetime,
        end_time: datetime,
        timeframe: str
    ) -> int:
        """
        計算給定時間範圍內預期的 K 線數量

        Args:
            start_time: 起始時間
            end_time: 結束時間
            timeframe: 時間週期

        Returns:
            預期的 K 線數量
        """
        # 將 timeframe 轉換為秒數
        interval_seconds = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }.get(timeframe, 60)

        # 計算時間差（秒）
        time_diff = (end_time - start_time).total_seconds()

        # 計算預期數量（無條件進位）
        expected = int(time_diff / interval_seconds)

        return expected

    def _create_backfill_tasks_from_validation(
        self,
        market_id: int,
        timeframe: str,
        validation_result: Dict
    ):
        """
        根據驗證結果建立補資料任務

        Args:
            market_id: 市場ID
            timeframe: 時間週期
            validation_result: 驗證結果
        """
        # 檢查是否有缺失區間警告
        for warning in validation_result.get('warnings', []):
            if warning['type'] == 'missing_interval':
                gaps = warning.get('details', [])

                for gap in gaps:
                    task_id = self.backfill_scheduler.create_backfill_task(
                        market_id=market_id,
                        data_type='ohlcv',
                        timeframe=timeframe,
                        start_time=gap['start_time'],
                        end_time=gap['end_time'],
                        priority=5,
                        expected_records=gap['missing_count']
                    )

                    logger.info(
                        f"Created backfill task #{task_id} for gap: "
                        f"{gap['start_time']} - {gap['end_time']}"
                    )

    def generate_quality_report(
        self,
        market_id: Optional[int] = None,
        hours: int = 24
    ) -> Dict:
        """
        生成品質報告 (V3 Schema: 從 system_logs 讀取)

        Args:
            market_id: 市場ID（可選，None 表示所有市場）
            hours: 統計時間範圍（小時）

        Returns:
            品質報告字典
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                # 從 system_logs 中提取 LEVEL='QUALITY' 的記錄
                # 並從 metadata JSONB 中提取數值
                query = """
                    SELECT
                        AVG(value) AS avg_score,
                        MIN(value) AS min_score,
                        MAX(value) AS max_score,
                        COUNT(*) AS total_checks,
                        SUM(CASE WHEN (metadata->>'missing_rate')::numeric > 0.05 THEN 1 ELSE 0 END) AS failed_checks,
                        SUM((metadata->>'missing_count')::numeric) AS total_missing,
                        0 AS total_out_of_order, -- V3 簡化，暫不追蹤
                        0 AS total_price_jumps   -- V3 簡化，暫不追蹤
                    FROM system_logs
                    WHERE level = 'QUALITY'
                      AND module = 'collector'
                      AND time >= NOW() - INTERVAL '%s hours'
                """
                
                params = [hours]
                if market_id:
                    query += " AND (metadata->>'market_id')::int = %s"
                    params.append(market_id)

                cur.execute(query, tuple(params))
                row = cur.fetchone()

        return {
            'market_id': market_id,
            'hours': hours,
            'avg_score': float(row[0]) if row[0] else 0.0,
            'min_score': float(row[1]) if row[1] else 0.0,
            'max_score': float(row[2]) if row[2] else 0.0,
            'total_checks': row[3] or 0,
            'failed_checks': row[4] or 0,
            'total_missing': row[5] or 0,
            'total_out_of_order': row[6] or 0,
            'total_price_jumps': row[7] or 0
        }

    def close(self):
        """關閉資源"""
        self.db.close()
        self.backfill_scheduler.close()


# 範例用法
if __name__ == "__main__":
    checker = DataQualityChecker()

    # 檢查單一市場
    result = checker.check_ohlcv_quality(
        market_id=1,  # BTC/USDT on Binance
        timeframe="1m",
        lookback_hours=24,
        create_backfill_tasks=True
    )

    logger.info("Quality check result:")
    logger.info(f"  Total records: {result['total_records']}")
    logger.info(f"  Valid: {result['valid']}")
    logger.info(f"  Errors: {len(result['errors'])}")
    logger.info(f"  Warnings: {len(result['warnings'])}")

    # 生成品質報告
    report = checker.generate_quality_report(market_id=1, hours=24)
    logger.info("Quality report (last 24h):")
    logger.info(f"  Average score: {report['avg_score']:.2f}")
    logger.info(f"  Total checks: {report['total_checks']}")
    logger.info(f"  Failed checks: {report['failed_checks']}")
    logger.info(f"  Total missing: {report['total_missing']}")

    checker.close()
