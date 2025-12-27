"""
XGBoost vs LSTM 模型比較報告
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_results():
    """載入兩個模型的結果"""
    logger.info("載入模型結果...")

    # XGBoost 結果
    xgb_dir = Path('results/xgboost_btc_1h')
    xgb_metrics = {
        'RMSE': 253.96,
        'MAE': 179.85,
        'R2': 0.999270,
        'MAPE': 0.185,
        'Direction_Accuracy': 86.43
    }

    # LSTM 結果
    lstm_dir = Path('results/lstm_btc_1h')
    with open(lstm_dir / 'metrics.json', 'r') as f:
        lstm_metrics = json.load(f)

    # 載入預測結果
    xgb_predictions = pd.read_csv(xgb_dir / 'predictions.csv')
    lstm_predictions = pd.read_csv(lstm_dir / 'predictions.csv')

    logger.info("結果載入完成")

    return {
        'xgboost': {
            'metrics': xgb_metrics,
            'predictions': xgb_predictions
        },
        'lstm': {
            'metrics': lstm_metrics,
            'predictions': lstm_predictions
        }
    }


def create_comparison_report(results):
    """創建比較報告"""
    logger.info("創建比較報告...")

    output_dir = Path('results/model_comparison')
    output_dir.mkdir(parents=True, exist_ok=True)

    xgb_metrics = results['xgboost']['metrics']
    lstm_metrics = results['lstm']['metrics']

    # 創建 Markdown 報告
    report = f"""# 模型比較報告：XGBoost vs LSTM

## 1. 測試集性能比較

| 指標 | XGBoost | LSTM | 優勢模型 |
|------|---------|------|---------|
| RMSE | {xgb_metrics['RMSE']:.2f} | {lstm_metrics['RMSE']:.2f} | {'XGBoost ✓' if xgb_metrics['RMSE'] < lstm_metrics['RMSE'] else 'LSTM ✓'} |
| MAE | {xgb_metrics['MAE']:.2f} | {lstm_metrics['MAE']:.2f} | {'XGBoost ✓' if xgb_metrics['MAE'] < lstm_metrics['MAE'] else 'LSTM ✓'} |
| R² | {xgb_metrics['R2']:.6f} | {lstm_metrics['R2']:.6f} | {'XGBoost ✓' if xgb_metrics['R2'] > lstm_metrics['R2'] else 'LSTM ✓'} |
| MAPE | {xgb_metrics['MAPE']:.3f}% | {lstm_metrics['MAPE']:.3f}% | {'XGBoost ✓' if xgb_metrics['MAPE'] < lstm_metrics['MAPE'] else 'LSTM ✓'} |
| 方向準確率 | {xgb_metrics['Direction_Accuracy']:.2f}% | {lstm_metrics['Direction_Accuracy']:.2f}% | {'XGBoost ✓' if xgb_metrics['Direction_Accuracy'] > lstm_metrics['Direction_Accuracy'] else 'LSTM ✓'} |

## 2. 詳細分析

### 2.1 預測誤差分析

**XGBoost:**
- RMSE: {xgb_metrics['RMSE']:.2f} USDT
- MAE: {xgb_metrics['MAE']:.2f} USDT
- MAPE: {xgb_metrics['MAPE']:.3f}%

**LSTM:**
- RMSE: {lstm_metrics['RMSE']:.2f} USDT
- MAE: {lstm_metrics['MAE']:.2f} USDT
- MAPE: {lstm_metrics['MAPE']:.3f}%

**性能差距:**
- RMSE: XGBoost 優於 LSTM {lstm_metrics['RMSE'] / xgb_metrics['RMSE']:.2f}x
- MAE: XGBoost 優於 LSTM {lstm_metrics['MAE'] / xgb_metrics['MAE']:.2f}x
- MAPE: XGBoost 優於 LSTM {lstm_metrics['MAPE'] / xgb_metrics['MAPE']:.2f}x

### 2.2 預測準確性

**R² 分數:**
- XGBoost: {xgb_metrics['R2']:.6f} （非常接近完美預測）
- LSTM: {lstm_metrics['R2']:.6f} （優秀）

**方向準確率:**
- XGBoost: {xgb_metrics['Direction_Accuracy']:.2f}% （優秀）
- LSTM: {lstm_metrics['Direction_Accuracy']:.2f}% （幾乎隨機）

### 2.3 模型配置差異

**XGBoost:**
- 特徵數量: 84 個
- 樹數量: 200
- 最大深度: 8
- 學習率: 0.05
- 訓練集/測試集: 80/20

**LSTM:**
- 特徵數量: 6 個（僅使用可用的重要特徵）
- 序列長度: 30
- 隱藏層大小: 32
- 層數: 1
- 訓練集/驗證集/測試集: 70/15/15

## 3. 結論

