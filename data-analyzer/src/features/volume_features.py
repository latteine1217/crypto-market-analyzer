"""
成交量特徵計算模組

職責：
- 計算成交量相關特徵
- 成交量變化
- 成交量比率
- 成交量指標（OBV, VWAP等）
"""
import numpy as np
import pandas as pd


class VolumeFeatures:
    """成交量特徵計算器"""

    @staticmethod
    def calculate_volume_changes(
        df: pd.DataFrame,
        periods: list = [1, 5, 10, 20]
    ) -> pd.DataFrame:
        """
        計算成交量變化

        Args:
            df: OHLCV DataFrame
            periods: 計算週期列表

        Returns:
            包含成交量變化特徵的 DataFrame
        """
        result = df.copy()

        for period in periods:
            # 成交量變化量
            result[f'volume_change_{period}'] = (
                result['volume'] - result['volume'].shift(period)
            )

            # 成交量變化率
            result[f'volume_change_pct_{period}'] = (
                result['volume'].pct_change(period) * 100
            )

        return result

    @staticmethod
    def calculate_volume_ma(
        df: pd.DataFrame,
        windows: list = [5, 10, 20, 50]
    ) -> pd.DataFrame:
        """
        計算成交量移動平均

        Args:
            df: OHLCV DataFrame
            windows: MA 視窗大小列表

        Returns:
            包含成交量 MA 的 DataFrame
        """
        result = df.copy()

        for window in windows:
            result[f'volume_ma_{window}'] = result['volume'].rolling(window=window).mean()

            # 成交量相對於 MA 的比率
            result[f'volume_to_ma_{window}'] = (
                result['volume'] / result[f'volume_ma_{window}']
            )

        return result

    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.DataFrame:
        """
        計算能量潮 (On-Balance Volume, OBV)

        Args:
            df: OHLCV DataFrame

        Returns:
            包含 OBV 的 DataFrame
        """
        result = df.copy()

        # 價格上漲時累加成交量，下跌時累減成交量
        obv = []
        obv_value = 0

        for i in range(len(result)):
            if i == 0:
                obv_value = result['volume'].iloc[i]
            else:
                if result['close'].iloc[i] > result['close'].iloc[i-1]:
                    obv_value += result['volume'].iloc[i]
                elif result['close'].iloc[i] < result['close'].iloc[i-1]:
                    obv_value -= result['volume'].iloc[i]

            obv.append(obv_value)

        result['obv'] = obv

        return result

    @staticmethod
    def calculate_vwap(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """
        計算成交量加權平均價格 (Volume Weighted Average Price, VWAP)

        Args:
            df: OHLCV DataFrame
            window: 計算視窗

        Returns:
            包含 VWAP 的 DataFrame
        """
        result = df.copy()

        # 典型價格（Typical Price）
        typical_price = (result['high'] + result['low'] + result['close']) / 3

        # VWAP
        result[f'vwap_{window}'] = (
            (typical_price * result['volume']).rolling(window=window).sum() /
            result['volume'].rolling(window=window).sum()
        )

        # 價格相對於 VWAP 的位置
        result[f'price_to_vwap_{window}'] = (
            (result['close'] - result[f'vwap_{window}']) / result[f'vwap_{window}'] * 100
        )

        return result

    @staticmethod
    def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        計算資金流量指標 (Money Flow Index, MFI)

        Args:
            df: OHLCV DataFrame
            period: MFI 計算週期

        Returns:
            包含 MFI 的 DataFrame
        """
        result = df.copy()

        # 典型價格
        typical_price = (result['high'] + result['low'] + result['close']) / 3

        # 資金流量
        money_flow = typical_price * result['volume']

        # 正負資金流量
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)

        # 滾動總和
        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()

        # MFI
        mfr = positive_mf / negative_mf
        result[f'mfi_{period}'] = 100 - (100 / (1 + mfr))

        return result

    @classmethod
    def calculate_all(
        cls,
        df: pd.DataFrame,
        change_periods: list = [1, 5, 10, 20],
        ma_windows: list = [5, 10, 20, 50],
        vwap_window: int = 20,
        mfi_period: int = 14
    ) -> pd.DataFrame:
        """
        計算所有成交量特徵

        Args:
            df: OHLCV DataFrame
            change_periods: 成交量變化週期
            ma_windows: 成交量 MA 視窗
            vwap_window: VWAP 視窗
            mfi_period: MFI 週期

        Returns:
            包含所有成交量特徵的 DataFrame
        """
        result = df.copy()

        result = cls.calculate_volume_changes(result, periods=change_periods)
        result = cls.calculate_volume_ma(result, windows=ma_windows)
        result = cls.calculate_obv(result)
        result = cls.calculate_vwap(result, window=vwap_window)
        result = cls.calculate_mfi(result, period=mfi_period)

        return result
