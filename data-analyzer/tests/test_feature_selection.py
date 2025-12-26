"""
特徵選擇測試腳本

用途：測試特徵選擇 pipeline 是否正常運作
"""
import sys
from pathlib import Path

# 加入 src 到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from features.feature_pipeline import FeaturePipeline
from feature_selection.selection_pipeline import SelectionPipeline


def test_feature_selection():
    """測試完整的特徵選擇流程"""

    print("=" * 60)
    print("特徵選擇 Pipeline 測試")
    print("=" * 60)

    # 1. 先用特徵工程 pipeline 計算所有特徵
    print("\n### 步驟 1: 計算所有特徵 ###")
    feature_pipeline = FeaturePipeline()

    df_features = feature_pipeline.run(
        symbol='BTC/USDT',
        timeframe='1m',
        limit=500,
        dropna=True
    )

    if df_features.empty:
        print("❌ 無法載入資料")
        return

    print(f"\n原始特徵數: {df_features.shape[1]}")

    # 2. 準備目標變數（使用未來 1 期的收益率作為目標）
    print("\n### 步驟 2: 準備目標變數 ###")
    df_features['target'] = df_features['close'].pct_change(1).shift(-1)
    df_features = df_features.dropna()

    print(f"目標變數: target (未來 1 期收益率)")
    print(f"目標統計: mean={df_features['target'].mean():.6f}, std={df_features['target'].std():.6f}")

    # 3. 執行特徵選擇
    print("\n### 步驟 3: 執行特徵選擇 ###")
    selection_pipeline = SelectionPipeline()

    df_selected, report = selection_pipeline.run(
        df=df_features,
        target_col='target',
        methods=['remove_constant', 'remove_low_variance', 'remove_missing', 'remove_correlated', 'importance'],
        scale_method='standard',
        correlation_threshold=0.95,
        variance_threshold=0.01,
        importance_method='random_forest',
        top_n=30,  # 只保留前 30 個最重要的特徵
        clip_outliers=True,
        outlier_std=3.0
    )

    # 4. 列印報告
    print("\n### 步驟 4: 特徵選擇結果 ###")
    selection_pipeline.print_report()

    # 5. 顯示最終選擇的特徵
    print("\n最終選擇的特徵:")
    selected_features = [col for col in df_selected.columns if col != 'target']
    for i, feature in enumerate(selected_features[:20], 1):  # 只顯示前 20 個
        print(f"  {i}. {feature}")

    if len(selected_features) > 20:
        print(f"  ... 還有 {len(selected_features) - 20} 個特徵")

    # 6. 顯示資料摘要
    print("\n最終資料摘要:")
    print(df_selected.describe())

    print("\n" + "=" * 60)
    print("✅ 測試完成！")
    print("=" * 60)

    return df_selected, report


if __name__ == "__main__":
    df_selected, report = test_feature_selection()
