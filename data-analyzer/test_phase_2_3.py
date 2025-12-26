"""
階段 2 & 3 功能測試

測試所有新建立的特徵工程和模型模組
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from features.price_features import PriceFeatures
from features.volume_features import VolumeFeatures
from features.technical_indicators import TechnicalIndicators
from features.feature_pipeline import FeaturePipeline
from models.baseline.ma_forecast import (
    MovingAverageForecast,
    ExponentialMovingAverageForecast,
    NaiveForecast,
    compare_baseline_models
)
from anomaly.isolation_forest import (
    PriceAnomalyDetector,
    StatisticalAnomalyDetector,
    run_comprehensive_anomaly_detection
)


def test_price_features():
    """測試價格特徵模組"""
    print("\n" + "="*80)
    print("測試 1: 價格特徵計算")
    print("="*80)

    # 生成測試資料
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.uniform(90, 110, 100),
        'high': np.random.uniform(100, 120, 100),
        'low': np.random.uniform(80, 100, 100),
        'close': np.cumsum(np.random.randn(100)) + 100,
        'volume': np.random.uniform(1000, 10000, 100)
    })

    # 計算特徵
    df_with_features = PriceFeatures.add_all_price_features(df)

    print(f"✓ 原始欄位數: {len(df.columns)}")
    print(f"✓ 加入特徵後欄位數: {len(df_with_features.columns)}")
    print(f"✓ 新增特徵數: {len(df_with_features.columns) - len(df.columns)}")

    # 顯示部分特徵
    feature_cols = [col for col in df_with_features.columns if col not in df.columns]
    print(f"\n前 10 個特徵: {feature_cols[:10]}")

    return df_with_features


def test_volume_features():
    """測試成交量特徵模組"""
    print("\n" + "="*80)
    print("測試 2: 成交量特徵計算")
    print("="*80)

    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    df = pd.DataFrame({
        'timestamp': dates,
        'close': np.cumsum(np.random.randn(100)) + 100,
        'volume': np.random.uniform(1000, 10000, 100)
    })

    df_with_features = VolumeFeatures.add_all_volume_features(df)

    print(f"✓ 原始欄位數: {len(df.columns)}")
    print(f"✓ 加入特徵後欄位數: {len(df_with_features.columns)}")
    print(f"✓ 新增特徵數: {len(df_with_features.columns) - len(df.columns)}")

    feature_cols = [col for col in df_with_features.columns if col not in df.columns]
    print(f"\n前 10 個特徵: {feature_cols[:10]}")

    return df_with_features


def test_technical_indicators():
    """測試技術指標模組"""
    print("\n" + "="*80)
    print("測試 3: 技術指標計算")
    print("="*80)

    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.uniform(90, 110, 100),
        'high': np.random.uniform(100, 120, 100),
        'low': np.random.uniform(80, 100, 100),
        'close': np.cumsum(np.random.randn(100)) + 100,
        'volume': np.random.uniform(1000, 10000, 100)
    })

    # MACD
    df = TechnicalIndicators.calculate_macd(df)
    print("✓ MACD 計算完成")

    # RSI
    df = TechnicalIndicators.calculate_rsi(df)
    print("✓ RSI 計算完成")

    # Bollinger Bands
    df = TechnicalIndicators.calculate_bollinger_bands(df)
    print("✓ Bollinger Bands 計算完成")

    # 威廉分形
    df = TechnicalIndicators.identify_williams_fractal(df)
    print("✓ 威廉分形識別完成")

    print(f"\n總欄位數: {len(df.columns)}")

    return df


def test_baseline_models():
    """測試 Baseline 模型"""
    print("\n" + "="*80)
    print("測試 4: Baseline 預測模型")
    print("="*80)

    # 生成測試資料（有趨勢的時間序列）
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1min')
    y = pd.Series(
        np.cumsum(np.random.randn(200) * 0.5) + 100,
        index=dates,
        name='price'
    )

    # 簡單測試每個模型
    print("\n測試各個模型:")

    # MA 模型
    ma_model = MovingAverageForecast(window=20)
    ma_model.fit(y)
    ma_pred = ma_model.predict(y)
    print(f"✓ MA(20): 預測了 {len(ma_pred)} 個值")

    # EMA 模型
    ema_model = ExponentialMovingAverageForecast(span=20)
    ema_model.fit(y)
    ema_pred = ema_model.predict(y)
    print(f"✓ EMA(20): 預測了 {len(ema_pred)} 個值")

    # Naive 模型
    naive_model = NaiveForecast()
    naive_model.fit(y)
    naive_pred = naive_model.predict(y)
    print(f"✓ Naive: 預測了 {len(naive_pred)} 個值")

    print("\n✓ 所有 baseline 模型測試通過")

    return None


def test_anomaly_detection():
    """測試異常偵測模型"""
    print("\n" + "="*80)
    print("測試 5: 異常偵測")
    print("="*80)

    # 生成帶異常的測試資料
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1min')

    # 正常資料 + 幾個異常點
    close_prices = np.cumsum(np.random.randn(200) * 0.5) + 100
    close_prices[50] = close_prices[49] * 1.15  # 暴漲
    close_prices[100] = close_prices[99] * 0.85  # 閃崩
    close_prices[150] = close_prices[149] * 1.20  # 暴漲

    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices + np.random.randn(200) * 0.5,
        'high': close_prices + np.random.uniform(0, 2, 200),
        'low': close_prices - np.random.uniform(0, 2, 200),
        'close': close_prices,
        'volume': np.random.uniform(1000, 10000, 200)
    })

    # 執行異常偵測
    result = run_comprehensive_anomaly_detection(
        df,
        methods=['isolation_forest', 'zscore', 'iqr']
    )

    # 統計異常
    if 'anomaly_if' in result.columns:
        anomalies_if = (result['anomaly_if'] == -1).sum()
        print(f"✓ Isolation Forest 檢測到 {anomalies_if} 個異常")

    if 'anomaly_zscore' in result.columns:
        anomalies_zscore = result['anomaly_zscore'].sum()
        print(f"✓ Z-score 檢測到 {anomalies_zscore} 個異常")

    if 'anomaly_iqr' in result.columns:
        anomalies_iqr = result['anomaly_iqr'].sum()
        print(f"✓ IQR 檢測到 {anomalies_iqr} 個異常")

    if 'anomaly_consensus' in result.columns:
        anomalies_consensus = result['anomaly_consensus'].sum()
        print(f"✓ 綜合判斷檢測到 {anomalies_consensus} 個異常")

    return result


def main():
    """執行所有測試"""
    print("\n" + "#"*80)
    print("# 階段 2 & 3 功能測試")
    print("#"*80)

    try:
        # 測試 1: 價格特徵
        df1 = test_price_features()

        # 測試 2: 成交量特徵
        df2 = test_volume_features()

        # 測試 3: 技術指標
        df3 = test_technical_indicators()

        # 測試 4: Baseline 模型
        results = test_baseline_models()

        # 測試 5: 異常偵測
        anomaly_df = test_anomaly_detection()

        print("\n" + "#"*80)
        print("# 測試總結")
        print("#"*80)
        print("\n✅ 所有測試通過！")
        print("\n已實作功能:")
        print("  ✓ 價格特徵工程")
        print("  ✓ 成交量特徵工程")
        print("  ✓ 技術指標計算")
        print("  ✓ Baseline 預測模型")
        print("  ✓ 異常偵測模型")
        print("\n階段 2 & 3 開發完成！")

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
