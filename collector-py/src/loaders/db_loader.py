"""
資料庫載入器 (V3 Schema 優化版)
負責將抓取的數據寫入 TimescaleDB
使用連接池管理資料庫連接
"""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_batch
from typing import List, Dict, Optional
from datetime import datetime, timezone, date, time
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
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
        """
        self.min_conn = min_conn
        self.max_conn = max_conn

        # 確保連接池已初始化
        if DatabaseLoader._connection_pool is None:
            self._init_connection_pool()

        # 保持向後兼容性
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
                        options='-c statement_timeout=30000'
                    )
                    logger.info(f"Database connection pool initialized (min={self.min_conn}, max={self.max_conn})")
                except Exception as e:
                    logger.error(f"Failed to initialize connection pool: {e}")
                    raise

    @contextmanager
    def get_connection(self):
        """從連接池獲取連接 (Context Manager)"""
        conn = None
        try:
            conn = DatabaseLoader._connection_pool.getconn()
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                DatabaseLoader._connection_pool.putconn(conn, close=True)
                conn = None # 防止 finally 再次 putconn
            raise
        finally:
            if conn:
                DatabaseLoader._connection_pool.putconn(conn)

    def ensure_connection(self):
        """確保連接池可用 (向後相容)"""
        if DatabaseLoader._connection_pool is None:
            self._init_connection_pool()

    def get_market_id(self, exchange_name: str, symbol: str) -> Optional[int]:
        """取得市場ID，若不存在則建立"""
        self.ensure_connection()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # 1. 取得 exchange_id
                cur.execute("SELECT id FROM exchanges WHERE name = %s", (exchange_name,))
                row = cur.fetchone()
                if not row:
                    logger.error(f"Exchange {exchange_name} not found")
                    return None
                exchange_id = row[0]

                # 2. 解析 symbol
                try:
                    base_asset, quote_asset = parse_symbol(symbol)
                except Exception:
                    base_asset, quote_asset = symbol.split('/')[0], 'USDT'
                
                normalized_symbol = normalize_symbol(symbol)

                # ✅ 優先從 symbol_registry 尋找匹配
                cur.execute("""
                    SELECT market_type, base_asset, quote_asset 
                    FROM symbol_registry 
                    WHERE exchange_id = %s AND native_symbol = %s
                """, (exchange_id, normalized_symbol))
                reg_row = cur.fetchone()

                if reg_row:
                    market_type, base_asset, quote_asset = reg_row
                else:
                    # 3. 降級邏輯 (Heuristic)
                    market_type = 'spot'
                    if exchange_name.lower() in ['bybit', 'okx']:
                        market_type = 'linear_perpetual'
                    logger.warning(f"Symbol {normalized_symbol} not found in registry for {exchange_name}, using heuristics.")

                cur.execute("""
                    INSERT INTO markets (exchange_id, symbol, base_asset, quote_asset, market_type, is_active)
                    VALUES (%s, %s, %s, %s, %s, FALSE)
                    ON CONFLICT (exchange_id, symbol) DO UPDATE SET
                        base_asset = EXCLUDED.base_asset,
                        quote_asset = EXCLUDED.quote_asset,
                        market_type = EXCLUDED.market_type
                    RETURNING id
                """, (exchange_id, normalized_symbol, base_asset, quote_asset, market_type))
                
                result = cur.fetchone()
                if result:
                    market_id = result[0]
                else:
                    cur.execute("SELECT id FROM markets WHERE exchange_id = %s AND symbol = %s", (exchange_id, normalized_symbol))
                    market_id = cur.fetchone()[0]

                conn.commit()
                return market_id

    def get_market_info(self, market_id: int) -> Optional[Dict]:
        """取得市場資訊 (exchange, symbol)"""
        self.ensure_connection()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT e.name as exchange, m.symbol
                    FROM markets m
                    JOIN exchanges e ON m.exchange_id = e.id
                    WHERE m.id = %s
                """, (market_id,))
                row = cur.fetchone()
                if row:
                    return {'exchange': row[0], 'symbol': row[1]}
                return None

    def get_active_markets(self, exchange_name: Optional[str] = None) -> List[Dict]:
        """取得活躍市場列表"""
        self.ensure_connection()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT m.id, m.symbol, e.name AS exchange
                    FROM markets m
                    JOIN exchanges e ON m.exchange_id = e.id
                    WHERE m.is_active = TRUE
                """
                params = []
                if exchange_name:
                    query += " AND e.name = %s"
                    params.append(exchange_name)
                query += " ORDER BY m.id"

                cur.execute(query, tuple(params))
                rows = cur.fetchall()

        return [
            {'id': row[0], 'symbol': row[1], 'exchange': row[2]}
            for row in rows
        ]

    def insert_ohlcv_batch(self, market_id: int, timeframe: str, ohlcv_data: List[List]) -> int:
        """批次插入 OHLCV 數據 (V3 Schema: time 欄位)"""
        if not ohlcv_data: return 0
        self.ensure_connection()
        
        rows = []
        for candle in ohlcv_data:
            ts_ms, o, h, l, c, v = candle[:6]
            time_val = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            rows.append((market_id, time_val, timeframe, o, h, l, c, v))

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, """
                    INSERT INTO ohlcv (market_id, time, timeframe, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (market_id, time, timeframe)
                    DO UPDATE SET open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close, volume=EXCLUDED.volume
                """, rows)
                conn.commit()
        return len(rows)

    def insert_trades_batch(self, market_id: int, trades_data: List[Dict]) -> int:
        """批次插入交易數據 (V3 Schema: time 欄位)"""
        if not trades_data: return 0
        self.ensure_connection()
        
        rows = []
        for trade in trades_data:
            time_val = datetime.fromtimestamp(trade['timestamp'] / 1000, tz=timezone.utc)
            rows.append((market_id, time_val, trade['price'], trade['amount'], trade['side'], trade['id']))

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, """
                    INSERT INTO trades (market_id, time, price, amount, side, trade_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (market_id, time, trade_id) DO NOTHING
                """, rows)
                conn.commit()
        return len(rows)

    def insert_orderbook_batch(self, market_id: int, orderbook_data: List[Dict]) -> int:
        """批次插入訂單簿快照 (V3: 寫入 market_metrics)"""
        if not orderbook_data: return 0
        self.ensure_connection()
        import json
        
        rows = []
        for snapshot in orderbook_data:
            ts = snapshot.get('timestamp')
            time_val = datetime.fromtimestamp(ts / 1000, tz=timezone.utc) if ts else datetime.now(tz=timezone.utc)
            metadata = {'bids': snapshot['bids'], 'asks': snapshot['asks']}
            rows.append((market_id, time_val, 'orderbook_snapshot', 0, json.dumps(metadata)))

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, """
                    INSERT INTO market_metrics (market_id, time, name, value, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (market_id, time, name) DO UPDATE SET metadata = EXCLUDED.metadata
                """, rows)
                conn.commit()
        return len(rows)

    def get_latest_ohlcv_time(self, market_id: int, timeframe: str) -> Optional[datetime]:
        """獲取最新 K 線時間"""
        self.ensure_connection()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(time) FROM ohlcv WHERE market_id = %s AND timeframe = %s", (market_id, timeframe))
                result = cur.fetchone()
                return result[0] if result else None

    def insert_quality_metrics(self, **metrics) -> int:
        """插入資料品質指標 (V3: 存入 system_logs)"""
        self.ensure_connection()
        import json
        
        # 提取核心標籤，其餘放入 metadata
        market_id = metrics.get('market_id')
        timeframe = metrics.get('timeframe')
        quality_score = metrics.get('quality_score', 0)
        
        # 計算 status (若未提供)
        status = metrics.get('status')
        if not status:
            missing_rate = metrics.get('missing_rate', 0)
            if missing_rate <= 0.03: status = 'GOOD'
            elif missing_rate <= 0.1: status = 'ACCEPTABLE'
            else: status = 'POOR'
        
        metadata = {
            'market_id': market_id,
            'timeframe': timeframe,
            'missing_rate': metrics.get('missing_rate'),
            'missing_count': metrics.get('missing_count'),
            'expected_count': metrics.get('expected_count'),
            'actual_count': metrics.get('actual_count'),
            'status': status,
            'issues': metrics.get('issues', []),
            'backfill_task_created': metrics.get('backfill_task_created', False)
        }
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO system_logs (time, module, level, message, value, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (metrics.get('check_time', datetime.now(timezone.utc)), 'collector', 'QUALITY', 
                      f"Quality check for {market_id} {timeframe}: {status}", 
                      quality_score, json.dumps(metadata)))
                conn.commit()
        return 1

    def insert_system_log(
        self,
        *,
        module: str,
        level: str,
        message: str,
        value: float | None = None,
        metadata: dict | None = None,
        log_time: datetime | None = None,
    ) -> int:
        """插入 system_logs（通用，可用於外部來源抓取品質與狀態記錄）"""
        self.ensure_connection()
        import json

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO system_logs (time, module, level, message, value, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        log_time or datetime.now(timezone.utc),
                        module,
                        level,
                        message,
                        value,
                        json.dumps(metadata or {}, ensure_ascii=False),
                    ),
                )
                conn.commit()
        return 1

    def insert_funding_rate(self, market_id: int, funding_data: Dict) -> int:
        """插入單筆資金費率"""
        return self.insert_funding_rate_batch(market_id, [funding_data])

    def insert_funding_rate_batch(self, market_id: int, funding_data_list: List[Dict]) -> int:
        """批次插入資金費率 (存入 market_metrics)"""
        if not funding_data_list: return 0
        self.ensure_connection()
        import json
        rows = []
        for data in funding_data_list:
            # DB 約束：market_metrics.value NOT NULL
            # 當上游交易所未提供 funding_rate（None）時跳過，避免整批插入失敗。
            if data.get('funding_rate') is None:
                continue
            if not data.get('funding_time'):
                continue

            metadata = {
                'funding_rate_daily': data.get('funding_rate_daily'),
                'next_funding_time': str(data.get('next_funding_time')) if data.get('next_funding_time') else None,
                'mark_price': data.get('mark_price'),
                'index_price': data.get('index_price')
            }
            rows.append((market_id, data['funding_time'], 'funding_rate', data['funding_rate'], json.dumps(metadata)))

        if not rows:
            return 0

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, """
                    INSERT INTO market_metrics (market_id, time, name, value, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (market_id, time, name) DO UPDATE SET value = EXCLUDED.value, metadata = EXCLUDED.metadata
                """, rows)
                conn.commit()
        return len(rows)

    def insert_open_interest(self, market_id: int, oi_data: Dict) -> int:
        """插入單筆未平倉量"""
        return self.insert_open_interest_batch(market_id, [oi_data])

    def insert_open_interest_batch(self, market_id: int, oi_data_list: List[Dict]) -> int:
        """批次插入未平倉量 (存入 market_metrics)"""
        if not oi_data_list: return 0
        self.ensure_connection()
        import json
        rows = []
        for data in oi_data_list:
            metadata = {
                'open_interest_usd': data.get('open_interest_usd'),
                'price': data.get('price'),
                'volume_24h': data.get('volume_24h')
            }
            rows.append((market_id, data['timestamp'], 'open_interest', data['open_interest'], json.dumps(metadata)))
            
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, """
                    INSERT INTO market_metrics (market_id, time, name, value, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (market_id, time, name) DO UPDATE SET value = EXCLUDED.value, metadata = EXCLUDED.metadata
                """, rows)
                conn.commit()
        return len(rows)

    def insert_fear_greed_index(self, data: Dict) -> int:
        """插入 Fear & Greed Index (global_indicators)"""
        self.ensure_connection()
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO global_indicators (time, category, name, value, classification)
                    VALUES (%s, 'sentiment', 'fear_greed', %s, %s)
                    ON CONFLICT (time, category, name) DO UPDATE SET value = EXCLUDED.value, classification = EXCLUDED.classification
                """, (data['timestamp'], data['value'], data['classification']))
                conn.commit()
        return 1

    def insert_etf_flows_batch(self, etf_flows_data: List[Dict]) -> int:
        """批次插入 ETF 流向 (global_indicators)"""
        if not etf_flows_data: return 0
        self.ensure_connection()
        import json
        rows = []
        etf_tz = ZoneInfo("America/New_York") if ZoneInfo else timezone.utc
        for flow in etf_flows_data:
            timestamp = flow.get('timestamp')
            if not timestamp:
                flow_date = flow.get('date')
                if isinstance(flow_date, datetime):
                    timestamp = flow_date
                elif isinstance(flow_date, date):
                    timestamp = datetime.combine(flow_date, time(16, 0), tzinfo=etf_tz)
                else:
                    timestamp = datetime.now(timezone.utc)
            if isinstance(timestamp, datetime) and timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=etf_tz)
            if isinstance(timestamp, datetime):
                timestamp = timestamp.astimezone(timezone.utc)

            metadata = {
                'product_name': flow.get('product_name'),
                'issuer': flow.get('issuer'),
                'asset_type': flow.get('asset_type'),
                'total_aum_usd': flow.get('total_aum_usd'),
                'date': str(flow.get('date'))
            }
            # SoSoValue OpenAPI 會回傳的額外欄位（可用於 dashboard/分析）
            for key in ('total_value_traded_usd', 'cum_net_inflow_usd', 'source'):
                if flow.get(key) is not None:
                    metadata[key] = flow.get(key)
            # Premium/Discount to NAV：溢價率（以 ratio 表示，例如 0.001 = +0.1%）
            for key in ('nav_per_share', 'market_price', 'premium_rate'):
                if flow.get(key) is not None:
                    metadata[key] = flow.get(key)
            for key in ('source_url', 'source_last_updated', 'schema_fingerprint', 'fetch_method'):
                if flow.get(key) is not None:
                    metadata[key] = flow.get(key)
            rows.append((timestamp, 'etf', flow['product_code'], flow['net_flow_usd'], json.dumps(metadata)))
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, """
                    INSERT INTO global_indicators (time, category, name, value, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (time, category, name) DO UPDATE SET value = EXCLUDED.value, metadata = EXCLUDED.metadata
                """, rows)
                conn.commit()
        return len(rows)

    def insert_liquidations_batch(self, liquidations_data: List[Dict]) -> int:
        """批次插入爆倉數據"""
        if not liquidations_data: return 0
        self.ensure_connection()
        
        rows = []
        for liq in liquidations_data:
            # 確保 time 是 datetime 對象
            time_val = liq['time']
            if isinstance(time_val, (int, float)):
                 time_val = datetime.fromtimestamp(time_val / 1000, tz=timezone.utc)
            
            rows.append((
                time_val,
                liq['exchange'],
                liq['symbol'],
                liq['side'],
                liq['price'],
                liq['quantity'],
                liq['value_usd']
            ))

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, """
                    INSERT INTO liquidations (time, exchange, symbol, side, price, quantity, value_usd)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (time, exchange, symbol, side, price) DO NOTHING
                """, rows)
                conn.commit()
        return len(rows)

    def insert_market_signals(self, signals: List[Dict]) -> int:
        """批次插入市場訊號"""
        if not signals: return 0
        self.ensure_connection()
        import json
        
        rows = []
        for sig in signals:
            rows.append((
                sig['time'],
                sig['symbol'],
                sig['signal_type'],
                sig['side'],
                sig['severity'],
                sig.get('price_at_signal'),
                sig.get('message'),
                json.dumps(sig.get('metadata', {}))
            ))

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, """
                    INSERT INTO market_signals (time, symbol, signal_type, side, severity, price_at_signal, message, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (time, symbol, signal_type) DO UPDATE SET
                        severity = EXCLUDED.severity,
                        message = EXCLUDED.message,
                        metadata = EXCLUDED.metadata
                """, rows)
                conn.commit()
        return len(rows)

    def close(self):
        """關閉連接池"""
        if DatabaseLoader._connection_pool:
            DatabaseLoader._connection_pool.closeall()
            logger.info("Database connection pool closed")

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass
