"""
異常檢測模型 Demo 測試腳本

測試多種異常檢測方法：
1. Isolation Forest
2. Z-Score
3. MAD (Median Absolute Deviation)
4. Composite Detector

使用含有人工注入異常的合成資料進行測試。
"""

import sys
import logging
from pathlib import Path
from typing import Tuple
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非互動式後端
import matplotlib.pyplot as plt

# 添加專案路徑
sys.path.append(str(Path(__file__).parent))

from src.models.anomaly import (
    IsolationForestDetector,
    ZScoreDetector,
    MADDetector,
    CompositeDetector
)

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_price_data_with_anomalies(
    n_samples: int = 2000,
    base_price: float = 50000,
    trend: float = 0.0001,
    volatility: float = 0.015,
    n_anomalies: int = 10,
    anomaly_magnitude: float = 5.0,
    random_seed: int = 42
) -> Tuple[pd.Series, pd.Series]:
    """
    生成含有異常的價格資料

    Args:
        n_samples: 樣本數
        base_price: 基礎價格
        trend: 趨勢
        volatility: 波動率
        n_anomalies: 異常數量
        anomaly_magnitude: 異常幅度（標準差倍數）
        random_seed: 隨機種子

    Returns:
        (價格序列, 真實異常標記)
    """
    np.random.seed(random_seed)

    # 生成正常價格
    returns = np.random.normal(trend, volatility, n_samples)

    # 添加週期性
    t = np.arange(n_samples)
    seasonal = 0.003 * np.sin(2 * np.pi * t / 100)
    returns += seasonal

    # 計算價格
    prices = base_price * np.exp(np.cumsum(returns))

    # 創建時間索引
    timestamps = pd.date_range(
        start='2024-01-01',
        periods=n_samples,
        freq='1min'
    )

    prices_series = pd.Series(prices, index=timestamps, name='close')

    # 注入異常（flash crash / pump）
    true_anomalies = pd.Series(False, index=timestamps)

    anomaly_indices = np.random.choice(
        range(100, n_samples - 100),  # 避免邊界
        size=n_anomalies,
        replace=False
    )

    logger.info(f"注入 {n_anomalies} 個異常事件...")

    for idx in anomaly_indices:
        anomaly_type = np.random.choice(['crash', 'pump', 'spike'])

        if anomaly_type == 'crash':
            # Flash crash: 突然下跌後部分恢復
            prices_series.iloc[idx] *= (1 - anomaly_magnitude * volatility)
            prices_series.iloc[idx+1] *= (1 + anomaly_magnitude * volatility * 0.5)
            true_anomalies.iloc[idx:idx+2] = True
            logger.info(f"  - Flash crash at index {idx}")

        elif anomaly_type == 'pump':
            # Pump: 突然上漲後部分回落
            prices_series.iloc[idx] *= (1 + anomaly_magnitude * volatility)
            prices_series.iloc[idx+1] *= (1 - anomaly_magnitude * volatility * 0.5)
            true_anomalies.iloc[idx:idx+2] = True
            logger.info(f"  - Pump at index {idx}")

        else:  # spike
            # 價格尖峰
            prices_series.iloc[idx] *= (1 + anomaly_magnitude * volatility *
                                       np.random.choice([-1, 1]))
            true_anomalies.iloc[idx] = True
            logger.info(f"  - Spike at index {idx}")

    return prices_series, true_anomalies


def test_isolation_forest():
    """測試 Isolation Forest"""
    logger.info("=" * 60)
    logger.info("測試 1: Isolation Forest 異常檢測")
    logger.info("=" * 60)

    # 生成資料
    prices, true_anomalies = generate_price_data_with_anomalies()

    # 分割訓練/測試
    train_size = int(len(prices) * 0.7)
    train_prices = prices.iloc[:train_size]
    test_prices = prices.iloc[train_size:]
    test_true_anomalies = true_anomalies.iloc[train_size:]

    # 訓練模型
    logger.info("訓練 Isolation Forest...")
    detector = IsolationForestDetector(
        contamination=0.05,  # 預期 5% 異常
        n_estimators=50,     # 輕量級配置
        random_state=42
    )
    detector.fit(train_prices)

    # 檢測
    logger.info("檢測異常...")
    results = detector.predict(test_prices)

    # 評估
    stats = detector.get_anomaly_statistics(results)

    logger.info("\nIsolation Forest 統計：")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # 計算準確率（與真實異常對比）
    aligned_results = results.reindex(test_true_anomalies.index, fill_value=False)
    precision, recall, f1 = calculate_metrics(
        test_true_anomalies,
        aligned_results['anomaly']
    )

    logger.info(f"\n性能指標：")
    logger.info(f"  Precision: {precision:.2%}")
    logger.info(f"  Recall: {recall:.2%}")
    logger.info(f"  F1-Score: {f1:.2%}")

    return detector, results, test_prices, test_true_anomalies


