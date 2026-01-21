#!/usr/bin/env python3
"""
測試 ETF Flows Collector (Mock Data)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from connectors.etf_flows_collector import SoSoValueETFCollector
from loaders.db_loader import DatabaseLoader
from loguru import logger

def test_etf_collector():
    """測試 ETF 收集器"""
    logger.info("=== Testing ETF Flows Collector (Mock Data) ===")
    
    collector = SoSoValueETFCollector()
    
    logger.info("Step 1: Generating mock ETF data...")
    data = collector.fetch_all_etf_flows(days=7)
    
    if not data:
        logger.error("❌ Failed to generate mock data")
        return False
    
    logger.info(f"✅ Generated {len(data)} ETF records")
    logger.info(f"   - BTC ETFs: {len([d for d in data if d['asset_type'] == 'BTC'])}")
    logger.info(f"   - ETH ETFs: {len([d for d in data if d['asset_type'] == 'ETH'])}")
    
    # 顯示樣本
    logger.info("\nSample record:")
    sample = data[0]
    logger.info(f"   - Date: {sample['date']}")
    logger.info(f"   - Product: {sample['product_code']} ({sample['product_name']})")
    logger.info(f"   - Issuer: {sample['issuer']}")
    logger.info(f"   - Net Flow: ${sample['net_flow_usd']:,.2f}")
    logger.info(f"   - AUM: ${sample['total_aum_usd']:,.2f}")
    
    logger.info("\nStep 2: Testing database insertion...")
    db_loader = DatabaseLoader()
    
    try:
        result = db_loader.insert_etf_flows_batch(data)
        logger.info(f"✅ Successfully inserted {result} ETF records")
        
        logger.info("\nStep 3: Verifying database query...")
        with db_loader.get_connection() as conn:
            with conn.cursor() as cur:
                # 查詢最新記錄
                cur.execute("""
                    SELECT date, product_code, asset_type, net_flow_usd
                    FROM etf_flows
                    ORDER BY timestamp DESC
                    LIMIT 5
                """)
                rows = cur.fetchall()
                
                if rows:
                    logger.info(f"✅ Database verification passed:")
                    for row in rows:
                        logger.info(f"   - {row[0]}: {row[1]} ({row[2]}) = ${row[3]:,.2f}")
                else:
                    logger.warning("⚠️  No records found in database")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_etf_collector()
    
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
