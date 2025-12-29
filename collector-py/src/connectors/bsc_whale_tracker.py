"""
Binance Smart Chain (BSC) 大額交易追蹤器

使用 BscScan API 追蹤 BSC 主網和 BEP-20 代幣的大額交易
BSC 與 Ethereum 架構相似，都是 EVM 兼容鏈
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


class BSCWhaleTracker(BlockchainConnector):
    """Binance Smart Chain 大額交易追蹤器 (使用 Etherscan API v2)"""

    # Etherscan API v2 端點（BscScan 也使用 v2 API）
    API_VERSION = "v2"
    CHAIN_ID = 56  # BSC Mainnet

    # API Actions
    NORMAL_TX_ACTION = "txlist"
    BEP20_TX_ACTION = "tokentx"
    BALANCE_ACTION = "balance"

    # 常用 BEP-20 代幣合約地址
    TOKEN_CONTRACTS = {
        'USDT': '0x55d398326f99059ff775485246999027b3197955',  # BSC-USD
        'USDC': '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d',
        'BUSD': '0xe9e7cea3dedca5984780bafc599bd69add087d56',  # Binance USD
        'WBNB': '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c',
        'BTCB': '0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c',  # Bitcoin BEP2
    }

    def __init__(
        self,
        api_key: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 BSC 追蹤器

        Args:
            api_key: BscScan API Key
            config: 配置字典
        """
        super().__init__('BSC', api_key, config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.price_cache: Dict[str, tuple[Decimal, datetime]] = {}
        self.price_cache_ttl = 300

    async def _get_session(self) -> aiohttp.ClientSession:
        """獲取或創建 aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """關閉連接"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _call_bscscan_api(
        self,
        module: str,
        action: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        調用 BscScan API v2 (使用 Etherscan API v2)

        Args:
            module: API 模塊
            action: API 動作
            params: 額外參數

        Returns:
            API 響應字典
        """
        session = await self._get_session()

        # API v2 基礎參數 (必須包含 chainid)
        request_params = {
            'chainid': self.CHAIN_ID,
            'module': module,
            'action': action,
            'apikey': self.api_key
        }

        if params:
            request_params.update(params)

        # 構建 v2 API URL
        # 從 https://api.bscscan.com/api 變成 https://api.bscscan.com/v2/api
        if '/api' in self.api_url:
            base_url = self.api_url.rsplit('/api', 1)[0]
            api_v2_url = f"{base_url}/{self.API_VERSION}/api"
        else:
            api_v2_url = self.api_url

        try:
            async with session.get(
                api_v2_url,
                params=request_params,
                timeout=self.timeout
            ) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get('status') == '1':
                    return data.get('result', [])
                else:
                    error_msg = data.get('message', 'Unknown error')
                    logger.warning(f"BscScan API v2 錯誤: {error_msg}")
                    return []

        except aiohttp.ClientError as e:
            logger.error(f"BscScan API v2 請求失敗: {e}")
            return []

    async def get_recent_transactions(
        self,
        address: Optional[str] = None,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[WhaleTransaction]:
        """獲取最近的交易"""
        if not address:
            logger.warning("BSC 追蹤器需要指定地址才能查詢交易")
            return []

        start_block = 0
        end_block = 99999999

        if start_time:
            start_block = await self._timestamp_to_block(start_time)
        if end_time:
            end_block = await self._timestamp_to_block(end_time)

        # 獲取 BNB 轉帳
        normal_txs = await self._get_normal_transactions(
            address, start_block, end_block, limit
        )

        # 獲取 BEP-20 代幣轉帳
        token_txs = await self._get_token_transactions(
            address, start_block, end_block, limit
        )

        all_txs = normal_txs + token_txs
        all_txs.sort(key=lambda tx: tx.timestamp, reverse=True)

        return all_txs[:limit]

    async def _get_normal_transactions(
        self,
        address: str,
        start_block: int,
        end_block: int,
        limit: int
    ) -> List[WhaleTransaction]:
        """獲取 BNB 主幣轉帳"""
        params = {
            'address': address,
            'startblock': start_block,
            'endblock': end_block,
            'page': 1,
            'offset': limit,
            'sort': 'desc'
        }

        result = await self._call_bscscan_api('account', self.NORMAL_TX_ACTION, params)

        if not result:
            return []

        transactions = []
        for tx_data in result:
            try:
                tx = await self._parse_normal_transaction(tx_data)
                if tx:
                    transactions.append(tx)
            except Exception as e:
                logger.error(f"解析 BNB 交易失敗: {e}")

        return transactions

    async def _get_token_transactions(
        self,
        address: str,
        start_block: int,
        end_block: int,
        limit: int
    ) -> List[WhaleTransaction]:
        """獲取 BEP-20 代幣轉帳"""
        params = {
            'address': address,
            'startblock': start_block,
            'endblock': end_block,
            'page': 1,
            'offset': limit,
            'sort': 'desc'
        }

        result = await self._call_bscscan_api('account', self.BEP20_TX_ACTION, params)

        if not result:
            return []

        transactions = []
        for tx_data in result:
            try:
                tx = await self._parse_token_transaction(tx_data)
                if tx:
                    transactions.append(tx)
            except Exception as e:
                logger.error(f"解析 BEP-20 交易失敗: {e}")

        return transactions

    async def _parse_normal_transaction(self, tx_data: Dict) -> Optional[WhaleTransaction]:
        """解析 BNB 交易"""
        amount = Decimal(tx_data.get('value', '0')) / Decimal(10 ** 18)

        is_whale, is_anomaly = await self.is_large_transaction(amount, None)

        if not is_whale:
            return None

        tx = WhaleTransaction(
            blockchain='BSC',
            tx_hash=tx_data.get('hash', ''),
            timestamp=datetime.fromtimestamp(int(tx_data.get('timeStamp', 0))),
            block_number=int(tx_data.get('blockNumber', 0)),
            from_address=tx_data.get('from', ''),
            to_address=tx_data.get('to', ''),
            amount=amount,
            token_symbol=None,  # BNB 主幣
            is_whale=is_whale,
            is_anomaly=is_anomaly,
            gas_used=int(tx_data.get('gasUsed', 0)),
            gas_price=int(tx_data.get('gasPrice', 0)),
        )

        if tx.gas_used and tx.gas_price:
            tx.tx_fee = Decimal(tx.gas_used * tx.gas_price) / Decimal(10 ** 18)

        return tx

    async def _parse_token_transaction(self, tx_data: Dict) -> Optional[WhaleTransaction]:
        """解析 BEP-20 代幣交易"""
        token_symbol = tx_data.get('tokenSymbol', '')
        token_decimal = int(tx_data.get('tokenDecimal', 18))

        amount = Decimal(tx_data.get('value', '0')) / Decimal(10 ** token_decimal)

        is_whale, is_anomaly = await self.is_large_transaction(amount, token_symbol)

        if not is_whale:
            return None

        tx = WhaleTransaction(
            blockchain='BSC',
            tx_hash=tx_data.get('hash', ''),
            timestamp=datetime.fromtimestamp(int(tx_data.get('timeStamp', 0))),
            block_number=int(tx_data.get('blockNumber', 0)),
            from_address=tx_data.get('from', ''),
            to_address=tx_data.get('to', ''),
            amount=amount,
            token_symbol=token_symbol,
            token_contract=tx_data.get('contractAddress', ''),
            is_whale=is_whale,
            is_anomaly=is_anomaly,
            gas_used=int(tx_data.get('gasUsed', 0)) if tx_data.get('gasUsed') else None,
            gas_price=int(tx_data.get('gasPrice', 0)) if tx_data.get('gasPrice') else None,
        )

        return tx

    async def get_transaction_by_hash(self, tx_hash: str) -> Optional[WhaleTransaction]:
        """根據交易哈希獲取交易詳情"""
        logger.warning("BscScan API 不支持直接查詢單個交易")
        return None

    async def get_address_balance(self, address: str) -> Decimal:
        """獲取 BNB 餘額"""
        params = {
            'address': address,
            'tag': 'latest'
        }

        result = await self._call_bscscan_api('account', self.BALANCE_ACTION, params)

        if result and isinstance(result, str):
            return Decimal(result) / Decimal(10 ** 18)

        return Decimal('0')

    async def is_large_transaction(
        self,
        amount: Decimal,
        token_symbol: Optional[str] = None
    ) -> tuple[bool, bool]:
        """判斷是否為大額交易"""
        symbol = token_symbol or 'BNB'

        whale_amount = self.whale_threshold.get('amount', 1000)  # BNB 門檻
        anomaly_amount = self.anomaly_threshold.get('amount', 10000)

        is_whale = amount >= Decimal(whale_amount)
        is_anomaly = amount >= Decimal(anomaly_amount)

        return is_whale, is_anomaly

    async def get_usd_price(self, token_symbol: Optional[str] = None) -> Decimal:
        """獲取 BNB 或 BEP-20 代幣的美元價格"""
        symbol = (token_symbol or 'BNB').lower()

        # 檢查快取
        if symbol in self.price_cache:
            price, timestamp = self.price_cache[symbol]
            if datetime.now() - timestamp < timedelta(seconds=self.price_cache_ttl):
                return price

        coingecko_ids = {
            'bnb': 'binancecoin',
            'usdt': 'tether',
            'usdc': 'usd-coin',
            'busd': 'binance-usd',
            'wbnb': 'wbnb',
            'btcb': 'bitcoin-bep2',
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

            if symbol in ['usdt', 'usdc', 'busd']:
                return Decimal('1.0')

            return Decimal('0')

    async def _timestamp_to_block(self, timestamp: datetime) -> int:
        """將時間戳轉換為區塊號"""
        unix_timestamp = int(timestamp.timestamp())

        params = {
            'timestamp': unix_timestamp,
            'closest': 'before'
        }

        result = await self._call_bscscan_api('block', 'getblocknobytime', params)

        if result and isinstance(result, str):
            return int(result)

        return 0
