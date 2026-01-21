#!/usr/bin/env python3
"""
測試 Farside ETF Collector 的 Selenium 功能

執行方式：
python test_farside_selenium.py
"""

import sys
from pathlib import Path

# 加入專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from connectors.farside_etf_collector import FarsideInvestorsETFCollector
from loguru import logger

# 設定日誌級別
logger.remove()
logger.add(sys.stdout, level="INFO")


def test_selenium_basic():
    """測試 Selenium 基本功能"""
    logger.info("=" * 60)
    logger.info("Test 1: Selenium Driver Initialization")
    logger.info("=" * 60)
    
    collector = FarsideInvestorsETFCollector(use_selenium=True)
    
    driver = collector._init_selenium_driver()
    
    if driver:
        logger.info("✅ Selenium driver initialized successfully")
        return True
    else:
        logger.error("❌ Failed to initialize Selenium driver")
        return False


def test_fetch_bitcoin_page():
    """測試抓取 Bitcoin ETF 頁面"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: Fetch Bitcoin ETF Page")
    logger.info("=" * 60)
    
    collector = FarsideInvestorsETFCollector(use_selenium=True)
    
    html = collector._fetch_page_with_retry(collector.BASE_URL_BTC)
    
    if html:
        logger.info(f"✅ Successfully fetched Bitcoin page ({len(html)} bytes)")
        
        # 檢查是否包含預期內容
        if 'IBIT' in html or 'BlackRock' in html or 'table' in html.lower():
            logger.info("✅ Page contains expected ETF data")
            return True
        else:
            logger.warning("⚠️  Page fetched but content may be incomplete")
            return False
    else:
        logger.error("❌ Failed to fetch Bitcoin page")
        return False


def test_parse_bitcoin_data():
    """測試解析 Bitcoin ETF 資料"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 3: Parse Bitcoin ETF Data")
    logger.info("=" * 60)
    
    collector = FarsideInvestorsETFCollector(use_selenium=True)
    
    try:
        data = collector.fetch_bitcoin_etf_flows(days=7)
        
        if data and len(data) > 0:
            logger.info(f"✅ Successfully parsed {len(data)} Bitcoin ETF records")
            
            # 顯示前 3 筆資料作為示例
            logger.info("\nSample data (first 3 records):")
            for i, record in enumerate(data[:3]):
                logger.info(f"  {i+1}. {record['date']} | {record['product_code']} ({record['issuer']}) | ${record['net_flow_usd']:,.0f}")
            
            return True
        else:
            logger.warning("⚠️  No data parsed (this may be normal if no recent flows)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Parsing failed: {e}")
        return False


def test_fetch_ethereum_page():
    """測試抓取 Ethereum ETF 頁面"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 4: Fetch Ethereum ETF Page")
    logger.info("=" * 60)
    
    collector = FarsideInvestorsETFCollector(use_selenium=True)
    
    html = collector._fetch_page_with_retry(collector.BASE_URL_ETH)
    
    if html:
        logger.info(f"✅ Successfully fetched Ethereum page ({len(html)} bytes)")
        
        if 'ETHE' in html or 'Grayscale' in html or 'table' in html.lower():
            logger.info("✅ Page contains expected ETF data")
            return True
        else:
            logger.warning("⚠️  Page fetched but content may be incomplete")
            return False
    else:
        logger.error("❌ Failed to fetch Ethereum page")
        return False


def main():
    """執行所有測試"""
    logger.info("\n🚀 Starting Farside ETF Collector Selenium Tests\n")
    
    results = []
    
    # Test 1: Selenium Driver
    results.append(("Selenium Initialization", test_selenium_basic()))
    
    # Test 2: Fetch Bitcoin Page
    results.append(("Fetch Bitcoin Page", test_fetch_bitcoin_page()))
    
    # Test 3: Parse Bitcoin Data
    results.append(("Parse Bitcoin Data", test_parse_bitcoin_data()))
    
    # Test 4: Fetch Ethereum Page
    results.append(("Fetch Ethereum Page", test_fetch_ethereum_page()))
    
    # 總結測試結果
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} | {test_name}")
    
    logger.info("=" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
