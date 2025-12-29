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

    # Binance 熱錢包地址（已知有大量交易）
    test_address = "0x28C6c06298d514Db089934071355E5743bf21d60"

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


async def test_bscscan_v2_via_etherscan(api_key: str = "YourAPIKeyToken"):
    """
    測試 BSC 通過 Etherscan API v2 (chainid=56)

    重要：BSCScan API 已在 2025/12/18 關閉，需使用 Etherscan 統一 API
    文檔: https://docs.etherscan.io/etherscan-v2
    """
    print("\n" + "=" * 80)
    print("測試 BscScan via Etherscan API v2 (chainid=56)")
    print("=" * 80)

    # 使用 Etherscan 統一端點，chainid=56 for BSC
    base_url = "https://api.etherscan.io/v2/api"

    # Binance BSC 熱錢包
    test_address = "0x8894E0a0c962CB723c1976a4421c95949bE2D4E3"

    params = {
        'chainid': 56,  # BSC Mainnet
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
                    balance_bnb = Decimal(balance_wei) / Decimal(10 ** 18)
                    print(f"✓ 成功！地址餘額: {balance_bnb} BNB")
                    return True
                else:
                    error_msg = data.get('message', 'Unknown error')
                    print(f"✗ 失敗：{error_msg}")

                    # 檢查是否因為沒有付費方案
                    if 'subscription' in error_msg.lower() or 'plan' in error_msg.lower():
                        print("⚠️  注意：Etherscan API v2 對 BSC 可能需要付費方案")
                        print("    替代方案：考慮使用 BSCTrace API (https://www.nodereal.io)")

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

    # 已知的 Bitcoin 大戶地址（Binance 冷錢包）
    test_address = "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"

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

    test_address = "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"

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

    # 測試 2: BscScan via Etherscan API v2
    results['Etherscan V2 (BSC)'] = await test_bscscan_v2_via_etherscan()
    await asyncio.sleep(1)

    # 測試 3: blockchain.com API
    results['blockchain.com (BTC)'] = await test_blockchain_com_api()
    await asyncio.sleep(1)

    # 測試 4: Blockchair API (替代方案)
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
   - BSC: chainid=56
   - 支援 60+ EVM 鏈

2. BSCScan API 已廢棄 (2025/12/18)
   - 舊端點 api.bscscan.com 已停用
   - 必須遷移到 Etherscan API v2 或 BSCTrace
   - ⚠️  Etherscan V2 對 BSC 可能需要付費方案

3. Bitcoin API 選項
   - blockchain.com: 免費，無需 API key，但功能有限
   - Blockchair: 免費層級，數據更豐富，建議使用

4. 建議實作策略
   - Ethereum: 使用 Etherscan API v2 (chainid=1)
   - BSC: 評估 Etherscan V2 付費方案 或 使用 BSCTrace
   - Bitcoin: 優先使用 Blockchair，blockchain.com 作為備用
    """)


if __name__ == '__main__':
    asyncio.run(main())
