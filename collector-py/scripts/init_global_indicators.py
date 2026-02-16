#!/usr/bin/env python3
"""
初始化全球指標 (Global Indicators)
職責：
1. 抓取 Fear & Greed Index 完整歷史 (無需 API Key)
2. 抓取 ETF 資金流向歷史 (BTC & ETH, 無需 API Key)

執行方式: docker exec crypto_collector python /app/scripts/init_global_indicators.py
"""
import sys
import os
import time
import psycopg2
from typing import Optional

sys.path.insert(0, '/app/src')

from connectors.fear_greed_collector import FearGreedIndexCollector
from connectors.farside_etf_collector import FarsideInvestorsETFCollector
from loaders.db_loader import DatabaseLoader
from loguru import logger
from config import settings

def wait_for_db(max_retries=10, delay=5):
    """等待資料庫就緒"""
    logger.info("⏳ Waiting for database connection...")
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                dbname=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
                host=settings.postgres_host,
                port=settings.postgres_port
            )
            conn.close()
            logger.success("✅ Database is ready!")
            return True
        except Exception as e:
            logger.warning(f"Database not ready yet ({i+1}/{max_retries}): {e}")
            time.sleep(delay)
    
    logger.error("❌ Database connection timed out")
    return False

def collect_fear_greed(db_loader):
    """收集 Fear & Greed Index 歷史數據 (1年)"""
    logger.info("\n👻 Starting Fear & Greed Index Collection (365 days)...")
    
    try:
        collector = FearGreedIndexCollector()
        
        # 抓取歷史數據 (365天)
        history_data = collector.fetch_historical(days=365)
        
        if not history_data:
            logger.warning("⚠️ No Fear & Greed history fetched")
            return 0
        
        count = 0
        for data in history_data:
            try:
                db_loader.insert_fear_greed_index(data)
                count += 1
            except Exception as e:
                logger.error(f"Failed to insert record {data['timestamp']}: {e}")
                
        logger.success(f"✅ Fear & Greed: Inserted {count} historical records")
        return count
    except Exception as e:
        logger.error(f"❌ Fear & Greed collection failed: {e}")
        return 0

def collect_etf_flows(db_loader):
    """收集 ETF 資金流向 (365天)"""
    logger.info("\n🏦 Starting ETF Flows Collection (BTC & ETH, 365 days)...")
    logger.info("ℹ️  This uses Playwright/curl_cffi hybrid strategy. It may take a few minutes.")
    
    try:
        collector = FarsideInvestorsETFCollector()
        
        # 抓取 365 天歷史
        count = collector.run_collection(db_loader, days=365)
        
        if count > 0:
            logger.success(f"✅ ETF Flows: Inserted {count} records")
        else:
            logger.warning("⚠️  No ETF records inserted. Check logs for scraping issues.")
            
        return count
    except Exception as e:
        logger.error(f"❌ ETF collection failed: {e}")
        return 0

def main():
    logger.info("=" * 60)
    logger.info("🌍 GLOBAL INDICATORS INITIALIZATION")
    logger.info("=" * 60)
    
    # 1. 等待 DB
    if not wait_for_db():
        sys.exit(1)
        
    try:
        # 初始化載入器
        db_loader = DatabaseLoader()
        
        results = {
            'fear_greed': 0,
            'etf': 0
        }
        
        # 2. Fear & Greed (最快)
        results['fear_greed'] = collect_fear_greed(db_loader)
        
        # 3. ETF Flows (較慢，需爬蟲)
        results['etf'] = collect_etf_flows(db_loader)
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 INITIALIZATION SUMMARY")
        logger.info(f"   - Fear & Greed: {results['fear_greed']} records")
        logger.info(f"   - ETF Flows:    {results['etf']} records")
        logger.info("=" * 60)
        
        db_loader.close()
        
    except Exception as e:
        logger.error(f"Fatal error during initialization: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
