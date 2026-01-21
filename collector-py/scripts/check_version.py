
import ccxt
print(f"CCXT Version: {ccxt.__version__}")
exchanges = ['binance', 'bybit', 'okx']
for name in exchanges:
    ex = getattr(ccxt, name)()
    print(f"{name.capitalize()} fetchLiquidations support: {ex.has.get('fetchLiquidations')}")
