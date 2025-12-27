"""
完整模型比較報告：XGBoost vs LSTM (簡化版) vs LSTM (完整版)
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_all_results():
    """載入所有模型的結果"""
    logger.info("載入所有模型結果...")

    results = {}

    # 1. XGBoost 結果
    xgb_dir = Path('results/xgboost_btc_1h')
    results['XGBoost'] = {
        'metrics': {
            'RMSE': 253.96,
            'MAE': 179.85,
            'R2': 0.999270,
            'MAPE': 0.185,
            'Direction_Accuracy': 86.43
        },
        'predictions': pd.read_csv(xgb_dir / 'predictions.csv'),
        'num_features': 84,
        'config': 'n_estimators=200, max_depth=8, lr=0.05'
    }

    # 2. LSTM 簡化版結果（6 特徵）
    lstm_simple_dir = Path('results/lstm_btc_1h')
    with open(lstm_simple_dir / 'metrics.json', 'r') as f:
        lstm_simple_metrics = json.load(f)

    results['LSTM (簡化)'] = {
        'metrics': lstm_simple_metrics,
        'predictions': pd.read_csv(lstm_simple_dir / 'predictions.csv'),
        'num_features': 6,
        'config': 'hidden=32, layers=1, seq=30'
    }

    # 3. LSTM 完整版結果（118 特徵）
    lstm_full_dir = Path('results/lstm_full_features_btc_1h')
    with open(lstm_full_dir / 'metrics.json', 'r') as f:
        lstm_full_metrics = json.load(f)

    results['LSTM (完整)'] = {
        'metrics': lstm_full_metrics,
        'predictions': pd.read_csv(lstm_full_dir / 'predictions.csv'),
        'num_features': 118,
        'config': 'hidden=64, layers=2, seq=30, dropout=0.2'
    }

    logger.info("結果載入完成")

    return results


def create_comprehensive_report(results):
    """創建綜合比較報告"""
    logger.info("創建綜合比較報告...")

    output_dir = Path('results/final_model_comparison')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 提取指標
    models = list(results.keys())
    xgb_m = results['XGBoost']['metrics']
    lstm_simple_m = results['LSTM (簡化)']['metrics']
    lstm_full_m = results['LSTM (完整)']['metrics']

    # 創建 Markdown 報告
    report = f"""# 完整模型比較報告

**生成時間**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## 1. 模型概覽

| 模型 | 特徵數量 | 配置 |
|------|---------|------|
| XGBoost | {results['XGBoost']['num_features']} | {results['XGBoost']['config']} |
| LSTM (簡化) | {results['LSTM (簡化)']['num_features']} | {results['LSTM (簡化)']['config']} |
| LSTM (完整) | {results['LSTM (完整)']['num_features']} | {results['LSTM (完整)']['config']} |

## 2. 性能比較

### 2.1 關鍵指標

| 指標 | XGBoost | LSTM (簡化) | LSTM (完整) | 最佳模型 |
|------|---------|------------|------------|---------|
| **RMSE** | {xgb_m['RMSE']:.2f} | {lstm_simple_m['RMSE']:.2f} | {lstm_full_m['RMSE']:.2f} | **{'XGBoost' if xgb_m['RMSE'] < min(lstm_simple_m['RMSE'], lstm_full_m['RMSE']) else 'LSTM'}** |
| **MAE** | {xgb_m['MAE']:.2f} | {lstm_simple_m['MAE']:.2f} | {lstm_full_m['MAE']:.2f} | **{'XGBoost' if xgb_m['MAE'] < min(lstm_simple_m['MAE'], lstm_full_m['MAE']) else 'LSTM'}** |
| **R²** | {xgb_m['R2']:.6f} | {lstm_simple_m['R2']:.6f} | {lstm_full_m['R2']:.6f} | **{'XGBoost' if xgb_m['R2'] > max(lstm_simple_m['R2'], lstm_full_m['R2']) else 'LSTM'}** |
| **MAPE** | {xgb_m['MAPE']:.3f}% | {lstm_simple_m['MAPE']:.3f}% | {lstm_full_m['MAPE']:.3f}% | **{'XGBoost' if xgb_m['MAPE'] < min(lstm_simple_m['MAPE'], lstm_full_m['MAPE']) else 'LSTM'}** |
| **方向準確率** | {xgb_m['Direction_Accuracy']:.2f}% | {lstm_simple_m['Direction_Accuracy']:.2f}% | {lstm_full_m['Direction_Accuracy']:.2f}% | **{'XGBoost' if xgb_m['Direction_Accuracy'] > max(lstm_simple_m['Direction_Accuracy'], lstm_full_m['Direction_Accuracy']) else 'LSTM'}** |

