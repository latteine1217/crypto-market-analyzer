"""
XGBoost 超參數優化
使用網格搜索和交叉驗證尋找最佳超參數
"""

import numpy as np
import pandas as pd
import psycopg2
import logging
import json
import joblib
from pathlib import Path
from datetime import datetime
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_data_from_db():
    """從資料庫載入數據"""
    logger.info("從資料庫載入數據...")

    conn = psycopg2.connect(
        host='localhost',
        database='crypto_db',
        user='crypto',
        password='crypto_pass'
    )

    query = """
        SELECT o.open_time, o.open, o.high, o.low, o.close, o.volume, o.quote_volume
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = 'bybit'
            AND m.symbol = 'BTC/USDT'
            AND o.timeframe = '1h'
        ORDER BY o.open_time
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    logger.info(f"載入 {len(df)} 筆數據")
    logger.info(f"時間範圍: {df['open_time'].min()} ~ {df['open_time'].max()}")

    return df


def create_features(df):
    """創建完整特徵集"""
    logger.info("創建特徵...")

    from src.features.technical_indicators import TechnicalIndicators
    from src.features.price_features import PriceFeatures
    from src.features.volume_features import VolumeFeatures

    # 技術指標特徵
    tech_indicators = TechnicalIndicators()
    price_features = PriceFeatures()
    volume_features = VolumeFeatures()

    tech_feat = tech_indicators.calculate_all(df)
    price_feat = price_features.calculate_all(df)
    volume_feat = volume_features.calculate_all(df)

    # 移除重複的 OHLCV 列
    tech_cols = [col for col in tech_feat.columns
                if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]
    price_cols = [col for col in price_feat.columns
                 if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]
    volume_cols = [col for col in volume_feat.columns
                  if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]

    # 合併特徵
    features = pd.concat([
        tech_feat[tech_cols],
        price_feat[price_cols],
        volume_feat[volume_cols]
    ], axis=1)

    # 前向填充並刪除 NaN
    features = features.ffill().dropna()

    logger.info(f"特徵總數: {features.shape[1]}")

    return features


def optimize_hyperparameters(X_train, y_train):
    """超參數網格搜索"""
    logger.info("開始超參數優化...")

    # 定義參數網格
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [6, 8, 10],
        'learning_rate': [0.01, 0.05, 0.1],
        'subsample': [0.8, 0.9, 1.0],
        'colsample_bytree': [0.8, 0.9, 1.0],
        'min_child_weight': [1, 3, 5]
    }

    logger.info(f"參數網格大小: {np.prod([len(v) for v in param_grid.values()])} 組合")

    # 使用時間序列交叉驗證
    tscv = TimeSeriesSplit(n_splits=3)

    # 創建 XGBoost 模型
    xgb_model = xgb.XGBRegressor(
        objective='reg:squarederror',
        random_state=42,
        n_jobs=-1
    )

    # 網格搜索
    grid_search = GridSearchCV(
        estimator=xgb_model,
        param_grid=param_grid,
        cv=tscv,
        scoring='neg_mean_squared_error',
        n_jobs=-1,
        verbose=2
    )

    logger.info("開始網格搜索...")
    grid_search.fit(X_train, y_train)

    logger.info(f"最佳參數: {grid_search.best_params_}")
    logger.info(f"最佳分數 (負 MSE): {grid_search.best_score_:.4f}")

    return grid_search.best_estimator_, grid_search.best_params_, grid_search.cv_results_


def evaluate_model(model, X_test, y_test):
    """評估模型"""
    logger.info("評估優化後的模型...")

    y_pred = model.predict(X_test)

    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100

    # 方向準確率
    y_test_direction = np.diff(y_test) > 0
    y_pred_direction = np.diff(y_pred) > 0
    direction_accuracy = np.mean(y_test_direction == y_pred_direction) * 100

    metrics = {
        'RMSE': rmse,
        'MAE': mae,
        'R2': r2,
        'MAPE': mape,
        'Direction_Accuracy': direction_accuracy
    }

    logger.info("測試集性能:")
    for metric, value in metrics.items():
        logger.info(f"  {metric}: {value:.4f}")

    return metrics, y_pred


def plot_optimization_results(cv_results, output_dir):
    """繪製優化結果"""
    logger.info("繪製優化結果...")

    results_df = pd.DataFrame(cv_results)

    # 創建圖表
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # 1. 參數重要性分析 - n_estimators
    ax1 = axes[0, 0]
    param_scores = results_df.groupby('param_n_estimators')['mean_test_score'].mean()
    ax1.plot(param_scores.index.astype(int), -param_scores.values, marker='o', linewidth=2)
    ax1.set_xlabel('n_estimators')
    ax1.set_ylabel('Mean CV Score (RMSE)')
    ax1.set_title('Effect of n_estimators on Performance')
    ax1.grid(True, alpha=0.3)

    # 2. 參數重要性分析 - max_depth
    ax2 = axes[0, 1]
    param_scores = results_df.groupby('param_max_depth')['mean_test_score'].mean()
    ax2.plot(param_scores.index.astype(int), -param_scores.values, marker='o', linewidth=2)
    ax2.set_xlabel('max_depth')
    ax2.set_ylabel('Mean CV Score (RMSE)')
    ax2.set_title('Effect of max_depth on Performance')
    ax2.grid(True, alpha=0.3)

    # 3. 參數重要性分析 - learning_rate
    ax3 = axes[1, 0]
    param_scores = results_df.groupby('param_learning_rate')['mean_test_score'].mean()
    ax3.plot(param_scores.index.astype(float), -param_scores.values, marker='o', linewidth=2)
    ax3.set_xlabel('learning_rate')
    ax3.set_ylabel('Mean CV Score (RMSE)')
    ax3.set_title('Effect of learning_rate on Performance')
    ax3.grid(True, alpha=0.3)

    # 4. Top 10 參數組合
    ax4 = axes[1, 1]
    top_10 = results_df.nsmallest(10, 'rank_test_score')
    top_10_labels = [f"Config {i+1}" for i in range(len(top_10))]
    ax4.barh(top_10_labels, -top_10['mean_test_score'].values, alpha=0.8)
    ax4.set_xlabel('Mean CV Score (RMSE)')
    ax4.set_title('Top 10 Parameter Configurations')
    ax4.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    plt.savefig(output_dir / 'optimization_results.png', dpi=150, bbox_inches='tight')
    logger.info(f"優化結果圖已保存至 {output_dir / 'optimization_results.png'}")


def save_results(model, best_params, metrics, y_pred, y_test, cv_results, feature_names):
    """保存結果"""
    logger.info("保存優化結果...")

    output_dir = Path('results/xgboost_optimized_btc_1h')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存模型
    model_data = {
        'model': model,
        'best_params': best_params,
        'feature_names': feature_names
    }
    joblib.dump(model_data, output_dir / 'xgboost_optimized_model.joblib')

    # 保存指標
    with open(output_dir / 'metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    # 保存最佳參數
    with open(output_dir / 'best_params.json', 'w') as f:
        json.dump(best_params, f, indent=2)

    # 保存 CV 結果
    cv_results_df = pd.DataFrame(cv_results)
    cv_results_df.to_csv(output_dir / 'cv_results.csv', index=False)

    # 保存預測結果
    results_df = pd.DataFrame({
        'actual': y_test,
        'predicted': y_pred,
        'error': y_test - y_pred
    })
    results_df.to_csv(output_dir / 'predictions.csv', index=False)

    # 保存特徵重要性
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    feature_importance.to_csv(output_dir / 'feature_importance.csv', index=False)

    # 繪製優化結果
    plot_optimization_results(cv_results, output_dir)

    # 繪製評估圖表
    plot_evaluation(y_test, y_pred, metrics, output_dir)

    # 生成報告
    generate_report(best_params, metrics, feature_importance, output_dir)

    logger.info(f"結果已保存至 {output_dir}")


def plot_evaluation(y_test, y_pred, metrics, output_dir):
    """繪製評估圖表"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # 1. 實際 vs 預測
    axes[0, 0].plot(y_test[:300], label='Actual', linewidth=1.5, alpha=0.8)
    axes[0, 0].plot(y_pred[:300], label='Predicted', linewidth=1.5, alpha=0.8)
    axes[0, 0].set_title('Actual vs Predicted (First 300 samples)')
    axes[0, 0].set_xlabel('Sample')
    axes[0, 0].set_ylabel('Price (USDT)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # 2. 誤差分布
    errors = y_test - y_pred
    axes[0, 1].hist(errors, bins=50, edgecolor='black', alpha=0.7, color='steelblue')
    axes[0, 1].axvline(x=0, color='red', linestyle='--', linewidth=1.5)
    axes[0, 1].set_title(f'Error Distribution\nMean: {errors.mean():.2f}, Std: {errors.std():.2f}')
    axes[0, 1].set_xlabel('Error (USDT)')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].grid(True, alpha=0.3)

    # 3. 散點圖
    axes[1, 0].scatter(y_test, y_pred, alpha=0.3, s=10)
    axes[1, 0].plot([y_test.min(), y_test.max()],
                    [y_test.min(), y_test.max()],
                    'r--', linewidth=2, label='Perfect Prediction')
    axes[1, 0].set_title(f'Predicted vs Actual\nR² = {metrics["R2"]:.6f}')
    axes[1, 0].set_xlabel('Actual Price (USDT)')
    axes[1, 0].set_ylabel('Predicted Price (USDT)')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # 4. 性能指標表
    ax4 = axes[1, 1]
    ax4.axis('off')

    metrics_text = f"""
    Performance Metrics
    {'='*40}

    RMSE:              {metrics['RMSE']:.2f} USDT
    MAE:               {metrics['MAE']:.2f} USDT
    R²:                {metrics['R2']:.6f}
    MAPE:              {metrics['MAPE']:.3f}%
    Direction Accuracy: {metrics['Direction_Accuracy']:.2f}%
    """

    ax4.text(0.1, 0.5, metrics_text, fontsize=12, family='monospace',
             verticalalignment='center')

    plt.tight_layout()
    plt.savefig(output_dir / 'evaluation.png', dpi=150, bbox_inches='tight')


