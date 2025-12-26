"""
回測引擎核心

職責：
- 整合所有回測模組
- 管理時間循環
- 資料餵送與特徵計算
- 執行交易與記錄結果
"""
import pandas as pd
from typing import Dict, Optional
from loguru import logger

from .portfolio import Portfolio
from .executor import OrderExecutor, Order
from .metrics import PerformanceMetrics
from .strategy import StrategyBase


class BacktestEngine:
    """回測引擎"""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
        risk_free_rate: float = 0.0,
        position_size_pct: float = 0.95,  # 每次使用 95% 資金
    ):
        """
        初始化回測引擎

        Args:
            initial_capital: 初始資金
            commission_rate: 手續費率
            slippage_rate: 滑價率
            risk_free_rate: 無風險利率
            position_size_pct: 倉位比例（0-1）
        """
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct

        # 初始化模組
        self.portfolio = Portfolio(initial_capital)
        self.executor = OrderExecutor(
            commission_rate=commission_rate,
            slippage_rate=slippage_rate
        )
        self.metrics = PerformanceMetrics(risk_free_rate=risk_free_rate)

        # 回測狀態
        self.strategy: Optional[StrategyBase] = None
        self.current_bar_idx = 0

        logger.info("=" * 60)
        logger.info("回測引擎初始化")
        logger.info(f"初始資金: ${initial_capital:,.2f}")
        logger.info(f"手續費率: {commission_rate*100:.3f}%")
        logger.info(f"滑價率: {slippage_rate*100:.3f}%")
        logger.info(f"倉位比例: {position_size_pct*100:.1f}%")
        logger.info("=" * 60)

    def run(
        self,
        data: pd.DataFrame,
        strategy: StrategyBase,
        features: Optional[pd.DataFrame] = None,
        symbol: str = 'UNKNOWN'
    ) -> Dict:
        """
        執行回測

        Args:
            data: 市場資料（OHLCV DataFrame）
            strategy: 策略實例
            features: 特徵資料（可選）
            symbol: 標的代碼

        Returns:
            回測結果字典
        """
        logger.info("\n" + "=" * 60)
        logger.info(f"開始回測：{strategy.name}")
        logger.info(f"資料期間：{data.index[0]} 至 {data.index[-1]}")
        logger.info(f"資料筆數：{len(data)}")
        logger.info("=" * 60)

        self.strategy = strategy
        self.strategy.initialize()

        # 確保資料與特徵對齊
        if features is not None:
            # 只使用有特徵的時間點
            common_index = data.index.intersection(features.index)
            data = data.loc[common_index]
            features = features.loc[common_index]
            logger.info(f"資料與特徵對齊後筆數：{len(data)}")

        # 時間循環
        for idx, (timestamp, bar) in enumerate(data.iterrows()):
            self.current_bar_idx = idx

            # 取得當前特徵
            current_features = None
            if features is not None:
                current_features = features.loc[timestamp]

            # 加入 symbol 到 bar 資料
            bar = bar.copy()
            if 'symbol' not in bar:
                bar['symbol'] = symbol

            # 策略產生信號
            signal = strategy.on_data(timestamp, bar, current_features)

            if signal is None:
                continue

            # 記錄信號
            strategy.record_signal(signal)

            # 執行信號
            if signal.action == 'buy':
                self._execute_buy(signal, bar, timestamp)
            elif signal.action == 'sell':
                self._execute_sell(signal, bar, timestamp)
            # 'hold' 不執行任何動作

            # 記錄權益曲線
            market_prices = {symbol: bar['close']}
            self.portfolio.record_equity(timestamp, market_prices)

        # 策略結束
        strategy.finalize()

        # 計算績效指標
        equity_curve = self.portfolio.get_equity_curve_df()
        trades = self.portfolio.get_trades_df()

        metrics = self.metrics.calculate_all_metrics(
            equity_curve,
            trades,
            self.initial_capital
        )

        # 加入投資組合摘要
        portfolio_summary = self.portfolio.get_summary()
        metrics.update(portfolio_summary)

        logger.info("\n" + "=" * 60)
        logger.info("回測完成")
        logger.info("=" * 60)

        # 列印績效
        self.metrics.print_metrics(metrics)

        return {
            'metrics': metrics,
            'equity_curve': equity_curve,
            'trades': trades,
            'signals': strategy.get_signals_df(),
            'portfolio': self.portfolio,
            'strategy': strategy,
        }

    def _execute_buy(
        self,
        signal,
        bar: pd.Series,
        timestamp: pd.Timestamp
    ):
        """執行買入"""
        # 檢查是否已有持倉
        position = self.portfolio.get_position(signal.symbol)
        if position is not None and position.quantity > 0:
            logger.debug(f"已有持倉，跳過買入信號：{signal.symbol}")
            return

        # 計算倉位大小
        available_cash = self.portfolio.cash * self.position_size_pct
        current_price = bar['close']

        quantity = self.executor.calculate_position_size(
            available_cash,
            current_price,
            risk_fraction=1.0
        )

        if quantity <= 0:
            logger.warning(f"資金不足，無法買入：可用 ${available_cash:.2f}")
            return

        # 建立訂單
        order = Order(
            symbol=signal.symbol,
            side='buy',
            quantity=quantity,
            timestamp=timestamp
        )

        # 執行訂單
        exec_result = self.executor.execute_order(order, current_price, bar)

        if not exec_result.success:
            logger.warning(f"訂單執行失敗：{exec_result.message}")
            return

        # 更新投資組合
        try:
            self.portfolio.update_position(
                symbol=signal.symbol,
                side='buy',
                quantity=exec_result.executed_quantity,
                price=exec_result.executed_price,
                commission=exec_result.commission,
                slippage=exec_result.slippage_cost,
                timestamp=timestamp
            )

            # 更新策略持倉
            self.strategy.update_position(exec_result.executed_quantity)

            logger.debug(
                f"買入 {exec_result.executed_quantity:.4f} {signal.symbol} "
                f"@ ${exec_result.executed_price:.2f}"
            )

        except Exception as e:
            logger.error(f"更新投資組合失敗：{e}")

    def _execute_sell(
        self,
        signal,
        bar: pd.Series,
        timestamp: pd.Timestamp
    ):
        """執行賣出"""
        # 檢查持倉
        position = self.portfolio.get_position(signal.symbol)
        if position is None or position.quantity <= 0:
            logger.debug(f"無持倉，跳過賣出信號：{signal.symbol}")
            return

        # 全部賣出
        quantity = position.quantity
        current_price = bar['close']

        # 建立訂單
        order = Order(
            symbol=signal.symbol,
            side='sell',
            quantity=quantity,
            timestamp=timestamp
        )

        # 執行訂單
        exec_result = self.executor.execute_order(order, current_price, bar)

        if not exec_result.success:
            logger.warning(f"訂單執行失敗：{exec_result.message}")
            return

        # 更新投資組合
        try:
            self.portfolio.update_position(
                symbol=signal.symbol,
                side='sell',
                quantity=exec_result.executed_quantity,
                price=exec_result.executed_price,
                commission=exec_result.commission,
                slippage=exec_result.slippage_cost,
                timestamp=timestamp
            )

            # 更新策略持倉
            self.strategy.update_position(0)

            logger.debug(
                f"賣出 {exec_result.executed_quantity:.4f} {signal.symbol} "
                f"@ ${exec_result.executed_price:.2f}, "
                f"PnL: ${exec_result.executed_quantity * (exec_result.executed_price - position.avg_price):.2f}"
            )

        except Exception as e:
            logger.error(f"更新投資組合失敗：{e}")