def test_zscore():
    """測試 Z-Score"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 2: Z-Score 異常檢測")
    logger.info("=" * 60)

    prices, true_anomalies = generate_price_data_with_anomalies()

    # 訓練
    detector = ZScoreDetector(threshold=3.0, window=20)
    detector.fit(prices, return_based=True)

    # 檢測
    results = detector.predict(prices, return_based=True)
    stats = detector.get_anomaly_statistics(results)

    logger.info("\nZ-Score 統計：")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # 評估
    aligned_true = true_anomalies.reindex(results.index, fill_value=False)
    precision, recall, f1 = calculate_metrics(aligned_true, results['anomaly'])

    logger.info(f"\n性能指標：")
    logger.info(f"  Precision: {precision:.2%}")
    logger.info(f"  Recall: {recall:.2%}")
    logger.info(f"  F1-Score: {f1:.2%}")

    return detector, results


def test_mad():
    """測試 MAD"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 3: MAD 異常檢測")
    logger.info("=" * 60)

    prices, true_anomalies = generate_price_data_with_anomalies()

    # 訓練
    detector = MADDetector(threshold=3.5, window=20)
    detector.fit(prices, return_based=True)

    # 檢測
    results = detector.predict(prices, return_based=True)
    stats = detector.get_anomaly_statistics(results)

    logger.info("\nMAD 統計：")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    # 評估
    aligned_true = true_anomalies.reindex(results.index, fill_value=False)
    precision, recall, f1 = calculate_metrics(aligned_true, results['anomaly'])

    logger.info(f"\n性能指標：")
    logger.info(f"  Precision: {precision:.2%}")
    logger.info(f"  Recall: {recall:.2%}")
    logger.info(f"  F1-Score: {f1:.2%}")

    return detector, results


