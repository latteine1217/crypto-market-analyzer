"""
XGBoost 價格預測模型 Demo 測試腳本

使用合成資料驗證模型功能，適合在本地環境快速測試。
與 LSTM 結果比較，展示樹模型與深度學習的差異。
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

from src.models.ml.xgboost_forecast import XGBoostForecast
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


def test_xgboost_model_basic():
    """基礎功能測試"""
    logger.info("=" * 60)
    logger.info("測試 1: XGBoost 模型基礎功能")
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

    # 初始化模型（輕量級配置）
    logger.info("\n初始化 XGBoost 模型（輕量級配置）...")
    xgb_model = XGBoostForecast(
        n_estimators=50,        # 較少的樹
        max_depth=4,            # 較淺的樹
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        early_stopping_rounds=5
    )

    # 訓練模型
    logger.info("\n開始訓練...")
    xgb_model.fit(
        train_data,
        val_ratio=0.2,
        verbose=False  # 關閉詳細輸出以減少日誌
    )

    # 預測
    logger.info("\n進行預測...")
    predictions = xgb_model.predict(test_data)

    # 評估（需要對齊索引）
    # XGBoost 使用滯後特徵，會損失前面的樣本
    y_true = test_data.iloc[-len(predictions):]
    metrics = xgb_model.evaluate(y_true, predictions)

    logger.info("\n" + "=" * 60)
    logger.info("XGBoost 模型評估結果")
    logger.info("=" * 60)
    for metric_name, metric_value in metrics.items():
        logger.info(f"{metric_name:20s}: {metric_value:10.4f}")

    # 獲取特徵重要性
    logger.info("\n獲取特徵重要性（Top 10）...")
    feature_importance = xgb_model.get_feature_importance()
    logger.info("\n" + feature_importance.head(10).to_string(index=False))

    return xgb_model, predictions, y_true, metrics, feature_importance


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
    xgb_predictions: np.ndarray,
    xgb_model: XGBoostForecast,
    feature_importance: pd.DataFrame
):
    """繪製 demo 結果"""
    logger.info("\n生成視覺化圖表...")

    output_dir = Path('results/xgboost_demo')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 實際 vs 預測
    plt.figure(figsize=(12, 5))
    plt.plot(y_true.values[:200], label='實際價格', linewidth=2)
    plt.plot(xgb_predictions[:200], label='XGBoost 預測', linewidth=2, alpha=0.8)
    plt.title('XGBoost 價格預測示範（前 200 個點）', fontsize=14, fontweight='bold')
    plt.xlabel('時間步', fontsize=12)
    plt.ylabel('價格', fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/actual_vs_predicted.png', dpi=150)
    logger.info(f"✓ 已保存: {output_dir}/actual_vs_predicted.png")
    plt.close()

    # 2. 訓練歷史
    history = xgb_model.get_training_history()
    if not history.empty:
        plt.figure(figsize=(10, 5))
        plt.plot(history['iteration'], history['train_rmse'], label='訓練 RMSE', linewidth=2)
        plt.plot(history['iteration'], history['val_rmse'], label='驗證 RMSE', linewidth=2)
        plt.title('XGBoost 訓練歷史', fontsize=14, fontweight='bold')
        plt.xlabel('Iteration', fontsize=12)
        plt.ylabel('RMSE', fontsize=12)
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/training_history.png', dpi=150)
        logger.info(f"✓ 已保存: {output_dir}/training_history.png")
        plt.close()

    # 3. 殘差分析
    residuals = y_true.values - xgb_predictions
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.scatter(xgb_predictions, residuals, alpha=0.5, s=20)
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

    # 4. 特徵重要性（Top 20）
    top_features = feature_importance.head(20)
    plt.figure(figsize=(10, 8))
    plt.barh(range(len(top_features)), top_features['importance'].values)
    plt.yticks(range(len(top_features)), top_features['feature'].values)
    plt.xlabel('Importance', fontsize=12)
    plt.title('Top 20 Feature Importance', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/feature_importance.png', dpi=150)
    logger.info(f"✓ 已保存: {output_dir}/feature_importance.png")
    plt.close()


def compare_with_lstm_results():
    """與 LSTM 結果比較（如果存在）"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 3: 與 LSTM 模型比較")
    logger.info("=" * 60)

    lstm_metrics_path = Path('results/lstm_demo/metrics.json')
    if not lstm_metrics_path.exists():
        logger.info("未找到 LSTM 測試結果，跳過比較")
        return None

    # 這裡可以載入 LSTM 結果並比較
    # 暫時跳過，因為我們沒有保存 LSTM metrics.json
    logger.info("(需要先完善 LSTM 測試以保存 metrics.json)")


def main():
    """主函數"""
    logger.info("=" * 60)
    logger.info("XGBoost 價格預測模型 Demo 測試")
    logger.info("=" * 60)
    logger.info("配置: 輕量級模型，適合本地環境測試")
    logger.info("=" * 60)

    try:
        # 測試 1: XGBoost 基礎功能
        xgb_model, predictions, y_true, xgb_metrics, feature_importance = test_xgboost_model_basic()

        # 測試 2: Baseline 比較
        prices = generate_synthetic_price_data(n_samples=2000)
        baseline_results = test_baseline_comparison(prices)

        # 繪製結果
        plot_demo_results(y_true, predictions, xgb_model, feature_importance)

        # 保存模型
        model_dir = Path('models/saved')
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / 'xgboost_demo.pkl'
        xgb_model.save_model(str(model_path))
        logger.info(f"\n✓ 模型已保存: {model_path}")

        # 保存特徵重要性
        output_dir = Path('results/xgboost_demo')
        feature_importance.to_csv(output_dir / 'feature_importance.csv', index=False)
        logger.info(f"✓ 特徵重要性已保存: {output_dir}/feature_importance.csv")

        # 最終總結
        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有測試完成！")
        logger.info("=" * 60)
        logger.info(f"XGBoost RMSE: {xgb_metrics['rmse']:.4f}")
        logger.info(f"XGBoost MAE: {xgb_metrics['mae']:.4f}")
        logger.info(f"XGBoost R²: {xgb_metrics['r2']:.4f}")
        logger.info(f"方向準確率: {xgb_metrics['direction_accuracy']:.2f}%")
        logger.info("=" * 60)
        logger.info("結果保存於: results/xgboost_demo/")
        logger.info("模型保存於: models/saved/xgboost_demo.pkl")

        return True

    except Exception as e:
        logger.error(f"\n❌ 測試失敗: {str(e)}", exc_info=True)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
