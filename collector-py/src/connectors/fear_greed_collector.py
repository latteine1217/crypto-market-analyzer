import requests
from typing import Optional, Dict
from datetime import datetime
import os
from loguru import logger

class FearGreedIndexCollector:
    """
    Fear & Greed Index 抓取器
    資料來源：Alternative.me API
    API 文檔：https://alternative.me/crypto/fear-and-greed-index/
    
    分類標準：
    - 0-24: Extreme Fear
    - 25-44: Fear
    - 45-55: Neutral
    - 56-75: Greed
    - 76-100: Extreme Greed
    """
    BASE_URL = "https://api.alternative.me/fng/"

    def __init__(self):
        """初始化收集器（無需 API Key）"""
        pass

    def _classify_value(self, value: int) -> str:
        """將數值轉換為分類標籤"""
        if value <= 24:
            return "Extreme Fear"
        elif value <= 44:
            return "Fear"
        elif value <= 55:
            return "Neutral"
        elif value <= 75:
            return "Greed"
        else:
            return "Extreme Greed"

    def fetch_latest(self) -> Optional[Dict]:
        """
        抓取最新的 Fear & Greed Index
        
        Returns:
            {
                'timestamp': datetime object,
                'value': int (0-100),
                'classification': str
            }
        """
        try:
            logger.info("Fetching latest Fear & Greed Index from Alternative.me...")
            response = requests.get(
                self.BASE_URL,
                params={"limit": 1, "format": "json"},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('data'):
                logger.warning("No data returned from Fear & Greed API")
                return None
            
            latest = data['data'][0]
            value = int(latest['value'])
            timestamp = datetime.fromtimestamp(int(latest['timestamp']))
            
            result = {
                'timestamp': timestamp,
                'value': value,
                'classification': self._classify_value(value)
            }
            
            logger.info(
                f"Fear & Greed Index: {result['value']} ({result['classification']}) "
                f"at {result['timestamp']}"
            )
            return result
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Fear & Greed Index: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse Fear & Greed Index response: {e}")
            return None

    def fetch_historical(self, days: int = 30) -> list[Dict]:
        """
        抓取歷史數據
        
        Args:
            days: 天數（最多 365）
            
        Returns:
            List of {timestamp, value, classification}
        """
        try:
            logger.info(f"Fetching {days} days of Fear & Greed Index history...")
            response = requests.get(
                self.BASE_URL,
                params={"limit": days, "format": "json"},
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('data'):
                logger.warning("No historical data returned")
                return []
            
            results = []
            for item in data['data']:
                value = int(item['value'])
                timestamp = datetime.fromtimestamp(int(item['timestamp']))
                
                results.append({
                    'timestamp': timestamp,
                    'value': value,
                    'classification': self._classify_value(value)
                })
            
            logger.info(f"Successfully fetched {len(results)} historical records")
            return results
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch historical Fear & Greed Index: {e}")
            return []
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse historical response: {e}")
            return []

    def run_collection(self, db_loader) -> int:
        """
        執行一次完整的抓取任務
        
        Args:
            db_loader: 資料庫載入器實例
            
        Returns:
            插入的記錄數
        """
        data = self.fetch_latest()
        if not data:
            return 0
        
        return db_loader.insert_fear_greed_index(data)
