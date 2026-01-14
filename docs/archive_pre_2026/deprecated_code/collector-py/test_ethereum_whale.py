"""
測試 Ethereum 巨鯨追蹤器

執行方式:
python test_ethereum_whale.py
"""
import asyncio
import sys
from pathlib import Path

# 添加 src 到 Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from connectors.ethereum_whale_tracker import EthereumWhaleTracker
from utils.config_loader import load_whale_tracker_config, get_blockchain_config
from loguru import logger

# 配置日誌
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


async def test_price_api():
    """測試 1: 價格 API"""
    logger.info("=" * 60)
    logger.info("測試 1: 價格 API（CoinGecko）")
    logger.info("=" * 60)

    # 載入配置
    config = load_whale_tracker_config()
    eth_config = get_blockchain_config('ETH', config)

    tracker = EthereumWhaleTracker(
        api_key=eth_config.get('api_key', 'test'),
        config=eth_config
    )

    try:
        # 獲取 ETH 價格
        logger.info("查詢 ETH 價格...")
        eth_price = await tracker.get_usd_price(None)
        logger.success(f"✅ ETH 當前價格: ${eth_price:,.2f}")

        # 獲取 USDT 價格
        logger.info("查詢 USDT 價格...")
        usdt_price = await tracker.get_usd_price('USDT')
        logger.success(f"✅ USDT 當前價格: ${usdt_price:.4f}")

        # 獲取 USDC 價格
        logger.info("查詢 USDC 價格...")
        usdc_price = await tracker.get_usd_price('USDC')
        logger.success(f"✅ USDC 當前價格: ${usdc_price:.4f}")

        return True

    except Exception as e:
        logger.error(f"❌ 價格 API 測試失敗: {e}")
        return False

    finally:
        await tracker.close()