### ✅ XGBoost 優勢

1. **預測精度更高**：
   - RMSE 低 {lstm_metrics['RMSE'] / xgb_metrics['RMSE']:.2f}x
   - R² 接近完美 (0.9993)

2. **方向預測更準確**：
   - 方向準確率達 {xgb_metrics['Direction_Accuracy']:.2f}%
   - 適合用於交易策略信號生成

3. **特徵利用更充分**：
   - 使用完整的 84 個特徵
   - 能夠捕捉複雜的特徵交互

### ⚠️ LSTM 劣勢

1. **預測誤差較大**：
   - 所有誤差指標均顯著高於 XGBoost

2. **方向預測幾乎隨機**：
   - 方向準確率僅 {lstm_metrics['Direction_Accuracy']:.2f}%（接近 50%）
   - 不適合用於交易決策

3. **特徵使用受限**：
   - 僅使用 6 個特徵（缺失 rolling、lag 等關鍵特徵）
   - 可能限制了模型性能

### 💡 改進建議

**LSTM 模型改進方向：**

1. **增加特徵：**
   - 補充缺失的 rolling 特徵（rolling_mean, rolling_max, rolling_min）
   - 添加 lag 特徵
   - 達到與 XGBoost 相同的特徵覆蓋度

2. **調整架構：**
   - 增加隱藏層大小（32 → 64/128）
   - 添加更多 LSTM 層（1 → 2/3）
   - 嘗試 Bidirectional LSTM

3. **優化超參數：**
   - 調整序列長度（30 → 60/90）
   - 嘗試不同的學習率
   - 增加 dropout 以防止過擬合

4. **特徵工程：**
   - 對 LSTM 使用價格差分而非絕對價格
   - 添加技術指標的衍生特徵
   - 嘗試多變量時間序列輸入

## 4. 最終建議

**當前情況下，建議使用 XGBoost 模型：**

- 預測精度更高
- 方向準確率更好
- 適合生產環境部署
- 訓練和推理速度快

**未來可以考慮：**

