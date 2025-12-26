"""
LSTM 價格預測模型 Demo 測試腳本

使用合成資料驗證模型功能，適合在本地環境快速測試。
模型配置經過簡化以減輕計算負載。
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非互動式後端
import matplotlib.pyplot as plt

# 添加專案路徑
sys.path.append(str(Path(__file__).parent))

from src.models.ml.lstm_forecast import LSTMForecast
from src.models.baseline.ma_forecast import (
    MovingAverageForecast,
    NaiveForecast
)

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_synthetic_price_data(
    n_samples: int = 2000,
    base_price: float = 50000,
    trend: float = 0.0001,
    volatility: float = 0.02,
    random_seed: int = 42
) -> pd.Series:
    """
    生成合成價格資料

    Args:
        n_samples: 樣本數
        base_price: 基礎價格
        trend: 趨勢（正值為上漲，負值為下跌）
        volatility: 波動率
        random_seed: 隨機種子

    Returns:
        價格序列
    """
    np.random.seed(random_seed)

    # 生成隨機遊走 + 趨勢
    returns = np.random.normal(trend, volatility, n_samples)

    # 添加週期性成分（模擬日內波動）
    t = np.arange(n_samples)
    seasonal = 0.005 * np.sin(2 * np.pi * t / 100)  # 100 個時間點一個週期
    returns += seasonal

    # 計算價格
    prices = base_price * np.exp(np.cumsum(returns))

    # 創建時間索引
    timestamps = pd.date_range(
        start='2024-01-01',
        periods=n_samples,
        freq='1min'
    )

    return pd.Series(prices, index=timestamps, name='close')


def test_lstm_model_basic():
    """基礎功能測試"""
    logger.info("=" * 60)
    logger.info("測試 1: LSTM 模型基礎功能")
    logger.info("=" * 60)

    # 生成合成資料
    logger.info("生成合成價格資料...")
    prices = generate_synthetic_price_data(n_samples=2000)

    logger.info(f"資料範圍: {prices.min():.2f} - {prices.max():.2f}")
    logger.info(f"資料點數: {len(prices)}")

    # 分割資料
    train_size = int(len(prices) * 0.8)
    train_data = prices.iloc[:train_size]
    test_data = prices.iloc[train_size:]

    logger.info(f"訓練集: {len(train_data)} 筆")
    logger.info(f"測試集: {len(test_data)} 筆")

    # 初始化模型（簡化配置以減輕負載）
    logger.info("\n初始化 LSTM 模型（輕量級配置）...")
    lstm_model = LSTMForecast(
        sequence_length=30,  # 使用過去 30 個時間點
        hidden_size=32,      # 較小的隱藏層
        num_layers=1,        # 單層 LSTM
        dropout=0.1,
        learning_rate=0.01,
        batch_size=32,
        epochs=20,           # 較少的訓練輪數
        device='cpu'         # 使用 CPU 以相容性
    )

    # 訓練模型
    logger.info("\n開始訓練...")
    lstm_model.fit(
        train_data,
        val_ratio=0.2,
        early_stopping_patience=5,
        verbose=True
    )

    # 預測
    logger.info("\n進行預測...")
    predictions = lstm_model.predict(test_data)

    # 評估
    y_true = test_data.iloc[lstm_model.sequence_length:]
    metrics = lstm_model.evaluate(y_true, predictions)

    logger.info("\n" + "=" * 60)
    logger.info("LSTM 模型評估結果")
    logger.info("=" * 60)
    for metric_name, metric_value in metrics.items():
        logger.info(f"{metric_name:20s}: {metric_value:10.4f}")

    return lstm_model, predictions, y_true, metrics


def test_baseline_comparison(prices: pd.Series):
    """與 baseline 模型比較"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 2: 與 Baseline 模型比較")
    logger.info("=" * 60)

    train_size = int(len(prices) * 0.8)
    train_data = prices.iloc[:train_size]
    test_data = prices.iloc[train_size:]

    results = []

    # Naive 模型
    logger.info("訓練 Naive 模型...")
    naive = NaiveForecast()
    naive.fit(train_data)
    naive_pred = naive.predict(test_data)
    naive_metrics = naive.evaluate(test_data, naive_pred)
    naive_metrics['model'] = 'Naive'
    results.append(naive_metrics)

    # MA 模型
    for window in [10, 20]:
        logger.info(f"訓練 MA_{window} 模型...")
        ma = MovingAverageForecast(window=window)
        ma.fit(train_data)
        ma_pred = ma.predict(test_data)
        ma_metrics = ma.evaluate(test_data, ma_pred)
        ma_metrics['model'] = f'MA_{window}'
        results.append(ma_metrics)

    # 轉換為 DataFrame
    results_df = pd.DataFrame(results)
    results_df = results_df[['model', 'rmse', 'mae', 'r2', 'mape']]
    results_df = results_df.sort_values('rmse')

    logger.info("\nBaseline 模型結果：")
    logger.info(results_df.to_string())

    return results_df


