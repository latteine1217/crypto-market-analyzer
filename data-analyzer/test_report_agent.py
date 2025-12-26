"""
Report Agent 測試腳本

用途：測試完整的報表生成流程
"""
import sys
from pathlib import Path

# 加入 src 到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from datetime import datetime, timedelta
from reports import ReportAgent


def test_comprehensive_report():
    """測試綜合報表生成"""
    print("=" * 60)
    print("測試綜合報表生成功能")
    print("=" * 60)

    # 初始化 Report Agent
    agent = ReportAgent(
        output_dir="reports",
        db_config={
            'host': 'localhost',
            'port': 5432,
            'database': 'crypto_market',
            'user': 'postgres',
            'password': ''
        }
    )

    # 生成日報（過去 24 小時）
    print("\n### 生成日報 ###")
    try:
        result = agent.generate_comprehensive_report(
            report_type='daily',
            markets=['BTC/USDT', 'ETH/USDT'],
            strategies=['RSI', 'MA_Cross', 'BuyAndHold'],
            formats=['html']  # 先只生成 HTML
        )

        print("\n報表生成成功！")
        print(f"報表類型：{result['report_type']}")
        print(f"報表期間：{result['period']['start']} ~ {result['period']['end']}")
        print(f"\n統計資訊：")
        print(f"  資料品質記錄數：{result['statistics']['quality_records']}")
        print(f"  策略數：{result['statistics']['strategies']}")
        print(f"  模型數：{result['statistics']['models']}")

        print(f"\n生成的檔案：")
        for format_type, path in result['output_paths'].items():
            print(f"  {format_type}: {path}")

        print(f"\nJSON 資料：{result['json_path']}")

    except Exception as e:
        print(f"❌ 報表生成失敗：{e}")
        import traceback
        traceback.print_exc()

    agent.close()


def test_backtest_report_from_results():
    """從現有回測結果生成報表"""
    print("\n" + "=" * 60)
    print("測試從現有回測結果生成報表")
    print("=" * 60)

    agent = ReportAgent(output_dir="reports")

    # 檢查是否有現有的回測結果
    backtest_dir = Path("results/backtest_reports")
    if not backtest_dir.exists():
        print("❌ 回測結果目錄不存在，跳過此測試")
        return

    # 查找策略
    strategies = [d.name for d in backtest_dir.iterdir() if d.is_dir()]
    print(f"找到策略：{strategies}")

    if strategies:
        # 為每個策略生成報表
        for strategy_name in strategies:
            print(f"\n### 為 {strategy_name} 生成報表 ###")

            # 模擬回測結果（實際應從檔案讀取）
            mock_results = {
                'metrics': {
                    'total_return': 0.15,
                    'sharpe_ratio': 1.25,
                    'max_drawdown': 0.08,
                    'win_rate': 0.65,
                    'total_trades': 50,
                    'win_trades': 33,
                    'loss_trades': 17,
                    'avg_win': 0.025,
                    'avg_loss': -0.015,
                    'profit_factor': 2.5,
                },
                'equity_curve': None,  # 實際應載入 CSV
                'trades': None,        # 實際應載入 CSV
                'signals': None,       # 實際應載入 CSV
            }

            import pandas as pd
            mock_market_data = pd.DataFrame({
                'close': [100, 101, 102],
            }, index=pd.date_range('2024-01-01', periods=3, freq='1D'))

            try:
                paths = agent.generate_backtest_report(
                    backtest_results=mock_results,
                    strategy_name=strategy_name,
                    market_data=mock_market_data,
                    formats=['html']
                )

                print(f"✓ 報表已生成：")
                for format_type, path in paths.items():
                    print(f"  {format_type}: {path}")

            except Exception as e:
                print(f"❌ 生成失敗：{e}")

    agent.close()


def test_quality_report():
    """測試資料品質報表"""
    print("\n" + "=" * 60)
    print("測試資料品質報表生成")
    print("=" * 60)

    agent = ReportAgent(
        output_dir="reports",
        db_config={
            'host': 'localhost',
            'port': 5432,
            'database': 'crypto_market',
            'user': 'postgres',
            'password': ''
        }
    )

    try:
        paths = agent.generate_quality_report(
            markets=['BTC/USDT'],
            hours=24,
            formats=['html']
        )

        print("✓ 資料品質報表已生成：")
        for format_type, path in paths.items():
            print(f"  {format_type}: {path}")

    except Exception as e:
        print(f"❌ 生成失敗：{e}")
        import traceback
        traceback.print_exc()

    agent.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Report Agent 完整測試")
    print("=" * 60)

    # 測試 1：綜合報表
    test_comprehensive_report()

    # 測試 2：從現有回測結果生成報表
    test_backtest_report_from_results()

    # 測試 3：資料品質報表
    test_quality_report()

    print("\n" + "=" * 60)
    print("✅ 所有測試完成！")
    print("=" * 60)
