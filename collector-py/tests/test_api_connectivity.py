"""
API 連接測試腳本

測試 Etherscan API v2、BscScan API v2 和 blockchain.com API 的連接性
"""
import asyncio
import aiohttp
from decimal import Decimal
from datetime import datetime


async def test_etherscan_v2_api(api_key: str = "YourAPIKeyToken"):
    """
    測試 Etherscan API v2 (Ethereum Mainnet)

    文檔: https://docs.etherscan.io/etherscan-v2
    """
    print("=" * 80)
    print("測試 Etherscan API v2 (Ethereum Mainnet)")
    print("=" * 80)

    # Etherscan API v2 統一端點
    base_url = "https://api.etherscan.io/v2/api"

    # Ethereum Foundation 地址
    test_address = "0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe"

    params = {
        'chainid': 1,  # Ethereum Mainnet
        'module': 'account',
        'action': 'balance',
        'address': test_address,
        'tag': 'latest',
        'apikey': api_key
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params, timeout=30) as response:
                print(f"請求 URL: {response.url}")
                print(f"HTTP 狀態碼: {response.status}")

                data = await response.json()
                print(f"回應內容: {data}")

                if data.get('status') == '1':
                    balance_wei = int(data.get('result', 0))
                    balance_eth = Decimal(balance_wei) / Decimal(10 ** 18)
                    print(f"✓ 成功！地址餘額: {balance_eth} ETH")
                    return True
                else:
                    print(f"✗ 失敗：{data.get('message', 'Unknown error')}")
                    return False

    except Exception as e:
        print(f"✗ 請求異常: {e}")
        return False


async def test_blockchain_com_api():
    """
    測試 blockchain.com Bitcoin API

    文檔: https://www.blockchain.com/explorer/api/q
    注意：blockchain.com 公開 API 不需要 API key
    """
    print("\n" + "=" * 80)
    print("測試 blockchain.com Bitcoin API")
    print("=" * 80)

    # 已知的 Bitcoin 大戶地址
    test_address = "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF"

    # 測試 1: 查詢地址餘額
    print("\n[測試 1] 查詢地址餘額")
    balance_url = f"https://blockchain.info/q/addressbalance/{test_address}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(balance_url, timeout=30) as response:
                print(f"請求 URL: {balance_url}")
                print(f"HTTP 狀態碼: {response.status}")

                if response.status == 200:
                    balance_satoshi = int(await response.text())
                    balance_btc = Decimal(balance_satoshi) / Decimal(10 ** 8)
                    print(f"✓ 成功！地址餘額: {balance_btc} BTC ({balance_satoshi} satoshi)")
                else:
                    print(f"✗ 失敗：HTTP {response.status}")
                    return False

    except Exception as e:
        print(f"✗ 請求異常: {e}")
        return False

    # 測試 2: 查詢地址交易記錄
    print("\n[測試 2] 查詢地址交易記錄（最近 10 筆）")
    rawaddr_url = f"https://blockchain.info/rawaddr/{test_address}?limit=10"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(rawaddr_url, timeout=30) as response:
                print(f"請求 URL: {rawaddr_url}")
                print(f"HTTP 狀態碼: {response.status}")

                if response.status == 200:
                    data = await response.json()

                    txs = data.get('txs', [])
                    print(f"✓ 成功！找到 {len(txs)} 筆交易")

                    if txs:
                        print("\n最新交易範例:")
                        latest_tx = txs[0]
                        print(f"  交易哈希: {latest_tx.get('hash', 'N/A')}")
                        print(f"  時間: {datetime.fromtimestamp(latest_tx.get('time', 0))}")
                        print(f"  輸入數: {len(latest_tx.get('inputs', []))}")
                        print(f"  輸出數: {len(latest_tx.get('out', []))}")

                    return True
                else:
                    print(f"✗ 失敗：HTTP {response.status}")
                    return False

    except Exception as e:
        print(f"✗ 請求異常: {e}")
        return False


async def test_blockchain_com_alternative_blockchair():
    """
    測試 Blockchair API (blockchain.com 的替代方案)

    文檔: https://api.blockchair.com/docs
    """
    print("\n" + "=" * 80)
    print("測試 Blockchair Bitcoin API (blockchain.com 替代方案)")
    print("=" * 80)

    test_address = "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF"

    # Blockchair 地址 API
    url = f"https://api.blockchair.com/bitcoin/dashboards/address/{test_address}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                print(f"請求 URL: {url}")
                print(f"HTTP 狀態碼: {response.status}")

                if response.status == 200:
                    data = await response.json()

                    address_data = data.get('data', {}).get(test_address, {})
                    address_info = address_data.get('address', {})

                    balance_satoshi = address_info.get('balance', 0)
                    balance_btc = Decimal(balance_satoshi) / Decimal(10 ** 8)

                    print(f"✓ 成功！")
                    print(f"  地址餘額: {balance_btc} BTC")
                    print(f"  交易次數: {address_info.get('transaction_count', 0)}")
                    print(f"  總接收: {Decimal(address_info.get('received', 0)) / Decimal(10 ** 8)} BTC")
                    print(f"  總支出: {Decimal(address_info.get('spent', 0)) / Decimal(10 ** 8)} BTC")

                    return True
                else:
                    print(f"✗ 失敗：HTTP {response.status}")
                    return False

    except Exception as e:
        print(f"✗ 請求異常: {e}")
        return False


async def main():
    """主測試函數"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "區塊鏈 API 連接測試報告" + " " * 34 + "║")
    print("╚" + "═" * 78 + "╝")
    print(f"\n測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {}

    # 測試 1: Etherscan API v2 (Ethereum)
    results['Etherscan V2 (ETH)'] = await test_etherscan_v2_api()
    await asyncio.sleep(1)  # 避免速率限制

    # 測試 2: blockchain.com API
    results['blockchain.com (BTC)'] = await test_blockchain_com_api()
    await asyncio.sleep(1)

    # 測試 3: Blockchair API (替代方案)
    results['Blockchair (BTC)'] = await test_blockchain_com_alternative_blockchair()

    # 總結報告
    print("\n" + "=" * 80)
    print("測試總結")
    print("=" * 80)

    for api_name, success in results.items():
        status = "✓ 通過" if success else "✗ 失敗"
        print(f"{api_name:30s} : {status}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print("\n" + "-" * 80)
    print(f"通過率: {passed}/{total} ({100 * passed / total:.1f}%)")
    print("-" * 80)

    # 重要建議
    print("\n" + "=" * 80)
    print("重要發現與建議")
    print("=" * 80)
    print("""
1. Etherscan API v2 統一多鏈支援
   - 單一端點: https://api.etherscan.io/v2/api
   - 使用 chainid 參數區分不同鏈
   - Ethereum: chainid=1
   - 支援 60+ EVM 鏈

2. Bitcoin API 選項
   - blockchain.com: 免費，無需 API key，但功能有限
   - Blockchair: 免費層級，數據更豐富，建議使用

3. 建議實作策略
   - Ethereum: 使用 Etherscan API v2 (chainid=1)
   - Bitcoin: 優先使用 Blockchair，blockchain.com 作為備用
    """)


if __name__ == '__main__':
    asyncio.run(main())