def plot_demo_results(
    y_true: pd.Series,
    lstm_predictions: np.ndarray,
    lstm_model: LSTMForecast
):
    """繪製 demo 結果"""
    logger.info("\n生成視覺化圖表...")

    output_dir = Path('results/lstm_demo')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 實際 vs 預測
    plt.figure(figsize=(12, 5))
    plt.plot(y_true.values[:200], label='實際價格', linewidth=2)
    plt.plot(lstm_predictions[:200], label='LSTM 預測', linewidth=2, alpha=0.8)
    plt.title('LSTM 價格預測示範（前 200 個點）', fontsize=14, fontweight='bold')
    plt.xlabel('時間步', fontsize=12)
    plt.ylabel('價格', fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/actual_vs_predicted.png', dpi=150)
    logger.info(f"✓ 已保存: {output_dir}/actual_vs_predicted.png")
    plt.close()

    # 2. 訓練歷史
    history = lstm_model.get_training_history()
    plt.figure(figsize=(10, 5))
    plt.plot(history['epoch'], history['train_loss'], label='訓練損失', linewidth=2)
    plt.plot(history['epoch'], history['val_loss'], label='驗證損失', linewidth=2)
    plt.title('LSTM 訓練歷史', fontsize=14, fontweight='bold')
    plt.xlabel('Epoch', fontsize=12)
    plt.ylabel('損失 (MSE)', fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/training_history.png', dpi=150)
    logger.info(f"✓ 已保存: {output_dir}/training_history.png")
    plt.close()

    # 3. 殘差分析
    residuals = y_true.values - lstm_predictions
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.scatter(lstm_predictions, residuals, alpha=0.5, s=20)
    ax1.axhline(y=0, color='r', linestyle='--', linewidth=2)
    ax1.set_title('殘差 vs 預測值', fontsize=12, fontweight='bold')
    ax1.set_xlabel('預測值', fontsize=11)
    ax1.set_ylabel('殘差', fontsize=11)
    ax1.grid(True, alpha=0.3)

    ax2.hist(residuals, bins=30, edgecolor='black', alpha=0.7)
    ax2.set_title('殘差分布', fontsize=12, fontweight='bold')
    ax2.set_xlabel('殘差', fontsize=11)
    ax2.set_ylabel('頻率', fontsize=11)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/residuals.png', dpi=150)
    logger.info(f"✓ 已保存: {output_dir}/residuals.png")
    plt.close()


def main():
    """主函數"""
    logger.info("=" * 60)
    logger.info("LSTM 價格預測模型 Demo 測試")
    logger.info("=" * 60)
    logger.info("配置: 輕量級模型，適合本地環境測試")
    logger.info("=" * 60)

    try:
        # 測試 1: LSTM 基礎功能
        lstm_model, predictions, y_true, lstm_metrics = test_lstm_model_basic()

        # 測試 2: Baseline 比較
        prices = generate_synthetic_price_data(n_samples=2000)
        baseline_results = test_baseline_comparison(prices)

        # 繪製結果
        plot_demo_results(y_true, predictions, lstm_model)

        # 保存模型
        model_dir = Path('models/saved')
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / 'lstm_demo.pth'
        lstm_model.save_model(str(model_path))
        logger.info(f"\n✓ 模型已保存: {model_path}")

        # 最終總結
        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有測試完成！")
        logger.info("=" * 60)
        logger.info(f"LSTM RMSE: {lstm_metrics['rmse']:.4f}")
        logger.info(f"LSTM MAE: {lstm_metrics['mae']:.4f}")
        logger.info(f"LSTM R²: {lstm_metrics['r2']:.4f}")
        logger.info(f"方向準確率: {lstm_metrics['direction_accuracy']:.2f}%")
        logger.info("=" * 60)
        logger.info("結果保存於: results/lstm_demo/")
        logger.info("模型保存於: models/saved/lstm_demo.pth")

        return True

    except Exception as e:
        logger.error(f"\n❌ 測試失敗: {str(e)}", exc_info=True)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
