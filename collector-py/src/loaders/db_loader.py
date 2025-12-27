"""
資料庫載入器
負責將抓取的數據寫入TimescaleDB
"""
import psycopg2
from psycopg2.extras import execute_batch
from typing import List, Dict, Optional
from datetime import datetime, timezone
from loguru import logger

from config import settings


class DatabaseLoader:
    """資料庫載入器"""

    def __init__(self):
        """初始化資料庫連接"""
        self.conn = None
        self.connect()

    def connect(self):
        """建立資料庫連接"""
        try:
            self.conn = psycopg2.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                dbname=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def get_market_id(self, exchange_name: str, symbol: str) -> Optional[int]:
        """
        取得市場ID，若不存在則建立

        Args:
            exchange_name: 交易所名稱
            symbol: 交易對符號

        Returns:
            market_id
        """
        with self.conn.cursor() as cur:
            # 先取得exchange_id
            cur.execute(
                "SELECT id FROM exchanges WHERE name = %s",
                (exchange_name,)
            )
            row = cur.fetchone()
            if not row:
                logger.error(f"Exchange {exchange_name} not found")
                return None
            exchange_id = row[0]

            # 查詢或插入market
            cur.execute(
                """
                INSERT INTO markets (exchange_id, symbol, base_asset, quote_asset)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (exchange_id, symbol) DO NOTHING
                RETURNING id
                """,
                (exchange_id, symbol, symbol.split('/')[0], symbol.split('/')[1])
            )
            result = cur.fetchone()
            if result:
                market_id = result[0]
            else:
                # 已存在，查詢id
                cur.execute(
                    "SELECT id FROM markets WHERE exchange_id = %s AND symbol = %s",
                    (exchange_id, symbol)
                )
                market_id = cur.fetchone()[0]

            self.conn.commit()
            return market_id

    def insert_ohlcv_batch(
        self,
        market_id: int,
        timeframe: str,
        ohlcv_data: List[List]
    ) -> int:
        """
        批次插入OHLCV數據

        Args:
            market_id: 市場ID
            timeframe: 時間週期
            ohlcv_data: [[timestamp, open, high, low, close, volume], ...]

        Returns:
            插入的行數
        """
        if not ohlcv_data:
            return 0

        # 準備數據
        rows = []
        for candle in ohlcv_data:
            ts_ms, o, h, l, c, v = candle[:6]
            open_time = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            rows.append((market_id, timeframe, open_time, o, h, l, c, v))

        # 批次插入
        with self.conn.cursor() as cur:
            execute_batch(
                cur,
                """
                INSERT INTO ohlcv (
                    market_id, timeframe, open_time,
                    open, high, low, close, volume
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (market_id, timeframe, open_time)
                DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
                """,
                rows,
                page_size=500
            )
            self.conn.commit()

        logger.info(
            f"Inserted {len(rows)} {timeframe} candles for market_id={market_id}"
        )
        return len(rows)

    def insert_trades_batch(
        self,
        market_id: int,
        trades_data: List[Dict]
    ) -> int:
        """
        批次插入交易數據

        Args:
            market_id: 市場ID
            trades_data: ccxt返回的trades列表

        Returns:
            插入的行數
        """
        if not trades_data:
            return 0

        rows = []
        for trade in trades_data:
            trade_id = trade['id']
            price = trade['price']
            amount = trade['amount']
            side = trade['side']
            timestamp = datetime.fromtimestamp(trade['timestamp'] / 1000, tz=timezone.utc)
            rows.append((market_id, trade_id, price, amount, side, timestamp))

        with self.conn.cursor() as cur:
            execute_batch(
                cur,
                """
                INSERT INTO trades (
                    market_id, trade_id, price, quantity, side, timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (market_id, timestamp, trade_id) DO NOTHING
                """,
                rows,
                page_size=500
            )
            self.conn.commit()

        logger.info(f"Inserted {len(rows)} trades for market_id={market_id}")
        return len(rows)

    def insert_orderbook_batch(
        self,
        market_id: int,
        orderbook_data: List[Dict]
    ) -> int:
        """
        批次插入訂單簿快照

        Args:
            market_id: 市場ID
            orderbook_data: [{
                'timestamp': int (milliseconds),
                'bids': [[price, quantity], ...],
                'asks': [[price, quantity], ...]
            }, ...]

        Returns:
            插入的行數
        """
        if not orderbook_data:
            return 0

        import json

        rows = []
        for snapshot in orderbook_data:
            # 處理 timestamp 可能為 None 的情況
            ts = snapshot.get('timestamp')
            if ts is None:
                timestamp = datetime.now(tz=timezone.utc)
            else:
                timestamp = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)

            bids_json = json.dumps(snapshot['bids'])
            asks_json = json.dumps(snapshot['asks'])
            rows.append((market_id, timestamp, bids_json, asks_json))

        with self.conn.cursor() as cur:
            execute_batch(
                cur,
                """
                INSERT INTO orderbook_snapshots (
                    market_id, timestamp, bids, asks
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (market_id, timestamp)
                DO UPDATE SET
                    bids = EXCLUDED.bids,
                    asks = EXCLUDED.asks
                """,
                rows,
                page_size=500
            )
            self.conn.commit()

        logger.info(f"Inserted {len(rows)} orderbook snapshots for market_id={market_id}")
        return len(rows)

    def get_latest_ohlcv_time(
        self,
        market_id: int,
        timeframe: str
    ) -> Optional[datetime]:
        """
        獲取最新K線時間

        Args:
            market_id: 市場ID
            timeframe: 時間週期

        Returns:
            最新K線的open_time，若無數據則返回None
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT MAX(open_time)
                FROM ohlcv
                WHERE market_id = %s AND timeframe = %s
                """,
                (market_id, timeframe)
            )
            result = cur.fetchone()
            return result[0] if result else None

    def insert_quality_summary(
        self,
        market_id: int,
        data_type: str,
        timeframe: Optional[str],
        time_range_start: datetime,
        time_range_end: datetime,
        total_records: int,
        validation_result: Dict
    ) -> int:
        """
        插入資料品質摘要

        Args:
            market_id: 市場ID
            data_type: 資料類型
            timeframe: 時間週期（可選）
            time_range_start: 資料時間範圍開始
            time_range_end: 資料時間範圍結束
            total_records: 總記錄數
            validation_result: DataValidator 返回的驗證結果

        Returns:
            插入的記錄ID
        """
        import json

        # 統計各類錯誤數量
        missing_count = 0
        duplicate_count = 0
        out_of_order_count = 0
        price_jump_count = 0
        volume_spike_count = 0

        for error in validation_result.get('errors', []):
            if error['type'] == 'out_of_order_timestamp':
                out_of_order_count = error['count']

        for warning in validation_result.get('warnings', []):
            if warning['type'] == 'price_jump':
                price_jump_count = warning['count']
            elif warning['type'] == 'volume_spike':
                volume_spike_count = warning['count']
            elif warning['type'] == 'missing_interval':
                missing_count = sum(
                    gap['missing_count']
                    for gap in warning.get('details', [])
                )

        # 計算品質分數
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT calculate_quality_score(%s, %s, %s, %s, %s, %s)
                """,
                (total_records, missing_count, duplicate_count,
                 out_of_order_count, price_jump_count, volume_spike_count)
            )
            quality_score = cur.fetchone()[0]

        # 插入摘要
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO data_quality_summary (
                    market_id, data_type, timeframe, check_time,
                    time_range_start, time_range_end, total_records,
                    missing_count, duplicate_count, out_of_order_count,
                    price_jump_count, volume_spike_count,
                    quality_score, is_valid,
                    validation_errors, validation_warnings
                )
                VALUES (
                    %s, %s, %s, NOW(),
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s
                )
                RETURNING id
                """,
                (
                    market_id, data_type, timeframe,
                    time_range_start, time_range_end, total_records,
                    missing_count, duplicate_count, out_of_order_count,
                    price_jump_count, volume_spike_count,
                    quality_score, validation_result.get('valid', True),
                    json.dumps(validation_result.get('errors', [])),
                    json.dumps(validation_result.get('warnings', []))
                )
            )
            summary_id = cur.fetchone()[0]
            self.conn.commit()

        logger.info(
            f"Inserted quality summary #{summary_id}: "
            f"market_id={market_id}, score={quality_score:.2f}"
        )
        return summary_id

    def close(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """支援context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """自動關閉連接"""
        self.close()
