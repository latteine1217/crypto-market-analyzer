#!/usr/bin/env python3
"""
手動觸發 ETF 收集任務以測試 Farside 抓取流程（無 Selenium）

執行方式：
docker exec -it crypto_collector python /app/test_etf_collection.py
"""

import sys
sys.path.insert(0, '/app/src')

from loguru import logger
from connectors.farside_etf_collector import FarsideInvestorsETFCollector
from loaders.db_loader import DatabaseLoader
from config import settings

# 設定日誌
logger.remove()
logger.add(sys.stdout, level="INFO")

def main():
    logger.info("=" * 60)
    logger.info("Manual ETF Collection Test (Farside Investors)")
    logger.info("=" * 60)
    
    # 初始化資料庫連接（使用默認設置，從環境變數讀取）
    db = DatabaseLoader()
    
    # 初始化 Farside ETF Collector
    collector = FarsideInvestorsETFCollector()
    
    # 執行收集任務
    try:
        count = collector.run_collection(db, days=7)
        
        if count > 0:
            logger.success(f"✅ Successfully collected {count} ETF flow records!")
            
            # 查詢資料庫驗證
            with db.conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        date, 
                        product_code, 
                        issuer, 
                        asset_type, 
                        net_flow_usd 
                    FROM etf_flows 
                    ORDER BY date DESC, asset_type, issuer 
                    LIMIT 10
                """)
                results = cur.fetchall()
                
                logger.info("\n" + "=" * 60)
                logger.info("Latest ETF Flow Records in Database:")
                logger.info("=" * 60)
                
                for row in results:
                    date, product_code, issuer, asset_type, net_flow_usd = row
                    logger.info(
                        f"{date} | {asset_type} | {product_code} ({issuer}) | "
                        f"${net_flow_usd / 1_000_000:,.1f}M"
                    )
                
                # 統計總數
                cur.execute("SELECT COUNT(*), asset_type FROM etf_flows GROUP BY asset_type")
                stats = cur.fetchall()
                
                logger.info("\n" + "=" * 60)
                logger.info("Database ETF Flow Statistics:")
                logger.info("=" * 60)
                
                for count, asset_type in stats:
                    logger.info(f"{asset_type}: {count} records")
                
        else:
            logger.warning("⚠️  No ETF data collected")
            
    except Exception as e:
        logger.error(f"❌ Collection failed: {e}", exc_info=True)
        return 1
    
    finally:
        db.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("Test Complete!")
    logger.info("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
