"""
特徵標準化/正規化工具

職責：
- 標準化（Standardization）
- 正規化（Normalization）
- Min-Max 縮放
- Robust 縮放
"""
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from loguru import logger


class FeatureScaler:
    """特徵縮放器"""

    def __init__(self):
        """初始化縮放器"""
        self.scaler = None
        self.scaler_type = None
        self.feature_names = None

    def fit_transform(
        self,
        df: pd.DataFrame,
        method: str = 'standard',
        exclude_cols: Optional[list] = None
    ) -> pd.DataFrame:
        """
        擬合並轉換特徵

        Args:
            df: 特徵 DataFrame
            method: 縮放方法
                - 'standard': 標準化 (mean=0, std=1)
                - 'minmax': Min-Max 縮放 (0-1)
                - 'robust': Robust 縮放 (使用四分位數)
                - 'normalize': L2 正規化
            exclude_cols: 要排除的欄位列表

        Returns:
            縮放後的 DataFrame
        """
        try:
            from sklearn.preprocessing import (
                StandardScaler,
                MinMaxScaler,
                RobustScaler,
                Normalizer
            )
        except ImportError:
            logger.error("需要安裝 scikit-learn")
            raise

        logger.info(f"使用 {method} 方法進行特徵縮放...")

        # 選擇要縮放的欄位
        if exclude_cols is None:
            exclude_cols = []

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cols_to_scale = [col for col in numeric_cols if col not in exclude_cols]

        # 選擇縮放器
        if method == 'standard':
            self.scaler = StandardScaler()
        elif method == 'minmax':
            self.scaler = MinMaxScaler()
        elif method == 'robust':
            self.scaler = RobustScaler()
        elif method == 'normalize':
            self.scaler = Normalizer()
        else:
            raise ValueError(f"不支援的縮放方法: {method}")

        self.scaler_type = method
        self.feature_names = cols_to_scale

        # 縮放
        result = df.copy()
        result[cols_to_scale] = self.scaler.fit_transform(df[cols_to_scale].fillna(0))

        logger.info(f"已縮放 {len(cols_to_scale)} 個特徵")

        return result

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        使用已擬合的縮放器轉換新資料

        Args:
            df: 特徵 DataFrame

        Returns:
            縮放後的 DataFrame
        """
        if self.scaler is None:
            raise ValueError("請先使用 fit_transform 擬合縮放器")

        result = df.copy()
        result[self.feature_names] = self.scaler.transform(df[self.feature_names].fillna(0))

        return result

    def inverse_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        反轉縮放

        Args:
            df: 縮放後的 DataFrame

        Returns:
            原始尺度的 DataFrame
        """
        if self.scaler is None:
            raise ValueError("請先使用 fit_transform 擬合縮放器")

        result = df.copy()
        result[self.feature_names] = self.scaler.inverse_transform(df[self.feature_names])

        return result

    @staticmethod
    def clip_outliers(
        df: pd.DataFrame,
        std_threshold: float = 3.0
    ) -> pd.DataFrame:
        """
        裁剪異常值（使用標準差方法）

        Args:
            df: 特徵 DataFrame
            std_threshold: 標準差閾值

        Returns:
            處理後的 DataFrame
        """
        logger.info(f"裁剪異常值（閾值: {std_threshold} 個標準差）...")

        result = df.copy()
        numeric_cols = result.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            mean = result[col].mean()
            std = result[col].std()

            lower_bound = mean - std_threshold * std
            upper_bound = mean + std_threshold * std

            result[col] = result[col].clip(lower=lower_bound, upper=upper_bound)

        return result

    @staticmethod
    def handle_missing_values(
        df: pd.DataFrame,
        method: str = 'mean'
    ) -> pd.DataFrame:
        """
        處理缺失值

        Args:
            df: 特徵 DataFrame
            method: 處理方法
                - 'mean': 使用平均值填補
                - 'median': 使用中位數填補
                - 'forward': 前向填補
                - 'backward': 後向填補
                - 'zero': 使用 0 填補

        Returns:
            處理後的 DataFrame
        """
        logger.info(f"處理缺失值（方法: {method}）...")

        result = df.copy()
        numeric_cols = result.select_dtypes(include=[np.number]).columns

        if method == 'mean':
            result[numeric_cols] = result[numeric_cols].fillna(result[numeric_cols].mean())
        elif method == 'median':
            result[numeric_cols] = result[numeric_cols].fillna(result[numeric_cols].median())
        elif method == 'forward':
            result[numeric_cols] = result[numeric_cols].fillna(method='ffill')
        elif method == 'backward':
            result[numeric_cols] = result[numeric_cols].fillna(method='bfill')
        elif method == 'zero':
            result[numeric_cols] = result[numeric_cols].fillna(0)
        else:
            raise ValueError(f"不支援的方法: {method}")

        return result
