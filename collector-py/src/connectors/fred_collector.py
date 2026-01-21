import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
import os

class FREDCollector:
    """
    FRED (Federal Reserve Economic Data) 收集器
    
    資料來源：
    1. FRED API (官方) - 實際公布值
    2. Trading Economics / Investing.com (爬蟲) - 市場預期值
    
    追蹤重要指標：
    - UNRATE: 失業率
    - CPIAUCSL: CPI 消費者物價指數
    - FEDFUNDS: 聯邦基金利率
    - GDP: GDP 成長率
    """
    
    FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
    
    # 關鍵經濟指標配置
    KEY_INDICATORS = {
        'UNRATE': {
            'name': 'Unemployment Rate',
            'unit': '%',
            'frequency': 'monthly'
        },
        'CPIAUCSL': {
            'name': 'Consumer Price Index',
            'unit': 'Index',
            'frequency': 'monthly'
        },
        'FEDFUNDS': {
            'name': 'Federal Funds Rate',
            'unit': '%',
            'frequency': 'monthly'
        },
        'GDP': {
            'name': 'Gross Domestic Product',
            'unit': 'Billions',
            'frequency': 'quarterly'
        }
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 FRED Collector
        
        Args:
            api_key: FRED API Key (免費註冊：https://fred.stlouisfed.org/docs/api/api_key.html)
        """
        self.api_key = api_key or os.getenv('FRED_API_KEY')
        
        if not self.api_key:
            logger.warning(
                "FRED_API_KEY not found. "
                "Register at: https://fred.stlouisfed.org/docs/api/api_key.html"
            )
    
    def fetch_series_data(
        self, 
        series_id: str, 
        lookback_days: int = 365
    ) -> List[Dict]:
        """
        抓取 FRED 時序資料
        
        Args:
            series_id: FRED Series ID (e.g., 'UNRATE')
            lookback_days: 回溯天數
            
        Returns:
            List of {timestamp, value, series_id, series_name, unit, frequency}
        """
        if not self.api_key:
            logger.error("FRED API Key is required")
            return []
        
        if series_id not in self.KEY_INDICATORS:
            logger.warning(f"Unknown series ID: {series_id}")
            return []
        
        try:
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            
            logger.info(f"Fetching FRED series: {series_id} (from {start_date})...")
            
            params = {
                'api_key': self.api_key,
                'series_id': series_id,
                'file_type': 'json',
                'observation_start': start_date,
                'sort_order': 'desc',
                'limit': 100
            }
            
            response = requests.get(
                self.FRED_BASE_URL,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'observations' not in data:
                logger.warning(f"No observations found for {series_id}")
                return []
            
            results = []
            metadata = self.KEY_INDICATORS[series_id]
            
            for obs in data['observations']:
                # 跳過無效值
                if obs['value'] == '.':
                    continue
                
                try:
                    value = float(obs['value'])
                    timestamp = datetime.strptime(obs['date'], '%Y-%m-%d')
                    
                    results.append({
                        'series_id': series_id,
                        'series_name': metadata['name'],
                        'timestamp': timestamp,
                        'value': value,
                        'forecast_value': None,  # 稍後由 forecast scraper 填充
                        'unit': metadata['unit'],
                        'frequency': metadata['frequency']
                    })
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse observation: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(results)} observations for {series_id}")
            return results
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch FRED data for {series_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching FRED data: {e}")
            return []
    
    def fetch_all_indicators(self, lookback_days: int = 365) -> List[Dict]:
        """
        抓取所有關鍵指標
        
        Args:
            lookback_days: 回溯天數
            
        Returns:
            合併的所有指標資料
        """
        all_data = []
        
        for series_id in self.KEY_INDICATORS.keys():
            data = self.fetch_series_data(series_id, lookback_days)
            all_data.extend(data)
        
        logger.info(f"Total FRED records collected: {len(all_data)}")
        return all_data
    
    def run_collection(self, db_loader, lookback_days: int = 730) -> int:
        """
        執行一次完整的抓取任務
        
        Args:
            db_loader: 資料庫載入器實例
            lookback_days: 回溯天數（預設 730 天 = 2 年，涵蓋完整經濟週期）
            
        Returns:
            插入的記錄數
        """
        if not self.api_key:
            logger.error("Cannot run FRED collection without API Key")
            logger.info("Get your free API key at: https://fred.stlouisfed.org/docs/api/api_key.html")
            return 0
        
        all_data = self.fetch_all_indicators(lookback_days)
        
        if not all_data:
            logger.warning("No FRED data collected")
            return 0
        
        # 批次插入
        inserted_count = 0
        for data in all_data:
            try:
                result = db_loader.insert_fred_indicator(data)
                inserted_count += result
            except Exception as e:
                logger.error(f"Failed to insert FRED indicator: {e}")
                continue
        
        return inserted_count


class TradingEconomicsForecastScraper:
    """
    Trading Economics 預期值爬蟲 (備用方案)
    
    注意：Web Scraping 較不穩定，建議使用 Trading Economics API (付費)
    API: https://tradingeconomics.com/api
    """
    
    def __init__(self):
        self.base_url = "https://tradingeconomics.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def fetch_forecast(self, indicator: str) -> Optional[Dict]:
        """
        抓取指標的市場預期值
        
        Args:
            indicator: 指標名稱 (e.g., 'unemployment-rate')
            
        Returns:
            {forecast_value: float, timestamp: datetime} or None
        """
        logger.warning(
            "Trading Economics scraper is not implemented yet. "
            "Consider using their official API for reliable forecasts."
        )
        
        # TODO: 實作爬蟲邏輯
        # 1. 訪問 https://tradingeconomics.com/united-states/unemployment-rate
        # 2. 解析 HTML 找到 Forecast 欄位
        # 3. 返回預期值與時間戳
        
        return None
