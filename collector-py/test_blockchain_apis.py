"""
測試所有區塊鏈 API 連接

驗證 Etherscan, BscScan, Blockchain.com 等 API 是否正常運作
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 添加 src 到 Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from connectors.ethereum_whale_tracker import EthereumWhaleTracker
from connectors.bsc_whale_tracker import BSCWhaleTracker
from connectors.bitcoin_whale_tracker import BitcoinWhaleTracker
from utils.config_loader import load_whale_tracker_config, get_blockchain_config


async def test_ethereum_api():
    """測試 Etherscan API"""
    logger.info("=" * 60)
    logger.info("測試 Etherscan API (Ethereum)")
    logger.info("=" * 60)

    try:
        config = load_whale_tracker_config()
        eth_config = get_blockchain_config('ETH', config)

        logger.info(f"API URL: {eth_config['api_url']}")
        logger.info(f"API Key: {eth_config['api_key'][:10]}..." if eth_config['api_key'] else "No API Key")

        tracker = EthereumWhaleTracker(
            api_key=eth_config['api_key'],
            config=eth_config
        )

        # 測試 1: 獲取 ETH 價格
        logger.info("\n[測試 1] 獲取 ETH 價格")
        eth_price = await tracker.get_usd_price(None)
        logger.success(f"✓ ETH 當前價格: ${eth_price}")

        # 測試 2: 獲取 Binance 熱錢包的最近交易
        binance_hot_wallet = '0x28C6c06298d514Db089934071355E5743bf21d60'
        logger.info(f"\n[測試 2] 查詢 Binance 熱錢包大額交易: {binance_hot_wallet[:10]}...")

        txs = await tracker.get_recent_transactions(
            address=binance_hot_wallet,
            limit=5
        )

        logger.success(f"✓ 找到 {len(txs)} 筆大額交易")

        if txs:
            for i, tx in enumerate(txs[:3], 1):
                logger.info(f"""
                交易 {i}:
                  哈希: {tx.tx_hash[:10]}...
                  時間: {tx.timestamp}
                  金額: {tx.amount:.4f} {tx.token_symbol or 'ETH'}
                  從: {tx.from_address[:10]}...
                  到: {tx.to_address[:10]}...
                  大額: {tx.is_whale}, 異常: {tx.is_anomaly}
                """)

        await tracker.close()
        logger.success("✓ Etherscan API 測試通過\n")
        return True

    except Exception as e:
        logger.error(f"✗ Etherscan API 測試失敗: {e}\n")
        return False


async def test_bsc_api():
    """測試 BscScan API"""
    logger.info("=" * 60)
    logger.info("測試 BscScan API (Binance Smart Chain)")
    logger.info("=" * 60)

    try:
        config = load_whale_tracker_config()
        bsc_config = get_blockchain_config('BSC', config)

        logger.info(f"API URL: {bsc_config['api_url']}")
        logger.info(f"API Key: {bsc_config['api_key'][:10]}..." if bsc_config['api_key'] else "No API Key")

        tracker = BSCWhaleTracker(
            api_key=bsc_config['api_key'],
            config=bsc_config
        )

        # 測試 1: 獲取 BNB 價格
        logger.info("\n[測試 1] 獲取 BNB 價格")
        bnb_price = await tracker.get_usd_price(None)
        logger.success(f"✓ BNB 當前價格: ${bnb_price}")

        # 測試 2: 獲取 Binance 在 BSC 上的熱錢包交易
        binance_bsc_wallet = '0x8894E0a0c962CB723c1976a4421c95949bE2D4E3'  # Binance 14
        logger.info(f"\n[測試 2] 查詢 Binance BSC 熱錢包大額交易: {binance_bsc_wallet[:10]}...")

        txs = await tracker.get_recent_transactions(
            address=binance_bsc_wallet,
            limit=5
        )

        logger.success(f"✓ 找到 {len(txs)} 筆大額交易")

        if txs:
            for i, tx in enumerate(txs[:3], 1):
                logger.info(f"""
                交易 {i}:
                  哈希: {tx.tx_hash[:10]}...
                  時間: {tx.timestamp}
                  金額: {tx.amount:.4f} {tx.token_symbol or 'BNB'}
                  從: {tx.from_address[:10]}...
                  到: {tx.to_address[:10]}...
                  大額: {tx.is_whale}, 異常: {tx.is_anomaly}
                """)

        await tracker.close()
        logger.success("✓ BscScan API 測試通過\n")
        return True

    except Exception as e:
        logger.error(f"✗ BscScan API 測試失敗: {e}\n")
        return False


async def test_bitcoin_api():
    """測試 Blockchain.com API"""
    logger.info("=" * 60)
    logger.info("測試 Blockchain.com API (Bitcoin)")
    logger.info("=" * 60)

    try:
        config = load_whale_tracker_config()
        btc_config = get_blockchain_config('BTC', config)

        logger.info(f"API URL: {btc_config['api_url']}")
        logger.info("注意: Blockchain.com 公開 API 不需要 API Key")

        tracker = BitcoinWhaleTracker(
            api_key=None,
            config=btc_config
        )

        # 測試 1: 獲取 BTC 價格
        logger.info("\n[測試 1] 獲取 BTC 價格")
        btc_price = await tracker.get_usd_price(None)
        logger.success(f"✓ BTC 當前價格: ${btc_price}")

        # 測試 2: 獲取大額交易（使用 Blockchair API）
        logger.info("\n[測試 2] 查詢全網大額 BTC 交易（使用 Blockchair）")

        txs = await tracker.get_recent_transactions(limit=5)

        logger.success(f"✓ 找到 {len(txs)} 筆大額交易")

        if txs:
            for i, tx in enumerate(txs[:3], 1):
                logger.info(f"""
                交易 {i}:
                  哈希: {tx.tx_hash[:10]}...
                  時間: {tx.timestamp}
                  金額: {tx.amount:.4f} BTC
                  大額: {tx.is_whale}, 異常: {tx.is_anomaly}
                """)

        await tracker.close()
        logger.success("✓ Blockchain.com API 測試通過\n")
        return True

    except Exception as e:
        logger.error(f"✗ Blockchain.com API 測試失敗: {e}\n")
        return False


async def main():
    """主測試函數"""
    logger.info("\n" + "=" * 60)
    logger.info("開始測試所有區塊鏈 API")
    logger.info("=" * 60 + "\n")

    results = {
        'Etherscan (ETH)': False,
        'BscScan (BSC)': False,
        'Blockchain.com (BTC)': False,
    }

    # 測試 Etherscan
    results['Etherscan (ETH)'] = await test_ethereum_api()

    # 測試 BscScan
    results['BscScan (BSC)'] = await test_bsc_api()

    # 測試 Blockchain.com
    results['Blockchain.com (BTC)'] = await test_bitcoin_api()

    # 總結
    logger.info("=" * 60)
    logger.info("測試結果總結")
    logger.info("=" * 60)

    for api_name, success in results.items():
        status = "✓ 通過" if success else "✗ 失敗"
        logger.info(f"{api_name}: {status}")

    all_passed = all(results.values())

    if all_passed:
        logger.success("\n所有 API 測試通過! 🎉")
    else:
        logger.warning("\n部分 API 測試失敗，請檢查配置")

    return all_passed


if __name__ == '__main__':
    # 配置 logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # 運行測試
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
