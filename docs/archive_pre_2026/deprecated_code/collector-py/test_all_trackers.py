"""
測試所有區塊鏈追蹤器

驗證基本功能：價格 API、門檻邏輯、配置載入
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from connectors.ethereum_whale_tracker import EthereumWhaleTracker
from connectors.bsc_whale_tracker import BSCWhaleTracker
from connectors.bitcoin_whale_tracker import BitcoinWhaleTracker
from connectors.tron_whale_tracker import TronWhaleTracker
from utils.config_loader import load_whale_tracker_config, get_blockchain_config
from loguru import logger

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level="INFO"
)


async def test_tracker(tracker_class, blockchain_name: str):
    """
    測試單個追蹤器

    Args:
        tracker_class: 追蹤器類別
        blockchain_name: 區塊鏈名稱
    """
    logger.info(f"\n{'=' * 70}")
    logger.info(f"測試 {blockchain_name} 追蹤器")
    logger.info(f"{'=' * 70}")

    config = load_whale_tracker_config()
    chain_config = get_blockchain_config(blockchain_name, config)

    tracker = tracker_class(
        api_key=chain_config.get('api_key', 'test'),
        config=chain_config
    )

    results = {
        '價格查詢': False,
        '門檻邏輯': False,
    }

    try:
        # 測試 1: 價格查詢
        logger.info(f"\n📊 測試 1: 價格查詢")
        try:
            price = await tracker.get_usd_price(None)
            if price > 0:
                logger.success(f"✅ {blockchain_name} 當前價格: ${price:,.2f}")
                results['價格查詢'] = True
            else:
                logger.warning(f"⚠️  價格為 0，可能是 API 問題")
        except Exception as e:
            logger.error(f"❌ 價格查詢失敗: {e}")

        # 測試 2: 門檻邏輯
        logger.info(f"\n🎯 測試 2: 門檻邏輯")
        try:
            # 測試不同金額
            test_amounts = {
                'ETH': [(100, False, False), (500, True, False), (10000, True, True)],
                'BSC': [(100, False, False), (1000, True, False), (10000, True, True)],
                'BTC': [(10, False, False), (50, True, False), (1000, True, True)],
                'TRX': [(1000000, False, False), (5000000, True, False), (50000000, True, True)],
            }

            amounts = test_amounts.get(blockchain_name, [])
            all_correct = True

            for amount, expected_whale, expected_anomaly in amounts:
                is_whale, is_anomaly = await tracker.is_large_transaction(
                    Decimal(str(amount)),
                    None
                )

                status = ""
                if is_anomaly:
                    status = "🚨 異常"
                elif is_whale:
                    status = "🐋 巨鯨"
                else:
                    status = "⚪ 普通"

                correct = (is_whale == expected_whale and is_anomaly == expected_anomaly)
                symbol = "✅" if correct else "❌"

                logger.info(f"  {symbol} {amount:>10,} → {status}")

                if not correct:
                    all_correct = False

            if all_correct:
                logger.success(f"✅ 門檻邏輯正確")
                results['門檻邏輯'] = True
            else:
                logger.warning(f"⚠️  門檻邏輯有誤")

        except Exception as e:
            logger.error(f"❌ 門檻邏輯測試失敗: {e}")

    finally:
        await tracker.close()

    # 匯總結果
    logger.info(f"\n{'─' * 70}")
    logger.info(f"{blockchain_name} 測試結果:")
    for test_name, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        logger.info(f"  {test_name:15s} → {status}")

    return all(results.values())


async def main():
    """運行所有測試"""
    logger.info("🚀 開始測試所有區塊鏈追蹤器\n")

    trackers = [
        (EthereumWhaleTracker, 'ETH'),
        (BSCWhaleTracker, 'BSC'),
        (BitcoinWhaleTracker, 'BTC'),
        (TronWhaleTracker, 'TRX'),
    ]

    results = {}

    for tracker_class, blockchain_name in trackers:
        try:
            passed = await test_tracker(tracker_class, blockchain_name)
            results[blockchain_name] = passed
            await asyncio.sleep(1)  # 避免 API 速率限制
        except Exception as e:
            logger.error(f"❌ {blockchain_name} 追蹤器測試異常: {e}")
            results[blockchain_name] = False

    # 總結
    logger.info(f"\n{'=' * 70}")
    logger.info("📊 所有追蹤器測試總結")
    logger.info(f"{'=' * 70}\n")

    all_passed = True
    for blockchain, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        logger.info(f"  {blockchain:15s} → {status}")
        if not passed:
            all_passed = False

    logger.info(f"\n{'=' * 70}")
    if all_passed:
        logger.success("🎉 所有追蹤器測試通過！")
        logger.info("\n下一步:")
        logger.info("  1. 註冊 API keys (Etherscan, BscScan 等)")
        logger.info("  2. 建立主收集程式")
        logger.info("  3. 創建 Dashboard 頁面")
    else:
        logger.warning("⚠️  部分追蹤器測試失敗")
        logger.info("\n建議:")
        logger.info("  - 檢查配置文件 configs/whale_tracker.yml")
        logger.info("  - 確認網路連接正常")
        logger.info("  - 查看上方詳細錯誤訊息")


if __name__ == '__main__':
    asyncio.run(main())
