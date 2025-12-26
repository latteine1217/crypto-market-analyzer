"""
績效指標計算器

職責：
- 計算收益率指標
- 計算風險指標
- 計算交易統計
- 生成績效報告
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional
from loguru import logger


class PerformanceMetrics:
    """績效指標計算器"""

    def __init__(self, risk_free_rate: float = 0.0):
        """
        初始化

        Args:
            risk_free_rate: 無風險利率（年化，小數形式）
        """
        self.risk_free_rate = risk_free_rate

    def calculate_all_metrics(
        self,
        equity_curve: pd.DataFrame,
        trades: pd.DataFrame,
        initial_capital: float
    ) -> Dict:
        """
        計算所有績效指標

        Args:
            equity_curve: 權益曲線 DataFrame
            trades: 交易記錄 DataFrame
            initial_capital: 初始資金

        Returns:
            績效指標字典
        """
        if equity_curve.empty:
            logger.warning("權益曲線為空，無法計算績效指標")
            return {}

        metrics = {}

        # 收益率指標
        metrics.update(self._calculate_return_metrics(equity_curve, initial_capital))

        # 風險指標
        metrics.update(self._calculate_risk_metrics(equity_curve))

        # 風險調整後收益指標
        metrics.update(self._calculate_risk_adjusted_metrics(equity_curve))

        # 交易統計
        if not trades.empty:
            metrics.update(self._calculate_trade_statistics(trades))

        return metrics

    def _calculate_return_metrics(
        self,
        equity_curve: pd.DataFrame,
        initial_capital: float
    ) -> Dict:
        """計算收益率指標"""

        final_equity = equity_curve['total_equity'].iloc[-1]
        total_return = (final_equity - initial_capital) / initial_capital

        # 計算年化收益率
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        years = days / 365.25
        if years > 0:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = 0.0

        # 計算每日收益率
        equity_curve['daily_return'] = equity_curve['total_equity'].pct_change()

        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'final_equity': final_equity,
            'peak_equity': equity_curve['total_equity'].max(),
        }

    def _calculate_risk_metrics(self, equity_curve: pd.DataFrame) -> Dict:
        """計算風險指標"""

        # 最大回撤
        cummax = equity_curve['total_equity'].cummax()
        drawdown = (equity_curve['total_equity'] - cummax) / cummax
        max_drawdown = drawdown.min()

        # 最大回撤期間
        drawdown_series = equity_curve['total_equity'] / cummax - 1
        is_drawdown = drawdown_series < 0

        if is_drawdown.any():
            # 找出回撤期間
            drawdown_periods = []
            in_drawdown = False
            start_idx = None

            for idx, val in is_drawdown.items():
                if val and not in_drawdown:
                    in_drawdown = True
                    start_idx = idx
                elif not val and in_drawdown:
                    in_drawdown = False
                    drawdown_periods.append((start_idx, idx))

            if in_drawdown and start_idx is not None:
                drawdown_periods.append((start_idx, equity_curve.index[-1]))

            # 計算最長回撤期間
            if drawdown_periods:
                max_drawdown_duration = max(
                    (end - start).days for start, end in drawdown_periods
                )
            else:
                max_drawdown_duration = 0
        else:
            max_drawdown_duration = 0

        # 波動率
        if 'daily_return' in equity_curve.columns:
            daily_volatility = equity_curve['daily_return'].std()
            annualized_volatility = daily_volatility * np.sqrt(252)
        else:
            daily_volatility = 0.0
            annualized_volatility = 0.0

        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_duration_days': max_drawdown_duration,
            'volatility': annualized_volatility,
            'daily_volatility': daily_volatility,
        }

    def _calculate_risk_adjusted_metrics(
        self,
        equity_curve: pd.DataFrame
    ) -> Dict:
        """計算風險調整後收益指標"""

        if 'daily_return' not in equity_curve.columns:
            equity_curve['daily_return'] = equity_curve['total_equity'].pct_change()

        returns = equity_curve['daily_return'].dropna()

        if len(returns) == 0:
            return {
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0,
            }

        # Sharpe Ratio
        excess_returns = returns - self.risk_free_rate / 252
        if returns.std() > 0:
            sharpe_ratio = (excess_returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # Sortino Ratio（只考慮下行波動）
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std()
            if downside_std > 0:
                sortino_ratio = (excess_returns.mean() / downside_std) * np.sqrt(252)
            else:
                sortino_ratio = 0.0
        else:
            sortino_ratio = 0.0

        # Calmar Ratio（年化收益 / 最大回撤）
        cummax = equity_curve['total_equity'].cummax()
        drawdown = (equity_curve['total_equity'] - cummax) / cummax
        max_drawdown = abs(drawdown.min())

        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        years = days / 365.25
        if years > 0 and max_drawdown > 0:
            annualized_return = (returns.mean() * 252)
            calmar_ratio = annualized_return / max_drawdown
        else:
            calmar_ratio = 0.0

        return {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
        }

    def _calculate_trade_statistics(self, trades: pd.DataFrame) -> Dict:
        """計算交易統計"""

        total_trades = len(trades)

        if total_trades == 0:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'avg_trade_pnl': 0.0,
            }

        # 只統計平倉交易（有 PnL 的）
        closed_trades = trades[trades['pnl'] != 0]

        if len(closed_trades) == 0:
            return {
                'total_trades': total_trades,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'avg_trade_pnl': 0.0,
            }

        winning_trades = closed_trades[closed_trades['pnl'] > 0]
        losing_trades = closed_trades[closed_trades['pnl'] < 0]

        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        win_rate = num_wins / len(closed_trades) if len(closed_trades) > 0 else 0.0

        avg_win = winning_trades['pnl'].mean() if num_wins > 0 else 0.0
        avg_loss = losing_trades['pnl'].mean() if num_losses > 0 else 0.0

        # Profit Factor = 總盈利 / 總虧損
        total_wins = winning_trades['pnl'].sum() if num_wins > 0 else 0.0
        total_losses = abs(losing_trades['pnl'].sum()) if num_losses > 0 else 0.0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0

        avg_trade_pnl = closed_trades['pnl'].mean()

        # 交易成本
        total_commission = trades['commission'].sum()
        total_slippage = trades['slippage'].sum()

        return {
            'total_trades': total_trades,
            'closed_trades': len(closed_trades),
            'winning_trades': num_wins,
            'losing_trades': num_losses,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_trade_pnl': avg_trade_pnl,
            'total_commission': total_commission,
            'total_slippage': total_slippage,
            'total_costs': total_commission + total_slippage,
        }

    def print_metrics(self, metrics: Dict):
        """列印績效指標"""

        print("\n" + "=" * 60)
        print("績效指標報告")
        print("=" * 60)

        # 收益指標
        print("\n### 收益指標 ###")
        print(f"總收益率: {metrics.get('total_return', 0)*100:.2f}%")
        print(f"年化收益率: {metrics.get('annualized_return', 0)*100:.2f}%")
        print(f"最終權益: ${metrics.get('final_equity', 0):,.2f}")
        print(f"最高權益: ${metrics.get('peak_equity', 0):,.2f}")

        # 風險指標
        print("\n### 風險指標 ###")
        print(f"最大回撤: {metrics.get('max_drawdown', 0)*100:.2f}%")
        print(f"最大回撤期間: {metrics.get('max_drawdown_duration_days', 0)} 天")
        print(f"年化波動率: {metrics.get('volatility', 0)*100:.2f}%")

        # 風險調整後收益
        print("\n### 風險調整後收益 ###")
        print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}")
        print(f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.3f}")
        print(f"Calmar Ratio: {metrics.get('calmar_ratio', 0):.3f}")

        # 交易統計
        if 'total_trades' in metrics:
            print("\n### 交易統計 ###")
            print(f"總交易次數: {metrics.get('total_trades', 0)}")
            print(f"平倉交易: {metrics.get('closed_trades', 0)}")
            print(f"獲利交易: {metrics.get('winning_trades', 0)}")
            print(f"虧損交易: {metrics.get('losing_trades', 0)}")
            print(f"勝率: {metrics.get('win_rate', 0)*100:.2f}%")
            print(f"平均獲利: ${metrics.get('avg_win', 0):.2f}")
            print(f"平均虧損: ${metrics.get('avg_loss', 0):.2f}")
            print(f"盈虧比: {metrics.get('profit_factor', 0):.3f}")
            print(f"平均每筆交易: ${metrics.get('avg_trade_pnl', 0):.2f}")
            print(f"總手續費: ${metrics.get('total_commission', 0):.2f}")
            print(f"總滑價: ${metrics.get('total_slippage', 0):.2f}")
            print(f"總成本: ${metrics.get('total_costs', 0):.2f}")

        print("=" * 60)
