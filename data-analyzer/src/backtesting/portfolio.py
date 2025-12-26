"""
投資組合管理模組

職責：
- 記錄持倉、現金、總權益
- 處理訂單執行後的狀態更新
- 提供持倉查詢介面
- 記錄歷史權益曲線
"""
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class Position:
    """持倉資訊"""
    symbol: str
    quantity: float  # 持倉數量（正數=多頭，負數=空頭）
    avg_price: float  # 平均成本
    entry_time: pd.Timestamp = None

    @property
    def value(self) -> float:
        """持倉市值（以平均成本計算）"""
        return abs(self.quantity) * self.avg_price

    def unrealized_pnl(self, current_price: float) -> float:
        """未實現損益"""
        if self.quantity > 0:
            # 多頭
            return self.quantity * (current_price - self.avg_price)
        elif self.quantity < 0:
            # 空頭
            return abs(self.quantity) * (self.avg_price - current_price)
        else:
            return 0.0


@dataclass
class Trade:
    """交易記錄"""
    timestamp: pd.Timestamp
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: float
    commission: float
    slippage: float
    pnl: float = 0.0  # 實現損益（平倉時才有）


class Portfolio:
    """投資組合管理器"""

    def __init__(
        self,
        initial_capital: float,
        leverage: float = 1.0
    ):
        """
        初始化投資組合

        Args:
            initial_capital: 初始資金
            leverage: 槓桿倍數（1.0 = 無槓桿）
        """
        self.initial_capital = initial_capital
        self.leverage = leverage

        # 當前狀態
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}

        # 歷史記錄
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []

        logger.info(f"投資組合初始化：資金 ${initial_capital:,.2f}, 槓桿 {leverage}x")

    @property
    def total_equity(self) -> float:
        """總權益 = 現金 + 持倉市值"""
        positions_value = sum(pos.value for pos in self.positions.values())
        return self.cash + positions_value

    @property
    def buying_power(self) -> float:
        """可用購買力 = 現金 × 槓桿"""
        return self.cash * self.leverage

    def get_position(self, symbol: str) -> Optional[Position]:
        """取得特定標的的持倉"""
        return self.positions.get(symbol)

    def update_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        commission: float,
        slippage: float,
        timestamp: pd.Timestamp
    ) -> Trade:
        """
        更新持倉

        Args:
            symbol: 標的代碼
            side: 'buy' 或 'sell'
            quantity: 交易數量（正數）
            price: 成交價格
            commission: 手續費
            slippage: 滑價成本
            timestamp: 交易時間

        Returns:
            交易記錄
        """
        total_cost = commission + slippage

        if side == 'buy':
            # 買入
            cost = quantity * price + total_cost

            if cost > self.buying_power:
                raise ValueError(f"資金不足：需要 ${cost:,.2f}, 可用 ${self.buying_power:,.2f}")

            self.cash -= cost

            if symbol in self.positions:
                # 加倉
                pos = self.positions[symbol]
                total_quantity = pos.quantity + quantity
                total_value = pos.quantity * pos.avg_price + quantity * price
                pos.avg_price = total_value / total_quantity
                pos.quantity = total_quantity
            else:
                # 開倉
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=price,
                    entry_time=timestamp
                )

            pnl = 0.0

        else:  # sell
            # 賣出
            if symbol not in self.positions:
                raise ValueError(f"無持倉可賣：{symbol}")

            pos = self.positions[symbol]

            if quantity > pos.quantity:
                raise ValueError(f"賣出數量 ({quantity}) 超過持倉 ({pos.quantity})")

            # 計算實現損益
            pnl = quantity * (price - pos.avg_price) - total_cost

            # 更新現金
            self.cash += quantity * price - total_cost

            # 更新持倉
            pos.quantity -= quantity

            if pos.quantity == 0:
                # 完全平倉
                del self.positions[symbol]

        # 記錄交易
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            commission=commission,
            slippage=slippage,
            pnl=pnl
        )

        self.trades.append(trade)

        logger.debug(
            f"{side.upper()} {quantity} {symbol} @ ${price:.2f} "
            f"(手續費: ${commission:.2f}, 滑價: ${slippage:.2f}, "
            f"PnL: ${pnl:.2f})"
        )

        return trade

    def record_equity(self, timestamp: pd.Timestamp, market_prices: Dict[str, float]):
        """
        記錄權益曲線

        Args:
            timestamp: 時間戳
            market_prices: 各標的當前市價 {symbol: price}
        """
        # 計算未實現損益
        unrealized_pnl = 0.0
        for symbol, pos in self.positions.items():
            if symbol in market_prices:
                unrealized_pnl += pos.unrealized_pnl(market_prices[symbol])

        # 計算總權益（使用市價）
        positions_value = sum(
            abs(pos.quantity) * market_prices.get(pos.symbol, pos.avg_price)
            for pos in self.positions.values()
        )
        total_equity = self.cash + positions_value

        self.equity_curve.append({
            'timestamp': timestamp,
            'cash': self.cash,
            'positions_value': positions_value,
            'total_equity': total_equity,
            'unrealized_pnl': unrealized_pnl,
            'return': (total_equity - self.initial_capital) / self.initial_capital
        })

    def get_equity_curve_df(self) -> pd.DataFrame:
        """取得權益曲線 DataFrame"""
        if not self.equity_curve:
            return pd.DataFrame()

        df = pd.DataFrame(self.equity_curve)
        df.set_index('timestamp', inplace=True)
        return df

    def get_trades_df(self) -> pd.DataFrame:
        """取得交易記錄 DataFrame"""
        if not self.trades:
            return pd.DataFrame()

        trades_data = [
            {
                'timestamp': t.timestamp,
                'symbol': t.symbol,
                'side': t.side,
                'quantity': t.quantity,
                'price': t.price,
                'commission': t.commission,
                'slippage': t.slippage,
                'pnl': t.pnl
            }
            for t in self.trades
        ]

        df = pd.DataFrame(trades_data)
        df.set_index('timestamp', inplace=True)
        return df

    def get_summary(self) -> Dict:
        """取得投資組合摘要"""
        total_pnl = sum(t.pnl for t in self.trades)
        total_commission = sum(t.commission for t in self.trades)
        total_slippage = sum(t.slippage for t in self.trades)

        return {
            'initial_capital': self.initial_capital,
            'final_equity': self.total_equity,
            'cash': self.cash,
            'positions_count': len(self.positions),
            'total_trades': len(self.trades),
            'total_pnl': total_pnl,
            'total_return': (self.total_equity - self.initial_capital) / self.initial_capital,
            'total_commission': total_commission,
            'total_slippage': total_slippage,
            'net_pnl': total_pnl - total_commission - total_slippage
        }
