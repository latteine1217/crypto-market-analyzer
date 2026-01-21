
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from loguru import logger

def test_manual():
    logger.info("Starting Manual Liquidation Test (No DB)...")
    
    # Patch DatabaseLoader to avoid DB connection error during LiquidationCollector init
    with patch('connectors.liquidation_collector.DatabaseLoader') as MockLoader:
        # Import inside patch to ensure patch applies if module was not already loaded, 
        # or if it was loaded, patch where it is used.
        # Since we imported LiquidationCollector at top, we should patch where it is imported FROM
        # or patch the class in the module.
        # Ideally, we patch 'loaders.db_loader.DatabaseLoader' but LiquidationCollector imports it.
        # Let's import inside function to be safe or rely on patch target string.
        
        from connectors.liquidation_collector import LiquidationCollector
        
        collector = LiquidationCollector()
        # collector.loader is now a Mock instance
        collector.loader.insert_liquidations_batch = MagicMock(side_effect=lambda data: print(f"Mock Insert: {len(data)} records"))
        
        # Run for BTC and ETH
        symbols = ['BTC/USDT', 'ETH/USDT']
        
        # 1. Test Binance
        logger.info("--- Testing Binance ---")
        data_binance = []
        for s in symbols:
            res = collector.collect_binance(s)
            logger.info(f"Binance {s}: Got {len(res)} records")
            if res:
                logger.info(f"Sample: {res[0]}")
            data_binance.extend(res)
            
        # 2. Test Bybit
        logger.info("--- Testing Bybit ---")
        data_bybit = []
        for s in symbols:
            res = collector.collect_bybit(s)
            logger.info(f"Bybit {s}: Got {len(res)} records")
            if res:
                logger.info(f"Sample: {res[0]}")
            data_bybit.extend(res)

        # 3. Test OKX
        logger.info("--- Testing OKX ---")
        data_okx = []
        for s in symbols:
            res = collector.collect_okx(s)
            logger.info(f"OKX {s}: Got {len(res)} records")
            if res:
                logger.info(f"Sample: {res[0]}")
            data_okx.extend(res)

    logger.info("Test Complete.")

if __name__ == "__main__":
    test_manual()
