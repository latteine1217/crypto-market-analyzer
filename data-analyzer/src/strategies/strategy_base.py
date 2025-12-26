"""
策略基類
定義統一的策略介面

規則：
1. 策略只看經過清洗與標準化的資料
2. 回測環境必須嚴格避免未來資訊
3. 所有策略結果都需可重現
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from enum import Enum
import pandas as pd


class SignalType(Enum):
    """信號類型"""
    LONG = 1
    SHORT = -1
    EXIT = 0
    HOLD = None


class StrategyBase(ABC):
    """
    策略基類

    所有策略都必須繼承此類並實作 generate_signals 方法
    """

    def __init__(self, name: str, params: Optional[Dict] = None):
        """
        初始化策略

        Args:
            name: 策略名稱
            params: 策略參數
        """
        self.name = name
        self.params = params or {}

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成交易信號

        Args:
            data: 清洗後的 OHLCV 資料（包含特徵）

        Returns:
            信號序列（索引與 data 相同）
            值為 SignalType: LONG(1), SHORT(-1), EXIT(0), HOLD(None)

        注意：
            - 不允許使用 t+1 的資料決定 t 時點的交易決策
            - 所有計算必須基於當前及之前的資料
        """
        pass

    def validate_params(self) -> bool:
        """
        驗證策略參數

        Returns:
            參數是否有效
        """
        return True

    def get_required_features(self) -> List[str]:
        """
        獲取策略所需特徵列表

        Returns:
            特徵名稱列表
        """
        return []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', params={self.params})"
