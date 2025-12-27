"""
測試 Binance 替代方案
包括備用域名和其他交易所
"""
import ccxt
from datetime import datetime

def test_endpoints():
    """測試不同的 Binance 端點"""
    print("=" * 60)
    print("測試 Binance 替代端點")
    print("=" * 60)
    print()

    # Binance 的不同端點
    endpoints = {
        'Binance 主站': 'https://api.binance.com',
        'Binance US': 'https://api.binance.us',
        'Binance 測試網': 'https://testnet.binance.vision',
    }

    results = {}

    for name, base_url in endpoints.items():
        print(f"測試 {name} ({base_url})...")
        try:
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'urls': {'api': base_url},
                'timeout': 10000,
            })

            # 嘗試獲取伺服器時間
            server_time = exchange.fetch_time()
            server_dt = datetime.fromtimestamp(server_time / 1000)
            print(f"  ✓ 連線成功！伺服器時間: {server_dt}")
            results[name] = 'success'
        except Exception as e:
            print(f"  ✗ 連線失敗: {str(e)[:80]}")
            results[name] = 'failed'
        print()

    return results


def test_alternative_exchanges():
    """測試其他交易所 API"""
    print("=" * 60)
    print("測試其他交易所 API")
    print("=" * 60)
    print()

    exchanges = {
        'OKX': ccxt.okx,
        'Bybit': ccxt.bybit,
        'Kraken': ccxt.kraken,
        'Coinbase': ccxt.coinbase,
    }

    results = {}

    for name, exchange_class in exchanges.items():
        print(f"測試 {name}...")
        try:
            exchange = exchange_class({
                'enableRateLimit': True,
                'timeout': 10000,
            })

            # 測試連線
            server_time = exchange.fetch_time()
            server_dt = datetime.fromtimestamp(server_time / 1000)

            # 嘗試獲取 BTC 價格
            try:
                ticker = exchange.fetch_ticker('BTC/USDT')
                price = ticker['last']
                print(f"  ✓ 連線成功！BTC 價格: ${price:,.2f}")
                results[name] = 'success'
            except:
                print(f"  ✓ 連線成功！伺服器時間: {server_dt}")
                results[name] = 'success (no BTC/USDT)'

        except Exception as e:
            print(f"  ✗ 連線失敗: {str(e)[:80]}")
            results[name] = 'failed'
        print()

    return results


def show_recommendations(binance_results, alternative_results):
    """顯示建議"""
    print("=" * 60)
    print("診斷結果與建議")
    print("=" * 60)
    print()

    # 檢查是否有任何 Binance 端點可用
    binance_working = any(v == 'success' for v in binance_results.values())
    alternatives_working = any('success' in v for v in alternative_results.values())

    if binance_working:
        print("✅ Binance API 可用")
        print()
        print("建議：")
        working_endpoints = [k for k, v in binance_results.items() if v == 'success']
        for endpoint in working_endpoints:
            print(f"  • 使用 {endpoint}")
    else:
        print("❌ 所有 Binance 端點都無法連接")
        print()
        print("可能原因：")
        print("  1. Binance 在您的地區被封鎖")
        print("  2. ISP/網路防火牆封鎖 Binance")
        print("  3. 需要使用 VPN 或代理")
        print()

    if alternatives_working:
        print("✅ 可用的替代交易所：")
        working_exchanges = [k for k, v in alternative_results.items() if 'success' in v]
        for exchange in working_exchanges:
            print(f"  • {exchange}")
        print()
        print("建議：")
        print("  1. 使用上述可用的交易所代替 Binance")
        print("  2. 修改 collector 配置以使用替代交易所")
        print("  3. 可以同時從多個交易所收集資料")
    else:
        print("❌ 所有測試的交易所都無法連接")
        print()
        print("建議：")
        print("  1. 檢查網路防火牆設定")
        print("  2. 考慮使用 VPN")
        print("  3. 聯繫網路管理員")

    print()
    print("=" * 60)
    print()

    # 顯示配置範例
    if alternatives_working:
        print("配置範例（collector-py/src/config.py）：")
        print()
        print("```python")
        print("# 使用 OKX 代替 Binance")
        print("import ccxt")
        print()
        print("exchange = ccxt.okx({")
        print("    'enableRateLimit': True,")
        print("    'timeout': 30000,")
        print("})")
        print("```")
        print()


if __name__ == "__main__":
    # 測試 Binance 端點
    binance_results = test_endpoints()

    # 測試其他交易所
    alternative_results = test_alternative_exchanges()

    # 顯示建議
    show_recommendations(binance_results, alternative_results)
