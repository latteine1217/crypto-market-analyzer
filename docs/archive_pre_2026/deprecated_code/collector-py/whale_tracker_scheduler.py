#!/usr/bin/env python3
"""
鯨魚追蹤排程器
每 5-10 分鐘自動收集 Ethereum 大額交易
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
import signal

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from connectors.ethereum_whale_tracker import EthereumWhaleTracker
from connectors.bitcoin_whale_tracker import BitcoinWhaleTracker
from connectors.bsc_whale_tracker import BSCWhaleTracker
from connectors.tron_whale_tracker import TronWhaleTracker
from loaders.blockchain_loader import BlockchainDataLoader
from utils.config_loader import load_whale_tracker_config, get_blockchain_config


class WhaleTrackerScheduler:
    """鯨魚追蹤排程器"""

    def __init__(self, interval_minutes=10):
        """
        初始化排程器

        Args:
            interval_minutes: 執行間隔（分鐘）
        """
        self.interval_minutes = interval_minutes
        self.scheduler = AsyncIOScheduler()
        self.trackers = {}  # 多鏈追蹤器字典 {blockchain: tracker}
        self.loader = None
        self.config = None
        self.running = False

        # 統計資訊
        self.total_runs = 0
        self.total_transactions = 0
        self.last_run_time = None
        self.last_run_count = 0
        self.stats_by_chain = {}  # 各鏈統計 {blockchain: count}

    async def initialize(self):
        """初始化連接器"""
        logger.info("=" * 80)
        logger.info("🐋 多鏈鯨魚追蹤排程器初始化")
        logger.info("=" * 80)

        # 載入配置
        self.config = load_whale_tracker_config()

        logger.info(f"執行間隔: 每 {self.interval_minutes} 分鐘")
        logger.info("")

        # 建立各鏈追蹤器
        blockchains = ['ETH', 'BTC', 'BSC', 'TRX']

        for blockchain in blockchains:
            try:
                bc_config = get_blockchain_config(blockchain, self.config)

                # 根據不同鏈創建對應的追蹤器
                if blockchain == 'ETH':
                    tracker = EthereumWhaleTracker(
                        api_key=bc_config['api_key'],
                        config=bc_config
                    )
                elif blockchain == 'BTC':
                    tracker = BitcoinWhaleTracker(
                        api_key=bc_config.get('api_key'),  # BTC 可能不需要 key
                        config=bc_config
                    )
                elif blockchain == 'BSC':
                    tracker = BSCWhaleTracker(
                        api_key=bc_config['api_key'],
                        config=bc_config
                    )
                elif blockchain == 'TRX':
                    tracker = TronWhaleTracker(
                        api_key=bc_config.get('api_key'),
                        config=bc_config
                    )

                self.trackers[blockchain] = tracker
                self.stats_by_chain[blockchain] = 0

                # 顯示配置信息
                threshold_key = 'BTC' if blockchain == 'BTC' else 'ETH' if blockchain == 'ETH' else 'BNB' if blockchain == 'BSC' else 'TRX'
                threshold = self.config['thresholds'].get(threshold_key, {}).get('amount', 'N/A')
                logger.info(f"  ✅ {blockchain:3s} 追蹤器已啟用 | 門檻: ≥ {threshold}")

            except Exception as e:
                logger.warning(f"  ⚠️  {blockchain} 追蹤器初始化失敗: {e}")

        logger.info("")
        logger.info(f"已啟用 {len(self.trackers)} 條鏈追蹤")

        # 建立資料載入器
        self.loader = BlockchainDataLoader(
            db_config=self.config['database']
        )
        await self.loader.connect()

        logger.success("✅ 初始化完成")

    async def collect_whales(self):
        """收集大額交易（多鏈）"""
        try:
            run_start = datetime.now()
            logger.info("\n" + "=" * 80)
            logger.info(f"[執行 #{self.total_runs + 1}] 開始收集多鏈大額交易")
            logger.info(f"時間: {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)

            # 計算時間範圍（查詢過去的間隔時間 + 緩衝）
            lookback_minutes = self.interval_minutes + 5  # 加 5 分鐘緩衝
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=lookback_minutes)

            logger.info(f"查詢時間範圍: {start_time.strftime('%H:%M')} ~ {end_time.strftime('%H:%M')}")
            logger.info("")

            # 各鏈監控地址配置
            monitored_addresses = {
                'ETH': [
                    "0x28C6c06298d514Db089934071355E5743bf21d60",  # Binance 14
                    "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE",  # Binance
                    "0xdFd5293D8e347dFe59E90eFd55b2956a1343963d",  # Binance Cold
                    "0xA090e606E30bD747d4E6245a1517EbE430F0057e",  # Coinbase
                    "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3",  # Coinbase Cold
                ],
                'BSC': [
                    "0x28C6c06298d514Db089934071355E5743bf21d60",  # Binance (BSC)
                    "0x8894E0a0c962CB723c1976a4421c95949bE2D4E3",  # Binance Hot
                ],
                'BTC': [
                    "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97",  # Binance Cold
                    "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",  # Binance Hot
                ],
                'TRX': [
                    "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE",  # Binance
                ]
            }

            all_whale_txs = []

            # 循環處理各鏈
            for blockchain, tracker in self.trackers.items():
                logger.info(f"🔗 {blockchain} 鏈追蹤:")

                addresses = monitored_addresses.get(blockchain, [])
                chain_txs = []

                for address in addresses:
                    try:
                        # 獲取大額交易
                        whale_txs = await tracker.get_recent_transactions(
                            address=address,
                            limit=50,
                            start_time=start_time,
                            end_time=end_time
                        )

                        if whale_txs:
                            logger.success(f"  ✅ {address[:10]}... 找到 {len(whale_txs)} 筆")
                            chain_txs.extend(whale_txs)

                            # 顯示摘要（前 2 筆）
                            for tx in whale_txs[:2]:
                                amount_str = f"{tx.amount:,.2f} {tx.token_symbol or blockchain}"
                                whale_marker = "🚨" if tx.is_anomaly else "🐋"
                                logger.info(f"      {whale_marker} {amount_str}")

                    except Exception as e:
                        logger.warning(f"  ⚠️  {address[:10]}... 查詢失敗: {e}")
                        continue

                    # 速率限制
                    await asyncio.sleep(0.5)

                if chain_txs:
                    all_whale_txs.extend(chain_txs)
                    self.stats_by_chain[blockchain] += len(chain_txs)
                    logger.info(f"  📊 {blockchain} 本次: {len(chain_txs)} 筆\n")
                else:
                    logger.info(f"  📭 {blockchain} 未發現大額交易\n")

            # 按鏈分組寫入資料庫
            if all_whale_txs:
                logger.info(f"\n💾 寫入 {len(all_whale_txs)} 筆交易到資料庫...")

                # 按區塊鏈分組
                from collections import defaultdict
                txs_by_chain = defaultdict(list)
                for tx in all_whale_txs:
                    txs_by_chain[tx.blockchain].append(tx)

                total_success = 0
                for blockchain, txs in txs_by_chain.items():
                    success_count = await self.loader.insert_whale_transactions(txs)
                    total_success += success_count
                    logger.info(f"  ✅ {blockchain}: {success_count}/{len(txs)} 筆")

                logger.success(f"✅ 總計成功寫入 {total_success} 筆")
                self.last_run_count = total_success
            else:
                logger.info("📭 本次未發現大額交易")
                self.last_run_count = 0

            # 更新統計
            self.total_runs += 1
            self.total_transactions += len(all_whale_txs)
            self.last_run_time = run_start

            duration = (datetime.now() - run_start).total_seconds()
            logger.info(f"\n⏱️  執行耗時: {duration:.2f} 秒")
            logger.info(f"📊 累計: {self.total_runs} 次執行，{self.total_transactions} 筆交易")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"❌ 收集失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def print_status(self):
        """打印當前狀態"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 多鏈鯨魚追蹤排程器狀態")
        logger.info("=" * 80)
        logger.info(f"運行狀態: {'🟢 執行中' if self.running else '🔴 已停止'}")
        logger.info(f"執行間隔: {self.interval_minutes} 分鐘")
        logger.info(f"累計執行: {self.total_runs} 次")
        logger.info(f"累計交易: {self.total_transactions} 筆")
        logger.info("")
        logger.info("各鏈統計:")
        for blockchain, count in self.stats_by_chain.items():
            logger.info(f"  {blockchain}: {count} 筆")
        if self.last_run_time:
            logger.info("")
            logger.info(f"上次執行: {self.last_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"上次收集: {self.last_run_count} 筆")
        logger.info("=" * 80 + "\n")

    async def start(self):
        """啟動排程器"""
        await self.initialize()

        # 設定排程任務
        self.scheduler.add_job(
            self.collect_whales,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id='whale_collector',
            name='收集大額交易',
            replace_existing=True
        )

        # 立即執行一次
        logger.info("🚀 立即執行首次收集...")
        await self.collect_whales()

        # 啟動排程器
        self.scheduler.start()
        self.running = True

        logger.info(f"\n✅ 排程器已啟動！每 {self.interval_minutes} 分鐘執行一次")
        logger.info(f"下次執行時間: {(datetime.now() + timedelta(minutes=self.interval_minutes)).strftime('%H:%M:%S')}")

        # 定期打印狀態（每小時一次）
        self.scheduler.add_job(
            self.print_status,
            trigger=IntervalTrigger(hours=1),
            id='print_status',
            name='打印狀態'
        )

    async def stop(self):
        """停止排程器"""
        logger.info("\n🛑 正在停止排程器...")
        self.running = False

        if self.scheduler.running:
            self.scheduler.shutdown()

        # 關閉所有追蹤器
        for blockchain, tracker in self.trackers.items():
            try:
                await tracker.close()
                logger.info(f"  ✅ {blockchain} 追蹤器已關閉")
            except Exception as e:
                logger.warning(f"  ⚠️  {blockchain} 追蹤器關閉失敗: {e}")

        if self.loader:
            await self.loader.close()

        self.print_status()
        logger.success("✅ 排程器已停止")

    async def run_forever(self):
        """持續運行"""
        await self.start()

        # 等待中斷信號
        try:
            while self.running:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("\n收到停止信號")
        finally:
            await self.stop()


async def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='鯨魚追蹤排程器')
    parser.add_argument(
        '--interval',
        type=int,
        default=10,
        help='執行間隔（分鐘），預設 10 分鐘'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='只執行一次後退出'
    )

    args = parser.parse_args()

    scheduler = WhaleTrackerScheduler(interval_minutes=args.interval)

    if args.once:
        # 單次執行模式
        await scheduler.initialize()
        await scheduler.collect_whales()
        await scheduler.stop()
    else:
        # 持續運行模式
        await scheduler.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
