"""
測試 Binance API 連線狀態
"""
import ccxt
import json
from datetime import datetime

def test_binance_connection():
    """測試 Binance API 連線"""
    print("=" * 60)
    print("Binance API 連線測試")
    print("=" * 60)
    print()

    try:
        # 初始化 Binance 客戶端
        print("1. 初始化 Binance 客戶端...")
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'timeout': 30000,
        })
        print("   ✓ 客戶端初始化成功")
        print()

        # 測試伺服器時間
        print("2. 測試伺服器連接...")
        server_time = exchange.fetch_time()
        server_dt = datetime.fromtimestamp(server_time / 1000)
        print(f"   ✓ Binance 伺服器時間: {server_dt}")
        print()

        # 測試市場資料
        print("3. 載入市場資料...")
        markets = exchange.load_markets()
        print(f"   ✓ 成功載入 {len(markets)} 個交易對")
        print()

        # 測試獲取 BTCUSDT ticker
        print("4. 測試獲取 BTC/USDT ticker...")
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"   ✓ BTC/USDT 當前價格: ${ticker['last']:,.2f}")
        print(f"   ✓ 24h 最高: ${ticker['high']:,.2f}")
        print(f"   ✓ 24h 最低: ${ticker['low']:,.2f}")
        print(f"   ✓ 24h 成交量: {ticker['baseVolume']:,.2f} BTC")
        print()

        # 測試獲取 K 線資料
        print("5. 測試獲取 K 線資料...")
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=5)
        print(f"   ✓ 成功獲取 {len(ohlcv)} 條 K 線")
        print(f"   最新 K 線時間: {datetime.fromtimestamp(ohlcv[-1][0] / 1000)}")
        print(f"   最新收盤價: ${ohlcv[-1][4]:,.2f}")
        print()

        # 測試獲取訂單簿
        print("6. 測試獲取訂單簿...")
        orderbook = exchange.fetch_order_book('BTC/USDT', limit=5)
        print(f"   ✓ 買盤深度: {len(orderbook['bids'])} 檔")
        print(f"   ✓ 賣盤深度: {len(orderbook['asks'])} 檔")
        print(f"   最佳買價: ${orderbook['bids'][0][0]:,.2f}")
        print(f"   最佳賣價: ${orderbook['asks'][0][0]:,.2f}")
        print()

        # 測試獲取最近成交
        print("7. 測試獲取最近成交...")
        trades = exchange.fetch_trades('BTC/USDT', limit=5)
        print(f"   ✓ 成功獲取 {len(trades)} 筆成交記錄")
        latest_trade = trades[-1]
        print(f"   最新成交時間: {datetime.fromtimestamp(latest_trade['timestamp'] / 1000)}")
        print(f"   最新成交價: ${latest_trade['price']:,.2f}")
        print(f"   最新成交量: {latest_trade['amount']:.6f} BTC")
        print()

        # 測試 API 限流資訊
        print("8. API 限流資訊...")
        rate_limit = exchange.rateLimit
        print(f"   ✓ 請求間隔: {rate_limit}ms")
        print()

        # 總結
        print("=" * 60)
        print("✅ 所有測試通過！Binance API 連線正常")
        print("=" * 60)

        return True

    except ccxt.NetworkError as e:
        print(f"❌ 網路錯誤: {e}")
        print("   請檢查網路連接")
        return False

    except ccxt.ExchangeError as e:
        print(f"❌ 交易所錯誤: {e}")
        print("   可能是 API 限流或交易對不存在")
        return False

    except Exception as e:
        print(f"❌ 未知錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_symbols():
    """測試多個交易對"""
    print("\n")
    print("=" * 60)
    print("測試多個交易對")
    print("=" * 60)
    print()

    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']

    try:
        exchange = ccxt.binance({'enableRateLimit': True})

        for symbol in symbols:
            ticker = exchange.fetch_ticker(symbol)
            print(f"{symbol:12} | ${ticker['last']:>12,.2f} | "
                  f"24h 變化: {ticker['percentage']:>6.2f}%")

        print()
        print("✅ 多個交易對測試通過")
        return True

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


if __name__ == "__main__":
    # 執行基本連線測試
    success = test_binance_connection()

    # 如果基本測試成功，執行多交易對測試
    if success:
        test_multiple_symbols()

    print()
