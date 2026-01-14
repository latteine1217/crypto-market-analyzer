import requests
from typing import List, Dict, Optional
from datetime import datetime
import os
from loguru import logger
from dateutil import parser

class CryptoPanicCollector:
    """
    CryptoPanic 新聞抓取器
    API 文檔: https://cryptopanic.com/developer/api/
    """
    BASE_URL = "https://cryptopanic.com/api/developer/v2/posts/"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('CRYPTOPANIC_API_KEY')
        if not self.api_key:
            logger.warning("CRYPTOPANIC_API_KEY not found. API requests will be limited or fail.")

    def fetch_latest_news(self, filter_type: str = 'all', currencies: List[str] = None) -> List[Dict]:
        """
        抓取最新新聞
        """
        params = {
            "auth_token": self.api_key,
            "filter": filter_type
        }
        
        if currencies:
            params["currencies"] = ",".join(currencies)

        try:
            logger.info(f"Fetching news from CryptoPanic (filter: {filter_type})...")
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            if results:
                logger.debug(f"Raw first news item: {results[0]}")
            
            formatted_news = []
            for item in results:
                # 轉換 CryptoPanic 格式到我們的 DB 格式
                votes = item.get('votes', {})
                external_id = item.get('id')
                slug = item.get('slug', '')
                
                # 處理缺失的 URL: 優先取 url 欄位，若無則構造備份 URL
                url = item.get('url')
                if not url and external_id:
                    url = f"https://cryptopanic.com/news/{external_id}/{slug}"
                
                # 處理缺失的 domain
                source_info = item.get('source') or {}
                source_domain = item.get('domain')
                if not source_domain and isinstance(source_info, dict):
                    source_domain = source_info.get('domain') or source_info.get('title')
                
                if not url:
                    logger.warning(f"Skipping news item {external_id} due to missing URL")
                    continue

                news_item = {
                    'external_id': external_id,
                    'title': item.get('title'),
                    'url': url,
                    'source_domain': source_domain,
                    'published_at': parser.parse(item.get('published_at')),
                    'votes_positive': votes.get('positive', 0),
                    'votes_negative': votes.get('negative', 0),
                    'votes_important': votes.get('important', 0),
                    'votes_liked': votes.get('liked', 0),
                    'votes_disliked': votes.get('disliked', 0),
                    'votes_lol': votes.get('lol', 0),
                    'votes_toxic': votes.get('toxic', 0),
                    'votes_save': votes.get('saved', 0),
                    'kind': item.get('kind'),
                    'currencies': item.get('currencies', []),
                    'metadata': {
                        'source': source_info,
                        'slug': slug
                    }
                }
                formatted_news.append(news_item)
                
            return formatted_news

        except Exception as e:
            logger.error(f"Failed to fetch news from CryptoPanic: {e}")
            return []

    def run_collection(self, db_loader) -> int:
        """
        執行一次完整的抓取任務
        """
        news_data = self.fetch_latest_news()
        if not news_data:
            return 0
            
        return db_loader.insert_news_batch(news_data)
