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
        self.backfill_scheduler = backfill_scheduler or BackfillScheduler(
            db_conn=self.db.conn
        )

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
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=lookback_hours)

        # 從資料庫抓取資料
        ohlcv_data = self._fetch_ohlcv_from_db(
            market_id, timeframe, start_time, end_time
        )

        if not ohlcv_data:
            logger.warning(f"No OHLCV data found for quality check")
            return {
                'market_id': market_id,
                'timeframe': timeframe,
                'total_records': 0,
                'valid': False,
                'errors': [{'type': 'no_data', 'message': 'No data in range'}],
                'warnings': []
            }

        # 執行品質驗證
        validation_result = self.validator.validate_ohlcv_batch(
            ohlcv_data, timeframe
        )

        # 記錄品質摘要到資料庫
        self.db.insert_quality_summary(
            market_id=market_id,
            data_type='ohlcv',
            timeframe=timeframe,
            time_range_start=start_time,
            time_range_end=end_time,
            total_records=len(ohlcv_data),
            validation_result=validation_result
        )

        # 如果需要，建立補資料任務
        if create_backfill_tasks:
            self._create_backfill_tasks_from_validation(
                market_id, timeframe, validation_result
            )

        logger.info(
            f"Quality check completed: "
            f"records={validation_result['total_records']}, "
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
        with self.db.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    EXTRACT(EPOCH FROM open_time) * 1000,
                    open, high, low, close, volume
                FROM ohlcv
                WHERE market_id = %s
                  AND timeframe = %s
                  AND open_time >= %s
                  AND open_time < %s
                ORDER BY open_time ASC
                """,
                (market_id, timeframe, start_time, end_time)
            )
            rows = cur.fetchall()

        return [list(row) for row in rows]

    def _get_active_markets(self) -> List[Dict]:
        """
        取得所有活躍市場

        Returns:
            市場列表 [{'id': int, 'symbol': str, 'exchange': str}, ...]
        """
        with self.db.conn.cursor() as cur:
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
        生成品質報告

        Args:
            market_id: 市場ID（可選，None 表示所有市場）
            hours: 統計時間範圍（小時）

        Returns:
            品質報告字典
        """
        with self.db.conn.cursor() as cur:
            if market_id:
                cur.execute(
                    """
                    SELECT
                        AVG(quality_score) AS avg_score,
                        MIN(quality_score) AS min_score,
                        MAX(quality_score) AS max_score,
                        COUNT(*) AS total_checks,
                        SUM(CASE WHEN is_valid = FALSE THEN 1 ELSE 0 END) AS failed_checks,
                        SUM(missing_count) AS total_missing,
                        SUM(out_of_order_count) AS total_out_of_order,
                        SUM(price_jump_count) AS total_price_jumps
                    FROM data_quality_summary
                    WHERE market_id = %s
                      AND check_time >= NOW() - INTERVAL '%s hours'
                    """,
                    (market_id, hours)
                )
            else:
                cur.execute(
                    """
                    SELECT
                        AVG(quality_score) AS avg_score,
                        MIN(quality_score) AS min_score,
                        MAX(quality_score) AS max_score,
                        COUNT(*) AS total_checks,
                        SUM(CASE WHEN is_valid = FALSE THEN 1 ELSE 0 END) AS failed_checks,
                        SUM(missing_count) AS total_missing,
                        SUM(out_of_order_count) AS total_out_of_order,
                        SUM(price_jump_count) AS total_price_jumps
                    FROM data_quality_summary
                    WHERE check_time >= NOW() - INTERVAL '%s hours'
                    """,
                    (hours,)
                )

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

    print(f"Quality check result:")
    print(f"  Total records: {result['total_records']}")
    print(f"  Valid: {result['valid']}")
    print(f"  Errors: {len(result['errors'])}")
    print(f"  Warnings: {len(result['warnings'])}")

    # 生成品質報告
    report = checker.generate_quality_report(market_id=1, hours=24)
    print(f"\nQuality report (last 24h):")
    print(f"  Average score: {report['avg_score']:.2f}")
    print(f"  Total checks: {report['total_checks']}")
    print(f"  Failed checks: {report['failed_checks']}")
    print(f"  Total missing: {report['total_missing']}")

    checker.close()
