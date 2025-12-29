#!/usr/bin/env python3
"""
鯨魚追蹤收集器啟動腳本
定期收集 Ethereum/BSC/Bitcoin 大額交易
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from connectors.ethereum_whale_tracker import EthereumWhaleTracker
from loaders.blockchain_loader import BlockchainDataLoader
from utils.config_loader import load_whale_tracker_config, get_blockchain_config


async def collect_ethereum_whales(tracker, loader, lookback_hours=1):
    """收集 Ethereum 大額交易"""
    try:
        logger.info("=" * 80)
        logger.info(f"開始收集 Ethereum 大額交易（過去 {lookback_hours} 小時）")
        logger.info("=" * 80)

        # 計算時間範圍
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=lookback_hours)

        # 定義要監控的重要地址（交易所熱錢包）
        monitored_addresses = [
            "0x28C6c06298d514Db089934071355E5743bf21d60",  # Binance 14
            "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE",  # Binance
            "0xdFd5293D8e347dFe59E90eFd55b2956a1343963d",  # Binance Cold Wallet
            "0xA090e606E30bD747d4E6245a1517EbE430F0057e",  # Coinbase
            "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3",  # Coinbase Cold Wallet
        ]

        all_whale_txs = []

        for address in monitored_addresses:
            logger.info(f"查詢地址: {address[:10]}...")

            try:
                # 獲取最近交易（已自動過濾非大額交易）
                whale_txs = await tracker.get_recent_transactions(
                    address=address,
                    limit=50,
                    start_time=start_time,
                    end_time=end_time
                )

                if whale_txs:
                    logger.success(f"✅ 找到 {len(whale_txs)} 筆大額交易")
                    all_whale_txs.extend(whale_txs)

                    # 顯示前 3 筆
                    for i, tx in enumerate(whale_txs[:3], 1):
                        amount_str = f"{tx.amount:,.4f} {tx.token_symbol or 'ETH'}"
                        usd_str = f"(${tx.usd_value:,.2f})" if tx.usd_value else ""
                        whale_marker = "🚨" if tx.is_anomaly else "🐋"
                        logger.info(f"  {whale_marker} 交易 {i}: {amount_str} {usd_str}")
                else:
                    logger.info(f"  未找到大額交易")

            except Exception as e:
                logger.error(f"查詢地址 {address} 失敗: {e}")
                continue

            # 速率限制
            await asyncio.sleep(0.5)

        # 寫入資料庫
        if all_whale_txs:
            logger.info(f"\n開始寫入 {len(all_whale_txs)} 筆交易到資料庫...")
            success_count = await loader.insert_whale_transactions(all_whale_txs)
            logger.success(f"✅ 成功寫入 {success_count} 筆交易")
        else:
            logger.warning("未找到任何大額交易")

        return len(all_whale_txs)

    except Exception as e:
        logger.error(f"收集 Ethereum 交易失敗: {e}")
        raise


async def main():
    """主函數"""
    logger.info("🐋 鯨魚追蹤收集器啟動")
    logger.info(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 載入配置
    config = load_whale_tracker_config()
    eth_config = get_blockchain_config('ETH', config)

    logger.info(f"API Key: {eth_config['api_key'][:10]}...")
    logger.info(f"門檻: ETH ≥ {config['thresholds']['ETH']['amount']}")

    # 建立追蹤器和載入器
    tracker = EthereumWhaleTracker(
        api_key=eth_config['api_key'],
        config=eth_config
    )

    loader = BlockchainDataLoader(
        db_config=config['database']
    )
    await loader.connect()

    try:
        # 收集交易
        total = await collect_ethereum_whales(tracker, loader, lookback_hours=1)

        logger.info("\n" + "=" * 80)
        logger.success(f"✅ 鯨魚追蹤收集完成！共收集 {total} 筆大額交易")
        logger.info("=" * 80)

    finally:
        await tracker.close()
        await loader.close()


if __name__ == "__main__":
    asyncio.run(main())