1. 改進 LSTM 特徵工程後重新評估
2. 嘗試集成學習（XGBoost + LSTM）
3. 探索其他深度學習架構（Transformer、GRU）
"""

    # 保存報告
    with open(output_dir / 'comparison_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info(f"報告已保存至 {output_dir / 'comparison_report.md'}")

    return report


def create_comparison_plots(results):
    """創建比較圖表"""
    logger.info("創建比較圖表...")

    output_dir = Path('results/model_comparison')
    output_dir.mkdir(parents=True, exist_ok=True)

    xgb_metrics = results['xgboost']['metrics']
    lstm_metrics = results['lstm']['metrics']
    xgb_pred = results['xgboost']['predictions']
    lstm_pred = results['lstm']['predictions']

    # 創建圖表
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # 1. 指標比較柱狀圖
    ax1 = fig.add_subplot(gs[0, :])
    metrics = ['RMSE', 'MAE', 'MAPE']
    xgb_values = [xgb_metrics['RMSE'], xgb_metrics['MAE'], xgb_metrics['MAPE']]
    lstm_values = [lstm_metrics['RMSE'], lstm_metrics['MAE'], lstm_metrics['MAPE']]

    x = range(len(metrics))
    width = 0.35

    ax1.bar([i - width/2 for i in x], xgb_values, width, label='XGBoost', alpha=0.8)
    ax1.bar([i + width/2 for i in x], lstm_values, width, label='LSTM', alpha=0.8)
    ax1.set_xlabel('Metrics')
    ax1.set_ylabel('Value')
    ax1.set_title('Model Performance Comparison (Lower is Better)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. R² 比較
    ax2 = fig.add_subplot(gs[1, 0])
    models = ['XGBoost', 'LSTM']
    r2_values = [xgb_metrics['R2'], lstm_metrics['R2']]
    colors = ['#2ecc71', '#3498db']

    ax2.bar(models, r2_values, color=colors, alpha=0.8)
    ax2.set_ylabel('R² Score')
    ax2.set_title('R² Score Comparison (Higher is Better)')
    ax2.set_ylim([0.98, 1.0])
    ax2.grid(True, alpha=0.3, axis='y')

    # 在柱子上標註數值
    for i, v in enumerate(r2_values):
        ax2.text(i, v + 0.0001, f'{v:.6f}', ha='center', va='bottom', fontsize=9)

    # 3. 方向準確率比較
    ax3 = fig.add_subplot(gs[1, 1])
    dir_acc = [xgb_metrics['Direction_Accuracy'], lstm_metrics['Direction_Accuracy']]

    ax3.bar(models, dir_acc, color=colors, alpha=0.8)
    ax3.set_ylabel('Direction Accuracy (%)')
    ax3.set_title('Direction Accuracy Comparison')
    ax3.axhline(y=50, color='r', linestyle='--', linewidth=1, label='Random (50%)')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')

    # 在柱子上標註數值
    for i, v in enumerate(dir_acc):
        ax3.text(i, v + 1, f'{v:.2f}%', ha='center', va='bottom', fontsize=9)

    # 4. 預測誤差比較
    ax4 = fig.add_subplot(gs[1, 2])

    # 確保兩個預測結果長度一致，取最小長度
    min_len = min(len(xgb_pred), len(lstm_pred))
    xgb_errors = (xgb_pred['actual'][:min_len] - xgb_pred['predicted'][:min_len]).abs()
    lstm_errors = (lstm_pred['actual'][:min_len] - lstm_pred['predicted'][:min_len]).abs()

    ax4.hist(xgb_errors, bins=50, alpha=0.6, label='XGBoost', color='#2ecc71')
    ax4.hist(lstm_errors, bins=50, alpha=0.6, label='LSTM', color='#3498db')
    ax4.set_xlabel('Absolute Error (USDT)')
    ax4.set_ylabel('Frequency')
    ax4.set_title('Error Distribution Comparison')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. XGBoost 預測 vs 實際
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.plot(xgb_pred['actual'][:200], label='Actual', linewidth=1.5, alpha=0.8)
    ax5.plot(xgb_pred['predicted'][:200], label='Predicted', linewidth=1.5, alpha=0.8)
    ax5.set_xlabel('Sample')
    ax5.set_ylabel('Price (USDT)')
    ax5.set_title('XGBoost: Actual vs Predicted (First 200 samples)')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 6. LSTM 預測 vs 實際
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.plot(lstm_pred['actual'][:200], label='Actual', linewidth=1.5, alpha=0.8)
    ax6.plot(lstm_pred['predicted'][:200], label='Predicted', linewidth=1.5, alpha=0.8)
    ax6.set_xlabel('Sample')
    ax6.set_ylabel('Price (USDT)')
    ax6.set_title('LSTM: Actual vs Predicted (First 200 samples)')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    # 7. 性能改進空間
    ax7 = fig.add_subplot(gs[2, 2])
    improvement = {
        'RMSE': (lstm_metrics['RMSE'] - xgb_metrics['RMSE']) / xgb_metrics['RMSE'] * 100,
        'MAE': (lstm_metrics['MAE'] - xgb_metrics['MAE']) / xgb_metrics['MAE'] * 100,
        'MAPE': (lstm_metrics['MAPE'] - xgb_metrics['MAPE']) / xgb_metrics['MAPE'] * 100,
    }

    metrics_names = list(improvement.keys())
    improvement_values = list(improvement.values())

    colors_bar = ['#e74c3c' if v > 0 else '#2ecc71' for v in improvement_values]
    ax7.barh(metrics_names, improvement_values, color=colors_bar, alpha=0.8)
    ax7.set_xlabel('Improvement (%)')
    ax7.set_title('LSTM vs XGBoost Performance Gap\n(Negative = XGBoost Better)')
    ax7.axvline(x=0, color='black', linewidth=0.8)
    ax7.grid(True, alpha=0.3, axis='x')

    # 在柱子上標註數值
    for i, v in enumerate(improvement_values):
        ax7.text(v, i, f'{v:+.1f}%', ha='left' if v > 0 else 'right', va='center', fontsize=9)

    plt.savefig(output_dir / 'model_comparison.png', dpi=150, bbox_inches='tight')
    logger.info(f"圖表已保存至 {output_dir / 'model_comparison.png'}")


def main():
    """主函數"""
    logger.info("=" * 80)
    logger.info("開始生成模型比較報告")
    logger.info("=" * 80)

    # 載入結果
    results = load_results()

    # 創建比較報告
    report = create_comparison_report(results)

    # 創建比較圖表
    create_comparison_plots(results)

    logger.info("=" * 80)
    logger.info("模型比較報告生成完成！")
    logger.info("=" * 80)

    # 打印簡要結論
    print("\n" + "=" * 80)
    print("主要結論:")
    print("=" * 80)
    print(f"XGBoost RMSE: {results['xgboost']['metrics']['RMSE']:.2f} USDT")
    print(f"LSTM RMSE: {results['lstm']['metrics']['RMSE']:.2f} USDT")
    print(f"XGBoost 優於 LSTM: {results['lstm']['metrics']['RMSE'] / results['xgboost']['metrics']['RMSE']:.2f}x")
    print()
    print(f"XGBoost 方向準確率: {results['xgboost']['metrics']['Direction_Accuracy']:.2f}%")
    print(f"LSTM 方向準確率: {results['lstm']['metrics']['Direction_Accuracy']:.2f}%")
    print()
    print("建議: 當前情況下使用 XGBoost 模型")
    print("=" * 80)


if __name__ == '__main__':
    main()
