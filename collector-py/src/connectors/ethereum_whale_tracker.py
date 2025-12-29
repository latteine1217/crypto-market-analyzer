"""
Ethereum 大額交易追蹤器

使用 Etherscan API 追蹤 Ethereum 主網和 ERC-20 代幣的大額交易
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


class EthereumWhaleTracker(BlockchainConnector):
    """Ethereum 大額交易追蹤器 (使用 Etherscan API v2)"""

    # Etherscan API v2 端點
    API_VERSION = "v2"
    CHAIN_ID = 1  # Ethereum Mainnet

    # API Actions
    NORMAL_TX_ACTION = "txlist"
    ERC20_TX_ACTION = "tokentx"
    BALANCE_ACTION = "balance"

    # 常用 ERC-20 代幣合約地址
    TOKEN_CONTRACTS = {
        'USDT': '0xdac17f958d2ee523a2206206994597c13d831ec7',
        'USDC': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
        'DAI': '0x6b175474e89094c44da98b954eedeac495271d0f',
        'WETH': '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2',
        'WBTC': '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599',
    }

    def __init__(
        self,
        api_key: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 Ethereum 追蹤器

        Args:
            api_key: Etherscan API Key
            config: 配置字典
        """
        super().__init__('ETH', api_key, config)

        self.session: Optional[aiohttp.ClientSession] = None

        # 價格快取（避免頻繁查詢）
        self.price_cache: Dict[str, tuple[Decimal, datetime]] = {}
        self.price_cache_ttl = 300  # 5 分鐘

    async def _get_session(self) -> aiohttp.ClientSession:
        """獲取或創建 aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """關閉連接"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _call_etherscan_api(
        self,
        module: str,
        action: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        調用 Etherscan API v2

        Args:
            module: API 模塊（account, transaction 等）
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

        # 合併額外參數
        if params:
            request_params.update(params)

        # 構建 v2 API URL
        # 從 https://api.etherscan.io/api 變成 https://api.etherscan.io/v2/api
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

                # Etherscan API 返回格式: {status, message, result}
                if data.get('status') == '1':
                    return data.get('result', [])
                else:
                    error_msg = data.get('message', 'Unknown error')
                    logger.warning(f"Etherscan API v2 錯誤: {error_msg}")
                    return []

        except aiohttp.ClientError as e:
            logger.error(f"Etherscan API v2 請求失敗: {e}")
            return []

    async def get_recent_transactions(
        self,
        address: Optional[str] = None,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[WhaleTransaction]:
        """
        獲取最近的交易

        注意：Etherscan API 不直接支持全網大額交易查詢，
        需要指定地址或使用其他方法

        Args:
            address: Ethereum 地址（必須）
            limit: 返回交易數量
            start_time: 開始時間
            end_time: 結束時間

        Returns:
            WhaleTransaction 列表
        """
        if not address:
            logger.warning("Ethereum 追蹤器需要指定地址才能查詢交易")
            return []

        # 計算區塊範圍（若有時間參數）
        start_block = 0
        end_block = 99999999

        if start_time:
            start_block = await self._timestamp_to_block(start_time)
        if end_time:
            end_block = await self._timestamp_to_block(end_time)

        # 獲取普通 ETH 轉帳
        normal_txs = await self._get_normal_transactions(
            address, start_block, end_block, limit
        )

        # 獲取 ERC-20 代幣轉帳
        token_txs = await self._get_token_transactions(
            address, start_block, end_block, limit
        )

        # 合併並排序
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
        """獲取 ETH 主幣轉帳"""
        params = {
            'address': address,
            'startblock': start_block,
            'endblock': end_block,
            'page': 1,
            'offset': limit,
            'sort': 'desc'
        }

        result = await self._call_etherscan_api('account', self.NORMAL_TX_ACTION, params)

        if not result:
            return []

        transactions = []
        for tx_data in result:
            try:
                tx = await self._parse_normal_transaction(tx_data)
                if tx:
                    transactions.append(tx)
            except Exception as e:
                logger.error(f"解析 ETH 交易失敗: {e}, 數據: {tx_data}")

        return transactions

    async def _get_token_transactions(
        self,
        address: str,
        start_block: int,
        end_block: int,
        limit: int
    ) -> List[WhaleTransaction]:
        """獲取 ERC-20 代幣轉帳"""
        params = {
            'address': address,
            'startblock': start_block,
            'endblock': end_block,
            'page': 1,
            'offset': limit,
            'sort': 'desc'
        }

        result = await self._call_etherscan_api('account', self.ERC20_TX_ACTION, params)

        if not result:
            return []

        transactions = []
        for tx_data in result:
            try:
                tx = await self._parse_token_transaction(tx_data)
                if tx:
                    transactions.append(tx)
            except Exception as e:
                logger.error(f"解析 ERC-20 交易失敗: {e}, 數據: {tx_data}")

        return transactions

    async def _parse_normal_transaction(self, tx_data: Dict) -> Optional[WhaleTransaction]:
        """解析普通 ETH 交易"""
        amount = Decimal(tx_data.get('value', '0')) / Decimal(10 ** 18)

        # 檢查是否為大額交易
        is_whale, is_anomaly = await self.is_large_transaction(amount, None)

        if not is_whale:
            return None  # 不是大額交易，忽略

        tx = WhaleTransaction(
            blockchain='ETH',
            tx_hash=tx_data.get('hash', ''),
            timestamp=datetime.fromtimestamp(int(tx_data.get('timeStamp', 0))),
            block_number=int(tx_data.get('blockNumber', 0)),
            from_address=tx_data.get('from', ''),
            to_address=tx_data.get('to', ''),
            amount=amount,
            token_symbol=None,  # 主幣
            is_whale=is_whale,
            is_anomaly=is_anomaly,
            gas_used=int(tx_data.get('gasUsed', 0)),
            gas_price=int(tx_data.get('gasPrice', 0)),
        )

        # 計算交易手續費
        if tx.gas_used and tx.gas_price:
            tx.tx_fee = Decimal(tx.gas_used * tx.gas_price) / Decimal(10 ** 18)

        return tx

    async def _parse_token_transaction(self, tx_data: Dict) -> Optional[WhaleTransaction]:
        """解析 ERC-20 代幣交易"""
        token_symbol = tx_data.get('tokenSymbol', '')
        token_decimal = int(tx_data.get('tokenDecimal', 18))

        amount = Decimal(tx_data.get('value', '0')) / Decimal(10 ** token_decimal)

        # 檢查是否為大額交易
        is_whale, is_anomaly = await self.is_large_transaction(amount, token_symbol)

        if not is_whale:
            return None

        tx = WhaleTransaction(
            blockchain='ETH',
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
        """
        根據交易哈希獲取交易詳情

        Args:
            tx_hash: 交易哈希

        Returns:
            WhaleTransaction 或 None
        """
        # Etherscan 不直接提供單個交易查詢 API
        # 需要使用 eth_getTransactionByHash（需要 Infura 或自己的節點）
        logger.warning("Etherscan API 不支持直接查詢單個交易，請使用 get_recent_transactions")
        return None

    async def get_address_balance(self, address: str) -> Decimal:
        """
        獲取 ETH 餘額

        Args:
            address: Ethereum 地址

        Returns:
            餘額（ETH）
        """
        params = {
            'address': address,
            'tag': 'latest'
        }

        result = await self._call_etherscan_api('account', self.BALANCE_ACTION, params)

        if result and isinstance(result, str):
            return Decimal(result) / Decimal(10 ** 18)

        return Decimal('0')

    async def is_large_transaction(
        self,
        amount: Decimal,
        token_symbol: Optional[str] = None
    ) -> tuple[bool, bool]:
        """
        判斷是否為大額交易

        Args:
            amount: 交易金額
            token_symbol: 代幣符號（None 為 ETH）

        Returns:
            (is_whale, is_anomaly)
        """
        symbol = token_symbol or 'ETH'

        # 從配置獲取門檻
        # whale_threshold 和 anomaly_threshold 已經是特定幣種的配置
        # 結構: {'amount': 500, 'usd_value': 1000000}
        whale_amount = self.whale_threshold.get('amount', 500)
        anomaly_amount = self.anomaly_threshold.get('amount', 10000)

        # 對於非 ETH 代幣，使用代幣特定門檻或默認值
        # 這裡可以根據需要擴展，從全局配置中查找特定代幣門檻
        # 目前先使用 ETH 的門檻作為基準

        is_whale = amount >= Decimal(whale_amount)
        is_anomaly = amount >= Decimal(anomaly_amount)

        return is_whale, is_anomaly

    async def get_usd_price(self, token_symbol: Optional[str] = None) -> Decimal:
        """
        獲取 ETH 或 ERC-20 代幣的美元價格

        使用 CoinGecko API（免費，無需 API key）

        Args:
            token_symbol: 代幣符號（None 為 ETH）

        Returns:
            美元價格
        """
        symbol = (token_symbol or 'ETH').lower()

        # 檢查快取
        if symbol in self.price_cache:
            price, timestamp = self.price_cache[symbol]
            if datetime.now() - timestamp < timedelta(seconds=self.price_cache_ttl):
                return price

        # CoinGecko ID 映射
        coingecko_ids = {
            'eth': 'ethereum',
            'usdt': 'tether',
            'usdc': 'usd-coin',
            'dai': 'dai',
            'weth': 'weth',
            'wbtc': 'wrapped-bitcoin',
            'bnb': 'binancecoin',
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

                # 更新快取
                self.price_cache[symbol] = (price, datetime.now())

                return price

        except Exception as e:
            logger.error(f"獲取 {symbol} 價格失敗: {e}")

            # 穩定幣預設 $1
            if symbol in ['usdt', 'usdc', 'dai']:
                return Decimal('1.0')

            return Decimal('0')

    async def _timestamp_to_block(self, timestamp: datetime) -> int:
        """
        將時間戳轉換為最接近的區塊號

        Args:
            timestamp: 時間戳

        Returns:
            區塊號
        """
        # Etherscan 提供區塊號查詢 API
        unix_timestamp = int(timestamp.timestamp())

        params = {
            'timestamp': unix_timestamp,
            'closest': 'before'
        }

        result = await self._call_etherscan_api('block', 'getblocknobytime', params)

        if result and isinstance(result, str):
            return int(result)

        return 0


# ============================================================================
# 測試代碼
# ============================================================================
async def test_ethereum_tracker():
    """測試 Ethereum 追蹤器"""
    from utils.config_loader import load_whale_tracker_config, get_blockchain_config

    # 載入配置
    config = load_whale_tracker_config()
    eth_config = get_blockchain_config('ETH', config)

    # 創建追蹤器
    tracker = EthereumWhaleTracker(
        api_key=eth_config['api_key'],
        config=eth_config
    )

    try:
        # 測試 1: 獲取 Binance 熱錢包的最近交易
        binance_hot_wallet = '0x28C6c06298d514Db089934071355E5743bf21d60'

        logger.info(f"查詢 Binance 熱錢包交易: {binance_hot_wallet}")
        txs = await tracker.get_recent_transactions(
            address=binance_hot_wallet,
            limit=20
        )

        logger.info(f"找到 {len(txs)} 筆大額交易")

        for tx in txs[:5]:
            logger.info(f"""
            交易: {tx.tx_hash[:10]}...
            時間: {tx.timestamp}
            金額: {tx.amount} {tx.token_symbol or 'ETH'}
            從: {tx.from_address[:10]}...
            到: {tx.to_address[:10]}...
            大額: {tx.is_whale}, 異常: {tx.is_anomaly}
            """)

        # 測試 2: 獲取 ETH 價格
        eth_price = await tracker.get_usd_price(None)
        logger.info(f"ETH 當前價格: ${eth_price}")

        usdt_price = await tracker.get_usd_price('USDT')
        logger.info(f"USDT 當前價格: ${usdt_price}")

    finally:
        await tracker.close()


if __name__ == '__main__':
    asyncio.run(test_ethereum_tracker())
