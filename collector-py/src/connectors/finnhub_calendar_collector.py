"""
Finnhub Economic Calendar Collector
抓取宏觀經濟事件：Fed 決策、CPI、非農就業等
"""

import os
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)


class FinnhubCalendarCollector:
    """Finnhub Economic Calendar 資料收集器"""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    # 重要經濟指標關鍵字過濾
    IMPORTANT_KEYWORDS = [
        'Federal Reserve', 'FOMC', 'Fed', 'Interest Rate',
        'CPI', 'Consumer Price Index', 'Inflation',
        'Nonfarm', 'Non-Farm', 'Employment', 'Unemployment',
        'GDP', 'Gross Domestic Product',
        'PCE', 'Personal Consumption Expenditures',
        'Retail Sales', 'PMI', 'ISM'
    ]
    
    def __init__(self, api_key: str, db_conn):
        """
        初始化 Finnhub Calendar Collector
        
        Args:
            api_key: Finnhub API Key
            db_conn: 資料庫連線
        """
        self.api_key = api_key
        self.db_conn = db_conn
        self.session = requests.Session()
        self.session.headers.update({
            'X-Finnhub-Token': api_key
        })
    
    def _is_important_event(self, event_name: str) -> bool:
        """判斷是否為重要經濟事件"""
        return any(keyword.lower() in event_name.lower() for keyword in self.IMPORTANT_KEYWORDS)
    
    def _determine_impact(self, event_name: str, impact_str: Optional[str] = None) -> str:
        """
        判斷事件影響等級
        
        Args:
            event_name: 事件名稱
            impact_str: Finnhub 提供的 impact 字串
            
        Returns:
            'high', 'medium', or 'low'
        """
        # 優先使用 API 提供的 impact
        if impact_str:
            impact_lower = impact_str.lower()
            if '3' in impact_lower or 'high' in impact_lower:
                return 'high'
            elif '2' in impact_lower or 'medium' in impact_lower:
                return 'medium'
            else:
                return 'low'
        
        # 基於關鍵字判斷
        high_impact_keywords = ['FOMC', 'Fed', 'Interest Rate', 'CPI', 'Nonfarm', 'Non-Farm', 'GDP']
        medium_impact_keywords = ['Retail Sales', 'PMI', 'Unemployment', 'PCE']
        
        name_lower = event_name.lower()
        if any(kw.lower() in name_lower for kw in high_impact_keywords):
            return 'high'
        elif any(kw.lower() in name_lower for kw in medium_impact_keywords):
            return 'medium'
        else:
            return 'low'
    
    def _classify_event_type(self, event_name: str) -> str:
        """分類事件類型"""
        name_lower = event_name.lower()
        
        if 'fomc' in name_lower or 'federal reserve' in name_lower or 'interest rate' in name_lower:
            return 'fed'
        elif 'cpi' in name_lower or 'consumer price' in name_lower or 'inflation' in name_lower:
            return 'cpi'
        elif 'nonfarm' in name_lower or 'non-farm' in name_lower or 'payroll' in name_lower:
            return 'nonfarm'
        elif 'gdp' in name_lower:
            return 'gdp'
        elif 'unemployment' in name_lower:
            return 'unemployment'
        elif 'retail sales' in name_lower:
            return 'retail_sales'
        elif 'pmi' in name_lower or 'ism' in name_lower:
            return 'pmi'
        elif 'pce' in name_lower:
            return 'pce'
        else:
            return 'economic_indicator'
    
    def fetch_calendar(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """
        抓取經濟日曆資料
        
        Args:
            days_ahead: 抓取未來幾天的事件（預設 30 天）
            
        Returns:
            事件列表
        """
        from_date = datetime.now().strftime('%Y-%m-%d')
        to_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        url = f"{self.BASE_URL}/calendar/economic"
        params = {
            'from': from_date,
            'to': to_date
        }
        
        try:
            logger.info(f"Fetching Finnhub economic calendar from {from_date} to {to_date}")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            events = data.get('economicCalendar', [])
            
            # 過濾重要事件
            important_events = [e for e in events if self._is_important_event(e.get('event', ''))]
            
            logger.info(f"Fetched {len(events)} total events, {len(important_events)} important events")
            return important_events
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Finnhub calendar: {e}")
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
            event_name = event.get('event', '')
            event_date_str = event.get('time', '')
            
            # 解析日期（Finnhub 使用 Unix timestamp）
            try:
                event_date = datetime.fromtimestamp(int(event_date_str))
            except (ValueError, TypeError):
                logger.warning(f"Invalid date format for event: {event_name}")
                continue
            
            event_type = self._classify_event_type(event_name)
            impact = self._determine_impact(event_name, event.get('impact'))
            
            values.append((
                'finnhub',
                event_type,
                event_name,
                event.get('country', 'US'),
                event_date,
                impact,
                event.get('actual'),
                event.get('estimate'),
                event.get('previous'),
                json.dumps(event)  # 轉換成 JSON 字串
            ))
        
        if not values:
            return 0
        
        # 批次插入（使用 ON CONFLICT DO UPDATE）
        query = """
            INSERT INTO events (
                source, event_type, title, country, event_date, 
                impact, actual, forecast, previous, metadata
            ) VALUES %s
            ON CONFLICT (source, event_type, event_date, title) 
            DO UPDATE SET
                actual = EXCLUDED.actual,
                forecast = EXCLUDED.forecast,
                previous = EXCLUDED.previous,
                impact = EXCLUDED.impact,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
        """
        
        try:
            execute_values(cursor, query, values)
            self.db_conn.commit()
            logger.info(f"Successfully saved {len(values)} Finnhub events")
            return len(values)
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Error saving Finnhub events: {e}")
            return 0
        finally:
            cursor.close()
    
    def run(self) -> int:
        """執行收集任務"""
        logger.info("Starting Finnhub calendar collection")
        events = self.fetch_calendar(days_ahead=30)
        saved_count = self.save_events(events)
        logger.info(f"Finnhub calendar collection completed: {saved_count} events saved")
        return saved_count


def run_finnhub_calendar_collection(db_conn) -> int:
    """
    執行 Finnhub 經濟日曆收集
    
    Args:
        db_conn: 資料庫連線
        
    Returns:
        成功儲存的事件數量
    """
    api_key = os.getenv('FINNHUB_API_KEY')
    
    if not api_key:
        logger.error("FINNHUB_API_KEY not found in environment variables")
        return 0
    
    collector = FinnhubCalendarCollector(api_key, db_conn)
    return collector.run()
