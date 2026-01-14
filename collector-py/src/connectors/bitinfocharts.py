import requests
import pandas as pd
import logging
from datetime import datetime
from io import StringIO
import re

logger = logging.getLogger(__name__)

class BitInfoChartsClient:
    def __init__(self):
        self.base_url = "https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def fetch_distribution_data(self):
        """
        Fetches the Bitcoin distribution table (Rich List).
        Returns a list of dictionaries with stats for Balance Ranges.
        """
        try:
            logger.info(f"Fetching Rich List from {self.base_url}")
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 使用 Pandas 解析表格
            dfs = pd.read_html(StringIO(response.text))
            
            if not dfs:
                logger.error("No tables found in BitInfoCharts response")
                return None
                
            # 通常第一個表格是分佈表
            dist_df = dfs[0]
            
            stats = []
            
            # 解析分佈表 (Distribution by Balance)
            for index, row in dist_df.iterrows():
                try:
                    # Balance range (e.g., "[100 - 1,000)")
                    balance_range = str(row.iloc[0]).strip()
                    # 跳過 header 或 footer
                    if not balance_range or 'Balance' in balance_range or 'Total' in balance_range:
                        continue
                    
                    # Addresses (e.g. "13560")
                    addr_count_raw = str(row.iloc[1])
                    # 有時候會有額外文字，只取數字
                    addr_count = int(re.sub(r'[^\d]', '', addr_count_raw))
                    
                    # Total BTC (e.g. "4,200,000 BTC")
                    btc_raw = str(row.iloc[3])
                    # 去除 ' BTC' 和逗號
                    if 'BTC' in btc_raw:
                        btc_val = btc_raw.split('BTC')[0]
                    else:
                        btc_val = btc_raw.split(' ')[0]
                    
                    btc_amount = float(re.sub(r'[^\d.]', '', btc_val))
                    
                    # USD (e.g. "$100,000,000")
                    usd_raw = str(row.iloc[4])
                    usd_amount = float(re.sub(r'[^\d.]', '', usd_raw))
                    
                    # % Total Supply (e.g. "25% (90%)")
                    # 我們只取第一部分 (該區間佔比)
                    pct_raw = str(row.iloc[5])
                    if '%' in pct_raw:
                         pct_val = pct_raw.split('%')[0]
                         pct_supply = float(re.sub(r'[^\d.]', '', pct_val))
                    else:
                        pct_supply = 0.0

                    stats.append({
                        'rank_group': balance_range,
                        'address_count': addr_count,
                        'total_balance': btc_amount,
                        'total_balance_usd': usd_amount,
                        'percentage_of_supply': pct_supply,
                        'symbol': 'BTC'
                    })
                except Exception as e:
                    # 某些行可能是匯總或格式不同，跳過並記錄
                    # logger.debug(f"Skipping row {index}: {e}")
                    continue

            return stats

        except Exception as e:
            logger.error(f"Error fetching BitInfoCharts data: {e}")
            return None

if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    client = BitInfoChartsClient()
    data = client.fetch_distribution_data()
    if data:
        print(f"Parsed {len(data)} rows.")
        for row in data:
            print(row)