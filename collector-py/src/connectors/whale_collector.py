"""
Whale Collector (On-chain Data)
監控區塊鏈大額異動。首波支援 BTC (via mempool.space)。
"""
import requests
from datetime import datetime, timezone
from loguru import logger
from typing import List, Dict, Optional

class WhaleCollector:
    def __init__(self):
        # mempool.space 是開源且不需要 API Key 的優質數據源
        self.btc_api_url = "https://mempool.space/api"
        # 巨鯨定義門檻：50 BTC (約 $2M-$4M USD)
        self.whale_threshold_btc = 50.0

    def fetch_recent_btc_whales(self) -> List[Dict]:
        """
        獲取最近一個區塊中的大額交易。
        """
        try:
            # 1. 獲取最新區塊高度
            height_res = requests.get(f"{self.btc_api_url}/blocks/tip/height", timeout=10)
            height_res.raise_for_status()
            tip_height = int(height_res.text)

            # 2. 獲取最新區塊中的交易
            # 這裡我們取最近的區塊 hash
            hash_res = requests.get(f"{self.btc_api_url}/block-height/{tip_height}", timeout=10)
            block_hash = hash_res.text

            # 3. 獲取區塊內的交易 (分頁抓取前幾頁通常就夠了)
            tx_res = requests.get(f"{self.btc_api_url}/block/{block_hash}/txs", timeout=15)
            txs = tx_res.json()

            whale_txs = []
            for tx in txs:
                # 計算總輸出金額
                total_out_sats = sum(out.get('value', 0) for out in tx.get('vout', []))
                total_out_btc = total_out_sats / 100_000_000

                if total_out_btc >= self.whale_threshold_btc:
                    # 嘗試識別發送與接收地址 (簡化版)
                    from_addr = tx.get('vin', [{}])[0].get('prevout', {}).get('scriptpubkey_address', 'unknown')
                    to_addr = tx.get('vout', [{}])[0].get('scriptpubkey_address', 'unknown')
                    
                    whale_txs.append({
                        'tx_hash': tx['txid'],
                        'amount': total_out_btc,
                        'from_addr': from_addr,
                        'to_addr': to_addr,
                        'time': datetime.fromtimestamp(tx.get('status', {}).get('block_time', datetime.now().timestamp()), tz=timezone.utc),
                        'asset': 'BTC'
                    })

            logger.info(f"Detected {len(whale_txs)} whale transactions in BTC block {tip_height}")
            return whale_txs

        except Exception as e:
            logger.error(f"Failed to fetch BTC whale transactions: {e}")
            return []

    def run_collection(self, db_loader) -> int:
        """
        執行收集並存入資料庫。
        """
        txs = self.fetch_recent_btc_whales()
        if not txs:
            return 0

        inserted_count = 0
        try:
            with db_loader.get_connection() as conn:
                with conn.cursor() as cur:
                    # 獲取 BTC blockchain_id
                    cur.execute("SELECT id FROM blockchains WHERE name = 'BTC'")
                    res = cur.fetchone()
                    blockchain_id = res[0] if res else None
                    if not blockchain_id:
                        return 0

                    for tx in txs:
                        # 簡單估算 USD 金額 (這部分可以結合最新價格優化)
                        # 目前先存入數量，之後由 API 計算或補全
                        cur.execute("""
                            INSERT INTO whale_transactions 
                            (blockchain_id, time, tx_hash, from_addr, to_addr, amount_usd, asset)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (blockchain_id, time, tx_hash) DO NOTHING
                        """, (
                            blockchain_id, 
                            tx['time'], 
                            tx['tx_hash'], 
                            tx['from_addr'], 
                            tx['to_addr'],
                            tx['amount'] * 40000, # 假設價格暫存，實務上應從資料庫取最新價
                            tx['asset']
                        ))
                        if cur.rowcount > 0:
                            inserted_count += 1
                conn.commit()
            return inserted_count
        except Exception as e:
            logger.error(f"Error saving whale transactions: {e}")
            return 0
