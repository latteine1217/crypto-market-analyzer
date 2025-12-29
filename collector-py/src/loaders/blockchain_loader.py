"""
區塊鏈資料載入器

負責將區塊鏈巨鯨交易資料寫入 TimescaleDB
"""
import asyncpg
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
from decimal import Decimal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from connectors.blockchain_base import WhaleTransaction, WhaleAddress


class BlockchainDataLoader:
    """區塊鏈資料載入器"""

    def __init__(
        self,
        db_config: Dict[str, Any]
    ):
        """
        初始化載入器

        Args:
            db_config: 資料庫配置字典
                {
                    'host': 'localhost',
                    'port': 5432,
                    'user': 'crypto',
                    'password': 'crypto_pass',
                    'database': 'crypto_db'
                }
        """
        self.db_config = db_config
        self.pool: Optional[asyncpg.Pool] = None

        # 區塊鏈 ID 快取
        self.blockchain_id_cache: Dict[str, int] = {}

    async def connect(self):
        """建立資料庫連線池"""
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    host=self.db_config['host'],
                    port=self.db_config['port'],
                    user=self.db_config['user'],
                    password=self.db_config['password'],
                    database=self.db_config['database'],
                    min_size=2,
                    max_size=10,
                    command_timeout=60
                )
                logger.info("資料庫連線池建立成功")

                # 預載區塊鏈 ID
                await self._load_blockchain_ids()

            except Exception as e:
                logger.error(f"資料庫連線失敗: {e}")
                raise

    async def close(self):
        """關閉資料庫連線池"""
        if self.pool:
            await self.pool.close()
            logger.info("資料庫連線池已關閉")

    async def _load_blockchain_ids(self):
        """預載所有區塊鏈 ID 到快取"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, name FROM blockchains")
            self.blockchain_id_cache = {row['name']: row['id'] for row in rows}
            logger.info(f"載入 {len(self.blockchain_id_cache)} 個區塊鏈 ID: {self.blockchain_id_cache}")

    def _get_blockchain_id(self, blockchain: str) -> Optional[int]:
        """
        從快取取得區塊鏈 ID

        Args:
            blockchain: 區塊鏈名稱 (BTC, ETH, BSC, TRX)

        Returns:
            區塊鏈 ID 或 None
        """
        return self.blockchain_id_cache.get(blockchain.upper())

    async def insert_whale_address(
        self,
        address: WhaleAddress
    ) -> int:
        """
        插入或更新巨鯨地址

        Args:
            address: WhaleAddress 對象

        Returns:
            address_id
        """
        blockchain_id = self._get_blockchain_id(address.blockchain)
        if not blockchain_id:
            logger.error(f"未知的區塊鏈: {address.blockchain}")
            return None

        async with self.pool.acquire() as conn:
            # Upsert 邏輯
            query = """
                INSERT INTO whale_addresses (
                    blockchain_id, address, label, address_type,
                    is_exchange, exchange_name,
                    total_tx_count, total_inflow, total_outflow,
                    current_balance, first_seen, last_active
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                )
                ON CONFLICT (blockchain_id, address) DO UPDATE SET
                    label = COALESCE(EXCLUDED.label, whale_addresses.label),
                    address_type = COALESCE(EXCLUDED.address_type, whale_addresses.address_type),
                    is_exchange = EXCLUDED.is_exchange,
                    exchange_name = COALESCE(EXCLUDED.exchange_name, whale_addresses.exchange_name),
                    total_tx_count = whale_addresses.total_tx_count + EXCLUDED.total_tx_count,
                    total_inflow = whale_addresses.total_inflow + EXCLUDED.total_inflow,
                    total_outflow = whale_addresses.total_outflow + EXCLUDED.total_outflow,
                    current_balance = EXCLUDED.current_balance,
                    last_active = GREATEST(whale_addresses.last_active, EXCLUDED.last_active),
                    updated_at = NOW()
                RETURNING id
            """

            try:
                address_id = await conn.fetchval(
                    query,
                    blockchain_id,
                    address.address,
                    address.label,
                    address.address_type,
                    address.is_exchange,
                    address.exchange_name,
                    address.total_tx_count,
                    float(address.total_inflow) if address.total_inflow else 0,
                    float(address.total_outflow) if address.total_outflow else 0,
                    float(address.current_balance) if address.current_balance else None,
                    address.first_seen or datetime.now(),
                    address.last_active or datetime.now()
                )

                logger.debug(f"插入/更新地址: {address.address[:10]}... (ID: {address_id})")
                return address_id

            except Exception as e:
                logger.error(f"插入地址失敗: {e}")
                raise

    async def insert_whale_transactions(
        self,
        transactions: List[WhaleTransaction]
    ) -> int:
        """
        批次插入巨鯨交易

        Args:
            transactions: WhaleTransaction 列表

        Returns:
            成功插入的筆數
        """
        if not transactions:
            return 0

        blockchain = transactions[0].blockchain
        blockchain_id = self._get_blockchain_id(blockchain)

        if not blockchain_id:
            logger.error(f"未知的區塊鏈: {blockchain}")
            return 0

        async with self.pool.acquire() as conn:
            # 準備批次插入資料
            insert_query = """
                INSERT INTO whale_transactions (
                    blockchain_id, tx_hash, block_number, tx_timestamp,
                    from_address, to_address,
                    amount, amount_usd, token_symbol, token_contract,
                    is_exchange_inflow, is_exchange_outflow, exchange_name, direction,
                    is_whale, is_anomaly,
                    gas_used, gas_price, tx_fee,
                    data_source
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                )
                ON CONFLICT (blockchain_id, tx_timestamp, tx_hash) DO UPDATE SET
                    amount_usd = EXCLUDED.amount_usd,
                    is_exchange_inflow = EXCLUDED.is_exchange_inflow,
                    is_exchange_outflow = EXCLUDED.is_exchange_outflow,
                    exchange_name = EXCLUDED.exchange_name,
                    updated_at = NOW()
            """

            inserted_count = 0

            try:
                # 使用 transaction 確保原子性
                async with conn.transaction():
                    for tx in transactions:
                        try:
                            await conn.execute(
                                insert_query,
                                blockchain_id,
                                tx.tx_hash,
                                tx.block_number,
                                tx.timestamp,
                                tx.from_address,
                                tx.to_address,
                                float(tx.amount),
                                float(tx.amount_usd) if tx.amount_usd else None,
                                tx.token_symbol,
                                tx.token_contract,
                                tx.is_exchange_inflow,
                                tx.is_exchange_outflow,
                                tx.exchange_name,
                                tx.direction.value if tx.direction else 'neutral',
                                tx.is_whale,
                                tx.is_anomaly,
                                tx.gas_used,
                                tx.gas_price,
                                float(tx.tx_fee) if tx.tx_fee else None,
                                'auto_collector'  # data_source
                            )
                            inserted_count += 1

                        except Exception as e:
                            logger.warning(f"插入交易失敗 {tx.tx_hash[:10]}...: {e}")
                            continue

                logger.info(f"成功插入 {inserted_count}/{len(transactions)} 筆 {blockchain} 交易")
                return inserted_count

            except Exception as e:
                logger.error(f"批次插入交易失敗: {e}")
                raise

    async def get_latest_transaction_time(
        self,
        blockchain: str
    ) -> Optional[datetime]:
        """
        取得特定區塊鏈的最新交易時間

        Args:
            blockchain: 區塊鏈名稱

        Returns:
            最新交易時間或 None
        """
        blockchain_id = self._get_blockchain_id(blockchain)
        if not blockchain_id:
            return None

        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT get_latest_whale_tx_time($1)",
                blockchain_id
            )
            return result

    async def get_exchange_flow_stats(
        self,
        blockchain: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        取得交易所流入/流出統計

        Args:
            blockchain: 區塊鏈名稱
            start_time: 開始時間
            end_time: 結束時間

        Returns:
            統計資料列表
        """
        blockchain_id = self._get_blockchain_id(blockchain)
        if not blockchain_id:
            return []

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM get_exchange_flow_stats($1, $2, $3)",
                blockchain_id,
                start_time,
                end_time
            )

            return [dict(row) for row in rows]

    async def get_anomaly_transactions(
        self,
        blockchain: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        取得異常大額交易

        Args:
            blockchain: 區塊鏈名稱
            start_time: 開始時間
            end_time: 結束時間
            limit: 返回筆數限制

        Returns:
            異常交易列表
        """
        blockchain_id = self._get_blockchain_id(blockchain)
        if not blockchain_id:
            return []

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM get_anomaly_transactions($1, $2, $3, $4)",
                blockchain_id,
                start_time,
                end_time,
                limit
            )

            return [dict(row) for row in rows]

    async def get_transaction_count(
        self,
        blockchain: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """
        取得交易數量

        Args:
            blockchain: 區塊鏈名稱
            start_time: 開始時間 (可選)
            end_time: 結束時間 (可選)

        Returns:
            交易數量
        """
        blockchain_id = self._get_blockchain_id(blockchain)
        if not blockchain_id:
            return 0

        async with self.pool.acquire() as conn:
            query = "SELECT COUNT(*) FROM whale_transactions WHERE blockchain_id = $1"
            params = [blockchain_id]

            if start_time:
                query += " AND tx_timestamp >= $2"
                params.append(start_time)
            if end_time:
                param_idx = 3 if start_time else 2
                query += f" AND tx_timestamp <= ${param_idx}"
                params.append(end_time)

            count = await conn.fetchval(query, *params)
            return count


# ============================================================================
# 測試代碼
# ============================================================================
async def test_blockchain_loader():
    """測試區塊鏈資料載入器"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'user': os.getenv('POSTGRES_USER', 'crypto'),
        'password': os.getenv('POSTGRES_PASSWORD', 'crypto_pass'),
        'database': os.getenv('POSTGRES_DB', 'crypto_db')
    }

    loader = BlockchainDataLoader(db_config)

    try:
        await loader.connect()

        # 測試取得最新交易時間
        latest_time = await loader.get_latest_transaction_time('ETH')
        logger.info(f"ETH 最新交易時間: {latest_time}")

        # 測試取得交易數量
        count = await loader.get_transaction_count('ETH')
        logger.info(f"ETH 交易總數: {count}")

    finally:
        await loader.close()


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_blockchain_loader())
