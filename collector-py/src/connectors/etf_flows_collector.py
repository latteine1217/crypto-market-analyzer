"""
SoSoValue ETF API 對接策略文檔

## 現實評估

SoSoValue 是專業的 ETF 數據提供商，他們的 API 需要：
1. 商業授權（付費）
2. API Key 申請流程
3. 可能需要企業認證

## 替代方案

### 方案 1: 使用公開數據源（推薦）
- **CoinGlass**: https://www.coinglass.com/pro/Bitcoin_Etf
  - 提供免費的 Bitcoin/Ethereum ETF 流向數據
  - 數據更新及時
  - 可透過 Web Scraping 獲取

- **CoinDesk**: https://www.coindesk.com/price/bitcoin/etf-flows
  - 提供每日 ETF 流向彙總
  - 可透過 RSS 或 API 獲取

### 方案 2: 手動數據錄入（臨時）
- 每日從 SoSoValue 網站手動下載 CSV
- 透過腳本批次匯入資料庫
- 適合初期測試與驗證

### 方案 3: 使用 CoinGlass API（付費但較便宜）
- API: https://www.coinglass.com/api
- 提供 Bitcoin/Ethereum ETF 即時數據
- 月費約 $29-99（比 SoSoValue 便宜）

## 實施建議

**短期（1-2 週）：**
1. 實作 CoinGlass Web Scraper
2. 每日更新 ETF 流向數據
3. 建立基本視覺化

**中期（1-2 月）：**
1. 申請 CoinGlass API 授權
2. 替換 Scraper 為穩定 API
3. 新增告警功能

**長期（3+ 月）：**
1. 評估 SoSoValue 商業方案
2. 若數據需求擴大，考慮升級
"""

# 臨時實作：使用模擬數據進行測試
from typing import List, Dict
from datetime import date, timedelta
import random
from loguru import logger


class SoSoValueETFCollector:
    """
    SoSoValue ETF Collector
    
    狀態：部分功能（Mock Data）
    原因：SoSoValue API 需要商業授權
    
    替代方案：
    1. 使用 CoinGlass API (推薦)
    2. Web Scraping CoinGlass 網站
    3. 手動數據錄入
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        logger.warning(
            "SoSoValue API requires commercial license. "
            "Using mock data for testing. "
            "Please consider: https://www.coinglass.com/api"
        )
    
    def fetch_bitcoin_etf_flows(self, days: int = 7) -> List[Dict]:
        """
        抓取 Bitcoin ETF 流向（目前返回 Mock Data）
        
        實際實施時需替換為：
        1. CoinGlass API 調用
        2. SoSoValue API（需授權）
        3. Web Scraper
        """
        logger.info(f"Generating mock Bitcoin ETF data for last {days} days...")
        
        # 主要 Bitcoin ETF 產品
        products = [
            {'code': 'IBIT', 'name': 'iShares Bitcoin Trust', 'issuer': 'BlackRock'},
            {'code': 'FBTC', 'name': 'Fidelity Wise Origin Bitcoin Fund', 'issuer': 'Fidelity'},
            {'code': 'GBTC', 'name': 'Grayscale Bitcoin Trust', 'issuer': 'Grayscale'},
            {'code': 'BITB', 'name': 'Bitwise Bitcoin ETF', 'issuer': 'Bitwise'},
        ]
        
        results = []
        today = date.today()
        
        for i in range(days):
            flow_date = today - timedelta(days=i)
            
            for product in products:
                # 模擬資金流向（隨機但合理的範圍）
                base_flow = random.uniform(-50, 100)  # 百萬美元
                
                results.append({
                    'date': flow_date,
                    'product_code': product['code'],
                    'product_name': product['name'],
                    'issuer': product['issuer'],
                    'asset_type': 'BTC',
                    'net_flow_usd': base_flow * 1_000_000,  # 轉換為美元
                    'total_aum_usd': random.uniform(1, 10) * 1_000_000_000  # 10億級 AUM
                })
        
        logger.info(f"Generated {len(results)} mock Bitcoin ETF records")
        return results
    
    def fetch_ethereum_etf_flows(self, days: int = 7) -> List[Dict]:
        """抓取 Ethereum ETF 流向（Mock Data）"""
        logger.info(f"Generating mock Ethereum ETF data for last {days} days...")
        
        products = [
            {'code': 'ETHE', 'name': 'Grayscale Ethereum Trust', 'issuer': 'Grayscale'},
            {'code': 'FETH', 'name': 'Fidelity Ethereum Fund', 'issuer': 'Fidelity'},
        ]
        
        results = []
        today = date.today()
        
        for i in range(days):
            flow_date = today - timedelta(days=i)
            
            for product in products:
                base_flow = random.uniform(-20, 50)
                
                results.append({
                    'date': flow_date,
                    'product_code': product['code'],
                    'product_name': product['name'],
                    'issuer': product['issuer'],
                    'asset_type': 'ETH',
                    'net_flow_usd': base_flow * 1_000_000,
                    'total_aum_usd': random.uniform(0.5, 3) * 1_000_000_000
                })
        
        logger.info(f"Generated {len(results)} mock Ethereum ETF records")
        return results
    
    def fetch_all_etf_flows(self, days: int = 7) -> List[Dict]:
        """抓取所有 ETF 流向"""
        btc_flows = self.fetch_bitcoin_etf_flows(days)
        eth_flows = self.fetch_ethereum_etf_flows(days)
        return btc_flows + eth_flows
    
    def run_collection(self, db_loader, days: int = 7) -> int:
        """執行收集任務"""
        logger.warning("⚠️  Using MOCK DATA for ETF flows")
        logger.info("To use real data, consider:")
        logger.info("  1. CoinGlass API: https://www.coinglass.com/api")
        logger.info("  2. Manual CSV import from SoSoValue")
        
        data = self.fetch_all_etf_flows(days)
        
        if not data:
            return 0
        
        return db_loader.insert_etf_flows_batch(data)