def generate_report(best_params, metrics, feature_importance, output_dir):
    """生成優化報告"""
    report = f"""# XGBoost 超參數優化報告

**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 1. 最佳超參數

```python
{json.dumps(best_params, indent=2)}
```

## 2. 性能指標

| 指標 | 數值 | 說明 |
|------|------|------|
| RMSE | {metrics['RMSE']:.2f} | 均方根誤差 |
| MAE | {metrics['MAE']:.2f} | 平均絕對誤差 |
| R² | {metrics['R2']:.6f} | 決定係數 |
| MAPE | {metrics['MAPE']:.3f}% | 平均絕對百分比誤差 |
| 方向準確率 | {metrics['Direction_Accuracy']:.2f}% | 漲跌方向預測準確率 |

## 3. 前 20 個重要特徵

| 排名 | 特徵名稱 | 重要性 |
|------|----------|--------|
{chr(10).join([f"| {i+1} | {row['feature']} | {row['importance']:.2f} |" for i, row in feature_importance.head(20).iterrows()])}

## 4. 優化總結

### ✅ 優化成果

- 使用時間序列交叉驗證（3-fold）
- 網格搜索涵蓋 6 個關鍵超參數
- 確保模型在不同時間段的穩定性

### 📊 與基線模型比較

查看 `results/final_model_comparison/` 目錄中的完整比較報告。

### 🚀 下一步

1. 使用優化後的模型進行策略回測
2. 評估真實交易環境下的性能
3. 考慮集成學習進一步提升
"""

    with open(output_dir / 'optimization_report.md', 'w', encoding='utf-8') as f:
        f.write(report)


