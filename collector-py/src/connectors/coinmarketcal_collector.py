"""
CoinMarketCal API Collector
抓取加密貨幣重要事件：主網上線、代幣發行、硬分叉等
"""

import os
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)


class CoinMarketCalCollector:
    """CoinMarketCal 事件收集器"""
    
    BASE_URL = "https://developers.coinmarketcal.com/v1"
    
    # 重要事件類型
    IMPORTANT_CATEGORIES = [
        'Launch', 'Mainnet launch', 'Hard fork', 'Soft fork',
        'Token swap', 'Airdrop', 'Burn', 'Halving',
        'Exchange listing', 'Partnership', 'Conference'
    ]
    
    def __init__(self, api_key: str, db_conn):
        """
        初始化 CoinMarketCal Collector
        
        Args:
            api_key: CoinMarketCal API Key
            db_conn: 資料庫連線
        """
        self.api_key = api_key
        self.db_conn = db_conn
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': api_key,
            'Accept': 'application/json'
        })
    
    def _determine_impact(self, votes_count: int, category: str) -> str:
        """
        根據投票數與類別判斷影響等級
        
        Args:
            votes_count: 投票數
            category: 事件類別
            
        Returns:
            'high', 'medium', or 'low'
        """
        high_impact_categories = [
            'Mainnet launch', 'Hard fork', 'Halving', 'Token swap'
        ]
        
        if category in high_impact_categories or votes_count >= 500:
            return 'high'
        elif votes_count >= 100:
            return 'medium'
        else:
            return 'low'
    
    def _classify_event_type(self, category: str) -> str:
        """分類事件類型"""
        category_lower = category.lower()
        
        type_mapping = {
            'launch': 'token_launch',
            'mainnet': 'mainnet_launch',
            'fork': 'hard_fork',
            'swap': 'token_swap',
            'airdrop': 'airdrop',
            'burn': 'token_burn',
            'halving': 'halving',
            'listing': 'exchange_listing',
            'partnership': 'partnership',
            'conference': 'conference'
        }
        
        for key, value in type_mapping.items():
            if key in category_lower:
                return value
        
        return 'crypto_event'
    
    def fetch_events(self, days_ahead: int = 30, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        抓取加密貨幣事件
        
        Args:
            days_ahead: 抓取未來幾天的事件
            max_results: 最大結果數
            
        Returns:
            事件列表
        """
        from_date = datetime.now()
        to_date = from_date + timedelta(days=days_ahead)
        
        url = f"{self.BASE_URL}/events"
        params = {
            'dateRangeStart': from_date.strftime('%Y-%m-%d'),
            'dateRangeEnd': to_date.strftime('%Y-%m-%d'),
            'max': max_results,
            'sortBy': 'hot_events'  # 按熱門度排序
        }
        
        try:
            logger.info(f"Fetching CoinMarketCal events from {from_date.date()} to {to_date.date()}")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            events = data.get('body', [])
            
            # 過濾重要事件
            important_events = [
                e for e in events 
                if any(cat in e.get('categories', [{}])[0].get('name', '') for cat in self.IMPORTANT_CATEGORIES)
                or e.get('vote_count', 0) >= 50
            ]
            
            logger.info(f"Fetched {len(events)} total events, {len(important_events)} important events")
            return important_events
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching CoinMarketCal events: {e}")
            return []
    
    def save_events(self, events: List[Dict[str, Any]]) -> int:
        """
        儲存事件到資料庫
        
        Args:
            events: 事件列表
            
        Returns:
            成功儲存的事件數量
        """
        if not events:
            return 0
        
        cursor = self.db_conn.cursor()
        
        # 準備資料
        values = []
        for event in events:
            title = event.get('title', {}).get('en', 'Untitled Event')
            description = event.get('description', {}).get('en', '')
            
            # 解析日期
            date_event_str = event.get('date_event', '')
            try:
                # CoinMarketCal 使用 ISO 8601 格式
                event_date = datetime.fromisoformat(date_event_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                logger.warning(f"Invalid date format for event: {title}")
                continue
            
            # 提取幣種資訊
            coins = []
            if 'coins' in event:
                for coin in event['coins']:
                    symbol = coin.get('symbol', '')
                    if symbol:
                        coins.append(symbol.upper())
            
            # 分類與影響等級
            categories = event.get('categories', [])
            category_name = categories[0].get('name', '') if categories else ''
            event_type = self._classify_event_type(category_name)
            
            vote_count = event.get('vote_count', 0)
            impact = self._determine_impact(vote_count, category_name)
            
            # URL
            url = f"https://coinmarketcal.com/en/event/{event.get('id', '')}"
            
            values.append((
                'coinmarketcal',
                event_type,
                title,
                description if description else None,
                event_date,
                impact,
                coins if coins else None,
                url,
                json.dumps(event)  # 轉換成 JSON 字串
            ))
        
        if not values:
            return 0
        
        # 批次插入
        query = """
            INSERT INTO events (
                source, event_type, title, description, time,
                impact, coins, url, metadata
            ) VALUES %s
            ON CONFLICT (source, event_type, time, title)
            DO UPDATE SET
                description = EXCLUDED.description,
                impact = EXCLUDED.impact,
                coins = EXCLUDED.coins,
                url = EXCLUDED.url,
                metadata = EXCLUDED.metadata,
                created_at = NOW()
        """
        
        try:
            execute_values(cursor, query, values)
            self.db_conn.commit()
            logger.info(f"Successfully saved {len(values)} CoinMarketCal events")
            return len(values)
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Error saving CoinMarketCal events: {e}")
            return 0
        finally:
            cursor.close()
    
    def run(self) -> int:
        """執行收集任務"""
        logger.info("Starting CoinMarketCal collection")
        events = self.fetch_events(days_ahead=30, max_results=100)
        saved_count = self.save_events(events)
        logger.info(f"CoinMarketCal collection completed: {saved_count} events saved")
        return saved_count


def run_coinmarketcal_collection(db_conn) -> int:
    """
    執行 CoinMarketCal 事件收集
    
    Args:
        db_conn: 資料庫連線
        
    Returns:
        成功儲存的事件數量
    """
    api_key = os.getenv('COINMARKETCAL_API_KEY')
    
    if not api_key:
        logger.warning("COINMARKETCAL_API_KEY not found, skipping CoinMarketCal collection")
        return 0
    
    collector = CoinMarketCalCollector(api_key, db_conn)
    return collector.run()
