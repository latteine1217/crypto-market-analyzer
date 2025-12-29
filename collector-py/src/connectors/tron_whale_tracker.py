"""
Tron (TRX) 大額交易追蹤器

使用 TronGrid API 或 TronScan API 追蹤 Tron 主網和 TRC-20 代幣的大額交易
"""
import aiohttp
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from loguru import logger

from .blockchain_base import (
    BlockchainConnector,
    WhaleTransaction,
    TransactionDirection
)


class TronWhaleTracker(BlockchainConnector):
    """Tron 大額交易追蹤器"""

    # 常用 TRC-20 代幣合約地址
    TOKEN_CONTRACTS = {
        'USDT': 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t',  # Tron USDT
        'USDC': 'TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8',
        'USDD': 'TPYmHEhy5n8TCEfYGqW2rPxsghSfzghPDn',  # Decentralized USD
        'TUSD': 'TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4',
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 Tron 追蹤器

        Args:
            api_key: TronScan API Key（可選）
            config: 配置字典
        """
        super().__init__('TRX', api_key, config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.price_cache: Dict[str, tuple[Decimal, datetime]] = {}
        self.price_cache_ttl = 300

        # TronGrid API（無需 key）
        self.grid_url = self.config.get('grid_url', 'https://api.trongrid.io')

    async def _get_session(self) -> aiohttp.ClientSession:
        """獲取或創建 aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """關閉連接"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _call_tronscan_api(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        調用 TronScan API

        Args:
            endpoint: API 端點
            params: 請求參數

        Returns:
            API 響應
        """
        session = await self._get_session()
        url = f"{self.api_url}/{endpoint}"

        try:
            async with session.get(url, params=params, timeout=self.timeout) as response:
                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"TronScan API 請求失敗: {e}")
            return {}

    async def _call_trongrid_api(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        調用 TronGrid API

        Args:
            endpoint: API 端點
            params: 請求參數

        Returns:
            API 響應
        """
        session = await self._get_session()
        url = f"{self.grid_url}/{endpoint}"

        try:
            headers = {
                'TRON-PRO-API-KEY': self.api_key
            } if self.api_key else {}

            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout
            ) as response:
                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"TronGrid API 請求失敗: {e}")
            return {}

    async def get_recent_transactions(
        self,
        address: Optional[str] = None,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[WhaleTransaction]:
        """獲取最近的交易"""
        if not address:
            logger.warning("Tron 追蹤器需要指定地址才能查詢交易")
            return []

        # 使用 TronScan API 獲取地址交易
        return await self._get_address_transactions(address, limit)

    async def _get_address_transactions(
        self,
        address: str,
        limit: int
    ) -> List[WhaleTransaction]:
        """獲取地址的所有交易（TRX + TRC-20）"""
        transactions = []

        # 獲取 TRX 轉帳
        trx_txs = await self._get_trx_transactions(address, limit)
        transactions.extend(trx_txs)

        # 獲取 TRC-20 代幣轉帳
        token_txs = await self._get_trc20_transactions(address, limit)
        transactions.extend(token_txs)

        # 排序並限制數量
        transactions.sort(key=lambda tx: tx.timestamp, reverse=True)
        return transactions[:limit]

    async def _get_trx_transactions(
        self,
        address: str,
        limit: int
    ) -> List[WhaleTransaction]:
        """獲取 TRX 主幣轉帳（使用 TronScan）"""
        params = {
            'address': address,
            'limit': limit,
            'start': 0,
            'sort': '-timestamp'
        }

        data = await self._call_tronscan_api('transaction', params)
        txs_data = data.get('data', [])

        transactions = []
        for tx_data in txs_data:
            try:
                # 只處理 TRX 轉帳
                if tx_data.get('contractType') == 1:  # TransferContract
                    tx = await self._parse_trx_transaction(tx_data)
                    if tx:
                        transactions.append(tx)
            except Exception as e:
                logger.error(f"解析 TRX 交易失敗: {e}")

        return transactions

    async def _get_trc20_transactions(
        self,
        address: str,
        limit: int
    ) -> List[WhaleTransaction]:
        """獲取 TRC-20 代幣轉帳"""
        params = {
            'relatedAddress': address,
            'limit': limit,
            'start': 0,
            'sort': '-timestamp'
        }

        data = await self._call_tronscan_api('contract/events', params)
        txs_data = data.get('data', [])

        transactions = []
        for tx_data in txs_data:
            try:
                tx = await self._parse_trc20_transaction(tx_data)
                if tx:
                    transactions.append(tx)
            except Exception as e:
                logger.error(f"解析 TRC-20 交易失敗: {e}")

        return transactions

    async def _parse_trx_transaction(self, tx_data: Dict) -> Optional[WhaleTransaction]:
        """解析 TRX 交易"""
        # TRX 使用 sun 單位（1 TRX = 10^6 sun）
        amount_sun = tx_data.get('contractData', {}).get('amount', 0)
        amount = Decimal(amount_sun) / Decimal(10 ** 6)

        is_whale, is_anomaly = await self.is_large_transaction(amount, None)

        if not is_whale:
            return None

        tx = WhaleTransaction(
            blockchain='TRX',
            tx_hash=tx_data.get('hash', ''),
            timestamp=datetime.fromtimestamp(tx_data.get('timestamp', 0) / 1000),
            block_number=tx_data.get('block'),
            from_address=tx_data.get('ownerAddress', ''),
            to_address=tx_data.get('toAddress', ''),
            amount=amount,
            token_symbol=None,  # TRX 主幣
            is_whale=is_whale,
            is_anomaly=is_anomaly,
        )

        return tx

    async def _parse_trc20_transaction(self, tx_data: Dict) -> Optional[WhaleTransaction]:
        """解析 TRC-20 代幣交易"""
        # TRC-20 轉帳事件
        result = tx_data.get('result', {})

        # 獲取代幣資訊
        token_info = tx_data.get('tokenInfo', {})
        token_symbol = token_info.get('tokenAbbr', '')
        token_decimal = int(token_info.get('tokenDecimal', 6))

        # 金額（從 result 中獲取）
        amount_raw = int(result.get('0', 0), 16) if isinstance(result.get('0'), str) else result.get('0', 0)
        amount = Decimal(amount_raw) / Decimal(10 ** token_decimal)

        is_whale, is_anomaly = await self.is_large_transaction(amount, token_symbol)

        if not is_whale:
            return None

        tx = WhaleTransaction(
            blockchain='TRX',
            tx_hash=tx_data.get('transactionId', ''),
            timestamp=datetime.fromtimestamp(tx_data.get('timestamp', 0) / 1000),
            block_number=tx_data.get('block'),
            from_address=result.get('from_address', ''),
            to_address=result.get('to_address', ''),
            amount=amount,
            token_symbol=token_symbol,
            token_contract=tx_data.get('contractAddress', ''),
            is_whale=is_whale,
            is_anomaly=is_anomaly,
        )

        return tx

    async def get_transaction_by_hash(self, tx_hash: str) -> Optional[WhaleTransaction]:
        """根據交易哈希獲取交易詳情"""
        data = await self._call_tronscan_api('transaction-info', {'hash': tx_hash})

        if not data:
            return None

        # 根據交易類型解析
        if data.get('contractType') == 1:
            return await self._parse_trx_transaction(data)
        else:
            # TRC-20 需要額外處理
            return None

    async def get_address_balance(self, address: str) -> Decimal:
        """獲取 TRX 餘額（使用 TronGrid）"""
        endpoint = f"v1/accounts/{address}"
        data = await self._call_trongrid_api(endpoint)

        if data and 'data' in data:
            balance_sun = data['data'][0].get('balance', 0)
            return Decimal(balance_sun) / Decimal(10 ** 6)

        return Decimal('0')

    async def is_large_transaction(
        self,
        amount: Decimal,
        token_symbol: Optional[str] = None
    ) -> tuple[bool, bool]:
        """判斷是否為大額交易"""
        symbol = token_symbol or 'TRX'

        # TRX 門檻
        whale_amount = self.whale_threshold.get('amount', 5000000)  # 5M TRX
        anomaly_amount = self.anomaly_threshold.get('amount', 50000000)  # 50M TRX

        is_whale = amount >= Decimal(whale_amount)
        is_anomaly = amount >= Decimal(anomaly_amount)

        return is_whale, is_anomaly

    async def get_usd_price(self, token_symbol: Optional[str] = None) -> Decimal:
        """獲取 TRX 或 TRC-20 代幣的美元價格"""
        symbol = (token_symbol or 'TRX').lower()

        # 檢查快取
        if symbol in self.price_cache:
            price, timestamp = self.price_cache[symbol]
            if datetime.now() - timestamp < timedelta(seconds=self.price_cache_ttl):
                return price

        coingecko_ids = {
            'trx': 'tron',
            'usdt': 'tether',
            'usdc': 'usd-coin',
            'usdd': 'usdd',
            'tusd': 'true-usd',
        }

        coin_id = coingecko_ids.get(symbol, symbol)

        try:
            session = await self._get_session()
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd'
            }

            async with session.get(url, params=params, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()

                price = Decimal(str(data.get(coin_id, {}).get('usd', 0)))
                self.price_cache[symbol] = (price, datetime.now())

                return price

        except Exception as e:
            logger.error(f"獲取 {symbol} 價格失敗: {e}")

            if symbol in ['usdt', 'usdc', 'usdd', 'tusd']:
                return Decimal('1.0')

            return Decimal('0')