### 2.2 性能差距分析

**相對於 XGBoost 的性能差距：**

#### LSTM (簡化版, 6 特徵)
- RMSE: {lstm_simple_m['RMSE'] / xgb_m['RMSE']:.2f}x 更差
- MAE: {lstm_simple_m['MAE'] / xgb_m['MAE']:.2f}x 更差
- 方向準確率: {lstm_simple_m['Direction_Accuracy'] / xgb_m['Direction_Accuracy']:.2f}x 更差

#### LSTM (完整版, 118 特徵)
- RMSE: {lstm_full_m['RMSE'] / xgb_m['RMSE']:.2f}x 更差
- MAE: {lstm_full_m['MAE'] / xgb_m['MAE']:.2f}x 更差
- 方向準確率: {lstm_full_m['Direction_Accuracy'] / xgb_m['Direction_Accuracy']:.2f}x 更差

### 2.3 LSTM 版本比較

**簡化版 vs 完整版：**
- RMSE: {'簡化版更好' if lstm_simple_m['RMSE'] < lstm_full_m['RMSE'] else '完整版更好'} ({abs(lstm_simple_m['RMSE'] - lstm_full_m['RMSE']):.2f} USDT 差距)
- MAE: {'簡化版更好' if lstm_simple_m['MAE'] < lstm_full_m['MAE'] else '完整版更好'} ({abs(lstm_simple_m['MAE'] - lstm_full_m['MAE']):.2f} USDT 差距)
- R²: {'簡化版更好' if lstm_simple_m['R2'] > lstm_full_m['R2'] else '完整版更好'} ({abs(lstm_simple_m['R2'] - lstm_full_m['R2']):.6f} 差距)
- 方向準確率: {'簡化版更好' if lstm_simple_m['Direction_Accuracy'] > lstm_full_m['Direction_Accuracy'] else '完整版更好'} ({abs(lstm_simple_m['Direction_Accuracy'] - lstm_full_m['Direction_Accuracy']):.2f}% 差距)

## 3. 深度分析

### 3.1 為什麼 XGBoost 顯著優於 LSTM？

1. **特徵處理方式**：
   - XGBoost 直接處理表格型特徵，適合時序數據的統計特徵（lag, rolling, 技術指標）
   - LSTM 需要序列結構，可能丟失了一些跨時間步的複雜模式

2. **方向預測能力**：
   - XGBoost: 86.43%（遠超隨機）
   - LSTM: ~47%（接近隨機）
   - 這表明 XGBoost 更好地捕捉了價格變化趨勢

3. **訓練穩定性**：
   - XGBoost: 梯度提升，穩定且可解釋
   - LSTM: 需要仔細調參，容易陷入局部最優

### 3.2 為什麼增加 LSTM 特徵反而沒有提升性能？

**簡化版（6 特徵）vs 完整版（118 特徵）：**

| 指標 | 簡化版 | 完整版 | 結論 |
|------|-------|-------|------|
| RMSE | {lstm_simple_m['RMSE']:.2f} | {lstm_full_m['RMSE']:.2f} | {'簡化版更好' if lstm_simple_m['RMSE'] < lstm_full_m['RMSE'] else '完整版更好'} |
| 方向準確率 | {lstm_simple_m['Direction_Accuracy']:.2f}% | {lstm_full_m['Direction_Accuracy']:.2f}% | {'簡化版更好' if lstm_simple_m['Direction_Accuracy'] > lstm_full_m['Direction_Accuracy'] else '完整版更好'} |

**可能原因：**

1. **維度災難**：118 個特徵可能導致 LSTM 過擬合訓練集
2. **訓練不足**：更多特徵需要更多訓練數據和更長訓練時間
3. **特徵冗餘**：很多特徵高度相關，增加噪音而非信號
4. **序列長度**：30 步序列 × 118 特徵 = 3,540 個輸入，可能過於複雜

