#!/usr/bin/env python3
"""
測試 Fear & Greed Index Collector
快速驗證 API 連接與資料庫寫入
"""
import sys
import os

# 添加 src 到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from connectors.fear_greed_collector import FearGreedIndexCollector
from loaders.db_loader import DatabaseLoader
from loguru import logger

def test_fear_greed_collector():
    """測試 Fear & Greed Index 收集器"""
    logger.info("=== Testing Fear & Greed Index Collector ===")
    
    # 初始化 Collector
    collector = FearGreedIndexCollector()
    
    # 測試抓取最新數據
    logger.info("Step 1: Fetching latest Fear & Greed Index...")
    latest = collector.fetch_latest()
    
    if not latest:
        logger.error("❌ Failed to fetch latest data")
        return False
    
    logger.info(f"✅ Latest data fetched successfully:")
    logger.info(f"   - Timestamp: {latest['timestamp']}")
    logger.info(f"   - Value: {latest['value']}")
    logger.info(f"   - Classification: {latest['classification']}")
    
    # 測試寫入資料庫
    logger.info("\nStep 2: Testing database insertion...")
    db_loader = DatabaseLoader()
    
    try:
        result = db_loader.insert_fear_greed_index(latest)
        if result > 0:
            logger.info(f"✅ Successfully inserted {result} record into database")
        else:
            logger.warning("⚠️  No records inserted (may already exist)")
        
        # 驗證資料庫讀取
        logger.info("\nStep 3: Verifying database query...")
        with db_loader.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM get_latest_fear_greed()")
                row = cur.fetchone()
                if row:
                    logger.info(f"✅ Database verification passed:")
                    logger.info(f"   - Timestamp: {row[0]}")
                    logger.info(f"   - Value: {row[1]}")
                    logger.info(f"   - Classification: {row[2]}")
                else:
                    logger.error("❌ No data found in database")
                    return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fear_greed_collector()
    
    if success:
        logger.info("\n" + "="*50)
        logger.info("✅ All tests passed!")
        logger.info("="*50)
        sys.exit(0)
    else:
        logger.error("\n" + "="*50)
        logger.error("❌ Tests failed!")
        logger.error("="*50)
        sys.exit(1)
