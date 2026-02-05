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
    
    狀態：停用（不允許 demo/mock 資料）
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
            "Mock data is disabled. "
            "Please consider: https://www.coinglass.com/api"
        )
    
    def fetch_bitcoin_etf_flows(self, days: int = 7) -> List[Dict]:
        """
        抓取 Bitcoin ETF 流向（停用，返回空資料）
        
        實際實施時需替換為：
        1. CoinGlass API 調用
        2. SoSoValue API（需授權）
        3. Web Scraper
        """
        logger.warning("SoSoValue BTC ETF flow fetch is disabled without API access.")
        return []
    
    def fetch_ethereum_etf_flows(self, days: int = 7) -> List[Dict]:
        """抓取 Ethereum ETF 流向（停用，返回空資料）"""
        logger.warning("SoSoValue ETH ETF flow fetch is disabled without API access.")
        return []
    
    def fetch_all_etf_flows(self, days: int = 7) -> List[Dict]:
        """抓取所有 ETF 流向"""
        btc_flows = self.fetch_bitcoin_etf_flows(days)
        eth_flows = self.fetch_ethereum_etf_flows(days)
        return btc_flows + eth_flows
    
    def run_collection(self, db_loader, days: int = 7) -> int:
        """執行收集任務"""
        logger.warning("⚠️  ETF mock data disabled. No collection performed.")
        logger.info("To use real data, consider:")
        logger.info("  1. CoinGlass API: https://www.coinglass.com/api")
        logger.info("  2. Manual CSV import from SoSoValue")
        
        data = self.fetch_all_etf_flows(days)
        
        if not data:
            return 0
        
        return db_loader.insert_etf_flows_batch(data)
