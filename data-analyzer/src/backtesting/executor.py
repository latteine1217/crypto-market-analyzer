"""
交易執行模擬器

職責：
- 模擬市價單執行
- 計算滑價（slippage）
- 計算手續費（commission）
- 檢查訂單合法性
"""
import pandas as pd
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class Order:
    """訂單資訊"""
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    order_type: str = 'market'  # 'market' or 'limit'
    limit_price: Optional[float] = None
    timestamp: Optional[pd.Timestamp] = None


@dataclass
class ExecutionResult:
    """執行結果"""
    success: bool
    executed_price: float = 0.0
    executed_quantity: float = 0.0
    commission: float = 0.0
    slippage_cost: float = 0.0
    message: str = ""


class OrderExecutor:
    """訂單執行器"""

    def __init__(
        self,
        commission_rate: float = 0.001,  # 0.1% 手續費
        slippage_rate: float = 0.0005,  # 0.05% 滑價
        min_order_value: float = 10.0,  # 最小訂單金額
    ):
        """
        初始化執行器

        Args:
            commission_rate: 手續費率（小數形式）
            slippage_rate: 滑價率（小數形式）
            min_order_value: 最小訂單金額
        """
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.min_order_value = min_order_value

        logger.info(
            f"訂單執行器初始化：手續費率 {commission_rate*100:.3f}%, "
            f"滑價率 {slippage_rate*100:.3f}%, "
            f"最小訂單 ${min_order_value:.2f}"
        )

    def execute_order(
        self,
        order: Order,
        current_price: float,
        current_bar: pd.Series
    ) -> ExecutionResult:
        """
        執行訂單

        Args:
            order: 訂單資訊
            current_price: 當前市價（通常使用 close）
            current_bar: 當前 K 線資料（用於滑價計算）

        Returns:
            執行結果
        """
        # 驗證訂單
        validation_result = self._validate_order(order, current_price)
        if not validation_result.success:
            return validation_result

        # 計算執行價格
        executed_price = self._calculate_execution_price(
            order, current_price, current_bar
        )

        # 計算手續費
        commission = self._calculate_commission(order.quantity, executed_price)

        # 計算滑價成本
        slippage_cost = self._calculate_slippage(
            order, current_price, executed_price
        )

        return ExecutionResult(
            success=True,
            executed_price=executed_price,
            executed_quantity=order.quantity,
            commission=commission,
            slippage_cost=slippage_cost,
            message="訂單執行成功"
        )

    def _validate_order(
        self,
        order: Order,
        current_price: float
    ) -> ExecutionResult:
        """驗證訂單"""

        # 檢查數量
        if order.quantity <= 0:
            return ExecutionResult(
                success=False,
                message=f"訂單數量必須大於 0：{order.quantity}"
            )

        # 檢查訂單金額
        order_value = order.quantity * current_price
        if order_value < self.min_order_value:
            return ExecutionResult(
                success=False,
                message=f"訂單金額 ${order_value:.2f} 低於最小金額 ${self.min_order_value:.2f}"
            )

        # 檢查限價單
        if order.order_type == 'limit' and order.limit_price is None:
            return ExecutionResult(
                success=False,
                message="限價單必須指定限價"
            )

        return ExecutionResult(success=True)

    def _calculate_execution_price(
        self,
        order: Order,
        current_price: float,
        current_bar: pd.Series
    ) -> float:
        """
        計算執行價格

        模擬滑價：
        - 買單：以當前 K 線的最高價附近成交
        - 賣單：以當前 K 線的最低價附近成交
        """
        if order.order_type == 'market':
            if order.side == 'buy':
                # 買單：使用高價 + 滑價
                high = current_bar.get('high', current_price)
                slippage = current_price * self.slippage_rate
                executed_price = min(high, current_price + slippage)
            else:  # sell
                # 賣單：使用低價 - 滑價
                low = current_bar.get('low', current_price)
                slippage = current_price * self.slippage_rate
                executed_price = max(low, current_price - slippage)

        else:  # limit order
            # 限價單：檢查是否能成交
            if order.side == 'buy':
                # 買單：市價必須低於或等於限價才能成交
                if current_price <= order.limit_price:
                    executed_price = min(current_price, order.limit_price)
                else:
                    executed_price = current_price  # 實際上不會成交，這裡簡化處理
            else:  # sell
                # 賣單：市價必須高於或等於限價才能成交
                if current_price >= order.limit_price:
                    executed_price = max(current_price, order.limit_price)
                else:
                    executed_price = current_price

        return executed_price

    def _calculate_commission(
        self,
        quantity: float,
        price: float
    ) -> float:
        """計算手續費"""
        return quantity * price * self.commission_rate

    def _calculate_slippage(
        self,
        order: Order,
        expected_price: float,
        executed_price: float
    ) -> float:
        """
        計算滑價成本

        滑價 = |執行價格 - 預期價格| × 數量
        """
        price_diff = abs(executed_price - expected_price)
        return price_diff * order.quantity

    def calculate_position_size(
        self,
        available_capital: float,
        price: float,
        risk_fraction: float = 1.0
    ) -> float:
        """
        計算倉位大小

        Args:
            available_capital: 可用資金
            price: 當前價格
            risk_fraction: 風險比例（0-1）

        Returns:
            可購買數量
        """
        if price <= 0:
            return 0.0

        # 考慮手續費後的可用資金
        usable_capital = available_capital * risk_fraction
        cost_per_unit = price * (1 + self.commission_rate + self.slippage_rate)

        quantity = usable_capital / cost_per_unit

        return quantity

    def get_total_cost(
        self,
        quantity: float,
        price: float,
        side: str
    ) -> Tuple[float, float, float]:
        """
        計算總成本

        Args:
            quantity: 數量
            price: 價格
            side: 'buy' or 'sell'

        Returns:
            (總成本, 手續費, 滑價成本)
        """
        base_value = quantity * price
        commission = self._calculate_commission(quantity, price)

        # 簡化滑價計算
        if side == 'buy':
            slippage_cost = base_value * self.slippage_rate
        else:
            slippage_cost = base_value * self.slippage_rate

        total_cost = base_value + commission + slippage_cost

        return total_cost, commission, slippage_cost
