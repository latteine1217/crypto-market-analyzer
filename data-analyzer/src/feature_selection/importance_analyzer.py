"""
特徵重要性分析模組

職責：
- 使用機器學習模型評估特徵重要性
- 支援多種模型（Random Forest, XGBoost 等）
- 提供特徵排序和選擇建議
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from loguru import logger


class ImportanceAnalyzer:
    """特徵重要性分析器"""

    def __init__(self):
        """初始化特徵重要性分析器"""
        self.feature_importances = None
        self.model = None

    def calculate_random_forest_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_estimators: int = 100,
        random_state: int = 42,
        **kwargs
    ) -> pd.Series:
        """
        使用 Random Forest 計算特徵重要性

        Args:
            X: 特徵 DataFrame
            y: 目標變數
            n_estimators: 樹的數量
            random_state: 隨機種子
            **kwargs: 其他 RandomForestRegressor 參數

        Returns:
            特徵重要性 Series（降序排列）
        """
        try:
            from sklearn.ensemble import RandomForestRegressor
        except ImportError:
            logger.error("需要安裝 scikit-learn: pip install scikit-learn")
            raise

        logger.info(f"使用 Random Forest 計算特徵重要性（樹數: {n_estimators}）...")

        # 訓練 Random Forest
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1,
            **kwargs
        )

        # 移除 NaN
        X_clean = X.fillna(0)
        y_clean = y.fillna(y.mean())

        self.model.fit(X_clean, y_clean)

        # 取得特徵重要性
        importances = pd.Series(
            self.model.feature_importances_,
            index=X.columns
        ).sort_values(ascending=False)

        self.feature_importances = importances

        logger.info(f"計算完成！前 5 重要特徵: {list(importances.head().index)}")

        return importances

    def calculate_permutation_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model=None,
        n_repeats: int = 10,
        random_state: int = 42
    ) -> pd.Series:
        """
        使用 Permutation Importance 計算特徵重要性
        （更準確但計算成本較高）

        Args:
            X: 特徵 DataFrame
            y: 目標變數
            model: 已訓練的模型（如果為 None，使用 Random Forest）
            n_repeats: 重複次數
            random_state: 隨機種子

        Returns:
            特徵重要性 Series
        """
        try:
            from sklearn.inspection import permutation_importance
            from sklearn.ensemble import RandomForestRegressor
        except ImportError:
            logger.error("需要安裝 scikit-learn")
            raise

        logger.info("計算 Permutation Importance...")

        # 如果沒有提供模型，使用 Random Forest
        if model is None:
            model = RandomForestRegressor(n_estimators=100, random_state=random_state, n_jobs=-1)
            X_clean = X.fillna(0)
            y_clean = y.fillna(y.mean())
            model.fit(X_clean, y_clean)
        else:
            X_clean = X.fillna(0)
            y_clean = y.fillna(y.mean())

        # 計算 Permutation Importance
        perm_importance = permutation_importance(
            model,
            X_clean,
            y_clean,
            n_repeats=n_repeats,
            random_state=random_state,
            n_jobs=-1
        )

        importances = pd.Series(
            perm_importance.importances_mean,
            index=X.columns
        ).sort_values(ascending=False)

        logger.info("Permutation Importance 計算完成")

        return importances

    def select_top_features(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        method: str = 'random_forest',
        top_n: Optional[int] = None,
        threshold: Optional[float] = None,
        **kwargs
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        根據重要性選擇特徵

        Args:
            X: 特徵 DataFrame
            y: 目標變數
            method: 計算方法 ('random_forest', 'permutation')
            top_n: 選擇前 N 個特徵
            threshold: 重要性閾值（選擇重要性 > threshold 的特徵）
            **kwargs: 其他參數

        Returns:
            (選擇後的 DataFrame, 選中的特徵列表)
        """
        # 計算特徵重要性
        if method == 'random_forest':
            importances = self.calculate_random_forest_importance(X, y, **kwargs)
        elif method == 'permutation':
            importances = self.calculate_permutation_importance(X, y, **kwargs)
        else:
            raise ValueError(f"不支援的方法: {method}")

        # 選擇特徵
        if top_n is not None:
            selected_features = list(importances.head(top_n).index)
        elif threshold is not None:
            selected_features = list(importances[importances > threshold].index)
        else:
            # 預設選擇累積重要性達 95% 的特徵
            cumsum = importances.cumsum()
            selected_features = list(cumsum[cumsum <= 0.95].index)

        logger.info(f"選擇了 {len(selected_features)} 個特徵")

        X_selected = X[selected_features]

        return X_selected, selected_features

    def get_importance_summary(self) -> Dict:
        """
        取得特徵重要性摘要

        Returns:
            重要性摘要字典
        """
        if self.feature_importances is None:
            return {"error": "尚未計算特徵重要性"}

        summary = {
            'total_features': len(self.feature_importances),
            'top_10_features': list(self.feature_importances.head(10).to_dict().items()),
            'importance_stats': {
                'mean': float(self.feature_importances.mean()),
                'median': float(self.feature_importances.median()),
                'max': float(self.feature_importances.max()),
                'min': float(self.feature_importances.min()),
                'std': float(self.feature_importances.std())
            },
            'cumulative_95%': len(self.feature_importances[self.feature_importances.cumsum() <= 0.95])
        }

        return summary