async def test_threshold_logic():
    """測試 2: 大額交易判斷邏輯"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 2: 大額交易判斷邏輯")
    logger.info("=" * 60)

    config = load_whale_tracker_config()
    eth_config = get_blockchain_config('ETH', config)

    tracker = EthereumWhaleTracker(
        api_key=eth_config.get('api_key', 'test'),
        config=eth_config
    )

    try:
        from decimal import Decimal

        test_cases = [
            (Decimal('100'), 'ETH', "100 ETH"),
            (Decimal('500'), 'ETH', "500 ETH"),
            (Decimal('10000'), 'ETH', "10000 ETH"),
            (Decimal('100000'), 'USDT', "100K USDT"),
            (Decimal('500000'), 'USDT', "500K USDT"),
            (Decimal('10000000'), 'USDT', "10M USDT"),
        ]

        logger.info(f"門檻設定: ETH ≥500 (whale), ≥10000 (anomaly)")
        logger.info(f"門檻設定: USDT ≥500K (whale), ≥10M (anomaly)")
        logger.info("")

        for amount, symbol, desc in test_cases:
            is_whale, is_anomaly = await tracker.is_large_transaction(amount, symbol)

            status = ""
            if is_anomaly:
                status = "🚨 異常超大額"
            elif is_whale:
                status = "🐋 巨鯨交易"
            else:
                status = "⚪ 普通交易"

            logger.info(f"{desc:20s} → {status}")

        return True

    except Exception as e:
        logger.error(f"❌ 門檻邏輯測試失敗: {e}")
        return False

    finally:
        await tracker.close()


async def test_etherscan_api():
    """測試 3: Etherscan API（需要有效的 API key）"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 3: Etherscan API - 查詢 Binance 熱錢包")
    logger.info("=" * 60)

    config = load_whale_tracker_config()
    eth_config = get_blockchain_config('ETH', config)

    api_key = eth_config.get('api_key', '')

    if not api_key or api_key == 'YourEtherscanAPIKey':
        logger.warning("⚠️  未設定 Etherscan API Key")
        logger.info("請到 https://etherscan.io/myapikey 註冊並獲取免費 API key")
        logger.info("然後設定環境變數: export ETHERSCAN_API_KEY='your_key_here'")
        logger.info("或直接在 configs/whale_tracker.yml 中修改")
        return False

    tracker = EthereumWhaleTracker(
        api_key=api_key,
        config=eth_config
    )

    try:
        # Binance 熱錢包地址
        binance_hot_wallet = '0x28C6c06298d514Db089934071355E5743bf21d60'

        logger.info(f"查詢地址: {binance_hot_wallet}")
        logger.info(f"標籤: Binance Hot Wallet")
        logger.info("")

        # 查詢餘額
        logger.info("查詢 ETH 餘額...")
        balance = await tracker.get_address_balance(binance_hot_wallet)
        logger.success(f"✅ 餘額: {balance:,.4f} ETH")

        # 查詢最近交易
        logger.info("查詢最近 10 筆大額交易...")
        txs = await tracker.get_recent_transactions(
            address=binance_hot_wallet,
            limit=10
        )

        logger.success(f"✅ 找到 {len(txs)} 筆大額交易\n")

        if txs:
            logger.info("最近 5 筆大額交易:")
            logger.info("-" * 100)

            for i, tx in enumerate(txs[:5], 1):
                symbol = tx.token_symbol or 'ETH'
                whale_status = "🚨" if tx.is_anomaly else "🐋"

                logger.info(f"{i}. {whale_status} {tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"   TX: {tx.tx_hash[:20]}...")
                logger.info(f"   金額: {tx.amount:,.4f} {symbol}")
                if tx.amount_usd:
                    logger.info(f"   美元: ${tx.amount_usd:,.2f}")
                logger.info(f"   從: {tx.from_address[:20]}...")
                logger.info(f"   到: {tx.to_address[:20]}...")
                logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ Etherscan API 測試失敗: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    finally:
        await tracker.close()


async def test_transaction_enrichment():
    """測試 4: 交易豐富化（交易所標記）"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 4: 交易豐富化 - 交易所地址識別")
    logger.info("=" * 60)

    config = load_whale_tracker_config()
    eth_config = get_blockchain_config('ETH', config)

    tracker = EthereumWhaleTracker(
        api_key=eth_config.get('api_key', 'test'),
        config=eth_config
    )

    try:
        from connectors.blockchain_base import WhaleTransaction
        from decimal import Decimal
        from datetime import datetime

        # 模擬交易所地址庫
        exchange_addresses = {
            '0x28c6c06298d514db089934071355e5743bf21d60': 'Binance',
            '0x21a31ee1afc51d94c2efccaa2092ad1028285549': 'Binance',
            '0x71660c4005ba85c37ccec55d0c4493e66fe775d3': 'Coinbase',
        }

        # 測試案例
        test_cases = [
            {
                'name': '流入 Binance',
                'from': '0x1234567890abcdef1234567890abcdef12345678',
                'to': '0x28c6c06298d514db089934071355e5743bf21d60',
            },
            {
                'name': '流出 Coinbase',
                'from': '0x71660c4005ba85c37ccec55d0c4493e66fe775d3',
                'to': '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
            },
            {
                'name': '非交易所轉帳',
                'from': '0x1111111111111111111111111111111111111111',
                'to': '0x2222222222222222222222222222222222222222',
            },
        ]

        for test in test_cases:
            tx = WhaleTransaction(
                blockchain='ETH',
                tx_hash='0xtest123',
                timestamp=datetime.now(),
                from_address=test['from'],
                to_address=test['to'],
                amount=Decimal('500')
            )

            # 豐富交易資訊
            enriched_tx = await tracker.enrich_transaction(tx, exchange_addresses)

            logger.info(f"\n測試: {test['name']}")
            logger.info(f"  流入交易所: {'✅' if enriched_tx.is_exchange_inflow else '❌'}")
            logger.info(f"  流出交易所: {'✅' if enriched_tx.is_exchange_outflow else '❌'}")
            logger.info(f"  交易所名稱: {enriched_tx.exchange_name or 'N/A'}")
            logger.info(f"  方向: {enriched_tx.direction.value}")

        return True

    except Exception as e:
        logger.error(f"❌ 交易豐富化測試失敗: {e}")
        return False

    finally:
        await tracker.close()


async def main():
    """運行所有測試"""
    logger.info("🚀 開始測試 Ethereum 巨鯨追蹤器")
    logger.info("")

    results = {
        '價格 API': False,
        '門檻邏輯': False,
        'Etherscan API': False,
        '交易豐富化': False,
    }

    # 測試 1: 價格 API
    results['價格 API'] = await test_price_api()
    await asyncio.sleep(1)

    # 測試 2: 門檻邏輯
    results['門檻邏輯'] = await test_threshold_logic()
    await asyncio.sleep(1)

    # 測試 3: Etherscan API（可能失敗，如果沒有 API key）
    results['Etherscan API'] = await test_etherscan_api()
    await asyncio.sleep(1)

    # 測試 4: 交易豐富化
    results['交易豐富化'] = await test_transaction_enrichment()

    # 匯總結果
    logger.info("\n" + "=" * 60)
    logger.info("測試結果匯總")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        logger.info(f"{test_name:20s} → {status}")
        if not passed:
            all_passed = False

    logger.info("")
    if all_passed:
        logger.success("🎉 所有測試通過！")
    else:
        logger.warning("⚠️  部分測試失敗，請檢查上方錯誤訊息")

    logger.info("\n下一步:")
    logger.info("1. 如果 Etherscan API 測試失敗，請設定 API key")
    logger.info("2. 實作資料庫寫入功能")
    logger.info("3. 建立 Dashboard 頁面展示巨鯨交易")


if __name__ == '__main__':
    asyncio.run(main())
