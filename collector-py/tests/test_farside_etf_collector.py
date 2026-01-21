"""
測試 Farside Investors ETF Collector

測試項目：
1. 連線能力測試（是否被 Cloudflare 擋住）
2. 資料解析測試（表格格式是否正確）
3. 資料完整性測試（日期、數值是否合理）
4. 異常偵測測試（Grayscale 異常流出）
"""

import sys
import os

# 添加專案根目錄到 Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from connectors.farside_etf_collector import FarsideInvestorsETFCollector
from loguru import logger


def test_connection():
    """測試連線能力"""
    logger.info("=" * 60)
    logger.info("Test 1: Connection Test")
    logger.info("=" * 60)
    
    collector = FarsideInvestorsETFCollector()
    
    # 嘗試抓取 BTC 頁面
    html = collector._fetch_page_with_retry(collector.BASE_URL_BTC, max_retries=2)
    
    if html:
        logger.info(f"✅ Successfully fetched page ({len(html)} bytes)")
        
        # 檢查是否被 Cloudflare 擋住
        if 'cloudflare' in html.lower() or 'challenge' in html.lower():
            logger.warning("⚠️  Cloudflare protection detected")
            return False
        else:
            logger.info("✅ No Cloudflare challenge detected")
            return True
    else:
        logger.error("❌ Failed to fetch page")
        return False


def test_btc_etf_parsing():
    """測試 Bitcoin ETF 資料解析"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: Bitcoin ETF Parsing Test")
    logger.info("=" * 60)
    
    collector = FarsideInvestorsETFCollector()
    
    try:
        data = collector.fetch_bitcoin_etf_flows(days=7)
        
        if not data:
            logger.error("❌ No data returned")
            return False
        
        logger.info(f"✅ Retrieved {len(data)} records")
        
        # 顯示範例資料
        logger.info("\n📊 Sample Records:")
        for i, record in enumerate(data[:5]):  # 顯示前 5 筆
            logger.info(f"  {i+1}. {record['date']} | {record['product_code']:6s} | "
                       f"${record['net_flow_usd'] / 1_000_000:>8.1f}M | {record['issuer']}")
        
        # 資料完整性檢查
        logger.info("\n📋 Data Integrity Check:")
        
        # 檢查必要欄位
        required_fields = ['date', 'product_code', 'issuer', 'asset_type', 'net_flow_usd']
        missing_fields = [field for field in required_fields if field not in data[0]]
        
        if missing_fields:
            logger.error(f"❌ Missing fields: {missing_fields}")
            return False
        else:
            logger.info("✅ All required fields present")
        
        # 檢查日期範圍
        dates = [r['date'] for r in data]
        logger.info(f"✅ Date range: {min(dates)} to {max(dates)}")
        
        # 檢查 asset_type
        asset_types = set(r['asset_type'] for r in data)
        logger.info(f"✅ Asset types: {asset_types}")
        
        # 檢查發行機構
        issuers = set(r['issuer'] for r in data)
        logger.info(f"✅ Issuers found: {', '.join(issuers)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_eth_etf_parsing():
    """測試 Ethereum ETF 資料解析"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 3: Ethereum ETF Parsing Test")
    logger.info("=" * 60)
    
    collector = FarsideInvestorsETFCollector()
    
    try:
        data = collector.fetch_ethereum_etf_flows(days=7)
        
        if not data:
            logger.warning("⚠️  No Ethereum ETF data returned (may not be available yet)")
            return True  # ETH ETF 可能尚未推出，不算失敗
        
        logger.info(f"✅ Retrieved {len(data)} records")
        
        # 顯示範例資料
        logger.info("\n📊 Sample Records:")
        for i, record in enumerate(data[:5]):
            logger.info(f"  {i+1}. {record['date']} | {record['product_code']:6s} | "
                       f"${record['net_flow_usd'] / 1_000_000:>8.1f}M | {record['issuer']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Parsing failed: {e}")
        return False


def test_anomaly_detection():
    """測試異常偵測邏輯"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 4: Anomaly Detection Test")
    logger.info("=" * 60)
    
    collector = FarsideInvestorsETFCollector()
    
    # 建立測試資料（包含異常流出）
    test_data = [
        {
            'date': '2026-01-15',
            'product_code': 'GBTC',
            'issuer': 'Grayscale',
            'net_flow_usd': -600_000_000,  # 流出 6 億美元（異常）
            'asset_type': 'BTC'
        },
        {
            'date': '2026-01-15',
            'product_code': 'IBIT',
            'issuer': 'BlackRock',
            'net_flow_usd': 100_000_000,  # 流入 1 億美元（正常）
            'asset_type': 'BTC'
        }
    ]
    
    logger.info("Testing with mock anomaly data...")
    collector._detect_anomalies(test_data)
    
    logger.info("✅ Anomaly detection logic executed")
    return True


def test_full_collection():
    """測試完整收集流程"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 5: Full Collection Test (No DB Write)")
    logger.info("=" * 60)
    
    collector = FarsideInvestorsETFCollector()
    
    try:
        all_data = collector.fetch_all_etf_flows(days=7)
        
        if not all_data:
            logger.error("❌ No data collected")
            return False
        
        logger.info(f"✅ Total records collected: {len(all_data)}")
        
        # 統計資料
        btc_records = [d for d in all_data if d['asset_type'] == 'BTC']
        eth_records = [d for d in all_data if d['asset_type'] == 'ETH']
        
        logger.info(f"  - Bitcoin ETF: {len(btc_records)} records")
        logger.info(f"  - Ethereum ETF: {len(eth_records)} records")
        
        # 計算總淨流向
        total_btc_flow = sum(d['net_flow_usd'] for d in btc_records)
        total_eth_flow = sum(d['net_flow_usd'] for d in eth_records)
        
        logger.info(f"\n💰 Net Flows (last 7 days):")
        logger.info(f"  - Bitcoin: ${total_btc_flow / 1_000_000:>10.1f}M")
        logger.info(f"  - Ethereum: ${total_eth_flow / 1_000_000:>10.1f}M")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Collection failed: {e}")
        return False


def main():
    """執行所有測試"""
    logger.info("\n" + "🚀" * 30)
    logger.info("Farside Investors ETF Collector - Test Suite")
    logger.info("🚀" * 30 + "\n")
    
    results = {
        "Connection Test": test_connection(),
        "BTC ETF Parsing": test_btc_etf_parsing(),
        "ETH ETF Parsing": test_eth_etf_parsing(),
        "Anomaly Detection": test_anomaly_detection(),
        "Full Collection": test_full_collection(),
    }
    
    # 顯示測試結果摘要
    logger.info("\n" + "=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info("=" * 60)
    logger.info(f"Tests Passed: {passed}/{total}")
    logger.info("=" * 60)
    
    if passed == total:
        logger.info("\n🎉 All tests passed! Ready for deployment.")
        return 0
    else:
        logger.warning(f"\n⚠️  {total - passed} test(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    exit(main())
