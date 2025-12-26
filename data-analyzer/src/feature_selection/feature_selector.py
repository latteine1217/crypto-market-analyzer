"""
特徵選擇器

職責：
- 方差篩選（移除低方差特徵）
- 單變量特徵選擇
- 結合多種方法的綜合選擇
"""
import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Dict
from loguru import logger


class FeatureSelector:
    """特徵選擇器"""

    @staticmethod
    def remove_low_variance_features(
        df: pd.DataFrame,
        threshold: float = 0.01
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        移除低方差特徵

        Args:
            df: 特徵 DataFrame
            threshold: 方差閾值（相對方差：std/mean）

        Returns:
            (處理後的 DataFrame, 被移除的特徵列表)
        """
        logger.info(f"移除低方差特徵（閾值: {threshold}）...")

        # 計算相對方差（變異係數）
        numeric_df = df.select_dtypes(include=[np.number])

        # 避免除以零
        means = numeric_df.mean()
        stds = numeric_df.std()
        cv = stds / (means.abs() + 1e-10)  # 變異係數

        # 找出低方差特徵
        low_variance_features = cv[cv < threshold].index.tolist()

        logger.info(f"移除 {len(low_variance_features)} 個低方差特徵")

        # 移除特徵
        df_reduced = df.drop(columns=low_variance_features, errors='ignore')

        return df_reduced, low_variance_features

    @staticmethod
    def remove_constant_features(
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        移除常數特徵（所有值都相同）

        Args:
            df: 特徵 DataFrame

        Returns:
            (處理後的 DataFrame, 被移除的特徵列表)
        """
        logger.info("移除常數特徵...")

        numeric_df = df.select_dtypes(include=[np.number])

        # 找出常數特徵（標準差為 0）
        constant_features = numeric_df.columns[numeric_df.std() == 0].tolist()

        logger.info(f"移除 {len(constant_features)} 個常數特徵")

        df_reduced = df.drop(columns=constant_features, errors='ignore')

        return df_reduced, constant_features

    @staticmethod
    def remove_missing_features(
        df: pd.DataFrame,
        threshold: float = 0.5
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        移除缺失值過多的特徵

        Args:
            df: 特徵 DataFrame
            threshold: 缺失比例閾值（0-1）

        Returns:
            (處理後的 DataFrame, 被移除的特徵列表)
        """
        logger.info(f"移除缺失值過多的特徵（閾值: {threshold*100}%）...")

        # 計算缺失比例
        missing_ratio = df.isnull().sum() / len(df)

        # 找出缺失過多的特徵
        high_missing_features = missing_ratio[missing_ratio > threshold].index.tolist()

        logger.info(f"移除 {len(high_missing_features)} 個缺失值過多的特徵")

        df_reduced = df.drop(columns=high_missing_features, errors='ignore')

        return df_reduced, high_missing_features

    @classmethod
    def auto_select_features(
        cls,
        df: pd.DataFrame,
        remove_constant: bool = True,
        variance_threshold: float = 0.01,
        missing_threshold: float = 0.5
    ) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
        """
        自動進行基礎特徵選擇

        Args:
            df: 特徵 DataFrame
            remove_constant: 是否移除常數特徵
            variance_threshold: 方差閾值
            missing_threshold: 缺失值閾值

        Returns:
            (處理後的 DataFrame, 移除特徵的詳細資訊)
        """
        logger.info("=" * 60)
        logger.info("開始自動特徵選擇")
        logger.info(f"初始特徵數: {df.shape[1]}")
        logger.info("=" * 60)

        result = df.copy()
        removed_features = {}

        # 1. 移除常數特徵
        if remove_constant:
            result, const_features = cls.remove_constant_features(result)
            removed_features['constant'] = const_features

        # 2. 移除缺失過多的特徵
        result, missing_features = cls.remove_missing_features(result, missing_threshold)
        removed_features['high_missing'] = missing_features

        # 3. 移除低方差特徵
        result, low_var_features = cls.remove_low_variance_features(result, variance_threshold)
        removed_features['low_variance'] = low_var_features

        logger.info("=" * 60)
        logger.info(f"最終特徵數: {result.shape[1]}")
        logger.info(f"移除特徵總數: {df.shape[1] - result.shape[1]}")
        logger.info("=" * 60)

        return result, removed_features
