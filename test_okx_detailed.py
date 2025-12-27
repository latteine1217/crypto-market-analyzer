"""
詳細測試 OKX API 連線
"""
import ccxt
import requests
from datetime import datetime

def test_okx_direct():
    """直接測試 OKX API"""
    print("=" * 60)
    print("直接測試 OKX API")
    print("=" * 60)
    print()

    # 測試不同的 OKX 域名
    endpoints = [
        'https://www.okx.com/api/v5/public/time',
        'https://aws.okx.com/api/v5/public/time',
        'https://okx.com/api/v5/public/time',
    ]

    for endpoint in endpoints:
        print(f"測試: {endpoint}")
        try:
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ 成功！伺服器時間: {data}")
            else:
                print(f"  ✗ HTTP {response.status_code}")
        except requests.exceptions.ConnectionError as e:
            print(f"  ✗ 連接錯誤: {e}")
        except requests.exceptions.Timeout:
            print(f"  ✗ 超時")
        except Exception as e:
            print(f"  ✗ 錯誤: {e}")
        print()


def test_okx_ccxt():
    """使用 ccxt 測試 OKX"""
    print("=" * 60)
    print("使用 ccxt 測試 OKX")
    print("=" * 60)
    print()

    configs = [
        {'name': 'OKX 預設', 'config': {}},
        {'name': 'OKX AWS', 'config': {'hostname': 'aws.okx.com'}},
        {'name': 'OKX 主站', 'config': {'hostname': 'www.okx.com'}},
    ]

    for item in configs:
        name = item['name']
        config = {
            'enableRateLimit': True,
            'timeout': 15000,
            **item['config']
        }

        print(f"測試 {name}...")
        try:
            exchange = ccxt.okx(config)

            # 測試伺服器時間
            server_time = exchange.fetch_time()
            server_dt = datetime.fromtimestamp(server_time / 1000)
            print(f"  ✓ 連線成功！伺服器時間: {server_dt}")

            # 測試獲取 BTC ticker
            ticker = exchange.fetch_ticker('BTC/USDT')
            print(f"  ✓ BTC 價格: ${ticker['last']:,.2f}")
            return exchange  # 返回可用的連接

        except Exception as e:
            print(f"  ✗ 失敗: {str(e)[:100]}")
        print()

    return None


def test_okx_markets(exchange):
    """測試 OKX 市場資料"""
    if not exchange:
        return

    print("=" * 60)
    print("測試 OKX 市場資料")
    print("=" * 60)
    print()

    try:
        # 載入市場
        markets = exchange.load_markets()
        print(f"✓ 總共 {len(markets)} 個交易對")

        # 統計 USDT 交易對
        usdt_pairs = [s for s in markets.keys() if s.endswith('/USDT')]
        print(f"✓ USDT 交易對: {len(usdt_pairs)} 個")

        # 顯示前 10 個
        print(f"\n前 10 個 USDT 交易對:")
        for symbol in usdt_pairs[:10]:
            print(f"  - {symbol}")

        print()

        # 測試獲取多個交易對的價格
        test_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        print("測試獲取價格:")
        for symbol in test_symbols:
            ticker = exchange.fetch_ticker(symbol)
            print(f"  {symbol:12} ${ticker['last']:>12,.2f}")

        return True

    except Exception as e:
        print(f"✗ 錯誤: {e}")
        return False


if __name__ == "__main__":
    # 1. 直接測試 API
    test_okx_direct()

    # 2. 使用 ccxt 測試
    exchange = test_okx_ccxt()

    # 3. 如果成功，測試市場資料
    if exchange:
        test_okx_markets(exchange)
        print("\n✅ OKX API 可用！")
    else:
        print("\n❌ OKX API 無法連接")
        print("\n可能的解決方案:")
        print("  1. 檢查網路連接")
        print("  2. 嘗試使用 VPN")
        print("  3. 確認 OKX 在您的地區是否可用")
