"""
回測框架

模組：
- portfolio: 投資組合管理
- executor: 交易執行模擬
- metrics: 績效指標計算
- strategy: 策略基類
- engine: 回測引擎
- visualizer: 視覺化工具
"""
from .portfolio import Portfolio
from .executor import OrderExecutor
from .metrics import PerformanceMetrics
from .strategy import StrategyBase
from .engine import BacktestEngine
from .visualizer import BacktestVisualizer

__all__ = [
    'Portfolio',
    'OrderExecutor',
    'PerformanceMetrics',
    'StrategyBase',
    'BacktestEngine',
    'BacktestVisualizer',
]
