"""
回測視覺化工具

職責：
- 繪製權益曲線
- 繪製回撤圖
- 繪製價格與交易信號
- 繪製績效摘要圖表
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, Optional, Tuple
from pathlib import Path
from loguru import logger


class BacktestVisualizer:
    """回測視覺化器"""

    def __init__(self, figsize: Tuple[int, int] = (15, 10)):
        """
        初始化視覺化器

        Args:
            figsize: 圖表尺寸
        """
        self.figsize = figsize

        # 設定中文字體與樣式
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        plt.style.use('seaborn-v0_8-darkgrid')

    def plot_equity_curve(
        self,
        equity_curve: pd.DataFrame,
        title: str = "Equity Curve",
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        繪製權益曲線

        Args:
            equity_curve: 權益曲線 DataFrame
            title: 圖表標題
            save_path: 儲存路徑

        Returns:
            Figure 物件
        """
        fig, ax = plt.subplots(figsize=(self.figsize[0], 6))

        # 繪製總權益
        ax.plot(
            equity_curve.index,
            equity_curve['total_equity'],
            label='Total Equity',
            linewidth=2,
            color='#2E86AB'
        )

        # 繪製現金
        ax.plot(
            equity_curve.index,
            equity_curve['cash'],
            label='Cash',
            linewidth=1.5,
            color='#A23B72',
            alpha=0.7,
            linestyle='--'
        )

        # 繪製持倉市值
        ax.plot(
            equity_curve.index,
            equity_curve['positions_value'],
            label='Positions Value',
            linewidth=1.5,
            color='#F18F01',
            alpha=0.7,
            linestyle='--'
        )

        # 初始資本參考線
        initial_capital = equity_curve['total_equity'].iloc[0]
        ax.axhline(
            y=initial_capital,
            color='gray',
            linestyle=':',
            linewidth=1,
            label='Initial Capital'
        )

        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Value ($)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # 格式化 x 軸日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"權益曲線圖已儲存：{save_path}")

        return fig

    def plot_drawdown(
        self,
        equity_curve: pd.DataFrame,
        title: str = "Drawdown",
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        繪製回撤圖

        Args:
            equity_curve: 權益曲線 DataFrame
            title: 圖表標題
            save_path: 儲存路徑

        Returns:
            Figure 物件
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(self.figsize[0], 8))

        # 計算回撤
        cummax = equity_curve['total_equity'].cummax()
        drawdown = (equity_curve['total_equity'] - cummax) / cummax * 100

        # 上圖：權益曲線
        ax1.plot(
            equity_curve.index,
            equity_curve['total_equity'],
            label='Total Equity',
            linewidth=2,
            color='#2E86AB'
        )
        ax1.plot(
            equity_curve.index,
            cummax,
            label='Peak Equity',
            linewidth=1.5,
            color='#06A77D',
            linestyle='--',
            alpha=0.7
        )
        ax1.set_ylabel('Equity ($)', fontsize=12)
        ax1.set_title(title, fontsize=14, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)

        # 下圖：回撤
        ax2.fill_between(
            drawdown.index,
            drawdown,
            0,
            where=(drawdown < 0),
            color='#D62246',
            alpha=0.5,
            label='Drawdown'
        )
        ax2.plot(
            drawdown.index,
            drawdown,
            color='#D62246',
            linewidth=1.5
        )

        # 標記最大回撤
        max_dd_idx = drawdown.idxmin()
        max_dd_val = drawdown.min()
        ax2.scatter(
            [max_dd_idx],
            [max_dd_val],
            color='red',
            s=100,
            zorder=5,
            label=f'Max DD: {max_dd_val:.2f}%'
        )

        ax2.set_xlabel('Time', fontsize=12)
        ax2.set_ylabel('Drawdown (%)', fontsize=12)
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)

        # 格式化 x 軸
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))

        plt.xticks(rotation=45)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"回撤圖已儲存：{save_path}")

        return fig

    def plot_price_with_signals(
        self,
        market_data: pd.DataFrame,
        signals: pd.DataFrame,
        trades: pd.DataFrame,
        title: str = "Price & Signals",
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        繪製價格與交易信號

        Args:
            market_data: 市場資料（OHLCV）
            signals: 信號記錄
            trades: 交易記錄
            title: 圖表標題
            save_path: 儲存路徑

        Returns:
            Figure 物件
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(self.figsize[0], 10), height_ratios=[3, 1])

        # 上圖：價格與信號
        ax1.plot(
            market_data.index,
            market_data['close'],
            label='Close Price',
            linewidth=1.5,
            color='#2E86AB'
        )

        # 標記買入信號
        buy_signals = signals[signals['action'] == 'buy']
        if not buy_signals.empty:
            buy_prices = market_data.loc[buy_signals.index, 'close']
            ax1.scatter(
                buy_signals.index,
                buy_prices,
                marker='^',
                color='#06A77D',
                s=100,
                label='Buy Signal',
                zorder=5
            )

        # 標記賣出信號
        sell_signals = signals[signals['action'] == 'sell']
        if not sell_signals.empty:
            sell_prices = market_data.loc[sell_signals.index, 'close']
            ax1.scatter(
                sell_signals.index,
                sell_prices,
                marker='v',
                color='#D62246',
                s=100,
                label='Sell Signal',
                zorder=5
            )

        # 標記實際交易
        if not trades.empty:
            buy_trades = trades[trades['side'] == 'buy']
            sell_trades = trades[trades['side'] == 'sell']

            if not buy_trades.empty:
                ax1.scatter(
                    buy_trades.index,
                    buy_trades['price'],
                    marker='o',
                    color='green',
                    s=150,
                    edgecolors='black',
                    linewidths=2,
                    label='Buy Trade',
                    zorder=10
                )

            if not sell_trades.empty:
                ax1.scatter(
                    sell_trades.index,
                    sell_trades['price'],
                    marker='o',
                    color='red',
                    s=150,
                    edgecolors='black',
                    linewidths=2,
                    label='Sell Trade',
                    zorder=10
                )

        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.set_title(title, fontsize=14, fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)

        # 下圖：成交量
        ax2.bar(
            market_data.index,
            market_data['volume'],
            width=0.0007,  # 調整寬度以適應時間軸
            color='#A8DADC',
            alpha=0.7,
            label='Volume'
        )
        ax2.set_xlabel('Time', fontsize=12)
        ax2.set_ylabel('Volume', fontsize=12)
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)

        # 格式化 x 軸
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))

        plt.xticks(rotation=45)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"價格信號圖已儲存：{save_path}")

        return fig

    def plot_metrics_summary(
        self,
        metrics: Dict,
        title: str = "Performance Metrics",
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        繪製績效指標摘要

        Args:
            metrics: 績效指標字典
            title: 圖表標題
            save_path: 儲存路徑

        Returns:
            Figure 物件
        """
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        fig.suptitle(title, fontsize=16, fontweight='bold')

        # 1. 收益率條形圖
        ax1 = axes[0, 0]
        returns_data = {
            'Total\nReturn': metrics.get('total_return', 0) * 100,
            'Annual\nReturn': metrics.get('annualized_return', 0) * 100,
        }
        colors = ['#06A77D' if v > 0 else '#D62246' for v in returns_data.values()]
        ax1.bar(returns_data.keys(), returns_data.values(), color=colors, alpha=0.7)
        ax1.set_ylabel('Return (%)', fontsize=11)
        ax1.set_title('Returns', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

        # 2. 風險指標
        ax2 = axes[0, 1]
        risk_data = {
            'Max\nDrawdown': abs(metrics.get('max_drawdown', 0)) * 100,
            'Volatility': metrics.get('volatility', 0) * 100,
        }
        ax2.bar(risk_data.keys(), risk_data.values(), color='#F18F01', alpha=0.7)
        ax2.set_ylabel('Risk (%)', fontsize=11)
        ax2.set_title('Risk Metrics', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

        # 3. 風險調整後收益
        ax3 = axes[1, 0]
        ratio_data = {
            'Sharpe': metrics.get('sharpe_ratio', 0),
            'Sortino': metrics.get('sortino_ratio', 0),
            'Calmar': metrics.get('calmar_ratio', 0),
        }
        colors = ['#2E86AB' if v > 0 else '#D62246' for v in ratio_data.values()]
        ax3.bar(ratio_data.keys(), ratio_data.values(), color=colors, alpha=0.7)
        ax3.set_ylabel('Ratio', fontsize=11)
        ax3.set_title('Risk-Adjusted Returns', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

        # 4. 交易統計
        ax4 = axes[1, 1]
        trade_data = {
            'Total\nTrades': metrics.get('total_trades', 0),
            'Win\nRate (%)': metrics.get('win_rate', 0) * 100,
            'Profit\nFactor': metrics.get('profit_factor', 0),
        }
        ax4.bar(trade_data.keys(), trade_data.values(), color='#A23B72', alpha=0.7)
        ax4.set_ylabel('Value', fontsize=11)
        ax4.set_title('Trading Statistics', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"績效摘要圖已儲存：{save_path}")

        return fig

    def plot_comprehensive_report(
        self,
        equity_curve: pd.DataFrame,
        market_data: pd.DataFrame,
        signals: pd.DataFrame,
        trades: pd.DataFrame,
        metrics: Dict,
        strategy_name: str = "Strategy",
        save_dir: Optional[str] = None
    ):
        """
        生成完整的視覺化報告

        Args:
            equity_curve: 權益曲線
            market_data: 市場資料
            signals: 信號記錄
            trades: 交易記錄
            metrics: 績效指標
            strategy_name: 策略名稱
            save_dir: 儲存目錄
        """
        logger.info("=" * 60)
        logger.info(f"生成 {strategy_name} 視覺化報告")
        logger.info("=" * 60)

        if save_dir:
            save_dir = Path(save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)

        # 1. 權益曲線
        equity_path = str(save_dir / f"{strategy_name}_equity_curve.png") if save_dir else None
        self.plot_equity_curve(
            equity_curve,
            title=f"{strategy_name} - Equity Curve",
            save_path=equity_path
        )
        plt.close()

        # 2. 回撤圖
        drawdown_path = str(save_dir / f"{strategy_name}_drawdown.png") if save_dir else None
        self.plot_drawdown(
            equity_curve,
            title=f"{strategy_name} - Drawdown",
            save_path=drawdown_path
        )
        plt.close()

        # 3. 價格與信號
        signals_path = str(save_dir / f"{strategy_name}_signals.png") if save_dir else None
        self.plot_price_with_signals(
            market_data,
            signals,
            trades,
            title=f"{strategy_name} - Price & Signals",
            save_path=signals_path
        )
        plt.close()

        # 4. 績效摘要
        metrics_path = str(save_dir / f"{strategy_name}_metrics.png") if save_dir else None
        self.plot_metrics_summary(
            metrics,
            title=f"{strategy_name} - Performance Metrics",
            save_path=metrics_path
        )
        plt.close()

        logger.info("=" * 60)
        logger.info(f"視覺化報告生成完成！")
        if save_dir:
            logger.info(f"報告已儲存至：{save_dir}")
        logger.info("=" * 60)
