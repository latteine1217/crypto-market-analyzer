"""
策略基類

職責：
- 定義策略介面
- 接收市場資料與特徵
- 產生交易信號
"""
import pandas as pd
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from loguru import logger


@dataclass
class Signal:
    """交易信號"""
    timestamp: pd.Timestamp
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    quantity: Optional[float] = None  # None 表示使用預設倉位
    confidence: float = 1.0  # 信心分數 0-1
    reason: str = ""  # 信號原因


class StrategyBase(ABC):
    """策略基類"""

    def __init__(self, name: str, **params):
        """
        初始化策略

        Args:
            name: 策略名稱
            **params: 策略參數
        """
        self.name = name
        self.params = params

        # 內部狀態
        self.current_position = 0.0  # 當前持倉
        self.signals_history: List[Signal] = []

        logger.info(f"策略初始化：{name}")
        logger.info(f"策略參數：{params}")

    @abstractmethod
    def on_data(
        self,
        timestamp: pd.Timestamp,
        data: pd.Series,
        features: Optional[pd.Series] = None
    ) -> Optional[Signal]:
        """
        接收新資料並產生信號

        Args:
            timestamp: 時間戳
            data: 市場資料（OHLCV）
            features: 特徵資料

        Returns:
            交易信號（如果有）
        """
        pass

    @abstractmethod
    def initialize(self):
        """策略初始化（在回測開始前呼叫）"""
        pass

    @abstractmethod
    def finalize(self):
        """策略結束（在回測結束後呼叫）"""
        pass

    def update_position(self, quantity: float):
        """更新當前持倉"""
        self.current_position = quantity

    def record_signal(self, signal: Signal):
        """記錄信號"""
        self.signals_history.append(signal)

    def get_signals_df(self) -> pd.DataFrame:
        """取得信號歷史 DataFrame"""
        if not self.signals_history:
            return pd.DataFrame()

        signals_data = [
            {
                'timestamp': s.timestamp,
                'symbol': s.symbol,
                'action': s.action,
                'quantity': s.quantity,
                'confidence': s.confidence,
                'reason': s.reason
            }
            for s in self.signals_history
        ]

        df = pd.DataFrame(signals_data)
        df.set_index('timestamp', inplace=True)
        return df

    def get_param(self, key: str, default=None):
        """取得策略參數"""
        return self.params.get(key, default)


class BuyAndHoldStrategy(StrategyBase):
    """買入持有策略（基準策略）"""

    def __init__(self, **params):
        super().__init__(name="BuyAndHold", **params)
        self.has_bought = False

    def initialize(self):
        """初始化"""
        self.has_bought = False
        logger.info("BuyAndHold 策略初始化完成")

    def on_data(
        self,
        timestamp: pd.Timestamp,
        data: pd.Series,
        features: Optional[pd.Series] = None
    ) -> Optional[Signal]:
        """
        第一個 bar 買入，之後持有
        """
        if not self.has_bought:
            self.has_bought = True
            return Signal(
                timestamp=timestamp,
                symbol=data.get('symbol', 'UNKNOWN'),
                action='buy',
                quantity=None,  # 使用預設倉位
                confidence=1.0,
                reason="初始買入"
            )

        return Signal(
            timestamp=timestamp,
            symbol=data.get('symbol', 'UNKNOWN'),
            action='hold',
            reason="持有"
        )

    def finalize(self):
        """結束"""
        logger.info(f"BuyAndHold 策略完成，共產生 {len(self.signals_history)} 個信號")


class MovingAverageCrossStrategy(StrategyBase):
    """均線交叉策略"""

    def __init__(self, fast_period: int = 10, slow_period: int = 30, **params):
        super().__init__(name="MA_Cross", fast_period=fast_period, slow_period=slow_period, **params)
        self.fast_period = fast_period
        self.slow_period = slow_period

        # 用於儲存歷史資料計算均線
        self.price_history: List[float] = []

    def initialize(self):
        """初始化"""
        self.price_history = []
        logger.info(f"MA_Cross 策略初始化：快線 {self.fast_period}, 慢線 {self.slow_period}")

    def on_data(
        self,
        timestamp: pd.Timestamp,
        data: pd.Series,
        features: Optional[pd.Series] = None
    ) -> Optional[Signal]:
        """
        均線交叉策略邏輯：
        - 快線上穿慢線：買入
        - 快線下穿慢線：賣出
        """
        # 優先使用特徵中的均線（如果有）
        if features is not None:
            fast_ma_key = f'sma_{self.fast_period}'
            slow_ma_key = f'sma_{self.slow_period}'

            if fast_ma_key in features and slow_ma_key in features:
                fast_ma = features[fast_ma_key]
                slow_ma = features[slow_ma_key]

                # 檢查是否有足夠的歷史資料計算交叉
                if pd.isna(fast_ma) or pd.isna(slow_ma):
                    return Signal(
                        timestamp=timestamp,
                        symbol=data.get('symbol', 'UNKNOWN'),
                        action='hold',
                        reason="等待均線數據"
                    )

                # 判斷交叉
                # 需要前一期的資料來判斷是否交叉，這裡簡化為直接比較
                if fast_ma > slow_ma and self.current_position <= 0:
                    return Signal(
                        timestamp=timestamp,
                        symbol=data.get('symbol', 'UNKNOWN'),
                        action='buy',
                        confidence=0.8,
                        reason=f"快線({fast_ma:.2f}) > 慢線({slow_ma:.2f})"
                    )
                elif fast_ma < slow_ma and self.current_position > 0:
                    return Signal(
                        timestamp=timestamp,
                        symbol=data.get('symbol', 'UNKNOWN'),
                        action='sell',
                        confidence=0.8,
                        reason=f"快線({fast_ma:.2f}) < 慢線({slow_ma:.2f})"
                    )

        # 如果特徵中沒有均線，返回持有
        return Signal(
            timestamp=timestamp,
            symbol=data.get('symbol', 'UNKNOWN'),
            action='hold',
            reason="無均線數據"
        )

    def finalize(self):
        """結束"""
        logger.info(f"MA_Cross 策略完成，共產生 {len(self.signals_history)} 個信號")