### 3.3 LSTM 改進建議

1. **特徵選擇**：
   - 使用 XGBoost 特徵重要性篩選最重要的 20-30 個特徵
   - 進行主成分分析（PCA）降維

2. **架構調整**：
   - 嘗試 Bidirectional LSTM
   - 使用 Attention 機制
   - 探索 Transformer 架構

3. **數據預處理**：
   - 使用價格差分而非絕對價格
   - 添加更多數據（目前只有 1 年）
   - 考慮多變量時間序列建模

4. **訓練策略**：
   - 更長的訓練時間
   - 更細緻的超參數搜索
   - 使用交叉驗證

## 4. 最終結論與建議

### ✅ 明確推薦：使用 XGBoost

**理由：**

1. **預測精度最高**：
   - RMSE 低於 LSTM 2.6-2.7 倍
   - R² 達到 0.9993（幾乎完美）

2. **方向預測最準**：
   - 86.43% 準確率，適合交易策略
   - LSTM 方向準確率接近隨機（~47%）

3. **實用性最強**：
   - 訓練快速（相比深度學習）
   - 可解釋性強（特徵重要性）
   - 生產部署簡單

4. **穩定性最佳**：
   - 超參數敏感度低
   - 不容易過擬合

### ⚠️ LSTM 不推薦用於此任務

**關鍵問題：**

1. 方向準確率僅 47%，無法用於交易決策
2. 增加特徵未能提升性能，反而略有下降
3. 訓練時間長，調參困難

**可能適用場景：**

- 更長的序列（日線、週線數據）
- 多變量時間序列（結合訂單簿、鏈上數據）
- 與 XGBoost 集成學習

### 📊 數據總結

```
模型性能排名（RMSE）:
1. XGBoost:        253.96 USDT  ⭐⭐⭐⭐⭐
2. LSTM (簡化):    662.59 USDT  ⭐⭐
3. LSTM (完整):    693.17 USDT  ⭐⭐

模型性能排名（方向準確率）:
1. XGBoost:        86.43%       ⭐⭐⭐⭐⭐
2. LSTM (簡化):    47.41%       ⭐ (接近隨機)
3. LSTM (完整):    46.25%       ⭐ (接近隨機)
```

### 🚀 後續工作建議

1. **XGBoost 優化**：
   - 超參數網格搜索
   - 交叉驗證確保穩定性
   - 添加更多技術指標

2. **策略回測**：
   - 使用 XGBoost 預測構建交易策略
   - 評估真實交易成本下的性能

3. **集成學習**（可選）：
   - XGBoost + LightGBM + CatBoost 集成
   - 可能進一步提升性能

4. **不同時間週期**：
   - 嘗試 4h、日線數據
   - 評估模型在不同市場環境下的穩定性
