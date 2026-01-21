import requests
from typing import List, Dict, Optional
from datetime import datetime, date
import os
from loguru import logger

class ETFFlowsCollector:
    """
    ETF 資金流向抓取器
    資料來源：SoSoValue API
    API 文檔：https://data.sosovalue.com/api/docs
    
    追蹤：
    - Bitcoin ETF (IBIT, FBTC, GBTC 等)
    - Ethereum ETF (ETHE 等)
    """
    BASE_URL = "https://data.sosovalue.com/api/v1/etf"

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化收集器
        
        Args:
            api_key: SoSoValue API Key (可選，部分端點需要)
        """
        self.api_key = api_key or os.getenv('SOSOVALUE_API_KEY')
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json"
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def _normalize_issuer_name(self, issuer: str) -> str:
        """標準化發行機構名稱"""
        issuer_mapping = {
            "iShares": "BlackRock",
            "Fidelity": "Fidelity",
            "Grayscale": "Grayscale",
            "ARK": "ARK Invest",
            "Bitwise": "Bitwise",
            "VanEck": "VanEck",
            "21Shares": "21Shares",
            "Valkyrie": "Valkyrie",
            "ProShares": "ProShares",
            "WisdomTree": "WisdomTree"
        }
        
        for key, value in issuer_mapping.items():
            if key.lower() in issuer.lower():
                return value
        
        return issuer

    def fetch_bitcoin_etf_flows(self, days: int = 7) -> List[Dict]:
        """
        抓取 Bitcoin ETF 資金流向
        
        Args:
            days: 查詢天數
            
        Returns:
            List of {date, product_code, product_name, issuer, asset_type, net_flow_usd, total_aum_usd}
        """
        try:
            logger.info(f"Fetching Bitcoin ETF flows for last {days} days...")
            
            # SoSoValue 實際端點（需要根據實際 API 調整）
            # 注意：這是示範結構，實際 API 端點可能不同
            endpoint = f"{self.BASE_URL}/flows"
            params = {
                "asset": "BTC",
                "days": days,
                "format": "json"
            }
            
            response = requests.get(
                endpoint,
                params=params,
                headers=self.headers,
                timeout=15
            )
            
            # 如果 API 需要認證且返回 401/403，記錄警告並返回空列表
            if response.status_code in [401, 403]:
                logger.warning(
                    "SoSoValue API authentication required. "
                    "Please set SOSOVALUE_API_KEY environment variable."
                )
                return []
            
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # 解析 API 回傳數據（根據實際 API 格式調整）
            if isinstance(data, dict) and 'data' in data:
                flows = data.get('data', [])
            else:
                flows = data if isinstance(data, list) else []
            
            for item in flows:
                results.append({
                    'date': self._parse_date(item.get('date')),
                    'product_code': item.get('ticker') or item.get('symbol'),
                    'product_name': item.get('name') or item.get('product_name'),
                    'issuer': self._normalize_issuer_name(item.get('issuer', 'Unknown')),
                    'asset_type': 'BTC',
                    'net_flow_usd': float(item.get('net_flow', 0)),
                    'total_aum_usd': float(item.get('aum', 0)) if item.get('aum') else None
                })
            
            logger.info(f"Successfully fetched {len(results)} Bitcoin ETF records")
            return results
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Bitcoin ETF flows: {e}")
            return []
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse Bitcoin ETF data: {e}")
            return []

    def fetch_ethereum_etf_flows(self, days: int = 7) -> List[Dict]:
        """
        抓取 Ethereum ETF 資金流向
        
        Args:
            days: 查詢天數
            
        Returns:
            List of {date, product_code, product_name, issuer, asset_type, net_flow_usd, total_aum_usd}
        """
        try:
            logger.info(f"Fetching Ethereum ETF flows for last {days} days...")
            
            endpoint = f"{self.BASE_URL}/flows"
            params = {
                "asset": "ETH",
                "days": days,
                "format": "json"
            }
            
            response = requests.get(
                endpoint,
                params=params,
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code in [401, 403]:
                logger.warning("SoSoValue API authentication required for Ethereum ETF.")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            if isinstance(data, dict) and 'data' in data:
                flows = data.get('data', [])
            else:
                flows = data if isinstance(data, list) else []
            
            for item in flows:
                results.append({
                    'date': self._parse_date(item.get('date')),
                    'product_code': item.get('ticker') or item.get('symbol'),
                    'product_name': item.get('name') or item.get('product_name'),
                    'issuer': self._normalize_issuer_name(item.get('issuer', 'Unknown')),
                    'asset_type': 'ETH',
                    'net_flow_usd': float(item.get('net_flow', 0)),
                    'total_aum_usd': float(item.get('aum', 0)) if item.get('aum') else None
                })
            
            logger.info(f"Successfully fetched {len(results)} Ethereum ETF records")
            return results
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Ethereum ETF flows: {e}")
            return []
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse Ethereum ETF data: {e}")
            return []

    def _parse_date(self, date_str: str) -> date:
        """解析日期字串"""
        try:
            if isinstance(date_str, date):
                return date_str
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse date: {date_str}, using today")
            return date.today()

    def fetch_all_etf_flows(self, days: int = 7) -> List[Dict]:
        """
        抓取所有 ETF 資金流向（BTC + ETH）
        
        Args:
            days: 查詢天數
            
        Returns:
            合併的 BTC 與 ETH ETF 數據列表
        """
        btc_flows = self.fetch_bitcoin_etf_flows(days)
        eth_flows = self.fetch_ethereum_etf_flows(days)
        
        all_flows = btc_flows + eth_flows
        logger.info(f"Total ETF records collected: {len(all_flows)}")
        
        return all_flows

    def run_collection(self, db_loader, days: int = 7) -> int:
        """
        執行一次完整的抓取任務
        
        Args:
            db_loader: 資料庫載入器實例
            days: 查詢天數
            
        Returns:
            插入的記錄數
        """
        data = self.fetch_all_etf_flows(days)
        if not data:
            logger.warning("No ETF flow data collected")
            return 0
        
        return db_loader.insert_etf_flows_batch(data)
