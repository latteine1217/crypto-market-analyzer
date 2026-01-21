
import ccxt
import sys

def inspect_exchange(name, keywords):
    try:
        if name == 'binance':
            ex = ccxt.binance({'options': {'defaultType': 'future'}})
        elif name == 'bybit':
            ex = ccxt.bybit({'options': {'defaultType': 'linear'}})
        elif name == 'okx':
            ex = ccxt.okx({'options': {'defaultType': 'swap'}})
        else:
            return
            
        print(f"--- Inspecting {name} ---")
        found = []
        for attr in dir(ex):
            for k in keywords:
                if k.lower() in attr.lower():
                    found.append(attr)
        
        # Dedupe and sort
        found = sorted(list(set(found)))
        for f in found:
            print(f)
            
    except Exception as e:
        print(f"Error inspecting {name}: {e}")

if __name__ == "__main__":
    inspect_exchange('binance', ['force', 'liqi', 'liquidation'])
    inspect_exchange('bybit', ['liqi', 'liquidation'])
    inspect_exchange('okx', ['liqi', 'liquidation'])