def main():
    """主函數"""
    logger.info("=" * 80)
    logger.info("開始 XGBoost 超參數優化")
    logger.info("=" * 80)

    # 1. 載入數據
    df = load_data_from_db()

    # 2. 創建特徵
    features = create_features(df)

    # 確保索引對齊
    df = df.loc[features.index]
    target = df['close'].values

    logger.info(f"特徵形狀: {features.shape}")
    logger.info(f"目標形狀: {target.shape}")

    # 3. 分割數據（80/20）
    split_idx = int(len(features) * 0.8)
    X_train = features.iloc[:split_idx].values
    y_train = target[:split_idx]
    X_test = features.iloc[split_idx:].values
    y_test = target[split_idx:]

    logger.info(f"訓練集: {X_train.shape}, 測試集: {X_test.shape}")

    # 4. 超參數優化
    best_model, best_params, cv_results = optimize_hyperparameters(X_train, y_train)

    # 5. 評估模型
    metrics, y_pred = evaluate_model(best_model, X_test, y_test)

    # 6. 保存結果
    save_results(best_model, best_params, metrics, y_pred, y_test, cv_results, features.columns.tolist())

    logger.info("=" * 80)
    logger.info("XGBoost 超參數優化完成！")
    logger.info("=" * 80)
    logger.info(f"\n最佳參數: {best_params}")
    logger.info(f"\n性能總結:")
    logger.info(f"  RMSE: {metrics['RMSE']:.2f} USDT")
    logger.info(f"  R²: {metrics['R2']:.6f}")
    logger.info(f"  方向準確率: {metrics['Direction_Accuracy']:.2f}%")


if __name__ == '__main__':
    main()
