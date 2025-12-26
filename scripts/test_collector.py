#!/usr/bin/env python3
"""
Collector 功能測試腳本
驗證：
1. 資料庫連線
2. Binance API 連線
3. 資料抓取與寫入
"""
import sys
from pathlib import Path

# 添加 collector-py/src 到 Python 路徑
collector_src = Path(__file__).parent.parent / "collector-py" / "src"
sys.path.insert(0, str(collector_src))

from connectors.binance_rest import BinanceRESTConnector
from loaders.db_loader import DatabaseLoader
from loguru import logger

# 配置日誌
logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)


def test_binance_connection():
    """測試 Binance API 連線"""
    logger.info("=== 測試 1: Binance API 連線 ===")
    try:
        connector = BinanceRESTConnector()

        # 取得市場資訊
        market_info = connector.get_market_info("BTC/USDT")
        logger.success(f"✓ 成功連線 Binance")
        logger.info(f"  市場: {market_info['symbol']}")
        logger.info(f"  基礎貨幣: {market_info['base']}")
        logger.info(f"  報價貨幣: {market_info['quote']}")
        logger.info(f"  狀態: {'活躍' if market_info['active'] else '非活躍'}")

        return True
    except Exception as e:
        logger.error(f"✗ Binance 連線失敗: {e}")
        return False


def test_database_connection():
    """測試資料庫連線"""
    logger.info("\n=== 測試 2: 資料庫連線 ===")
    try:
        db = DatabaseLoader()

        # 取得 market_id
        market_id = db.get_market_id("binance", "BTC/USDT")
        if market_id:
            logger.success(f"✓ 成功連線資料庫")
            logger.info(f"  Market ID: {market_id}")
        else:
            logger.warning("⚠ 資料庫連線成功，但找不到 BTC/USDT 市場")

        db.close()
        return True
    except Exception as e:
        logger.error(f"✗ 資料庫連線失敗: {e}")
        return False


def test_data_fetch_and_store():
    """測試資料抓取與儲存"""
    logger.info("\n=== 測試 3: 資料抓取與儲存 ===")
    try:
        # 初始化連接器
        connector = BinanceRESTConnector()
        db = DatabaseLoader()

        # 取得 market_id
        market_id = db.get_market_id("binance", "BTC/USDT")
        if not market_id:
            logger.error("✗ 無法取得 market_id")
            return False

        # 抓取最近 10 根 K 線
        logger.info("  正在抓取 OHLCV 資料...")
        ohlcv = connector.fetch_ohlcv(
            symbol="BTC/USDT",
            timeframe="1m",
            limit=10
        )

        if not ohlcv:
            logger.error("✗ 未抓取到資料")
            return False

        logger.success(f"✓ 成功抓取 {len(ohlcv)} 根 K 線")

        # 顯示最新一根 K 線
        latest = ohlcv[-1]
        timestamp, o, h, l, c, v = latest[:6]
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)

        logger.info(f"  最新 K 線:")
        logger.info(f"    時間: {dt}")
        logger.info(f"    開盤: ${o:,.2f}")
        logger.info(f"    最高: ${h:,.2f}")
        logger.info(f"    最低: ${l:,.2f}")
        logger.info(f"    收盤: ${c:,.2f}")
        logger.info(f"    成交量: {v:.4f} BTC")

        # 寫入資料庫
        logger.info("  正在寫入資料庫...")
        count = db.insert_ohlcv_batch(market_id, "1m", ohlcv)
        logger.success(f"✓ 成功寫入 {count} 筆資料")

        # 驗證寫入
        latest_time = db.get_latest_ohlcv_time(market_id, "1m")
        if latest_time:
            logger.success(f"✓ 資料庫最新時間: {latest_time}")

        db.close()
        return True

    except Exception as e:
        logger.error(f"✗ 資料抓取失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函數"""
    logger.info("="*60)
    logger.info("Crypto Market Analyzer - Collector 功能測試")
    logger.info("="*60)

    results = []

    # 執行測試
    results.append(("Binance API 連線", test_binance_connection()))
    results.append(("資料庫連線", test_database_connection()))
    results.append(("資料抓取與儲存", test_data_fetch_and_store()))

    # 總結
    logger.info("\n" + "="*60)
    logger.info("測試總結")
    logger.info("="*60)

    for test_name, result in results:
        status = "✓ 通過" if result else "✗ 失敗"
        color = "green" if result else "red"
        logger.info(f"  {test_name}: {status}")

    total_passed = sum(1 for _, result in results if result)
    total_tests = len(results)

    logger.info(f"\n總計: {total_passed}/{total_tests} 測試通過")

    if total_passed == total_tests:
        logger.success("\n✓ 所有測試通過！專案運行正常。")
        return 0
    else:
        logger.error(f"\n✗ {total_tests - total_passed} 個測試失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
