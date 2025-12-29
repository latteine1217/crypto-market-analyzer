"""
區塊鏈連接器基礎類別

提供統一的介面給所有區塊鏈連接器實作
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum


class TransactionDirection(Enum):
    """交易方向"""
    INFLOW = "inflow"      # 流入交易所
    OUTFLOW = "outflow"    # 流出交易所
    NEUTRAL = "neutral"    # 非交易所相關


@dataclass
class WhaleTransaction:
    """
    大額交易數據類別

    統一表示來自不同區塊鏈的大額交易
    """
    # 基本資訊
    blockchain: str                          # BTC, ETH, BSC, TRX
    tx_hash: str                              # 交易哈希
    timestamp: datetime                       # 交易時間
    block_number: Optional[int] = None        # 區塊高度

    # 交易方
    from_address: str = ""                    # 發送地址
    to_address: str = ""                      # 接收地址

    # 金額資訊
    amount: Decimal = Decimal('0')            # 原始金額
    amount_usd: Optional[Decimal] = None      # 美元價值
    token_symbol: Optional[str] = None        # 代幣符號（None 為主幣）
    token_contract: Optional[str] = None      # 代幣合約地址

    # 交易所標記
    is_exchange_inflow: bool = False          # 流入交易所
    is_exchange_outflow: bool = False         # 流出交易所
    exchange_name: Optional[str] = None       # 交易所名稱
    direction: TransactionDirection = TransactionDirection.NEUTRAL

    # 分類標籤
    is_whale: bool = True                     # 是否為巨鯨交易
    is_anomaly: bool = False                  # 是否為異常超大額

    # 元數據
    gas_used: Optional[int] = None            # Gas 使用量
    gas_price: Optional[int] = None           # Gas 價格
    tx_fee: Optional[Decimal] = None          # 交易手續費

    # 額外資訊
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式，用於資料庫插入"""
        return {
            'blockchain': self.blockchain,
            'tx_hash': self.tx_hash,
            'timestamp': self.timestamp,
            'block_number': self.block_number,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'amount': float(self.amount),
            'amount_usd': float(self.amount_usd) if self.amount_usd else None,
            'token_symbol': self.token_symbol,
            'token_contract': self.token_contract,
            'is_exchange_inflow': self.is_exchange_inflow,
            'is_exchange_outflow': self.is_exchange_outflow,
            'exchange_name': self.exchange_name,
            'is_whale': self.is_whale,
            'is_anomaly': self.is_anomaly,
            'gas_used': self.gas_used,
            'gas_price': self.gas_price,
            'tx_fee': float(self.tx_fee) if self.tx_fee else None,
        }


@dataclass
class WhaleAddress:
    """巨鯨地址數據類別"""
    blockchain: str
    address: str
    label: Optional[str] = None
    address_type: Optional[str] = None        # exchange, whale, contract, etc.
    is_exchange: bool = False
    exchange_name: Optional[str] = None

    # 統計資訊（由系統自動計算）
    total_tx_count: int = 0
    total_inflow: Decimal = Decimal('0')
    total_outflow: Decimal = Decimal('0')
    current_balance: Optional[Decimal] = None

    first_seen: Optional[datetime] = None
    last_active: Optional[datetime] = None


