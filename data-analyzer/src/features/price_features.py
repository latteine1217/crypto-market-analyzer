"""
價格特徵工程模組

功能：
1. 計算價格相關特徵（報酬率、波動度等）
2. 價格動量特徵
3. 價格趨勢特徵
4. 價格分布特徵
"""
import pandas as pd
import numpy as np
from typing import Optional, List


class PriceFeatures:
    """價格特徵計算器"""

    @staticmethod
    def calculate_returns(
        df: pd.DataFrame,
        price_col: str = 'close',
        periods: List[int] = [1, 5, 15, 30, 60]
    ) -> pd.DataFrame:
        """
        計算多週期報酬率

        Args:
            df: 包含價格資料的 DataFrame
            price_col: 價格欄位名稱
            periods: 計算報酬率的週期列表

        Returns:
            包含各週期報酬率的 DataFrame
        """
        result = df.copy()

        for period in periods:
            # 簡單報酬率
            result[f'return_{period}'] = result[price_col].pct_change(period)

            # 對數報酬率（更適合金融分析）
            result[f'log_return_{period}'] = np.log(
                result[price_col] / result[price_col].shift(period)
            )

        return result

    @staticmethod
    def calculate_volatility(
        df: pd.DataFrame,
        return_col: str = 'return_1',
        windows: List[int] = [10, 20, 50]
    ) -> pd.DataFrame:
        """
        計算滾動波動度（標準差）

        Args:
            df: 包含報酬率的 DataFrame
            return_col: 報酬率欄位名稱
            windows: 滾動窗口大小列表

        Returns:
            包含各窗口波動度的 DataFrame
        """
        result = df.copy()

        for window in windows:
            result[f'volatility_{window}'] = result[return_col].rolling(
                window=window
            ).std()

        return result

    @staticmethod
    def calculate_momentum(
        df: pd.DataFrame,
        price_col: str = 'close',
        periods: List[int] = [5, 10, 20, 50]
    ) -> pd.DataFrame:
        """
        計算價格動量指標

        Args:
            df: 包含價格資料的 DataFrame
            price_col: 價格欄位名稱
            periods: 動量計算週期

        Returns:
            包含動量指標的 DataFrame
        """
        result = df.copy()

        for period in periods:
            # 動量 = 當前價格 / N期前價格 - 1
            result[f'momentum_{period}'] = (
                result[price_col] / result[price_col].shift(period) - 1
            )

            # ROC (Rate of Change)
            result[f'roc_{period}'] = (
                (result[price_col] - result[price_col].shift(period)) /
                result[price_col].shift(period) * 100
            )

        return result

    @staticmethod
    def calculate_price_position(
        df: pd.DataFrame,
        price_col: str = 'close',
        windows: List[int] = [20, 50, 200]
    ) -> pd.DataFrame:
        """
        計算價格在區間中的位置（0-1之間）

        Args:
            df: 包含價格資料的 DataFrame
            price_col: 價格欄位名稱
            windows: 滾動窗口大小列表

        Returns:
            包含價格位置指標的 DataFrame
        """
        result = df.copy()

        for window in windows:
            # 計算滾動最高價和最低價
            rolling_high = result[price_col].rolling(window=window).max()
            rolling_low = result[price_col].rolling(window=window).min()

            # 價格位置 = (當前價 - 最低價) / (最高價 - 最低價)
            result[f'price_position_{window}'] = (
                (result[price_col] - rolling_low) /
                (rolling_high - rolling_low)
            )

        return result

    @staticmethod
    def calculate_ohlc_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        從 OHLC 資料計算特徵

        Args:
            df: 包含 OHLC 資料的 DataFrame

        Returns:
            包含 OHLC 特徵的 DataFrame
        """
        result = df.copy()

        # 價格範圍
        result['price_range'] = result['high'] - result['low']
        result['price_range_pct'] = result['price_range'] / result['close']

        # 上下影線
        result['upper_shadow'] = result['high'] - result[['open', 'close']].max(axis=1)
        result['lower_shadow'] = result[['open', 'close']].min(axis=1) - result['low']

        # 實體大小
        result['body'] = abs(result['close'] - result['open'])
        result['body_pct'] = result['body'] / result['close']

        # K線方向
        result['is_bullish'] = (result['close'] > result['open']).astype(int)

        # 收盤價相對位置（在 high-low 區間中的位置）
        result['close_position'] = (
            (result['close'] - result['low']) / result['price_range']
        ).fillna(0.5)

        return result

    @staticmethod
    def calculate_gap(df: pd.DataFrame) -> pd.DataFrame:
        """
        計算跳空缺口

        Args:
            df: 包含 OHLC 資料的 DataFrame

        Returns:
            包含跳空缺口特徵的 DataFrame
        """
        result = df.copy()

        # 向上跳空：當前低價 > 前一根高價
        result['gap_up'] = (
            result['low'] > result['high'].shift(1)
        ).astype(int)

        # 向下跳空：當前高價 < 前一根低價
        result['gap_down'] = (
            result['high'] < result['low'].shift(1)
        ).astype(int)

        # 跳空大小（百分比）
        result['gap_size'] = (
            result['open'] - result['close'].shift(1)
        ) / result['close'].shift(1)

        return result

    @staticmethod
    def add_all_price_features(
        df: pd.DataFrame,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        一次性加入所有價格特徵

        Args:
            df: 原始 OHLCV 資料
            price_col: 價格欄位名稱

        Returns:
            包含所有價格特徵的 DataFrame
        """
        result = df.copy()

        # 報酬率
        result = PriceFeatures.calculate_returns(result, price_col)

        # 波動度
        result = PriceFeatures.calculate_volatility(result)

        # 動量
        result = PriceFeatures.calculate_momentum(result, price_col)

        # 價格位置
        result = PriceFeatures.calculate_price_position(result, price_col)

        # OHLC 特徵
        if all(col in result.columns for col in ['open', 'high', 'low', 'close']):
            result = PriceFeatures.calculate_ohlc_features(result)
            result = PriceFeatures.calculate_gap(result)

        return result
