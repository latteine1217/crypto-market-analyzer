"""
完整的區塊鏈 ETL 測試流程

測試從 API 抓取資料 → 驗證 → 載入資料庫的完整流程
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
from dotenv import load_dotenv
import os

# 載入環境變數
load_dotenv()

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from connectors.ethereum_whale_tracker import EthereumWhaleTracker
from connectors.bsc_whale_tracker import BSCWhaleTracker
from connectors.bitcoin_whale_tracker import BitcoinWhaleTracker
from loaders.blockchain_loader import BlockchainDataLoader
from validators.blockchain_validator import BlockchainDataValidator
from utils.config_loader import load_whale_tracker_config, get_blockchain_config


class BlockchainETL:
    """區塊鏈 ETL 流程管理器"""

    def __init__(self):
        """初始化 ETL"""
        # 載入配置
        self.config = load_whale_tracker_config()

        # 初始化資料庫配置
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'user': os.getenv('POSTGRES_USER', 'crypto'),
            'password': os.getenv('POSTGRES_PASSWORD', 'crypto_pass'),
            'database': os.getenv('POSTGRES_DB', 'crypto_db')
        }

        # 初始化組件
        self.loader = BlockchainDataLoader(self.db_config)
        self.validator = BlockchainDataValidator()

        # Trackers
        self.trackers = {}

    async def initialize(self):
        """初始化所有組件"""
        logger.info("初始化 ETL 組件...")

        # 連接資料庫
        await self.loader.connect()

        # 初始化 trackers
        eth_config = get_blockchain_config('ETH', self.config)
        self.trackers['ETH'] = EthereumWhaleTracker(
            api_key=eth_config['api_key'],
            config=eth_config
        )

        bsc_config = get_blockchain_config('BSC', self.config)
        self.trackers['BSC'] = BSCWhaleTracker(
            api_key=bsc_config['api_key'],
            config=bsc_config
        )

        btc_config = get_blockchain_config('BTC', self.config)
        self.trackers['BTC'] = BitcoinWhaleTracker(
            api_key=None,
            config=btc_config
        )

        logger.success("ETL 組件初始化完成")

    async def cleanup(self):
        """清理資源"""
        logger.info("清理 ETL 資源...")

        # 關閉所有 trackers
        for tracker in self.trackers.values():
            await tracker.close()

        # 關閉資料庫連線
        await self.loader.close()

        logger.success("資源清理完成")

    async def extract_ethereum_data(
        self,
        address: str,
        limit: int = 20
    ) -> list:
        """
        Extract: 從 Ethereum 抓取資料

        Args:
            address: 以太坊地址
            limit: 抓取數量

        Returns:
            交易列表
        """
        logger.info(f"[Extract] 抓取 Ethereum 資料: {address[:10]}...")

        tracker = self.trackers['ETH']

        try:
            txs = await tracker.get_recent_transactions(
                address=address,
                limit=limit
            )

            logger.success(f"[Extract] 成功抓取 {len(txs)} 筆 Ethereum 交易")
            return txs

        except Exception as e:
            logger.error(f"[Extract] 抓取 Ethereum 資料失敗: {e}")
            return []

    async def extract_bsc_data(
        self,
        address: str,
        limit: int = 20
    ) -> list:
        """
        Extract: 從 BSC 抓取資料

        Args:
            address: BSC 地址
            limit: 抓取數量

        Returns:
            交易列表
        """
        logger.info(f"[Extract] 抓取 BSC 資料: {address[:10]}...")

        tracker = self.trackers['BSC']

        try:
            txs = await tracker.get_recent_transactions(
                address=address,
                limit=limit
            )

            logger.success(f"[Extract] 成功抓取 {len(txs)} 筆 BSC 交易")
            return txs

        except Exception as e:
            logger.error(f"[Extract] 抓取 BSC 資料失敗: {e}")
            return []

    async def extract_bitcoin_data(
        self,
        limit: int = 10
    ) -> list:
        """
        Extract: 從 Bitcoin 抓取資料

        Args:
            limit: 抓取數量

        Returns:
            交易列表
        """
        logger.info(f"[Extract] 抓取 Bitcoin 大額交易...")

        tracker = self.trackers['BTC']

        try:
            txs = await tracker.get_recent_transactions(limit=limit)

            logger.success(f"[Extract] 成功抓取 {len(txs)} 筆 Bitcoin 交易")
            return txs

        except Exception as e:
            logger.error(f"[Extract] 抓取 Bitcoin 資料失敗: {e}")
            return []

    def transform_data(
        self,
        transactions: list,
        blockchain: str
    ) -> tuple:
        """
        Transform: 驗證與轉換資料

        Args:
            transactions: 交易列表
            blockchain: 區塊鏈名稱

        Returns:
            (valid_txs, quality_report) 元組
        """
        logger.info(f"[Transform] 驗證 {blockchain} 資料...")

        if not transactions:
            logger.warning(f"[Transform] {blockchain} 無資料需要驗證")
            return [], {}

        # 去重
        unique_txs = self.validator.deduplicate_transactions(transactions)

        # 驗證
        valid_txs, invalid_txs = self.validator.filter_valid_transactions(unique_txs)

        # 生成品質報告
        quality_report = self.validator.generate_quality_report(
            transactions,
            valid_txs,
            invalid_txs
        )

        logger.success(
            f"[Transform] {blockchain} 資料驗證完成: "
            f"{len(valid_txs)} 有效 / {len(invalid_txs)} 無效"
        )

        return valid_txs, quality_report

    async def load_data(
        self,
        transactions: list,
        blockchain: str
    ) -> int:
        """
        Load: 載入資料到資料庫

        Args:
            transactions: 交易列表
            blockchain: 區塊鏈名稱

        Returns:
            成功載入的筆數
        """
        logger.info(f"[Load] 載入 {blockchain} 資料到資料庫...")

        if not transactions:
            logger.warning(f"[Load] {blockchain} 無資料需要載入")
            return 0

        try:
            count = await self.loader.insert_whale_transactions(transactions)
            logger.success(f"[Load] 成功載入 {count} 筆 {blockchain} 交易")
            return count

        except Exception as e:
            logger.error(f"[Load] 載入 {blockchain} 資料失敗: {e}")
            return 0

    async def run_etl_pipeline(
        self,
        blockchain: str,
        **kwargs
    ) -> dict:
        """
        執行完整的 ETL 流程

        Args:
            blockchain: 區塊鏈名稱 (ETH, BSC, BTC)
            **kwargs: 額外參數 (address, limit 等)

        Returns:
            執行結果字典
        """
        logger.info("=" * 80)
        logger.info(f"開始 {blockchain} ETL 流程")
        logger.info("=" * 80)

        start_time = datetime.now()

        try:
            # Step 1: Extract
            if blockchain == 'ETH':
                address = kwargs.get('address')
                limit = kwargs.get('limit', 20)
                raw_txs = await self.extract_ethereum_data(address, limit)

            elif blockchain == 'BSC':
                address = kwargs.get('address')
                limit = kwargs.get('limit', 20)
                raw_txs = await self.extract_bsc_data(address, limit)

            elif blockchain == 'BTC':
                limit = kwargs.get('limit', 10)
                raw_txs = await self.extract_bitcoin_data(limit)

            else:
                logger.error(f"不支援的區塊鏈: {blockchain}")
                return {'success': False, 'error': 'Unsupported blockchain'}

            # Step 2: Transform
            valid_txs, quality_report = self.transform_data(raw_txs, blockchain)

            # Step 3: Load
            loaded_count = await self.load_data(valid_txs, blockchain)

            # 計算執行時間
            elapsed_time = (datetime.now() - start_time).total_seconds()

            # 執行結果
            result = {
                'success': True,
                'blockchain': blockchain,
                'extracted': len(raw_txs),
                'validated': len(valid_txs),
                'loaded': loaded_count,
                'quality_report': quality_report,
                'elapsed_time': elapsed_time
            }

            logger.info("=" * 80)
            logger.success(f"{blockchain} ETL 流程完成!")
            logger.info(f"抓取: {result['extracted']} 筆")
            logger.info(f"驗證通過: {result['validated']} 筆")
            logger.info(f"成功載入: {result['loaded']} 筆")
            logger.info(f"執行時間: {elapsed_time:.2f} 秒")
            logger.info("=" * 80)

            return result

        except Exception as e:
            logger.error(f"{blockchain} ETL 流程失敗: {e}")
            return {
                'success': False,
                'blockchain': blockchain,
                'error': str(e)
            }


async def main():
    """主測試函數"""
    # 配置 logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    etl = BlockchainETL()

    try:
        await etl.initialize()

        # 測試 Ethereum ETL
        logger.info("\n" + "=" * 80)
        logger.info("測試 1: Ethereum ETL")
        logger.info("=" * 80)

        eth_result = await etl.run_etl_pipeline(
            blockchain='ETH',
            address='0x28C6c06298d514Db089934071355E5743bf21d60',  # Binance Hot Wallet
            limit=10
        )

        # 測試 BSC ETL
        logger.info("\n" + "=" * 80)
        logger.info("測試 2: BSC ETL")
        logger.info("=" * 80)

        bsc_result = await etl.run_etl_pipeline(
            blockchain='BSC',
            address='0x8894E0a0c962CB723c1976a4421c95949bE2D4E3',  # Binance 14
            limit=10
        )

        # 測試 Bitcoin ETL (可選,因為 Blockchair 有限制)
        # logger.info("\n" + "=" * 80)
        # logger.info("測試 3: Bitcoin ETL")
        # logger.info("=" * 80)
        #
        # btc_result = await etl.run_etl_pipeline(
        #     blockchain='BTC',
        #     limit=5
        # )

        # 總結
        logger.info("\n" + "=" * 80)
        logger.info("ETL 測試總結")
        logger.info("=" * 80)
        logger.info(f"Ethereum: {eth_result.get('success', False)}")
        logger.info(f"BSC: {bsc_result.get('success', False)}")
        # logger.info(f"Bitcoin: {btc_result.get('success', False)}")

    finally:
        await etl.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