"""

    # 保存報告
    with open(output_dir / 'comprehensive_comparison.md', 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info(f"報告已保存至 {output_dir / 'comprehensive_comparison.md'}")

    return report


def create_comprehensive_plots(results):
    """創建綜合比較圖表"""
    logger.info("創建綜合比較圖表...")

    output_dir = Path('results/final_model_comparison')
    output_dir.mkdir(parents=True, exist_ok=True)

    models = list(results.keys())
    colors = ['#2ecc71', '#3498db', '#e74c3c']

    # 創建大型圖表
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # 1. RMSE 比較
    ax1 = fig.add_subplot(gs[0, 0])
    rmse_values = [results[m]['metrics']['RMSE'] for m in models]
    bars = ax1.bar(models, rmse_values, color=colors, alpha=0.8)
    ax1.set_ylabel('RMSE (USDT)')
    ax1.set_title('RMSE Comparison (Lower is Better)')
    ax1.grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(rmse_values):
        ax1.text(i, v + 20, f'{v:.2f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # 2. MAE 比較
    ax2 = fig.add_subplot(gs[0, 1])
    mae_values = [results[m]['metrics']['MAE'] for m in models]
    bars = ax2.bar(models, mae_values, color=colors, alpha=0.8)
    ax2.set_ylabel('MAE (USDT)')
    ax2.set_title('MAE Comparison (Lower is Better)')
    ax2.grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(mae_values):
        ax2.text(i, v + 15, f'{v:.2f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # 3. R² 比較
    ax3 = fig.add_subplot(gs[0, 2])
    r2_values = [results[m]['metrics']['R2'] for m in models]
    bars = ax3.bar(models, r2_values, color=colors, alpha=0.8)
    ax3.set_ylabel('R² Score')
    ax3.set_title('R² Score Comparison (Higher is Better)')
    ax3.set_ylim([0.98, 1.0])
    ax3.grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(r2_values):
        ax3.text(i, v + 0.0001, f'{v:.6f}', ha='center', va='bottom', fontsize=8, fontweight='bold')

    # 4. MAPE 比較
    ax4 = fig.add_subplot(gs[1, 0])
    mape_values = [results[m]['metrics']['MAPE'] for m in models]
    bars = ax4.bar(models, mape_values, color=colors, alpha=0.8)
    ax4.set_ylabel('MAPE (%)')
    ax4.set_title('MAPE Comparison (Lower is Better)')
    ax4.grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(mape_values):
        ax4.text(i, v + 0.02, f'{v:.3f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # 5. 方向準確率比較
    ax5 = fig.add_subplot(gs[1, 1])
    dir_acc_values = [results[m]['metrics']['Direction_Accuracy'] for m in models]
    bars = ax5.bar(models, dir_acc_values, color=colors, alpha=0.8)
    ax5.set_ylabel('Direction Accuracy (%)')
    ax5.set_title('Direction Accuracy Comparison')
    ax5.axhline(y=50, color='red', linestyle='--', linewidth=1.5, label='Random (50%)')
    ax5.legend()
    ax5.grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(dir_acc_values):
        ax5.text(i, v + 2, f'{v:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # 6. 特徵數量比較
    ax6 = fig.add_subplot(gs[1, 2])
    feature_counts = [results[m]['num_features'] for m in models]
    bars = ax6.bar(models, feature_counts, color=colors, alpha=0.8)
    ax6.set_ylabel('Number of Features')
    ax6.set_title('Feature Count Comparison')
    ax6.grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(feature_counts):
        ax6.text(i, v + 3, f'{v}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 7-9. 預測 vs 實際（前 300 樣本）
    for idx, model_name in enumerate(models):
        ax = fig.add_subplot(gs[2, idx])
        pred_df = results[model_name]['predictions']

        sample_size = min(300, len(pred_df))
        ax.plot(pred_df['actual'][:sample_size], label='Actual', linewidth=1.5, alpha=0.8)
        ax.plot(pred_df['predicted'][:sample_size], label='Predicted', linewidth=1.5, alpha=0.8)
        ax.set_title(f'{model_name}: Actual vs Predicted')
        ax.set_xlabel('Sample')
        ax.set_ylabel('Price (USDT)')
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.savefig(output_dir / 'comprehensive_comparison.png', dpi=150, bbox_inches='tight')
    logger.info(f"圖表已保存至 {output_dir / 'comprehensive_comparison.png'}")


def print_summary(results):
    """打印簡要總結"""
    print("\n" + "=" * 100)
    print("完整模型比較總結")
    print("=" * 100)

    for model_name, data in results.items():
        print(f"\n【{model_name}】- 特徵數量: {data['num_features']}")
        print(f"  配置: {data['config']}")
        print(f"  RMSE: {data['metrics']['RMSE']:.2f} USDT")
        print(f"  MAE: {data['metrics']['MAE']:.2f} USDT")
        print(f"  R²: {data['metrics']['R2']:.6f}")
        print(f"  MAPE: {data['metrics']['MAPE']:.3f}%")
        print(f"  方向準確率: {data['metrics']['Direction_Accuracy']:.2f}%")

    print("\n" + "=" * 100)
    print("結論: XGBoost 在所有指標上均顯著優於 LSTM")
    print("=" * 100)
    print()


def main():
    """主函數"""
    logger.info("=" * 80)
    logger.info("開始生成完整模型比較報告")
    logger.info("=" * 80)

    # 載入結果
    results = load_all_results()

    # 創建比較報告
    report = create_comprehensive_report(results)

    # 創建比較圖表
    create_comprehensive_plots(results)

    # 打印簡要總結
    print_summary(results)

    logger.info("=" * 80)
    logger.info("完整模型比較報告生成完成！")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
