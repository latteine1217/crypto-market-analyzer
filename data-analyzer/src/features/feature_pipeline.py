"""
特徵工程 Pipeline

統一管理和執行所有特徵計算
"""
import pandas as pd
import psycopg2
from typing import Optional, List, Dict
from datetime import datetime

from .price_features import PriceFeatures
from .volume_features import VolumeFeatures, OrderFlowFeatures
from .technical_indicators import TechnicalIndicators


class FeaturePipeline:
    """特徵工程管道"""

    def __init__(
        self,
        db_host: str = 'localhost',
        db_port: int = 5432,
        db_name: str = 'crypto_db',
        db_user: str = 'crypto',
        db_password: str = 'crypto_pass'
    ):
        """
        初始化 Pipeline

        Args:
            db_host: 資料庫主機
            db_port: 資料庫端口
            db_name: 資料庫名稱
            db_user: 資料庫使用者
            db_password: 資料庫密碼
        """
        self.conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )

    def load_ohlcv_data(
        self,
        exchange: str,
        symbol: str,
        timeframe: str = '1m',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        從資料庫載入 OHLCV 資料

        Args:
            exchange: 交易所名稱
            symbol: 交易對
            timeframe: 時間週期
            start_time: 開始時間
            end_time: 結束時間
            limit: 最大筆數

        Returns:
            OHLCV DataFrame
        """
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
        """

        params = [exchange, symbol, timeframe]

        if start_time:
            query += " AND o.open_time >= %s"
            params.append(start_time)

        if end_time:
            query += " AND o.open_time <= %s"
            params.append(end_time)

        query += " ORDER BY o.open_time ASC"

        if limit:
            query += f" LIMIT {limit}"

        df = pd.read_sql(query, self.conn, params=params)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df

    def load_trades_data(
        self,
        exchange: str,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        從資料庫載入 Trades 資料

        Args:
            exchange: 交易所名稱
            symbol: 交易對
            start_time: 開始時間
            end_time: 結束時間
            limit: 最大筆數

        Returns:
            Trades DataFrame
        """
        query = """
            SELECT
                t.timestamp,
                t.price,
                t.quantity,
                t.is_buyer_maker
            FROM trades t
            JOIN markets m ON t.market_id = m.id
            JOIN exchanges e ON m.exchange_id = e.id
            WHERE e.name = %s
              AND m.symbol = %s
        """

        params = [exchange, symbol]

        if start_time:
            query += " AND t.timestamp >= %s"
            params.append(start_time)

        if end_time:
            query += " AND t.timestamp <= %s"
            params.append(end_time)

        query += " ORDER BY t.timestamp ASC"

        if limit:
            query += f" LIMIT {limit}"

        df = pd.read_sql(query, self.conn, params=params)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df

    def build_features(
        self,
        df: pd.DataFrame,
        include_price: bool = True,
        include_volume: bool = True,
        include_technical: bool = True,
        custom_features: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        建立所有特徵

        Args:
            df: 原始 OHLCV 資料
            include_price: 是否包含價格特徵
            include_volume: 是否包含成交量特徵
            include_technical: 是否包含技術指標
            custom_features: 自定義特徵列表

        Returns:
            包含所有特徵的 DataFrame
        """
        result = df.copy()

        # 價格特徵
        if include_price:
            result = PriceFeatures.add_all_price_features(result)

        # 成交量特徵
        if include_volume and 'volume' in result.columns:
            result = VolumeFeatures.add_all_volume_features(result)

        # 技術指標
        if include_technical:
            # MACD
            result = TechnicalIndicators.calculate_macd(result)

            # 多週期 MA
            for period in [20, 60, 200]:
                result[f'sma_{period}'] = TechnicalIndicators.calculate_sma(
                    result['close'], period
                )
                result[f'ema_{period}'] = TechnicalIndicators.calculate_ema(
                    result['close'], period
                )

            # RSI
            result = TechnicalIndicators.calculate_rsi(result)

            # Bollinger Bands
            result = TechnicalIndicators.calculate_bollinger_bands(result)

        return result

    def prepare_for_modeling(
        self,
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        forward_periods: int = 1,
        drop_na: bool = True
    ) -> pd.DataFrame:
        """
        準備用於建模的資料

        Args:
            df: 包含特徵的 DataFrame
            target_col: 目標變數欄位（如果是預測任務）
            forward_periods: 向前預測的週期數
            drop_na: 是否刪除包含 NaN 的行

        Returns:
            準備好的 DataFrame
        """
        result = df.copy()

        # 如果指定目標變數，建立目標
        if target_col:
            result['target'] = result[target_col].shift(-forward_periods)

        # 刪除 NaN
        if drop_na:
            result = result.dropna()

        return result

    def get_feature_importance_ready_data(
        self,
        exchange: str,
        symbol: str,
        timeframe: str = '1m',
        target_type: str = 'return',
        forward_periods: int = 1,
        **kwargs
    ) -> tuple:
        """
        獲取準備好進行特徵重要性分析的資料

        Args:
            exchange: 交易所
            symbol: 交易對
            timeframe: 時間週期
            target_type: 目標類型 ('return', 'direction', 'volatility')
            forward_periods: 向前預測週期
            **kwargs: 傳遞給 load_ohlcv_data 的其他參數

        Returns:
            (X, y, feature_names) tuple
        """
        # 載入資料
        df = self.load_ohlcv_data(exchange, symbol, timeframe, **kwargs)

        # 建立特徵
        df = self.build_features(df)

        # 建立目標變數
        if target_type == 'return':
            df['target'] = df['close'].pct_change(forward_periods).shift(
                -forward_periods
            )
        elif target_type == 'direction':
            future_return = df['close'].pct_change(forward_periods).shift(
                -forward_periods
            )
            df['target'] = (future_return > 0).astype(int)
        elif target_type == 'volatility':
            df['target'] = df['close'].pct_change().rolling(
                forward_periods
            ).std().shift(-forward_periods)

        # 準備資料
        df = df.dropna()

        # 分離特徵和目標
        exclude_cols = ['timestamp', 'target', 'open_time']
        feature_cols = [
            col for col in df.columns
            if col not in exclude_cols
        ]

        X = df[feature_cols]
        y = df['target']

        return X, y, feature_cols

    def close(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()
