"""
實際使用範例

展示如何使用已實現的功能進行加密貨幣技術分析：
1. 載入市場資料
2. 計算技術指標
3. 應用交易策略
4. 生成交易信號報告
"""
import sys
from pathlib import Path
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from features.technical_indicators import TechnicalIndicators
from strategies.macd_strategy import MACDStrategy
from strategies.fractal_pattern_strategy import (
    FractalBreakoutStrategy,
    CombinedFractalMAStrategy
)


class TradingAnalyzer:
    """交易分析器"""

    def __init__(self):
        """初始化資料庫連接"""
        self.conn = psycopg2.connect(
            host='localhost',
            port=5432,
            dbname='crypto_db',
            user='crypto',
            password='crypto_pass'
        )

    def load_market_data(
        self,
        exchange: str,
        symbol: str,
        timeframe: str = '1m',
        limit: int = 1000
    ) -> pd.DataFrame:
        """載入市場資料"""
        query = """
            SELECT
                o.open_time as timestamp,
                o.open,
                o.high,
                o.low,
                o.close,
                o.volume
            FROM ohlcv o
            JOIN markets m ON o.market_id = m.id
            JOIN exchanges e ON m.exchange_id = e.id
            WHERE e.name = %s
              AND m.symbol = %s
              AND o.timeframe = %s
            ORDER BY o.open_time ASC
            LIMIT %s
        """

        df = pd.read_sql_query(
            query, self.conn,
            params=[exchange, symbol, timeframe, limit]
        )

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')

        return df

    def analyze_market(
        self,
        exchange: str,
        symbol: str,
        strategies: list = None
    ) -> dict:
        """
        完整市場分析

        Args:
            exchange: 交易所
            symbol: 交易對
            strategies: 策略列表（若無則使用預設）

        Returns:
            分析結果字典
        """
        print(f"\n{'=' * 80}")
        print(f"分析 {exchange.upper()} {symbol}")
        print(f"{'=' * 80}\n")

        # 1. 載入資料
        print("Step 1: 載入市場資料...")
        df = self.load_market_data(exchange, symbol, limit=500)
        print(f"  ✓ 載入 {len(df)} 根 K線")
        print(f"  時間範圍: {df.index[0]} ~ {df.index[-1]}\n")

        # 2. 計算技術指標
        print("Step 2: 計算技術指標...")
        df = TechnicalIndicators.add_all_indicators(df)
        print("  ✓ MACD")
        print("  ✓ MA (20, 60, 200)")
        print("  ✓ Williams Fractal")
        print("  ✓ 頭肩形態\n")

        # 3. 應用策略
        print("Step 3: 應用交易策略...")
        if strategies is None:
            strategies = [
                MACDStrategy(name="MACD_Cross"),
                FractalBreakoutStrategy(name="Fractal_Breakout"),
                CombinedFractalMAStrategy(name="Fractal_MA_Combined")
            ]

        signals_dict = {}
        for strategy in strategies:
            signals = strategy.generate_signals(df)
            signals_dict[strategy.name] = signals

            long_count = (signals == 1).sum()
            short_count = (signals == -1).sum()
            print(f"  ✓ {strategy.name}: {long_count} 買入, {short_count} 賣出\n")

        # 4. 生成報告
        result = {
            'data': df,
            'signals': signals_dict,
            'summary': self._generate_summary(df, signals_dict)
        }

        return result

    def _generate_summary(self, df: pd.DataFrame, signals_dict: dict) -> dict:
        """生成摘要統計"""
        latest = df.iloc[-1]

        summary = {
            'latest_price': latest['close'],
            'latest_time': df.index[-1],
            'macd': latest['macd'],
            'macd_signal': latest['macd_signal'],
            'macd_histogram': latest['macd_histogram'],
            'ma_20': latest['ma_20'],
            'ma_60': latest['ma_60'],
            'ma_200': latest['ma_200'],
            'price_vs_ma20': ((latest['close'] / latest['ma_20']) - 1) * 100,
            'price_vs_ma60': ((latest['close'] / latest['ma_60']) - 1) * 100,
            'strategy_signals': {}
        }

        # 統計各策略的最新信號
        for name, signals in signals_dict.items():
            # 找到最近的非 None 信號
            non_none_signals = signals[signals.notna()]
            if not non_none_signals.empty:
                latest_signal = non_none_signals.iloc[-1]
                signal_time = non_none_signals.index[-1]
                summary['strategy_signals'][name] = {
                    'signal': latest_signal,
                    'time': signal_time
                }

        return summary

    def print_report(self, result: dict):
        """列印分析報告"""
        summary = result['summary']

        print(f"\n{'=' * 80}")
        print("分析報告")
        print(f"{'=' * 80}\n")

        print(f"最新價格: {summary['latest_price']:.2f}")
        print(f"時間: {summary['latest_time']}\n")

        print("技術指標：")
        print(f"  MACD: {summary['macd']:.4f}")
        print(f"  Signal: {summary['macd_signal']:.4f}")
        print(f"  Histogram: {summary['macd_histogram']:.4f}")
        print(f"  MA 20: {summary['ma_20']:.2f} ({summary['price_vs_ma20']:+.2f}%)")
        print(f"  MA 60: {summary['ma_60']:.2f} ({summary['price_vs_ma60']:+.2f}%)")
        print(f"  MA 200: {summary['ma_200']:.2f}\n")

        print("策略信號：")
        for name, signal_info in summary['strategy_signals'].items():
            signal_value = signal_info['signal']
            signal_text = {1: '買入 🟢', -1: '賣出 🔴', 0: '平倉 ⚪'}.get(signal_value, '持有')
            print(f"  {name}: {signal_text} (於 {signal_info['time']})")

        print(f"\n{'=' * 80}\n")

    def plot_chart(self, result: dict, save_path: str = None):
        """繪製分析圖表"""
        df = result['data']
        signals = result['signals']

        fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

        # 子圖 1: 價格與 MA
        ax1 = axes[0]
        ax1.plot(df.index, df['close'], label='Close Price', color='black', linewidth=1)
        ax1.plot(df.index, df['ma_20'], label='MA 20', color='blue', alpha=0.7)
        ax1.plot(df.index, df['ma_60'], label='MA 60', color='orange', alpha=0.7)
        ax1.plot(df.index, df['ma_200'], label='MA 200', color='red', alpha=0.7)

        # 標記分形點
        fractals_up = df[df['fractal_up']]
        fractals_down = df[df['fractal_down']]
        ax1.scatter(fractals_up.index, fractals_up['high'], marker='^', color='green', s=50, label='Fractal Up')
        ax1.scatter(fractals_down.index, fractals_down['low'], marker='v', color='red', s=50, label='Fractal Down')

        ax1.set_ylabel('Price', fontsize=12)
        ax1.set_title('Price Chart with Moving Averages & Fractals', fontsize=14)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)

        # 子圖 2: MACD
        ax2 = axes[1]
        ax2.plot(df.index, df['macd'], label='MACD', color='blue')
        ax2.plot(df.index, df['macd_signal'], label='Signal', color='red')
        ax2.bar(df.index, df['macd_histogram'], label='Histogram', color='gray', alpha=0.3)
        ax2.axhline(0, color='black', linestyle='--', linewidth=0.5)
        ax2.set_ylabel('MACD', fontsize=12)
        ax2.set_title('MACD Indicator', fontsize=14)
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)

        # 子圖 3: 交易信號
        ax3 = axes[2]
        for name, signal_series in signals.items():
            buy_signals = signal_series[signal_series == 1]
            sell_signals = signal_series[signal_series == -1]

            if not buy_signals.empty:
                ax3.scatter(buy_signals.index, [0.5] * len(buy_signals),
                           marker='^', color='green', s=100, label=f'{name} Buy')
            if not sell_signals.empty:
                ax3.scatter(sell_signals.index, [-0.5] * len(sell_signals),
                           marker='v', color='red', s=100, label=f'{name} Sell')

        ax3.set_ylabel('Signals', fontsize=12)
        ax3.set_xlabel('Time', fontsize=12)
        ax3.set_title('Trading Signals', fontsize=14)
        ax3.set_ylim(-1, 1)
        ax3.legend(loc='best', fontsize=8)
        ax3.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"圖表已儲存至: {save_path}")

        plt.show()

    def close(self):
        """關閉連接"""
        if self.conn:
            self.conn.close()


def main():
    """主函數 - 範例使用"""
    print("\n" + "=" * 100)
    print(" " * 30 + "加密貨幣技術分析範例")
    print("=" * 100)

    # 建立分析器
    analyzer = TradingAnalyzer()

    try:
        # 分析 BTC/USDT
        result_btc = analyzer.analyze_market('binance', 'BTC/USDT')
        analyzer.print_report(result_btc)

        # 分析 ETH/USDT
        result_eth = analyzer.analyze_market('binance', 'ETH/USDT')
        analyzer.print_report(result_eth)

        # 繪製圖表（可選）
        print("是否繪製圖表？(需要 matplotlib 視窗)")
        # analyzer.plot_chart(result_btc, save_path='./reports/BTC_USDT_analysis.png')

    finally:
        analyzer.close()

    print("\n" + "=" * 100)
    print("分析完成")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    main()