def test_composite():
    """測試組合檢測器"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 4: Composite 組合檢測")
    logger.info("=" * 60)

    prices, true_anomalies = generate_price_data_with_anomalies()

    # 創建多個檢測器
    zscore_detector = ZScoreDetector(threshold=3.0, window=20)
    zscore_detector.fit(prices, return_based=True)

    mad_detector = MADDetector(threshold=3.5, window=20)
    mad_detector.fit(prices, return_based=True)

    # 組合檢測器
    composite = CompositeDetector(
        detectors=[zscore_detector, mad_detector],
        voting_strategy='any'  # 任一檢測器報警即視為異常
    )

    # 檢測
    results = composite.predict(prices, return_based=True)

    n_anomalies = results['anomaly'].sum()
    anomaly_ratio = n_anomalies / len(results) * 100

    logger.info(f"\nComposite 統計：")
    logger.info(f"  異常數量: {n_anomalies}")
    logger.info(f"  異常比例: {anomaly_ratio:.2f}%")

    # 評估
    aligned_true = true_anomalies.reindex(results.index, fill_value=False)
    precision, recall, f1 = calculate_metrics(aligned_true, results['anomaly'])

    logger.info(f"\n性能指標：")
    logger.info(f"  Precision: {precision:.2%}")
    logger.info(f"  Recall: {recall:.2%}")
    logger.info(f"  F1-Score: {f1:.2%}")

    return composite, results


def calculate_metrics(y_true: pd.Series, y_pred: pd.Series) -> Tuple[float, float, float]:
    """
    計算 Precision, Recall, F1-Score

    Args:
        y_true: 真實標記
        y_pred: 預測標記

    Returns:
        (precision, recall, f1)
    """
    tp = ((y_true == True) & (y_pred == True)).sum()
    fp = ((y_true == False) & (y_pred == True)).sum()
    fn = ((y_true == True) & (y_pred == False)).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return precision, recall, f1


def plot_anomaly_results(
    prices: pd.Series,
    true_anomalies: pd.Series,
    iso_results: pd.DataFrame,
    zscore_results: pd.DataFrame,
    mad_results: pd.DataFrame
):
    """繪製異常檢測結果"""
    logger.info("\n生成視覺化圖表...")

    output_dir = Path('results/anomaly_demo')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 完整時間序列 + 異常標記
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    # 真實異常
    ax = axes[0]
    ax.plot(prices.values, linewidth=1, alpha=0.7, label='Price')
    anomaly_idx = np.where(true_anomalies.values)[0]
    ax.scatter(anomaly_idx, prices.values[anomaly_idx],
               color='red', s=50, marker='x', label='True Anomaly', zorder=5)
    ax.set_title('True Anomalies (Injected)', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Isolation Forest
    ax = axes[1]
    ax.plot(iso_results.index, iso_results['price'].values, linewidth=1, alpha=0.7)
    iso_anomaly_idx = iso_results[iso_results['anomaly']].index
    iso_anomaly_prices = iso_results.loc[iso_anomaly_idx, 'price'].values
    ax.scatter(range(len(iso_results.loc[iso_anomaly_idx])), iso_anomaly_prices,
               color='red', s=50, marker='x', label='Detected Anomaly', zorder=5)
    ax.set_title('Isolation Forest Detection', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Z-Score
    ax = axes[2]
    ax.plot(zscore_results['price'].values, linewidth=1, alpha=0.7)
    zscore_anomaly_idx = np.where(zscore_results['anomaly'].values)[0]
    ax.scatter(zscore_anomaly_idx, zscore_results['price'].values[zscore_anomaly_idx],
               color='red', s=50, marker='x', label='Detected Anomaly', zorder=5)
    ax.set_title('Z-Score Detection (threshold=3.0)', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # MAD
    ax = axes[3]
    ax.plot(mad_results['price'].values, linewidth=1, alpha=0.7)
    mad_anomaly_idx = np.where(mad_results['anomaly'].values)[0]
    ax.scatter(mad_anomaly_idx, mad_results['price'].values[mad_anomaly_idx],
               color='red', s=50, marker='x', label='Detected Anomaly', zorder=5)
    ax.set_title('MAD Detection (threshold=3.5)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Time Step')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/anomaly_comparison.png', dpi=150)
    logger.info(f"✓ 已保存: {output_dir}/anomaly_comparison.png")
    plt.close()

    # 2. Z-Score 分布
    plt.figure(figsize=(10, 5))
    plt.hist(zscore_results['z_score'].dropna(), bins=50, alpha=0.7, edgecolor='black')
    plt.axvline(x=3.0, color='r', linestyle='--', linewidth=2, label='Threshold (+3.0)')
    plt.axvline(x=-3.0, color='r', linestyle='--', linewidth=2, label='Threshold (-3.0)')
    plt.title('Z-Score Distribution', fontsize=14, fontweight='bold')
    plt.xlabel('Z-Score')
    plt.ylabel('Frequency')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/zscore_distribution.png', dpi=150)
    logger.info(f"✓ 已保存: {output_dir}/zscore_distribution.png")
    plt.close()


def main():
    """主函數"""
    logger.info("=" * 60)
    logger.info("異常檢測模型 Demo 測試")
    logger.info("=" * 60)

    try:
        # 測試 1: Isolation Forest
        iso_detector, iso_results, test_prices, test_true_anomalies = test_isolation_forest()

        # 測試 2: Z-Score
        zscore_detector, zscore_results = test_zscore()

        # 測試 3: MAD
        mad_detector, mad_results = test_mad()

        # 測試 4: Composite
        composite_detector, composite_results = test_composite()

        # 繪製結果
        # 使用完整資料集進行視覺化
        full_prices, full_true_anomalies = generate_price_data_with_anomalies()
        full_zscore_results = zscore_detector.predict(full_prices, return_based=True)
        full_mad_results = mad_detector.predict(full_prices, return_based=True)

        # Isolation Forest 需要重新訓練和預測
        iso_temp = IsolationForestDetector(contamination=0.05, n_estimators=50, random_state=42)
        iso_temp.fit(full_prices.iloc[:int(len(full_prices)*0.7)])
        full_iso_results = iso_temp.predict(full_prices)

        plot_anomaly_results(
            full_prices,
            full_true_anomalies,
            full_iso_results,
            full_zscore_results,
            full_mad_results
        )

        # 保存檢測器
        model_dir = Path('models/saved')
        model_dir.mkdir(parents=True, exist_ok=True)
        iso_detector.save_model(str(model_dir / 'isolation_forest_demo.pkl'))
        logger.info(f"\n✓ Isolation Forest 模型已保存")

        # 最終總結
        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有測試完成！")
        logger.info("=" * 60)
        logger.info("結果保存於: results/anomaly_demo/")
        logger.info("模型保存於: models/saved/isolation_forest_demo.pkl")

        return True

    except Exception as e:
        logger.error(f"\n❌ 測試失敗: {str(e)}", exc_info=True)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
