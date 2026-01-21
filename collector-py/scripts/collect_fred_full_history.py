#!/usr/bin/env python3
"""
FRED 完整歷史資料抓取腳本
執行方式: docker exec crypto_collector python /app/scripts/collect_fred_full_history.py
"""
import sys
sys.path.insert(0, '/app/src')

from connectors.fred_collector import FREDCollector
from loaders.db_loader import DatabaseLoader
from loguru import logger
import os

def main():
    """執行 FRED 完整歷史資料抓取（2 年）"""
    
    logger.info("=" * 60)
    logger.info("🚀 FRED Full History Collection Started")
    logger.info("=" * 60)
    
    # 初始化
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        logger.error("❌ FRED_API_KEY not found in environment")
        return 1
    
    logger.info(f"✅ FRED API Key found: {api_key[:15]}...")
    
    try:
        # 建立連接
        db_loader = DatabaseLoader()
        collector = FREDCollector(api_key=api_key)
        
        logger.info("📊 Starting collection with 730 days lookback (2 years)...")
        
        # 執行收集
        count = collector.run_collection(db_loader, lookback_days=730)
        
        logger.success("=" * 60)
        logger.success(f"✅ Collection Completed: {count} records inserted")
        logger.success("=" * 60)
        
        # 顯示統計
        logger.info("\n📈 Fetching statistics from database...")
        
        with db_loader.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        name as series_id,
                        metadata->>'series_name' as series_name,
                        COUNT(*) as data_points,
                        MIN(time) as earliest_date,
                        MAX(time) as latest_date
                    FROM global_indicators
                    WHERE category = 'macro'
                    GROUP BY name, metadata->>'series_name'
                    ORDER BY name;
                """)
                results = cur.fetchall()
            
            if results:
                logger.info("\n" + "=" * 80)
                logger.info("📊 FRED Data Summary:")
                logger.info("=" * 80)
                for row in results:
                    series_id, series_name, points, earliest, latest = row
                    logger.info(f"  {series_id:10} | {series_name:25} | {points:3} points | {earliest} → {latest}")
                logger.info("=" * 80)
            else:
                logger.warning("⚠️  No data found in database")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Collection failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == '__main__':
    sys.exit(main())
