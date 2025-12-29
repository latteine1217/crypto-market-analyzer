"""
Bitcoin 大額交易追蹤器

使用 Blockchain.com API 追蹤 Bitcoin 主網的大額交易
Bitcoin 使用 UTXO 模型，與 EVM 鏈（ETH/BSC）架構不同
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


class BitcoinWhaleTracker(BlockchainConnector):
    """Bitcoin 大額交易追蹤器"""

    def __init__(
        self,
        api_key: Optional[str] = None,  # Blockchain.com 公開 API 不需要 key
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 Bitcoin 追蹤器

        Args:
            api_key: API Key（Blockchain.com 不需要）
            config: 配置字典
        """
        super().__init__('BTC', api_key, config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.price_cache: Optional[tuple[Decimal, datetime]] = None
        self.price_cache_ttl = 300

        # Blockchair API 作為備用
        self.blockchair_url = self.config.get('blockchair_url',
                                               'https://api.blockchair.com/bitcoin')

    async def _get_session(self) -> aiohttp.ClientSession:
        """獲取或創建 aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """關閉連接"""
        if self.session and not self.session.closed:
            await self.session.close()

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
            address: Bitcoin 地址（可選）
            limit: 返回交易數量
            start_time: 開始時間（暫不支持）
            end_time: 結束時間（暫不支持）

        Returns:
            WhaleTransaction 列表
        """
        if address:
            return await self._get_address_transactions(address, limit)
        else:
            # 獲取全網最新大額交易（使用 Blockchair）
            return await self._get_large_transactions_global(limit)

    async def _get_address_transactions(
        self,
        address: str,
        limit: int
    ) -> List[WhaleTransaction]:
        """
        獲取特定地址的交易

        使用 Blockchain.com API
        """
        session = await self._get_session()
        url = f"{self.api_url}/rawaddr/{address}"

        try:
            params = {
                'limit': min(limit, 50),  # Blockchain.com 限制
                'offset': 0
            }

            async with session.get(url, params=params, timeout=self.timeout) as response:
                response.raise_for_status()
                data = await response.json()

                txs_data = data.get('txs', [])
                transactions = []

                for tx_data in txs_data:
                    try:
                        tx = await self._parse_transaction(tx_data, address)
                        if tx:
                            transactions.append(tx)
                    except Exception as e:
                        logger.error(f"解析 BTC 交易失敗: {e}")

                return transactions

        except aiohttp.ClientError as e:
            logger.error(f"Blockchain.com API 請求失敗: {e}")
            return []

    async def _get_large_transactions_global(self, limit: int) -> List[WhaleTransaction]:
        """
        獲取全網大額交易

        使用 Blockchair API（更強大但有速率限制）
        """
        session = await self._get_session()
        url = f"{self.blockchair_url}/transactions"

        try:
            # Blockchair 支持按金額排序
            params = {
                'limit': limit,
                's': 'output_total(desc)',  # 按輸出總額降序
                'q': f'output_total_usd({int(self.whale_threshold.get("usd_value", 2000000))}..)'
            }

            async with session.get(url, params=params, timeout=self.timeout) as response:
                response.raise_for_status()
                data = await response.json()

                txs_data = data.get('data', [])
                transactions = []

                for tx_data in txs_data:
                    try:
                        tx = await self._parse_blockchair_transaction(tx_data)
                        if tx:
                            transactions.append(tx)
                    except Exception as e:
                        logger.error(f"解析 Blockchair 交易失敗: {e}")

                return transactions

        except aiohttp.ClientError as e:
            logger.error(f"Blockchair API 請求失敗: {e}")
            return []

    async def _parse_transaction(
        self,
        tx_data: Dict,
        query_address: str
    ) -> Optional[WhaleTransaction]:
        """
        解析 Blockchain.com API 返回的交易

        Bitcoin UTXO 模型較複雜，需要計算輸入輸出
        """
        # 計算總輸出金額（satoshi -> BTC）
        total_output = sum([out.get('value', 0) for out in tx_data.get('out', [])])
        amount = Decimal(total_output) / Decimal(10 ** 8)

        # 檢查是否為大額交易
        is_whale, is_anomaly = await self.is_large_transaction(amount, None)

        if not is_whale:
            return None

        # 判斷交易方向（相對於查詢地址）
        from_address = ''
        to_address = ''

        inputs = tx_data.get('inputs', [])
        outputs = tx_data.get('out', [])

        if inputs:
            from_address = inputs[0].get('prev_out', {}).get('addr', 'unknown')

        if outputs:
            to_address = outputs[0].get('addr', 'unknown')

        tx = WhaleTransaction(
            blockchain='BTC',
            tx_hash=tx_data.get('hash', ''),
            timestamp=datetime.fromtimestamp(tx_data.get('time', 0)),
            block_number=tx_data.get('block_height'),
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            token_symbol=None,  # Bitcoin 無代幣
            is_whale=is_whale,
            is_anomaly=is_anomaly,
            tx_fee=Decimal(tx_data.get('fee', 0)) / Decimal(10 ** 8),
        )

        return tx

    async def _parse_blockchair_transaction(self, tx_data: Dict) -> Optional[WhaleTransaction]:
        """解析 Blockchair API 返回的交易"""
        # Blockchair 直接提供 BTC 金額
        amount = Decimal(str(tx_data.get('output_total', 0))) / Decimal(10 ** 8)

        is_whale, is_anomaly = await self.is_large_transaction(amount, None)

        if not is_whale:
            return None

        tx = WhaleTransaction(
            blockchain='BTC',
            tx_hash=tx_data.get('hash', ''),
            timestamp=datetime.fromisoformat(tx_data.get('time', '').replace('Z', '+00:00')),
            block_number=tx_data.get('block_id'),
            from_address='multiple',  # Blockchair 不提供詳細地址
            to_address='multiple',
            amount=amount,
            token_symbol=None,
            is_whale=is_whale,
            is_anomaly=is_anomaly,
            tx_fee=Decimal(str(tx_data.get('fee', 0))) / Decimal(10 ** 8),
        )

        return tx

    async def get_transaction_by_hash(self, tx_hash: str) -> Optional[WhaleTransaction]:
        """根據交易哈希獲取交易詳情"""
        session = await self._get_session()
        url = f"{self.api_url}/rawtx/{tx_hash}"

        try:
            async with session.get(url, timeout=self.timeout) as response:
                response.raise_for_status()
                tx_data = await response.json()

                return await self._parse_transaction(tx_data, '')

        except aiohttp.ClientError as e:
            logger.error(f"獲取 BTC 交易失敗: {e}")
            return None

    async def get_address_balance(self, address: str) -> Decimal:
        """獲取 BTC 餘額"""
        session = await self._get_session()
        url = f"{self.api_url}/balance"

        try:
            params = {'active': address}

            async with session.get(url, params=params, timeout=self.timeout) as response:
                response.raise_for_status()
                data = await response.json()

                balance_satoshi = data.get(address, {}).get('final_balance', 0)
                return Decimal(balance_satoshi) / Decimal(10 ** 8)

        except aiohttp.ClientError as e:
            logger.error(f"獲取 BTC 餘額失敗: {e}")
            return Decimal('0')

    async def is_large_transaction(
        self,
        amount: Decimal,
        token_symbol: Optional[str] = None
    ) -> tuple[bool, bool]:
        """判斷是否為大額交易"""
        whale_amount = self.whale_threshold.get('amount', 50)  # BTC 門檻
        anomaly_amount = self.anomaly_threshold.get('amount', 1000)

        is_whale = amount >= Decimal(whale_amount)
        is_anomaly = amount >= Decimal(anomaly_amount)

        return is_whale, is_anomaly

    async def get_usd_price(self, token_symbol: Optional[str] = None) -> Decimal:
        """獲取 BTC 美元價格"""
        # 檢查快取
        if self.price_cache:
            price, timestamp = self.price_cache
            if datetime.now() - timestamp < timedelta(seconds=self.price_cache_ttl):
                return price

        try:
            session = await self._get_session()
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'bitcoin',
                'vs_currencies': 'usd'
            }

            async with session.get(url, params=params, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()

                price = Decimal(str(data.get('bitcoin', {}).get('usd', 0)))
                self.price_cache = (price, datetime.now())

                return price

        except Exception as e:
            logger.error(f"獲取 BTC 價格失敗: {e}")
            return Decimal('0')
