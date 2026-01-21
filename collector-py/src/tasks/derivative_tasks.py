"""
衍生品任務模組
負責資金費率 (Funding Rate) 與未平倉量 (Open Interest) 的收集
"""
from loguru import logger

def run_funding_rate_task(orchestrator, target_symbols=None):
    """收集資金費率任務"""
    if not target_symbols:
        target_symbols = ['BTCUSDT', 'ETHUSDT']  # 只追蹤 BTC 和 ETH

    for exchange_name, collector in orchestrator.funding_rate_collectors.items():
        try:
            logger.info(f"Collecting funding rates from {exchange_name.upper()}")
            funding_rates = collector.fetch_funding_rates_batch(target_symbols)
            
            for funding_data in funding_rates:
                symbol = funding_data['symbol']
                market_id = orchestrator.db.get_market_id(exchange_name, symbol)
                if market_id:
                    orchestrator.db.insert_funding_rate(market_id, funding_data)
            
            logger.success(f"Collected {len(funding_rates)} funding rates from {exchange_name}")
        except Exception as e:
            logger.error(f"Failed to collect funding rates from {exchange_name}: {e}")

def run_open_interest_task(orchestrator, target_symbols=None):
    """收集未平倉量任務"""
    if not target_symbols:
        target_symbols = ['BTCUSDT', 'ETHUSDT']  # 只追蹤 BTC 和 ETH

    for exchange_name, collector in orchestrator.open_interest_collectors.items():
        try:
            logger.info(f"Collecting open interest from {exchange_name.upper()}")
            oi_records = collector.fetch_open_interest_batch(target_symbols)
            
            for oi_data in oi_records:
                symbol = oi_data['symbol']
                market_id = orchestrator.db.get_market_id(exchange_name, symbol)
                if market_id:
                    orchestrator.db.insert_open_interest(market_id, oi_data)
            
            logger.success(f"Collected {len(oi_records)} open interest records from {exchange_name}")
        except Exception as e:
            logger.error(f"Failed to collect open interest from {exchange_name}: {e}")
