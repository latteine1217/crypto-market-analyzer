"""
測試 Funding Rate 和 Open Interest Collectors
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from connectors.funding_rate_collector import FundingRateCollector
from connectors.open_interest_collector import OpenInterestCollector
from loaders.db_loader import DatabaseLoader
from loguru import logger


def test_funding_rate_collector():
    """測試資金費率收集器"""
    logger.info("=" * 50)
    logger.info("Testing Funding Rate Collector")
    logger.info("=" * 50)
    
    # 初始化收集器
    collector = FundingRateCollector('binance')
    
    # 測試單一交易對
    symbol = 'BTCUSDT'
    logger.info(f"\n1. Fetching current funding rate for {symbol}")
    try:
        funding_rate = collector.fetch_funding_rate(symbol)
        if funding_rate:
            logger.info(f"✓ Funding Rate: {funding_rate['funding_rate']}")
            logger.info(f"✓ Daily Rate: {funding_rate['funding_rate_daily']}")
            logger.info(f"✓ Funding Time: {funding_rate['funding_time']}")
            logger.info(f"✓ Next Funding: {funding_rate['next_funding_time']}")
            logger.info(f"✓ Mark Price: {funding_rate['mark_price']}")
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
    
    # 測試歷史資金費率
    logger.info(f"\n2. Fetching funding rate history for {symbol}")
    try:
        history = collector.fetch_funding_rate_history(symbol, limit=5)
        logger.info(f"✓ Fetched {len(history)} historical records")
        if history:
            logger.info(f"  Latest: rate={history[0]['funding_rate']}, time={history[0]['funding_time']}")
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
    
    # 測試批次抓取
    logger.info("\n3. Batch fetching funding rates")
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    try:
        batch_results = collector.fetch_funding_rates_batch(symbols)
        logger.info(f"✓ Fetched {len(batch_results)} funding rates")
        for result in batch_results:
            logger.info(f"  {result['symbol']}: {result['funding_rate']}")
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
    
    # 測試取得可用交易對
    logger.info("\n4. Getting available perpetual symbols")
    try:
        available = collector.get_available_symbols()
        logger.info(f"✓ Found {len(available)} perpetual symbols")
        logger.info(f"  First 10: {available[:10]}")
    except Exception as e:
        logger.error(f"✗ Failed: {e}")


def test_open_interest_collector():
    """測試未平倉量收集器"""
    logger.info("\n" + "=" * 50)
    logger.info("Testing Open Interest Collector")
    logger.info("=" * 50)
    
    # 初始化收集器
    collector = OpenInterestCollector('binance')
    
    # 測試單一交易對
    symbol = 'BTCUSDT'
    logger.info(f"\n1. Fetching current open interest for {symbol}")
    try:
        oi_data = collector.fetch_open_interest(symbol)
        if oi_data:
            logger.info(f"✓ Open Interest: {oi_data['open_interest']}")
            if oi_data.get('open_interest_usd'):
                logger.info(f"✓ OI USD: ${oi_data['open_interest_usd']:,.2f}")
            if oi_data.get('price'):
                logger.info(f"✓ Price: ${oi_data['price']:,.2f}")
            logger.info(f"✓ Timestamp: {oi_data['timestamp']}")
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
    
    # 測試批次抓取
    logger.info("\n2. Batch fetching open interest")
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    try:
        batch_results = collector.fetch_open_interest_batch(symbols)
        logger.info(f"✓ Fetched {len(batch_results)} open interest records")
        for result in batch_results:
            usd_str = f"${result['open_interest_usd']:,.0f}" if result.get('open_interest_usd') else 'N/A'
            logger.info(
                f"  {result['symbol']}: "
                f"OI={result['open_interest']:,.2f}, "
                f"USD={usd_str}"
            )
    except Exception as e:
        logger.error(f"✗ Failed: {e}")


def test_database_integration():
    """測試資料庫整合"""
    logger.info("\n" + "=" * 50)
    logger.info("Testing Database Integration")
    logger.info("=" * 50)
    
    # 初始化
    db = DatabaseLoader()
    fr_collector = FundingRateCollector('binance')
    oi_collector = OpenInterestCollector('binance')
    
    symbol = 'BTCUSDT'
    
    # 取得 market_id
    logger.info(f"\n1. Getting market_id for {symbol}")
    market_id = db.get_market_id('binance', symbol)
    logger.info(f"✓ Market ID: {market_id}")
    
    # 測試插入資金費率
    logger.info("\n2. Testing funding rate insertion")
    try:
        funding_data = fr_collector.fetch_funding_rate(symbol)
        if funding_data:
            record_id = db.insert_funding_rate(market_id, funding_data)
            logger.info(f"✓ Inserted funding rate #{record_id}")
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
    
    # 測試插入未平倉量
    logger.info("\n3. Testing open interest insertion")
    try:
        oi_data = oi_collector.fetch_open_interest(symbol)
        if oi_data:
            record_id = db.insert_open_interest(market_id, oi_data)
            logger.info(f"✓ Inserted open interest #{record_id}")
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
    
    # 測試批次插入
    logger.info("\n4. Testing batch insertion")
    symbols = ['BTCUSDT', 'ETHUSDT']
    try:
        for sym in symbols:
            market_id = db.get_market_id('binance', sym)
            
            # 批次插入資金費率歷史
            history = fr_collector.fetch_funding_rate_history(sym, limit=3)
            if history:
                count = db.insert_funding_rate_batch(market_id, history)
                logger.info(f"✓ Inserted {count} funding rates for {sym}")
    except Exception as e:
        logger.error(f"✗ Failed: {e}")


if __name__ == '__main__':
    # 設定日誌
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # 執行測試
    test_funding_rate_collector()
    test_open_interest_collector()
    test_database_integration()
    
    logger.info("\n" + "=" * 50)
    logger.info("All tests completed!")
    logger.info("=" * 50)
