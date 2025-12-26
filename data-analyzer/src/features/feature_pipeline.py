"""
特徵計算 Pipeline

職責：
- 統一管理所有特徵計算流程
- 從資料庫載入 OHLCV 資料
- 計算所有特徵
- 儲存特徵資料
"""
import pandas as pd
import psycopg2
from typing import Optional, List, Dict
from loguru import logger

from .price_features import PriceFeatures
from .technical_indicators import TechnicalIndicators
from .volume_features import VolumeFeatures
from .volatility_features import VolatilityFeatures


class FeaturePipeline:
    """特徵計算 Pipeline"""

    def __init__(self, db_config: Optional[Dict] = None):
        """
        初始化 Pipeline

        Args:
            db_config: 資料庫配置
        """
        self.db_config = db_config or {
            'dbname': 'crypto_db',
            'user': 'crypto',
            'password': 'crypto_pass',
            'host': 'localhost',
            'port': '5432'
        }

    def load_ohlcv_from_db(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        從資料庫載入 OHLCV 資料

        Args:
            symbol: 交易對符號（如 "BTC/USDT"）
            timeframe: 時間週期（如 "1m"）
            start_time: 開始時間
            end_time: 結束時間
            limit: 限制筆數

        Returns:
            OHLCV DataFrame
        """
        conn = psycopg2.connect(**self.db_config)

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
            WHERE m.symbol = %s
                AND o.timeframe = %s
        """

        params = [symbol, timeframe]

        if start_time:
            query += " AND o.open_time >= %s"
            params.append(start_time)

        if end_time:
            query += " AND o.open_time <= %s"
            params.append(end_time)

        query += " ORDER BY o.open_time ASC"

        if limit:
            query += f" LIMIT {limit}"

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')

        logger.info(f"載入 {len(df)} 筆 {symbol} ({timeframe}) OHLCV 資料")

        return df

    def calculate_all_features(
        self,
        df: pd.DataFrame,
        feature_config: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        計算所有特徵

        Args:
            df: OHLCV DataFrame
            feature_config: 特徵配置（如果為 None，使用預設配置）

        Returns:
            包含所有特徵的 DataFrame
        """
        if df.empty:
            logger.warning("輸入資料為空，無法計算特徵")
            return df

        result = df.copy()

        # 使用預設配置
        config = feature_config or {
            'price': {
                'return_periods': [1, 5, 10, 20],
                'momentum_periods': [5, 10, 20],
                'position_windows': [20, 50, 100]
            },
            'technical': {
                'sma_windows': [5, 10, 20, 50],
                'ema_spans': [5, 10, 20, 50],
                'rsi_periods': [14],
                'bb_window': 20,
                'atr_period': 14
            },
            'volume': {
                'change_periods': [1, 5, 10, 20],
                'ma_windows': [5, 10, 20, 50],
                'vwap_window': 20,
                'mfi_period': 14
            },
            'volatility': {
                'hist_vol_windows': [5, 10, 20],
                'parkinson_windows': [5, 10, 20],
                'gk_windows': [5, 10, 20]
            }
        }

        logger.info("開始計算特徵...")

        # 1. 價格特徵
        logger.info("計算價格特徵...")
        result = PriceFeatures.calculate_all(
            result,
            **config['price']
        )

        # 2. 技術指標
        logger.info("計算技術指標...")
        result = TechnicalIndicators.calculate_all(
            result,
            **config['technical']
        )

        # 3. 成交量特徵
        if 'volume' in result.columns:
            logger.info("計算成交量特徵...")
            result = VolumeFeatures.calculate_all(
                result,
                **config['volume']
            )

        # 4. 波動率特徵
        logger.info("計算波動率特徵...")
        result = VolatilityFeatures.calculate_all(
            result,
            **config['volatility']
        )

        # 移除 NaN 值統計
        total_features = len(result.columns)
        nan_count = result.isna().sum().sum()
        logger.info(f"特徵計算完成！總特徵數: {total_features}, NaN 數量: {nan_count}")

        return result

    def run(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: Optional[int] = None,
        feature_config: Optional[Dict] = None,
        dropna: bool = False
    ) -> pd.DataFrame:
        """
        執行完整的特徵計算流程

        Args:
            symbol: 交易對符號
            timeframe: 時間週期
            start_time: 開始時間
            end_time: 結束時間
            limit: 限制筆數
            feature_config: 特徵配置
            dropna: 是否刪除包含 NaN 的行

        Returns:
            包含所有特徵的 DataFrame
        """
        logger.info("=" * 60)
        logger.info("特徵工程 Pipeline 開始")
        logger.info(f"交易對: {symbol}")
        logger.info(f"週期: {timeframe}")
        logger.info("=" * 60)

        # 1. 載入資料
        df = self.load_ohlcv_from_db(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        if df.empty:
            logger.error("無法載入資料")
            return df

        # 2. 計算特徵
        df_features = self.calculate_all_features(df, feature_config)

        # 3. 處理 NaN
        if dropna:
            before_len = len(df_features)
            df_features = df_features.dropna()
            logger.info(f"刪除 NaN 後：{before_len} -> {len(df_features)} 筆")

        logger.info("=" * 60)
        logger.info("特徵工程 Pipeline 完成")
        logger.info(f"最終資料筆數: {len(df_features)}")
        logger.info(f"特徵維度: {df_features.shape}")
        logger.info("=" * 60)

        return df_features

    def get_feature_names(self, df: pd.DataFrame) -> List[str]:
        """
        取得特徵名稱列表（排除 OHLCV 原始欄位）

        Args:
            df: 包含特徵的 DataFrame

        Returns:
            特徵名稱列表
        """
        base_cols = ['open', 'high', 'low', 'close', 'volume']
        feature_cols = [col for col in df.columns if col not in base_cols]
        return feature_cols

    def get_feature_summary(self, df: pd.DataFrame) -> Dict:
        """
        取得特徵摘要統計

        Args:
            df: 包含特徵的 DataFrame

        Returns:
            特徵摘要字典
        """
        feature_cols = self.get_feature_names(df)

        summary = {
            'total_features': len(feature_cols),
            'total_samples': len(df),
            'nan_ratio': df[feature_cols].isna().sum().sum() / (len(df) * len(feature_cols)),
            'feature_groups': {
                'price': len([c for c in feature_cols if any(k in c for k in ['return', 'momentum', 'price', 'roc'])]),
                'technical': len([c for c in feature_cols if any(k in c for k in ['sma', 'ema', 'rsi', 'macd', 'bb', 'stoch', 'adx'])]),
                'volume': len([c for c in feature_cols if 'volume' in c or any(k in c for k in ['obv', 'vwap', 'mfi'])]),
                'volatility': len([c for c in feature_cols if any(k in c for k in ['volatility', 'vol', 'atr'])])
            }
        }

        return summary
