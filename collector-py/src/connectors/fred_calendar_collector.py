"""
FRED Economic Calendar Collector
使用 Federal Reserve Economic Data (FRED) API 獲取實際的經濟數據發布時間
並基於歷史模式預測未來發布日期
"""

import os
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from calendar import monthrange
import requests
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)


class FREDCalendarCollector:
    """FRED 經濟日曆收集器（基於實際數據發布時間）"""
    
    BASE_URL = "https://api.stlouisfed.org/fred"
    
    # FRED Series IDs for major economic indicators
    SERIES_MAP = {
        'cpi': {
            'series_id': 'CPIAUCSL',
            'title': 'Consumer Price Index (CPI)',
            'event_type': 'cpi',
            'impact': 'high',
            'description': 'Monthly inflation data measuring changes in consumer prices',
            'frequency': 'monthly',
            'release_day_of_month': 12,  # 通常在每月 10-15 號發布
        },
        'pce': {
            'series_id': 'PCE',
            'title': 'Personal Consumption Expenditures (PCE)',
            'event_type': 'pce',
            'impact': 'high',
            'description': "Fed's preferred inflation measure",
            'frequency': 'monthly',
            'release_day_of_month': 28,  # 通常在月底發布
        },
        'nonfarm': {
            'series_id': 'PAYEMS',
            'title': 'Non-Farm Payroll (NFP)',
            'event_type': 'nonfarm',
            'impact': 'high',
            'description': 'Monthly employment report showing job additions/losses in the US economy',
            'frequency': 'monthly',
            'release_first_friday': True,  # 每月第一個週五
        },
        'unemployment': {
            'series_id': 'UNRATE',
            'title': 'Unemployment Rate',
            'event_type': 'unemployment',
            'impact': 'high',
            'description': 'Monthly unemployment rate',
            'frequency': 'monthly',
            'release_first_friday': True,
        },
        'gdp': {
            'series_id': 'GDP',
            'title': 'Gross Domestic Product (GDP)',
            'event_type': 'gdp',
            'impact': 'high',
            'description': 'Quarterly economic output',
            'frequency': 'quarterly',
            'release_day_of_month': 30,  # 約在季度結束後一個月
        },
        'retail_sales': {
            'series_id': 'RSXFS',
            'title': 'Retail Sales',
            'event_type': 'retail_sales',
            'impact': 'medium',
            'description': 'Monthly retail sales data',
            'frequency': 'monthly',
            'release_day_of_month': 15,
        },
        'industrial_production': {
            'series_id': 'INDPRO',
            'title': 'Industrial Production',
            'event_type': 'industrial_production',
            'impact': 'medium',
            'description': 'Monthly industrial output',
            'frequency': 'monthly',
            'release_day_of_month': 17,
        }
    }
    
    # 2026 年 FOMC 會議日期（來自 Fed 官網）
    FOMC_MEETINGS_2026 = [
        "2026-01-28",
        "2026-03-17",
        "2026-04-28",
        "2026-06-16",
        "2026-07-28",
        "2026-09-22",
        "2026-11-04",
        "2026-12-15",
    ]
    
    def __init__(self, api_key: str, db_conn):
        """
        初始化 FRED 日曆收集器
        
        Args:
            api_key: FRED API Key
            db_conn: 資料庫連線
        """
        self.api_key = api_key
        self.db_conn = db_conn
        self.session = requests.Session()
    
    def _get_first_friday(self, year: int, month: int) -> int:
        """取得某月第一個星期五的日期"""
        first_day = datetime(year, month, 1)
        first_weekday = first_day.weekday()
        
        if first_weekday <= 4:
            days_to_friday = 4 - first_weekday
        else:
            days_to_friday = 7 - first_weekday + 4
        
        return 1 + days_to_friday
    
    def _get_latest_observation(self, series_id: str) -> Optional[Dict[str, Any]]:
        """
        從 FRED API 獲取最新的數據觀測值
        
        Args:
            series_id: FRED series ID
            
        Returns:
            最新觀測值的字典，包含 date, value, realtime_start
        """
        url = f"{self.BASE_URL}/series/observations"
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'sort_order': 'desc',
            'limit': 1
        }
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            observations = data.get('observations', [])
            
            if observations:
                obs = observations[0]
                return {
                    'date': obs.get('date'),
                    'value': obs.get('value'),
                    'realtime_start': obs.get('realtime_start'),
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching FRED data for {series_id}: {e}")
            return None
    
    def _predict_next_release_dates(self, series_info: Dict[str, Any], months_ahead: int = 3) -> List[datetime]:
        """
        根據歷史模式預測未來的數據發布日期
        
        Args:
            series_info: Series 資訊（包含發布規則）
            months_ahead: 預測未來幾個月
            
        Returns:
            預測的發布日期列表
        """
        now = datetime.now()
        release_dates = []
        
        if series_info.get('release_first_friday'):
            # 每月第一個週五發布（如 NFP, Unemployment）
            for i in range(months_ahead + 1):
                target_date = now + timedelta(days=30 * i)
                year = target_date.year
                month = target_date.month
                
                first_friday_day = self._get_first_friday(year, month)
                release_date = datetime(year, month, first_friday_day, 8, 30)
                
                if release_date > now:
                    release_dates.append(release_date)
        
        elif series_info.get('frequency') == 'monthly':
            # 每月固定日期發布
            release_day = series_info.get('release_day_of_month', 15)
            
            for i in range(months_ahead + 1):
                target_date = now + timedelta(days=30 * i)
                year = target_date.year
                month = target_date.month
                
                # 確保日期不超過該月天數
                max_day = monthrange(year, month)[1]
                actual_day = min(release_day, max_day)
                
                release_date = datetime(year, month, actual_day)
                
                if release_date > now:
                    release_dates.append(release_date)
        
        elif series_info.get('frequency') == 'quarterly':
            # 每季度發布（GDP）
            quarters = [
                (1, datetime(now.year, 2, 28)),   # Q4 前一年 → Jan/Feb 發布
                (2, datetime(now.year, 4, 30)),   # Q1 → Apr 發布
                (3, datetime(now.year, 7, 31)),   # Q2 → Jul 發布
                (4, datetime(now.year, 10, 31)),  # Q3 → Oct 發布
            ]
            
            for quarter, release_date in quarters:
                if release_date > now and release_date <= now + timedelta(days=months_ahead * 31):
                    release_dates.append(release_date)
        
        return release_dates
    
    def generate_events(self, months_ahead: int = 3) -> List[Dict[str, Any]]:
        """
        生成未來幾個月的經濟事件
        
        Args:
            months_ahead: 預測未來幾個月的事件
            
        Returns:
            事件列表
        """
        events = []
        now = datetime.now()
        
        # 1. 從 FRED API 獲取數據並預測發布日期
        for key, series_info in self.SERIES_MAP.items():
            series_id = series_info['series_id']
            
            # 獲取最新觀測值
            latest_obs = self._get_latest_observation(series_id)
            
            if latest_obs:
                logger.info(f"{series_info['title']}: Latest data from {latest_obs['date']} (value: {latest_obs['value']})")
            
            # 預測未來發布日期
            release_dates = self._predict_next_release_dates(series_info, months_ahead)
            
            for release_date in release_dates:
                # 計算數據所屬期間
                if series_info.get('frequency') == 'monthly':
                    # 數據通常是前一個月的
                    data_month = (release_date - timedelta(days=15)).strftime('%B %Y')
                    title = f"{series_info['title']} - {data_month}"
                elif series_info.get('frequency') == 'quarterly':
                    # 計算是哪一季度
                    quarter = ((release_date.month - 1) // 3)
                    prev_quarter = quarter if quarter > 0 else 4
                    prev_year = release_date.year if quarter > 0 else release_date.year - 1
                    title = f"{series_info['title']} - Q{prev_quarter} {prev_year}"
                else:
                    title = series_info['title']
                
                events.append({
                    "event_type": series_info['event_type'],
                    "title": title,
                    "description": series_info['description'],
                    "event_date": release_date,
                    "country": "US",
                    "impact": series_info['impact'],
                    "source": "fred_api",
                    "series_id": series_id,
                    "previous": latest_obs.get('value') if latest_obs else None,
                })
        
        # 2. 添加 FOMC 會議（FRED 不提供）
        for meeting_date_str in self.FOMC_MEETINGS_2026:
            meeting_date = datetime.strptime(meeting_date_str, "%Y-%m-%d")
            
            if meeting_date > now and meeting_date <= now + timedelta(days=months_ahead * 31):
                events.append({
                    "event_type": "fed",
                    "title": "FOMC Meeting - Interest Rate Decision",
                    "description": "Federal Open Market Committee meets to decide monetary policy and interest rates",
                    "event_date": meeting_date,
                    "country": "US",
                    "impact": "high",
                    "source": "federal_reserve",
                })
        
        return events
    
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
            metadata = {
                "source": event.get("source", "fred_api"),
                "series_id": event.get("series_id"),
                "data_source": "FRED API" if event.get("source") == "fred_api" else "Federal Reserve",
            }
            
            values.append((
                "fred_calendar",  # source
                event["event_type"],
                event["title"],
                event["country"],
                event["event_date"],
                event["impact"],
                event.get("description"),
                None,  # actual (未來數據)
                None,  # forecast
                event.get("previous"),  # 最新歷史值
                json.dumps(metadata)
            ))
        
        if not values:
            return 0
        
        # 批次插入
        query = """
            INSERT INTO events (
                source, event_type, title, country, time, 
                impact, description, actual, forecast, previous, metadata
            ) VALUES %s
            ON CONFLICT (source, event_type, time, title) 
            DO UPDATE SET
                description = EXCLUDED.description,
                impact = EXCLUDED.impact,
                previous = EXCLUDED.previous,
                metadata = EXCLUDED.metadata,
                created_at = NOW()
        """
        
        try:
            execute_values(cursor, query, values)
            self.db_conn.commit()
            logger.info(f"Successfully saved {len(values)} FRED calendar events")
            return len(values)
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Error saving FRED calendar events: {e}")
            return 0
        finally:
            cursor.close()
    
    def run(self, months_ahead: int = 3) -> int:
        """執行收集任務"""
        logger.info("Starting FRED calendar collection")
        events = self.generate_events(months_ahead=months_ahead)
        saved_count = self.save_events(events)
        logger.info(f"FRED calendar collection completed: {saved_count} events saved")
        return saved_count


def run_fred_calendar_collection(db_conn, months_ahead: int = 3) -> int:
    """
    執行 FRED 經濟日曆收集
    
    Args:
        db_conn: 資料庫連線
        months_ahead: 生成未來幾個月的事件
        
    Returns:
        成功儲存的事件數量
    """
    api_key = os.getenv('FRED_API_KEY')
    
    if not api_key:
        logger.warning("FRED_API_KEY not found, skipping FRED calendar collection")
        return 0
    
    collector = FREDCalendarCollector(api_key, db_conn)
    return collector.run(months_ahead=months_ahead)
