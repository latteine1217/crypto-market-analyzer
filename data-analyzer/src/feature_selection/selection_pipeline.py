"""
特徵選擇 Pipeline

職責：
- 整合所有特徵選擇方法
- 提供完整的特徵優化流程
- 生成特徵選擇報告
"""
import pandas as pd
from typing import Dict, List, Optional, Tuple
from loguru import logger

from .correlation_analyzer import CorrelationAnalyzer
from .importance_analyzer import ImportanceAnalyzer
from .feature_selector import FeatureSelector
from .feature_scaler import FeatureScaler


class SelectionPipeline:
    """特徵選擇 Pipeline"""

    def __init__(self):
        """初始化 Pipeline"""
        self.correlation_analyzer = CorrelationAnalyzer()
        self.importance_analyzer = ImportanceAnalyzer()
        self.scaler = FeatureScaler()

        self.original_features = []
        self.selected_features = []
        self.removed_features = {}
        self.selection_report = {}

    def run(
        self,
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        methods: Optional[List[str]] = None,
        scale_method: str = 'standard',
        **kwargs
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        執行完整的特徵選擇流程

        Args:
            df: 特徵 DataFrame
            target_col: 目標變數欄位（如果有）
            methods: 要使用的方法列表
                - 'remove_constant': 移除常數特徵
                - 'remove_low_variance': 移除低方差特徵
                - 'remove_missing': 移除缺失過多的特徵
                - 'remove_correlated': 移除高度相關的特徵
                - 'importance': 基於重要性選擇
            scale_method: 縮放方法
            **kwargs: 其他參數

        Returns:
            (優化後的 DataFrame, 選擇報告)
        """
        logger.info("=" * 60)
        logger.info("特徵選擇 Pipeline 開始")
        logger.info(f"初始特徵數: {df.shape[1]}")
        logger.info(f"初始樣本數: {df.shape[0]}")
        logger.info("=" * 60)

        # 預設使用所有方法
        if methods is None:
            methods = [
                'remove_constant',
                'remove_low_variance',
                'remove_missing',
                'remove_correlated'
            ]

        result = df.copy()
        self.original_features = list(df.columns)

        # 1. 基礎特徵選擇
        logger.info("\n### 階段 1: 基礎特徵篩選 ###")

        if 'remove_constant' in methods or 'remove_low_variance' in methods or 'remove_missing' in methods:
            result, removed = FeatureSelector.auto_select_features(
                result,
                remove_constant='remove_constant' in methods,
                variance_threshold=kwargs.get('variance_threshold', 0.01),
                missing_threshold=kwargs.get('missing_threshold', 0.5)
            )
            self.removed_features.update(removed)

        # 2. 移除高度相關的特徵
        if 'remove_correlated' in methods:
            logger.info("\n### 階段 2: 移除高度相關特徵 ###")
            result, corr_removed = self.correlation_analyzer.remove_correlated_features(
                result,
                threshold=kwargs.get('correlation_threshold', 0.95),
                keep_strategy=kwargs.get('keep_strategy', 'variance')
            )
            self.removed_features['correlated'] = corr_removed

        # 3. 基於重要性選擇（如果有目標變數）
        if 'importance' in methods and target_col is not None and target_col in result.columns:
            logger.info("\n### 階段 3: 基於重要性選擇特徵 ###")

            X = result.drop(columns=[target_col])
            y = result[target_col]

            X_selected, selected_features = self.importance_analyzer.select_top_features(
                X, y,
                method=kwargs.get('importance_method', 'random_forest'),
                top_n=kwargs.get('top_n', None),
                threshold=kwargs.get('importance_threshold', None)
            )

            result = pd.concat([X_selected, y], axis=1)
            importance_removed = [f for f in X.columns if f not in selected_features]
            self.removed_features['low_importance'] = importance_removed

        # 4. 處理缺失值
        logger.info("\n### 階段 4: 處理缺失值 ###")
        result = FeatureScaler.handle_missing_values(
            result,
            method=kwargs.get('missing_method', 'forward')
        )

        # 5. 裁剪異常值（可選）
        if kwargs.get('clip_outliers', False):
            logger.info("\n### 階段 5: 裁剪異常值 ###")
            result = FeatureScaler.clip_outliers(
                result,
                std_threshold=kwargs.get('outlier_std', 3.0)
            )

        # 6. 特徵縮放
        logger.info(f"\n### 階段 6: 特徵縮放（{scale_method}） ###")
        exclude_cols = [target_col] if target_col and target_col in result.columns else []
        result = self.scaler.fit_transform(result, method=scale_method, exclude_cols=exclude_cols)

        # 記錄最終選擇的特徵
        self.selected_features = list(result.columns)

        # 生成報告
        self.selection_report = self._generate_report(df, result)

        logger.info("=" * 60)
        logger.info("特徵選擇 Pipeline 完成")
        logger.info(f"最終特徵數: {result.shape[1]}")
        logger.info(f"移除特徵數: {df.shape[1] - result.shape[1]}")
        logger.info(f"保留比例: {result.shape[1]/df.shape[1]*100:.1f}%")
        logger.info("=" * 60)

        return result, self.selection_report

    def _generate_report(self, df_original: pd.DataFrame, df_final: pd.DataFrame) -> Dict:
        """
        生成特徵選擇報告

        Args:
            df_original: 原始 DataFrame
            df_final: 處理後的 DataFrame

        Returns:
            報告字典
        """
        total_removed = sum(len(features) for features in self.removed_features.values())

        report = {
            'original_shape': df_original.shape,
            'final_shape': df_final.shape,
            'features_removed': {
                'total': total_removed,
                'by_reason': {k: len(v) for k, v in self.removed_features.items()}
            },
            'features_kept': len(df_final.columns),
            'retention_rate': len(df_final.columns) / len(df_original.columns),
            'removed_features_detail': self.removed_features,
            'correlation_summary': self.correlation_analyzer.get_correlation_summary(),
            'importance_summary': self.importance_analyzer.get_importance_summary()
        }

        return report

    def print_report(self):
        """列印特徵選擇報告"""
        if not self.selection_report:
            print("尚未執行特徵選擇")
            return

        print("\n" + "=" * 60)
        print("特徵選擇報告")
        print("=" * 60)

        print(f"\n原始維度: {self.selection_report['original_shape']}")
        print(f"最終維度: {self.selection_report['final_shape']}")
        print(f"保留率: {self.selection_report['retention_rate']*100:.1f}%")

        print(f"\n移除特徵統計:")
        for reason, count in self.selection_report['features_removed']['by_reason'].items():
            print(f"  - {reason}: {count} 個")

        if self.selection_report['correlation_summary'].get('high_corr_pairs'):
            print(f"\n高度相關特徵對: {self.selection_report['correlation_summary']['high_corr_pairs']} 對")

        if 'top_10_features' in self.selection_report['importance_summary']:
            print("\n前 10 重要特徵:")
            for feature, importance in self.selection_report['importance_summary']['top_10_features'][:10]:
                print(f"  {feature}: {importance:.4f}")

        print("=" * 60)
