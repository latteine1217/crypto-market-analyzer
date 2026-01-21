#!/usr/bin/env python3
"""
ExchangePool 記憶體優化測試腳本 (Bybit 專用版)

測試目標：
- 驗證 ExchangePool單例模式正確性
- 驗證 Bybit 實例共享
- 驗證記憶體優化統計資訊
"""
import sys
from pathlib import Path

# 添加 src 到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from connectors.exchange_pool import ExchangePool, get_shared_exchange
from connectors.funding_rate_collector import FundingRateCollector
from connectors.open_interest_collector import OpenInterestCollector
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")


def test_singleton_pattern():
    """測試單例模式"""
    print("\n" + "="*60)
    print("Test 1: Singleton Pattern")
    print("="*60)
    
    pool1 = ExchangePool()
    pool2 = ExchangePool()
    
    assert pool1 is pool2, "❌ ExchangePool 應該是單例模式"
    print("✅ ExchangePool 單例模式正確")


def test_shared_instance():
    """測試共享實例"""
    print("\n" + "="*60)
    print("Test 2: Shared CCXT Instances (Bybit)")
    print("="*60)
    
    # 建立多個 Collector
    collector1 = FundingRateCollector('bybit')
    collector2 = OpenInterestCollector('bybit')
    
    # 驗證它們使用相同的 CCXT 實例
    assert collector1.exchange is collector2.exchange, "❌ 應該共享相同的 CCXT 實例"
    
    print("✅ 多個 Collector 共享相同的 Bybit CCXT 實例")
    print(f"   - FundingRateCollector.exchange id: {id(collector1.exchange)}")
    print(f"   - OpenInterestCollector.exchange id: {id(collector2.exchange)}")


def test_multiple_exchanges():
    """測試同一交易所的不同市場"""
    print("\n" + "="*60)
    print("Test 3: Multiple Markets for Bybit")
    print("="*60)
    
    bybit_spot1 = get_shared_exchange('bybit', market_type='spot')
    bybit_spot2 = get_shared_exchange('bybit', market_type='spot')
    bybit_linear = get_shared_exchange('bybit', market_type='linear')
    
    # 同一市場應該返回相同實例
    assert bybit_spot1 is bybit_spot2, "❌ 同一市場應該返回相同實例"
    print("✅ 同一市場返回相同實例")
    
    # 不同市場應該返回不同實例
    assert bybit_spot1 is not bybit_linear, "❌ 不同市場應該返回不同實例"
    print("✅ 不同市場返回不同實例")


def test_memory_stats():
    """測試記憶體統計資訊"""
    print("\n" + "="*60)
    print("Test 4: Memory Optimization Statistics")
    print("="*60)
    
    pool = ExchangePool()
    stats = pool.get_stats()
    
    print(f"📊 ExchangePool 統計資訊:")
    print(f"   - 已載入實例數量: {stats['total_exchanges']}")
    print(f"   - 實例列表: {stats['exchanges']}")
    print(f"   - 估計節省記憶體: {stats['estimated_memory_saved_mb']} MB")
    print(f"   - 優化比例: {stats['optimization_ratio']}")
    
    assert 'bybit_spot' in stats['exchanges'], "❌ 應該包含 Bybit Spot"
    
    print("\n✅ 所有測試通過！")


def test_market_loading():
    """測試市場資訊載入"""
    print("\n" + "="*60)
    print("Test 5: Market Information Loading")
    print("="*60)
    
    bybit = get_shared_exchange('bybit')
    
    # ExchangePool 會自動預載入市場資訊
    assert len(bybit.markets) > 0, "❌ 市場資訊應該已預載入"
    
    print(f"✅ Bybit 市場資訊已預載入")
    print(f"   - 總交易對數量: {len(bybit.markets)}")
    print(f"   - 包含 BTC/USDT: {'BTC/USDT' in bybit.markets}")
    print(f"   - 包含 ETH/USDT: {'ETH/USDT' in bybit.markets}")


if __name__ == "__main__":
    try:
        print("\n🚀 開始測試 ExchangePool 記憶體優化 (Bybit 專用)")
        
        test_singleton_pattern()
        test_shared_instance()
        test_multiple_exchanges()
        test_memory_stats()
        test_market_loading()
        
        print("\n" + "="*60)
        print("🎉 所有測試通過！ExchangePool 運作正常")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ 測試失敗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)