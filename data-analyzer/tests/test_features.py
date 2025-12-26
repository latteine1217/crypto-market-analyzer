"""
特徵工程測試腳本

用途：測試特徵計算 pipeline 是否正常運作
"""
import sys
from pathlib import Path

# 加入 src 到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from features.feature_pipeline import FeaturePipeline


def test_feature_pipeline():
    """測試完整的特徵計算流程"""

    print("=" * 60)
    print("特徵工程 Pipeline 測試")
    print("=" * 60)

    # 初始化 Pipeline
    pipeline = FeaturePipeline()

    # 執行特徵計算（使用資料庫中的資料）
    df_features = pipeline.run(
        symbol='BTC/USDT',
        timeframe='1m',
        limit=500,  # 只取最新 500 筆資料測試
        dropna=True  # 刪除包含 NaN 的行
    )

    if df_features.empty:
        print("❌ 無法載入資料或計算特徵")
        return

    print("\n" + "=" * 60)
    print("特徵計算結果")
    print("=" * 60)

    # 顯示資料形狀
    print(f"\n資料形狀: {df_features.shape}")
    print(f"  - 樣本數: {df_features.shape[0]}")
    print(f"  - 特徵數: {df_features.shape[1]}")

    # 顯示特徵名稱
    feature_names = pipeline.get_feature_names(df_features)
    print(f"\n特徵總數（排除 OHLCV）: {len(feature_names)}")

    # 顯示特徵摘要
    summary = pipeline.get_feature_summary(df_features)
    print("\n特徵分組統計:")
    for group, count in summary['feature_groups'].items():
        print(f"  - {group}: {count} 個特徵")

    print(f"\nNaN 比率: {summary['nan_ratio']:.2%}")

    # 顯示前 5 行
    print("\n前 5 行資料:")
    print(df_features.head())

    # 顯示資料統計
    print("\n資料統計（部分特徵）:")
    important_features = [col for col in df_features.columns if any(
        key in col for key in ['close', 'return_1', 'rsi', 'macd', 'volume']
    )][:10]
    print(df_features[important_features].describe())

    print("\n" + "=" * 60)
    print("✅ 測試完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_feature_pipeline()
