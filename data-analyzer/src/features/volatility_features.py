"""
波動率特徵計算模組

職責：
- 計算波動率相關特徵
- 歷史波動率
- 真實波幅（ATR）
- 價格波動統計特徵
"""
import numpy as np
import pandas as pd


class VolatilityFeatures:
    """波動率特徵計算器"""

    @staticmethod
    def calculate_historical_volatility(
        df: pd.DataFrame,
        return_col: str = 'log_return_1',
        windows: list = [5, 10, 20, 50]
    ) -> pd.DataFrame:
        """
        計算歷史波動率（報酬率的標準差）

        Args:
            df: 包含報酬率的 DataFrame
            return_col: 報酬率欄位名稱
            windows: 滾動視窗大小列表

        Returns:
            包含歷史波動率的 DataFrame
        """
        result = df.copy()

        for window in windows:
            # 滾動標準差（歷史波動率）
            result[f'volatility_{window}'] = (
                result[return_col].rolling(window=window).std()
            )

            # 年化波動率（假設 1 分鐘 K 線，一年有 525600 分鐘）
            # 對於其他週期，需要相應調整
            result[f'volatility_annualized_{window}'] = (
                result[f'volatility_{window}'] * np.sqrt(525600)
            )

        return result

    @staticmethod
    def calculate_parkinson_volatility(
        df: pd.DataFrame,
        windows: list = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        計算 Parkinson 波動率（使用高低價資訊）
        比歷史波動率更有效率

        Args:
            df: OHLCV DataFrame
            windows: 滾動視窗大小列表

        Returns:
            包含 Parkinson 波動率的 DataFrame
        """
        result = df.copy()

        # 計算對數高低價比的平方
        hl_ratio_sq = (np.log(result['high'] / result['low'])) ** 2

        for window in windows:
            # Parkinson 波動率
            result[f'parkinson_vol_{window}'] = np.sqrt(
                hl_ratio_sq.rolling(window=window).sum() / (4 * window * np.log(2))
            )

        return result

    @staticmethod
    def calculate_garman_klass_volatility(
        df: pd.DataFrame,
        windows: list = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        計算 Garman-Klass 波動率（使用 OHLC 資訊）
        更準確的波動率估計

        Args:
            df: OHLCV DataFrame
            windows: 滾動視窗大小列表

        Returns:
            包含 Garman-Klass 波動率的 DataFrame
        """
        result = df.copy()

        # GK 波動率公式
        hl = (np.log(result['high'] / result['low'])) ** 2
        co = (np.log(result['close'] / result['open'])) ** 2

        for window in windows:
            result[f'gk_vol_{window}'] = np.sqrt(
                (0.5 * hl - (2 * np.log(2) - 1) * co).rolling(window=window).mean()
            )

        return result

    @staticmethod
    def calculate_volatility_ratio(
        df: pd.DataFrame,
        short_window: int = 5,
        long_window: int = 20
    ) -> pd.DataFrame:
        """
        計算波動率比率（短期波動率 / 長期波動率）

        Args:
            df: 包含報酬率的 DataFrame
            short_window: 短期視窗
            long_window: 長期視窗

        Returns:
            包含波動率比率的 DataFrame
        """
        result = df.copy()

        if 'log_return_1' in result.columns:
            short_vol = result['log_return_1'].rolling(window=short_window).std()
            long_vol = result['log_return_1'].rolling(window=long_window).std()

            result[f'vol_ratio_{short_window}_{long_window}'] = short_vol / long_vol

        return result

    @staticmethod
    def calculate_realized_volatility(
        df: pd.DataFrame,
        windows: list = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        計算已實現波動率（Realized Volatility）

        Args:
            df: 包含報酬率的 DataFrame
            windows: 滾動視窗大小列表

        Returns:
            包含已實現波動率的 DataFrame
        """
        result = df.copy()

        if 'log_return_1' in result.columns:
            for window in windows:
                # 已實現波動率 = sqrt(sum of squared returns)
                result[f'realized_vol_{window}'] = np.sqrt(
                    (result['log_return_1'] ** 2).rolling(window=window).sum()
                )

        return result

    @staticmethod
    def calculate_volatility_features(
        df: pd.DataFrame,
        windows: list = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        計算波動率統計特徵

        Args:
            df: 包含價格的 DataFrame
            windows: 滾動視窗大小列表

        Returns:
            包含波動率統計特徵的 DataFrame
        """
        result = df.copy()

        for window in windows:
            # 價格標準差
            result[f'price_std_{window}'] = result['close'].rolling(window=window).std()

            # 變異係數（標準差 / 平均值）
            result[f'price_cv_{window}'] = (
                result[f'price_std_{window}'] /
                result['close'].rolling(window=window).mean()
            )

            # 高低價範圍標準差
            price_range = result['high'] - result['low']
            result[f'range_std_{window}'] = price_range.rolling(window=window).std()

        return result

    @classmethod
    def calculate_all(
        cls,
        df: pd.DataFrame,
        hist_vol_windows: list = [5, 10, 20],
        parkinson_windows: list = [5, 10, 20],
        gk_windows: list = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        計算所有波動率特徵

        Args:
            df: OHLCV DataFrame
            hist_vol_windows: 歷史波動率視窗
            parkinson_windows: Parkinson 波動率視窗
            gk_windows: Garman-Klass 波動率視窗

        Returns:
            包含所有波動率特徵的 DataFrame
        """
        result = df.copy()

        # 確保有對數報酬率
        if 'log_return_1' in result.columns:
            result = cls.calculate_historical_volatility(result, windows=hist_vol_windows)
            result = cls.calculate_realized_volatility(result, windows=hist_vol_windows)
            result = cls.calculate_volatility_ratio(result)

        # 基於 OHLC 的波動率
        result = cls.calculate_parkinson_volatility(result, windows=parkinson_windows)
        result = cls.calculate_garman_klass_volatility(result, windows=gk_windows)
        result = cls.calculate_volatility_features(result, windows=hist_vol_windows)

        return result
