"""
資料載入模組

負責從 TimescaleDB 讀取各類資料，並使用 Redis 快取
"""
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from typing import Optional, List
import sys
from pathlib import Path
from loguru import logger

# 添加 data-analyzer 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / 'data-analyzer' / 'src'))

from features.technical_indicators import TechnicalIndicators
from strategies.macd_strategy import MACDStrategy
from strategies.fractal_pattern_strategy import (
    FractalBreakoutStrategy,
    CombinedFractalMAStrategy
)

from cache_manager import CacheManager


class DataLoader:
    """資料載入器"""

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 5432,
        database: str = 'crypto_db',
        user: str = 'crypto',
        password: str = 'crypto_pass',
        use_cache: bool = True,
        cache_ttl: int = 2  # 快取 2 秒（高頻刷新下的短暫快取）
    ):
        """
        初始化資料庫連接與快取

        Args:
            host: PostgreSQL 主機
            port: PostgreSQL 端口
            database: 資料庫名稱
            user: 使用者名稱
            password: 密碼
            use_cache: 是否啟用快取
            cache_ttl: 快取過期時間（秒）
        """
        self.conn_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }

        # 初始化快取
        self.cache = None
        if use_cache:
            try:
                self.cache = CacheManager(default_ttl=cache_ttl)
            except Exception as e:
                logger.warning(f"快取初始化失敗，將不使用快取: {e}")
                self.cache = None

    def get_connection(self):
        """取得資料庫連接"""
        return psycopg2.connect(**self.conn_params)

    def get_latest_prices(self, limit: int = 10) -> pd.DataFrame:
        """
        取得最新價格資料

        Returns:
            DataFrame with columns: exchange, symbol, price, change_24h, volume_24h
        """
        query = """
            WITH latest_prices AS (
                SELECT DISTINCT ON (m.id)
                    e.name as exchange,
                    m.symbol,
                    m.id as market_id,
                    o.close as price,
                    o.volume,
                    o.open_time
                FROM ohlcv o
                JOIN markets m ON o.market_id = m.id
                JOIN exchanges e ON m.exchange_id = e.id
                WHERE o.timeframe = '1m'
                ORDER BY m.id, o.open_time DESC
            ),
            prices_24h_ago AS (
                SELECT DISTINCT ON (m.id)
                    m.id as market_id,
                    o.close as price_24h_ago
                FROM ohlcv o
                JOIN markets m ON o.market_id = m.id
                WHERE o.timeframe = '1m'
                  AND o.open_time >= NOW() - INTERVAL '24 hours'
                  AND o.open_time <= NOW() - INTERVAL '23.5 hours'
                ORDER BY m.id, o.open_time ASC
            )
            SELECT
                lp.exchange,
                lp.symbol,
                lp.price,
                lp.volume,
                CASE
                    WHEN p24.price_24h_ago IS NOT NULL
                    THEN ((lp.price - p24.price_24h_ago) / p24.price_24h_ago * 100)
                    ELSE 0
                END as change_24h
            FROM latest_prices lp
            LEFT JOIN prices_24h_ago p24 ON lp.market_id = p24.market_id
            ORDER BY lp.exchange, lp.symbol
            LIMIT %s
        """

        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=[limit])

        return df

    def get_ohlcv_data(
        self,
        exchange: str,
        symbol: str,
        timeframe: str = '1m',
        limit: int = 500
    ) -> pd.DataFrame:
        """
        取得 OHLCV 資料（支援快取）

        Args:
            exchange: 交易所名稱
            symbol: 交易對
            timeframe: 時間週期
            limit: 資料筆數

        Returns:
            DataFrame with OHLCV data
        """
        # 檢查快取
        if self.cache and self.cache.enabled:
            cache_key = self.cache.make_key('ohlcv', exchange, symbol, timeframe, limit)
            cached_df = self.cache.get_df(cache_key)
            if cached_df is not None:
                return cached_df

        # 查詢資料庫
        query = """
            SELECT
                o.open_time as timestamp,
                o.open,
                o.high,
                o.low,
                o.close,
                o.volume
            FROM ohlcv o
            JOIN markets m ON o.market_id = m.id
            JOIN exchanges e ON m.exchange_id = e.id
            WHERE e.name = %s
              AND m.symbol = %s
              AND o.timeframe = %s
            ORDER BY o.open_time DESC
            LIMIT %s
        """

        with self.get_connection() as conn:
            df = pd.read_sql_query(
                query, conn,
                params=[exchange, symbol, timeframe, limit]
            )

        if not df.empty:
            df = df.sort_values('timestamp').reset_index(drop=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        # 儲存到快取
        if self.cache and self.cache.enabled and not df.empty:
            cache_key = self.cache.make_key('ohlcv', exchange, symbol, timeframe, limit)
            self.cache.set_df(cache_key, df)

        return df

    def get_ohlcv_with_indicators(
        self,
        exchange: str,
        symbol: str,
        timeframe: str = '1m',
        limit: int = 500
    ) -> pd.DataFrame:
        """
        取得帶技術指標的 OHLCV 資料

        Returns:
            DataFrame with OHLCV + technical indicators
        """
        df = self.get_ohlcv_data(exchange, symbol, timeframe, limit)

        if df.empty:
            return df

        # 計算技術指標
        df = TechnicalIndicators.calculate_all(df)

        return df

    def get_strategy_signals(
        self,
        exchange: str,
        symbol: str,
        strategies: Optional[List] = None
    ) -> dict:
        """
        取得策略信號

        Args:
            exchange: 交易所
            symbol: 交易對
            strategies: 策略列表（若無則使用預設）

        Returns:
            {strategy_name: signals_series}
        """
        # 取得資料
        df = self.get_ohlcv_with_indicators(exchange, symbol)

        if df.empty:
            return {}

        # 預設策略（暫時只使用 MACD，其他策略需要額外的技術指標方法）
        if strategies is None:
            strategies = [
                MACDStrategy(name="MACD_Cross"),
                # FractalBreakoutStrategy(name="Fractal_Breakout"),  # 需要 identify_williams_fractal
                # CombinedFractalMAStrategy(name="Fractal_MA")  # 需要 identify_williams_fractal
            ]

        # 生成信號
        signals_dict = {}
        for strategy in strategies:
            try:
                signals = strategy.generate_signals(df)
                signals_dict[strategy.name] = signals
            except Exception as e:
                print(f"Error generating signals for {strategy.name}: {e}")

        return signals_dict

    def get_orderbook_snapshots(
        self,
        exchange: str,
        symbol: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        取得訂單簿快照

        Returns:
            DataFrame with timestamp, bids, asks
        """
        market_id = self._get_market_id(exchange, symbol)
        if market_id is None:
            return pd.DataFrame()

        query = """
            SELECT
                timestamp,
                bids,
                asks
            FROM orderbook_snapshots
            WHERE market_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """

        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=[market_id, limit])

        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df

    def _get_market_id(self, exchange: str, symbol: str) -> Optional[int]:
        cache_key = None
        if self.cache and self.cache.enabled:
            cache_key = self.cache.make_key('market_id', exchange, symbol)
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        query = """
            SELECT m.id
            FROM markets m
            JOIN exchanges e ON m.exchange_id = e.id
            WHERE e.name = %s
              AND m.symbol = %s
            LIMIT 1
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (exchange, symbol))
                row = cur.fetchone()
                market_id = row[0] if row else None

        if market_id is not None and cache_key and self.cache:
            self.cache.set(cache_key, market_id, ttl=60)

        return market_id

    def get_market_summary(self, exchange: str, symbol: str) -> dict:
        """
        取得市場摘要資訊（支援快取）

        Returns:
            {
                'latest_price': float,
                'change_24h': float,
                'volume_24h': float,
                'high_24h': float,
                'low_24h': float,
                'macd': float,
                'macd_signal': float,
                'ma_20': float,
                'ma_60': float,
                'latest_signals': {...}
            }
        """
        # 檢查快取
        if self.cache and self.cache.enabled:
            cache_key = self.cache.make_key('market_summary', exchange, symbol)
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        # 取得最新資料
        df = self.get_ohlcv_with_indicators(exchange, symbol, limit=500)

        if df.empty:
            return {}

        latest = df.iloc[-1]

        # 計算 24 小時統計
        df_24h = df.tail(1440)  # 假設 1m timeframe
        high_24h = df_24h['high'].max() if len(df_24h) > 0 else latest['high']
        low_24h = df_24h['low'].min() if len(df_24h) > 0 else latest['low']
        volume_24h = df_24h['volume'].sum() if len(df_24h) > 0 else latest['volume']

        # 價格變化
        if len(df) > 1:
            price_24h_ago = df.iloc[0]['close']
            change_24h = ((latest['close'] - price_24h_ago) / price_24h_ago) * 100
        else:
            change_24h = 0

        # 最新信號
        signals = self.get_strategy_signals(exchange, symbol)
        latest_signals = {}
        for name, signal_series in signals.items():
            non_none = signal_series[signal_series.notna()]
            if not non_none.empty:
                latest_signals[name] = {
                    'signal': int(non_none.iloc[-1]),
                    'time': str(non_none.index[-1])
                }

        result = {
            'latest_price': float(latest['close']),
            'change_24h': float(change_24h),
            'volume_24h': float(volume_24h),
            'high_24h': float(high_24h),
            'low_24h': float(low_24h),
            'macd': float(latest['macd']) if pd.notna(latest['macd']) else None,
            'macd_signal': float(latest['macd_signal']) if pd.notna(latest['macd_signal']) else None,
            'ma_20': float(latest['sma_20']) if pd.notna(latest.get('sma_20')) else None,
            'ma_60': float(latest['sma_50']) if pd.notna(latest.get('sma_50')) else None,  # 使用 sma_50 因為沒有 sma_60
            'latest_signals': latest_signals
        }

        # 儲存到快取
        if self.cache and self.cache.enabled:
            cache_key = self.cache.make_key('market_summary', exchange, symbol)
            self.cache.set(cache_key, result)

        return result
