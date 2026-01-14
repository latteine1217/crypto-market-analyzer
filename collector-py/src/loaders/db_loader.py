"""
資料庫載入器
負責將抓取的數據寫入TimescaleDB
使用連接池管理資料庫連接
"""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_batch
from typing import List, Dict, Optional
from datetime import datetime, timezone
from contextlib import contextmanager
from loguru import logger

from config import settings
from utils.symbol_utils import parse_symbol, normalize_symbol


class DatabaseLoader:
    """資料庫載入器（使用連接池）"""

    # 類級別的連接池（所有實例共享）
    _connection_pool = None
    _pool_lock = None

    def __init__(self, min_conn: int = 2, max_conn: int = 10):
        """
        初始化資料庫載入器

        Args:
            min_conn: 最小連接數
            max_conn: 最大連接數
        """
        self.min_conn = min_conn
        self.max_conn = max_conn

        # 確保連接池已初始化
        if DatabaseLoader._connection_pool is None:
            self._init_connection_pool()

        # 保持向後兼容性的屬性
        self.conn = None

    def _init_connection_pool(self):
        """初始化連接池（線程安全）"""
        import threading

        if DatabaseLoader._pool_lock is None:
            DatabaseLoader._pool_lock = threading.Lock()

        with DatabaseLoader._pool_lock:
            if DatabaseLoader._connection_pool is None:
                try:
                    DatabaseLoader._connection_pool = pool.ThreadedConnectionPool(
                        minconn=self.min_conn,
                        maxconn=self.max_conn,
                        host=settings.postgres_host,
                        port=settings.postgres_port,
                        dbname=settings.postgres_db,
                        user=settings.postgres_user,
                        password=settings.postgres_password,
                        connect_timeout=10,
                        options='-c statement_timeout=30000'  # 30秒事務超時
                    )
                    logger.info(
                        f"Database connection pool initialized "
                        f"(min={self.min_conn}, max={self.max_conn})"
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize connection pool: {e}")
                    raise

    @contextmanager
    def get_connection(self):
        """
        從連接池獲取連接（context manager）

        使用方式:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
        """
        conn = None
        try:
            conn = DatabaseLoader._connection_pool.getconn()
            # 測試連接是否有效
            conn.isolation_level
            yield conn
        except psycopg2.OperationalError as e:
            logger.warning(f"Connection from pool is invalid: {e}")
            # 關閉無效連接
            if conn:
                try:
                    DatabaseLoader._connection_pool.putconn(conn, close=True)
                except:
                    pass
            # 獲取新連接
            conn = DatabaseLoader._connection_pool.getconn()
            yield conn
        finally:
            if conn:
                DatabaseLoader._connection_pool.putconn(conn)

    # 為了向後相容，保留舊的方法名
    def connect(self):
        """建立資料庫連接（為了向後相容）"""
        if DatabaseLoader._connection_pool is None:
            self._init_connection_pool()
        logger.info("Database connection pool ready")

    def ensure_connection(self):
        """
        確保連接池可用（為了向後相容）
        """
        if DatabaseLoader._connection_pool is None:
            self._init_connection_pool()

        # 測試連接池
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
        except Exception as e:
            logger.error(f"Connection pool test failed: {e}")
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
        self.ensure_connection()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
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

                # 解析 symbol 為 base 和 quote asset
                try:
                    base_asset, quote_asset = parse_symbol(symbol)
                except ValueError as e:
                    logger.error(f"Failed to parse symbol: {e}")
                    return None
                
                # 標準化 symbol 為交易所原生格式 (無斜線)
                normalized_symbol = normalize_symbol(symbol)
                
                # 查詢或插入market
                cur.execute(
                    """
                    INSERT INTO markets (exchange_id, symbol, base_asset, quote_asset)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (exchange_id, symbol) DO NOTHING
                    RETURNING id
                    """,
                    (exchange_id, normalized_symbol, base_asset, quote_asset)
                )
                result = cur.fetchone()
                if result:
                    market_id = result[0]
                else:
                    # 已存在，查詢id
                    cur.execute(
                        "SELECT id FROM markets WHERE exchange_id = %s AND symbol = %s",
                        (exchange_id, normalized_symbol)
                    )
                    market_id = cur.fetchone()[0]

                conn.commit()
                return market_id

    def get_market_info(self, market_id: int) -> Optional[Dict]:
        """
        根據 market_id 取得市場資訊
        
        Args:
            market_id: 市場ID
            
        Returns:
            market 資訊字典 {'exchange': str, 'symbol': str, 'base_asset': str, 'quote_asset': str}
            若不存在則返回 None
        """
        self.ensure_connection()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT e.name as exchange, m.symbol, m.base_asset, m.quote_asset
                    FROM markets m
                    JOIN exchanges e ON m.exchange_id = e.id
                    WHERE m.id = %s
                    """,
                    (market_id,)
                )
                row = cur.fetchone()
                if row:
                    return {
                        'exchange': row[0],
                        'symbol': row[1],
                        'base_asset': row[2],
                        'quote_asset': row[3]
                    }
                return None

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

        self.ensure_connection()
        # 準備數據
        rows = []
        for candle in ohlcv_data:
            ts_ms, o, h, l, c, v = candle[:6]
            open_time = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            rows.append((market_id, timeframe, open_time, o, h, l, c, v))

        # 批次插入
        with self.get_connection() as conn:
            with conn.cursor() as cur:
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
                conn.commit()

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

        self.ensure_connection()
        rows = []
        for trade in trades_data:
            trade_id = trade['id']
            price = trade['price']
            amount = trade['amount']
            side = trade['side']
            timestamp = datetime.fromtimestamp(trade['timestamp'] / 1000, tz=timezone.utc)
            rows.append((market_id, trade_id, price, amount, side, timestamp))

        with self.get_connection() as conn:
            with conn.cursor() as cur:
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
                conn.commit()

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

        self.ensure_connection()
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

        with self.get_connection() as conn:
            with conn.cursor() as cur:
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
                conn.commit()

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
        self.ensure_connection()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
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
        插入資料品質摘要（舊表，保持向後相容）

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
        self.ensure_connection()
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

        # 計算品質分數與插入摘要
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # 計算品質分數
                cur.execute(
                    """
                    SELECT calculate_quality_score(%s, %s, %s, %s, %s, %s)
                    """,
                    (total_records, missing_count, duplicate_count,
                     out_of_order_count, price_jump_count, volume_spike_count)
                )
                quality_score = cur.fetchone()[0]

            with conn.cursor() as cur:
                # 插入摘要
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
                conn.commit()

        logger.info(
            f"Inserted quality summary #{summary_id}: "
            f"market_id={market_id}, score={quality_score:.2f}"
        )
        return summary_id

    def insert_quality_metrics(
        self,
        market_id: int,
        timeframe: str,
        check_time: datetime,
        start_time: datetime,
        end_time: datetime,
        expected_count: int,
        actual_count: int,
        missing_count: int,
        missing_rate: float,
        duplicate_count: int = 0,
        timestamp_error_count: int = 0,
        quality_score: Optional[float] = None,
        status: Optional[str] = None,
        issues: Optional[List[Dict]] = None,
        backfill_task_created: bool = False
    ) -> int:
        """
        插入資料品質指標（新表，用於量化驗收標準）

        Args:
            market_id: 市場ID
            timeframe: 時間週期
            check_time: 檢查時間
            start_time: 資料起始時間
            end_time: 資料結束時間
            expected_count: 預期記錄數
            actual_count: 實際記錄數
            missing_count: 缺失記錄數
            missing_rate: 缺失率（0-1）
            duplicate_count: 重複記錄數
            timestamp_error_count: 時間戳錯誤數
            quality_score: 品質分數（0-100），若為None則自動計算
            status: 品質狀態（excellent/good/acceptable/poor/critical），若為None則自動判定
            issues: 問題列表（JSONB格式）
            backfill_task_created: 是否已建立補資料任務

        Returns:
            插入的記錄ID
        """
        self.ensure_connection()
        import json

        # 計算率值
        duplicate_rate = duplicate_count / actual_count if actual_count > 0 else 0
        timestamp_error_rate = timestamp_error_count / actual_count if actual_count > 0 else 0

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # 如果未提供 quality_score，使用 SQL 函數計算
                if quality_score is None:
                    cur.execute(
                        "SELECT calculate_quality_score(%s, %s, %s)",
                        (missing_rate, duplicate_rate, timestamp_error_rate)
                    )
                    quality_score = cur.fetchone()[0]

                # 如果未提供 status，使用 SQL 函數判定
                if status is None:
                    cur.execute(
                        "SELECT calculate_quality_status(%s)",
                        (missing_rate,)
                    )
                    status = cur.fetchone()[0]

            with conn.cursor() as cur:
                # 插入指標
                cur.execute(
                    """
                    INSERT INTO data_quality_metrics (
                        market_id, timeframe, check_time,
                        start_time, end_time,
                        expected_count, actual_count, missing_count,
                        missing_rate, duplicate_count, duplicate_rate, timestamp_error_rate,
                        quality_score, status,
                        issues, backfill_task_created
                    )
                    VALUES (
                        %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s
                    )
                    RETURNING id
                    """,
                    (
                        market_id, timeframe, check_time,
                        start_time, end_time,
                        expected_count, actual_count, missing_count,
                        missing_rate, duplicate_count, duplicate_rate, timestamp_error_rate,
                        quality_score, status,
                        json.dumps(issues or []), backfill_task_created
                    )
                )
                metrics_id = cur.fetchone()[0]
                conn.commit()

        logger.info(
            f"Inserted quality metrics #{metrics_id}: "
            f"market_id={market_id}, timeframe={timeframe}, "
            f"missing_rate={missing_rate:.4f} ({missing_rate*100:.2f}%), "
            f"score={quality_score:.2f}, status={status}"
        )
        return metrics_id

    def insert_funding_rate(
        self,
        market_id: int,
        funding_data: Dict
    ) -> int:
        """
        插入單筆資金費率記錄

        Args:
            market_id: 市場ID
            funding_data: {
                'funding_rate': float,
                'funding_rate_daily': float,
                'funding_time': datetime,
                'next_funding_time': datetime (optional),
                'funding_interval': int (optional),
                'mark_price': float (optional),
                'index_price': float (optional)
            }

        Returns:
            插入的記錄ID
        """
        self.ensure_connection()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO funding_rates (
                        market_id, funding_rate, funding_rate_daily,
                        funding_time, next_funding_time, funding_interval,
                        mark_price, index_price
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (market_id, funding_time) DO UPDATE SET
                        funding_rate = EXCLUDED.funding_rate,
                        funding_rate_daily = EXCLUDED.funding_rate_daily,
                        next_funding_time = EXCLUDED.next_funding_time,
                        funding_interval = EXCLUDED.funding_interval,
                        mark_price = EXCLUDED.mark_price,
                        index_price = EXCLUDED.index_price
                    RETURNING id
                    """,
                    (
                        market_id,
                        funding_data['funding_rate'],
                        funding_data.get('funding_rate_daily'),
                        funding_data['funding_time'],
                        funding_data.get('next_funding_time'),
                        funding_data.get('funding_interval'),
                        funding_data.get('mark_price'),
                        funding_data.get('index_price')
                    )
                )
                record_id = cur.fetchone()[0]
                conn.commit()

        logger.debug(f"Inserted funding rate #{record_id} for market_id={market_id}")
        return record_id

    def insert_funding_rate_batch(
        self,
        market_id: int,
        funding_data_list: List[Dict]
    ) -> int:
        """
        批次插入資金費率記錄

        Args:
            market_id: 市場ID
            funding_data_list: List of funding_data dicts

        Returns:
            插入的行數
        """
        if not funding_data_list:
            return 0

        self.ensure_connection()
        rows = []
        for data in funding_data_list:
            rows.append((
                market_id,
                data['funding_rate'],
                data.get('funding_rate_daily'),
                data['funding_time'],
                data.get('next_funding_time'),
                data.get('funding_interval'),
                data.get('mark_price'),
                data.get('index_price')
            ))

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(
                    cur,
                    """
                    INSERT INTO funding_rates (
                        market_id, funding_rate, funding_rate_daily,
                        funding_time, next_funding_time, funding_interval,
                        mark_price, index_price
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (market_id, funding_time) DO UPDATE SET
                        funding_rate = EXCLUDED.funding_rate,
                        funding_rate_daily = EXCLUDED.funding_rate_daily,
                        next_funding_time = EXCLUDED.next_funding_time,
                        funding_interval = EXCLUDED.funding_interval,
                        mark_price = EXCLUDED.mark_price,
                        index_price = EXCLUDED.index_price
                    """,
                    rows,
                    page_size=500
                )
                conn.commit()

        logger.info(f"Inserted {len(rows)} funding rates for market_id={market_id}")
        return len(rows)

    def insert_open_interest(
        self,
        market_id: int,
        oi_data: Dict
    ) -> int:
        """
        插入單筆未平倉量記錄

        Args:
            market_id: 市場ID
            oi_data: {
                'open_interest': float,
                'open_interest_usd': float (optional),
                'timestamp': datetime,
                'price': float (optional)
            }

        Returns:
            插入的記錄ID
        """
        self.ensure_connection()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO open_interest (
                        market_id, open_interest, open_interest_usd,
                        price, timestamp
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (market_id, timestamp) DO UPDATE SET
                        open_interest = EXCLUDED.open_interest,
                        open_interest_usd = EXCLUDED.open_interest_usd,
                        price = EXCLUDED.price
                    RETURNING id
                    """,
                    (
                        market_id,
                        oi_data['open_interest'],
                        oi_data.get('open_interest_usd'),
                        oi_data.get('price'),
                        oi_data['timestamp']
                    )
                )
                record_id = cur.fetchone()[0]
                conn.commit()

        logger.debug(f"Inserted open interest #{record_id} for market_id={market_id}")
        return record_id

    def insert_open_interest_batch(
        self,
        market_id: int,
        oi_data_list: List[Dict]
    ) -> int:
        """
        批次插入未平倉量記錄

        Args:
            market_id: 市場ID
            oi_data_list: List of oi_data dicts

        Returns:
            插入的行數
        """
        if not oi_data_list:
            return 0

        self.ensure_connection()
        rows = []
        for data in oi_data_list:
            rows.append((
                market_id,
                data['open_interest'],
                data.get('open_interest_usd'),
                data.get('price'),
                data['timestamp']
            ))

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(
                    cur,
                    """
                    INSERT INTO open_interest (
                        market_id, open_interest, open_interest_usd,
                        price, timestamp
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (market_id, timestamp) DO UPDATE SET
                        open_interest = EXCLUDED.open_interest,
                        open_interest_usd = EXCLUDED.open_interest_usd,
                        price = EXCLUDED.price
                    """,
                    rows,
                    page_size=500
                )
                conn.commit()

        logger.info(f"Inserted {len(rows)} open interest records for market_id={market_id}")
        return len(rows)

    def close(self):
        """關閉連接池（通常不需要調用，除非程序退出）"""
        if DatabaseLoader._connection_pool:
            DatabaseLoader._connection_pool.closeall()
            logger.info("Database connection pool closed")

    def __enter__(self):
        """支援context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出context manager時不關閉連接池（連接會被複用）"""
        pass  # 連接池會繼續運行，供其他實例使用

    def get_pool_status(self) -> Dict:
        """
        獲取連接池狀態

        Returns:
            連接池狀態資訊
        """
        if not DatabaseLoader._connection_pool:
            return {
                "initialized": False
            }

        # 查詢實際的資料庫連接狀態
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # 查詢當前應用的連接數
                    cur.execute("""
                        SELECT
                            count(*) FILTER (WHERE state = 'active') as active,
                            count(*) FILTER (WHERE state = 'idle') as idle,
                            count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
                            count(*) as total
                        FROM pg_stat_activity
                        WHERE datname = %s
                          AND application_name != 'PostgreSQL JDBC Driver'
                    """, (settings.postgres_db,))

                    row = cur.fetchone()
                    if row:
                        active, idle, idle_in_transaction, total = row
                        return {
                            "initialized": True,
                            "min_conn": self.min_conn,
                            "max_conn": self.max_conn,
                            "active": active or 0,
                            "idle": idle or 0,
                            "idle_in_transaction": idle_in_transaction or 0,
                            "total": total or 0,
                            "usage_rate": (total / self.max_conn * 100) if self.max_conn > 0 else 0
                        }
        except Exception as e:
            logger.error(f"Failed to get pool status: {e}")

        # Fallback to basic info
        return {
            "initialized": True,
            "min_conn": self.min_conn,
            "max_conn": self.max_conn
        }
