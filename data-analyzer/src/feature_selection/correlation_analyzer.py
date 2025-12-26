"""
特徵相關性分析模組

職責：
- 計算特徵之間的相關性
- 識別高度相關的特徵對
- 移除冗餘特徵
"""
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional
from loguru import logger


class CorrelationAnalyzer:
    """特徵相關性分析器"""

    def __init__(self, threshold: float = 0.95):
        """
        初始化相關性分析器

        Args:
            threshold: 相關性閾值，超過此值視為高度相關
        """
        self.threshold = threshold
        self.correlation_matrix = None
        self.high_corr_pairs = []

    def calculate_correlation(
        self,
        df: pd.DataFrame,
        method: str = 'pearson'
    ) -> pd.DataFrame:
        """
        計算特徵相關性矩陣

        Args:
            df: 特徵 DataFrame
            method: 相關性計算方法 ('pearson', 'spearman', 'kendall')

        Returns:
            相關性矩陣
        """
        logger.info(f"計算特徵相關性（方法: {method}）...")

        # 只選擇數值型欄位
        numeric_df = df.select_dtypes(include=[np.number])

        # 計算相關性
        self.correlation_matrix = numeric_df.corr(method=method)

        logger.info(f"相關性矩陣大小: {self.correlation_matrix.shape}")

        return self.correlation_matrix

    def find_high_correlation_pairs(
        self,
        correlation_matrix: Optional[pd.DataFrame] = None,
        threshold: Optional[float] = None
    ) -> List[Tuple[str, str, float]]:
        """
        找出高度相關的特徵對

        Args:
            correlation_matrix: 相關性矩陣（如果為 None，使用已計算的矩陣）
            threshold: 相關性閾值（如果為 None，使用初始化時的閾值）

        Returns:
            高度相關的特徵對列表 [(feature1, feature2, correlation), ...]
        """
        corr_matrix = correlation_matrix if correlation_matrix is not None else self.correlation_matrix
        thresh = threshold if threshold is not None else self.threshold

        if corr_matrix is None:
            raise ValueError("請先計算相關性矩陣")

        high_corr_pairs = []

        # 遍歷相關性矩陣的上三角（避免重複）
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_value = abs(corr_matrix.iloc[i, j])

                if corr_value >= thresh:
                    feature1 = corr_matrix.columns[i]
                    feature2 = corr_matrix.columns[j]
                    high_corr_pairs.append((feature1, feature2, corr_value))

        # 按相關性降序排序
        high_corr_pairs.sort(key=lambda x: x[2], reverse=True)

        self.high_corr_pairs = high_corr_pairs

        logger.info(f"找到 {len(high_corr_pairs)} 對高度相關的特徵（閾值: {thresh}）")

        return high_corr_pairs

    def remove_correlated_features(
        self,
        df: pd.DataFrame,
        threshold: Optional[float] = None,
        method: str = 'pearson',
        keep_strategy: str = 'first'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        移除高度相關的特徵

        Args:
            df: 特徵 DataFrame
            threshold: 相關性閾值
            method: 相關性計算方法
            keep_strategy: 保留策略
                - 'first': 保留第一個特徵
                - 'variance': 保留方差較大的特徵
                - 'mean_corr': 保留與其他特徵平均相關性較低的特徵

        Returns:
            (處理後的 DataFrame, 被移除的特徵列表)
        """
        thresh = threshold if threshold is not None else self.threshold

        # 計算相關性矩陣
        if self.correlation_matrix is None:
            self.calculate_correlation(df, method=method)

        # 找出高度相關的特徵對
        high_corr_pairs = self.find_high_correlation_pairs(threshold=thresh)

        # 決定要移除哪些特徵
        features_to_remove = set()

        for feature1, feature2, corr_value in high_corr_pairs:
            # 如果兩個特徵都還沒被標記為移除
            if feature1 not in features_to_remove and feature2 not in features_to_remove:
                # 根據策略決定移除哪個
                if keep_strategy == 'first':
                    # 保留第一個，移除第二個
                    features_to_remove.add(feature2)

                elif keep_strategy == 'variance':
                    # 保留方差較大的
                    if df[feature1].var() < df[feature2].var():
                        features_to_remove.add(feature1)
                    else:
                        features_to_remove.add(feature2)

                elif keep_strategy == 'mean_corr':
                    # 保留與其他特徵平均相關性較低的
                    mean_corr1 = abs(self.correlation_matrix[feature1]).mean()
                    mean_corr2 = abs(self.correlation_matrix[feature2]).mean()

                    if mean_corr1 > mean_corr2:
                        features_to_remove.add(feature1)
                    else:
                        features_to_remove.add(feature2)

        features_to_remove = list(features_to_remove)

        logger.info(f"移除 {len(features_to_remove)} 個高度相關的特徵")

        # 移除特徵
        df_reduced = df.drop(columns=features_to_remove)

        return df_reduced, features_to_remove

    def get_correlation_with_target(
        self,
        df: pd.DataFrame,
        target_col: str,
        method: str = 'pearson',
        top_n: Optional[int] = None
    ) -> pd.Series:
        """
        計算特徵與目標變數的相關性

        Args:
            df: 包含特徵和目標的 DataFrame
            target_col: 目標變數欄位名稱
            method: 相關性計算方法
            top_n: 返回前 N 個最相關的特徵

        Returns:
            特徵與目標的相關性（按絕對值降序排列）
        """
        if target_col not in df.columns:
            raise ValueError(f"目標欄位 '{target_col}' 不存在")

        # 計算與目標的相關性
        correlations = df.corr(method=method)[target_col].drop(target_col)

        # 按絕對值降序排序
        correlations_sorted = correlations.abs().sort_values(ascending=False)

        if top_n is not None:
            correlations_sorted = correlations_sorted.head(top_n)

        logger.info(f"計算了 {len(correlations_sorted)} 個特徵與目標的相關性")

        return correlations

    def get_correlation_summary(self) -> Dict:
        """
        取得相關性分析摘要

        Returns:
            相關性摘要字典
        """
        if self.correlation_matrix is None:
            return {"error": "尚未計算相關性矩陣"}

        # 取得上三角的相關性值（排除對角線）
        upper_triangle = np.triu(self.correlation_matrix.values, k=1)
        upper_triangle_flat = upper_triangle[upper_triangle != 0]

        summary = {
            'total_features': len(self.correlation_matrix),
            'total_pairs': len(upper_triangle_flat),
            'high_corr_pairs': len(self.high_corr_pairs),
            'correlation_stats': {
                'mean': float(np.mean(np.abs(upper_triangle_flat))),
                'median': float(np.median(np.abs(upper_triangle_flat))),
                'max': float(np.max(np.abs(upper_triangle_flat))),
                'min': float(np.min(np.abs(upper_triangle_flat))),
                'std': float(np.std(np.abs(upper_triangle_flat)))
            }
        }

        return summary