class BlockchainConnector(ABC):
    """
    區塊鏈連接器抽象基類

    所有具體的區塊鏈連接器都必須繼承此類並實作抽象方法
    """

    def __init__(
        self,
        blockchain: str,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化連接器

        Args:
            blockchain: 區塊鏈名稱（BTC, ETH, BSC, TRX）
            api_key: API 密鑰
            config: 配置字典
        """
        self.blockchain = blockchain
        self.api_key = api_key
        self.config = config or {}

        # 從配置中提取常用參數
        self.api_url = self.config.get('api_url', '')
        self.rate_limit = self.config.get('rate_limit', 5)
        self.timeout = self.config.get('timeout', 30)

        # 大額交易門檻
        self.whale_threshold = self.config.get('whale_threshold', {})
        self.anomaly_threshold = self.config.get('anomaly_threshold', {})

    @abstractmethod
    async def get_recent_transactions(
        self,
        address: Optional[str] = None,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[WhaleTransaction]:
        """
        獲取最近的交易

        Args:
            address: 特定地址（None 表示全網）
            limit: 返回交易數量限制
            start_time: 開始時間
            end_time: 結束時間

        Returns:
            WhaleTransaction 列表
        """
        pass

    @abstractmethod
    async def get_transaction_by_hash(self, tx_hash: str) -> Optional[WhaleTransaction]:
        """
        根據交易哈希獲取交易詳情

        Args:
            tx_hash: 交易哈希

        Returns:
            WhaleTransaction 或 None
        """
        pass

    @abstractmethod
    async def get_address_balance(self, address: str) -> Decimal:
        """
        獲取地址餘額

        Args:
            address: 區塊鏈地址

        Returns:
            餘額（Decimal）
        """
        pass

    @abstractmethod
    async def is_large_transaction(
        self,
        amount: Decimal,
        token_symbol: Optional[str] = None
    ) -> tuple[bool, bool]:
        """
        判斷是否為大額交易

        Args:
            amount: 交易金額
            token_symbol: 代幣符號（None 為主幣）

        Returns:
            (is_whale, is_anomaly) 元組
        """
        pass

    @abstractmethod
    async def get_usd_price(self, token_symbol: Optional[str] = None) -> Decimal:
        """
        獲取代幣/主幣的美元價格

        Args:
            token_symbol: 代幣符號（None 為主幣）

        Returns:
            美元價格
        """
        pass

    def is_exchange_address(
        self,
        address: str,
        exchange_addresses: Dict[str, str]
    ) -> tuple[bool, Optional[str]]:
        """
        檢查地址是否為交易所地址

        Args:
            address: 要檢查的地址
            exchange_addresses: 交易所地址映射 {address: exchange_name}

        Returns:
            (is_exchange, exchange_name) 元組
        """
        address_lower = address.lower()

        for ex_addr, ex_name in exchange_addresses.items():
            if ex_addr.lower() == address_lower:
                return True, ex_name

        return False, None

    def determine_transaction_direction(
        self,
        from_addr: str,
        to_addr: str,
        exchange_addresses: Dict[str, str]
    ) -> tuple[bool, bool, Optional[str], TransactionDirection]:
        """
        判斷交易方向（流入/流出交易所）

        Args:
            from_addr: 發送地址
            to_addr: 接收地址
            exchange_addresses: 交易所地址映射

        Returns:
            (is_inflow, is_outflow, exchange_name, direction)
        """
        from_is_exchange, from_exchange = self.is_exchange_address(
            from_addr, exchange_addresses
        )
        to_is_exchange, to_exchange = self.is_exchange_address(
            to_addr, exchange_addresses
        )

        # 流入交易所
        if to_is_exchange and not from_is_exchange:
            return True, False, to_exchange, TransactionDirection.INFLOW

        # 流出交易所
        if from_is_exchange and not to_is_exchange:
            return False, True, from_exchange, TransactionDirection.OUTFLOW

        # 交易所之間或非交易所相關
        return False, False, None, TransactionDirection.NEUTRAL

    async def enrich_transaction(
        self,
        tx: WhaleTransaction,
        exchange_addresses: Dict[str, str]
    ) -> WhaleTransaction:
        """
        豐富交易資訊（添加交易所標記、美元價值等）

        Args:
            tx: WhaleTransaction 對象
            exchange_addresses: 交易所地址映射

        Returns:
            豐富後的 WhaleTransaction
        """
        # 判斷交易方向
        is_inflow, is_outflow, ex_name, direction = self.determine_transaction_direction(
            tx.from_address,
            tx.to_address,
            exchange_addresses
        )

        tx.is_exchange_inflow = is_inflow
        tx.is_exchange_outflow = is_outflow
        tx.exchange_name = ex_name
        tx.direction = direction

        # 獲取美元價格（如果尚未設定）
        if tx.amount_usd is None:
            try:
                usd_price = await self.get_usd_price(tx.token_symbol)
                tx.amount_usd = tx.amount * usd_price
            except Exception as e:
                print(f"無法獲取美元價格: {e}")
                tx.amount_usd = None

        # 判斷是否為大額/異常交易
        is_whale, is_anomaly = await self.is_large_transaction(
            tx.amount,
            tx.token_symbol
        )
        tx.is_whale = is_whale
        tx.is_anomaly = is_anomaly

        return tx
