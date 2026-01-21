"""
Economic Calendar Collector (Static + Calculated Events)
基於公開的經濟事件週期生成即將到來的經濟指標發布日期
包含：Fed FOMC 會議、CPI、Non-Farm Payroll、GDP 等
"""

import os
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from calendar import monthrange
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)


class EconomicCalendarCollector:
    """經濟日曆收集器（基於固定週期計算）"""
    
    # 2026 年已知的 FOMC 會議日期（來自 Fed 官網）
    FOMC_MEETINGS_2026 = [
        "2026-01-28",  # Jan 27-28, 2026
        "2026-03-17",  # Mar 17-18, 2026
        "2026-04-28",  # Apr 28-29, 2026
        "2026-06-16",  # Jun 16-17, 2026
        "2026-07-28",  # Jul 28-29, 2026
        "2026-09-22",  # Sep 22-23, 2026
        "2026-11-04",  # Nov 4-5, 2026
        "2026-12-15",  # Dec 15-16, 2026
    ]
    
    def __init__(self, db_conn):
        """
        初始化經濟日曆收集器
        
        Args:
            db_conn: 資料庫連線
        """
        self.db_conn = db_conn
    
    def _get_first_friday(self, year: int, month: int) -> int:
        """
        取得某月第一個星期五的日期
        
        Args:
            year: 年份
            month: 月份
            
        Returns:
            該月第一個星期五的日期（日）
        """
        # 找出該月 1 號是星期幾（0=Monday, 4=Friday）
        first_day = datetime(year, month, 1)
        first_weekday = first_day.weekday()
        
        # 計算到第一個星期五需要幾天
        if first_weekday <= 4:  # 如果 1 號在週五之前
            days_to_friday = 4 - first_weekday
        else:  # 如果 1 號在週五之後
            days_to_friday = 7 - first_weekday + 4
        
        return 1 + days_to_friday
    
    def _get_cpi_release_date(self, year: int, month: int) -> datetime:
        """
        CPI 通常在每月 10-15 號左右發布（約在該月中旬）
        
        Args:
            year: 年份
            month: 月份（CPI 數據的月份，實際發布在下個月）
            
        Returns:
            CPI 發布日期
        """
        # CPI 數據在次月 10-15 號發布
        release_month = month + 1
        release_year = year
        
        if release_month > 12:
            release_month = 1
            release_year += 1
        
        # 假設在該月 12 號發布
        return datetime(release_year, release_month, 12)
    
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
        
        # 1. 添加 FOMC 會議
        for meeting_date_str in self.FOMC_MEETINGS_2026:
            meeting_date = datetime.strptime(meeting_date_str, "%Y-%m-%d")
            
            # 只添加未來的會議
            if meeting_date > now and meeting_date <= now + timedelta(days=months_ahead * 31):
                events.append({
                    "event_type": "fed",
                    "title": "FOMC Meeting - Interest Rate Decision",
                    "description": "Federal Open Market Committee meets to decide monetary policy and interest rates",
                    "event_date": meeting_date,
                    "country": "US",
                    "impact": "high",
                    "source": "federal_reserve"
                })
        
        # 2. 添加 Non-Farm Payroll（每月第一個週五）
        for i in range(months_ahead + 1):
            target_date = now + timedelta(days=30 * i)
            year = target_date.year
            month = target_date.month
            
            first_friday_day = self._get_first_friday(year, month)
            nfp_date = datetime(year, month, first_friday_day, 8, 30)  # 美東時間 8:30 AM
            
            if nfp_date > now:
                events.append({
                    "event_type": "nonfarm",
                    "title": f"Non-Farm Payroll (NFP) - {nfp_date.strftime('%B %Y')}",
                    "description": "Monthly employment report showing job additions/losses in the US economy",
                    "event_date": nfp_date,
                    "country": "US",
                    "impact": "high",
                    "source": "bureau_of_labor_statistics"
                })
        
        # 3. 添加 CPI（每月約 12 號）
        for i in range(months_ahead + 1):
            target_date = now + timedelta(days=30 * i)
            year = target_date.year
            month = target_date.month
            
            cpi_date = self._get_cpi_release_date(year, month)
            
            if cpi_date > now and cpi_date <= now + timedelta(days=months_ahead * 31):
                events.append({
                    "event_type": "cpi",
                    "title": f"Consumer Price Index (CPI) - {target_date.strftime('%B %Y')}",
                    "description": "Monthly inflation data measuring changes in consumer prices",
                    "event_date": cpi_date,
                    "country": "US",
                    "impact": "high",
                    "source": "bureau_of_labor_statistics"
                })
        
        # 4. 添加 GDP（每季度）
        # GDP 在每季度結束後約 1 個月發布
        quarters = [
            (1, datetime(now.year, 2, 28)),  # Q4 前一年 GDP → Jan 底發布
            (2, datetime(now.year, 4, 30)),  # Q1 GDP → Apr 底發布
            (3, datetime(now.year, 7, 31)),  # Q2 GDP → Jul 底發布
            (4, datetime(now.year, 10, 31)), # Q3 GDP → Oct 底發布
        ]
        
        for quarter, release_date in quarters:
            if release_date > now and release_date <= now + timedelta(days=months_ahead * 31):
                prev_quarter = quarter - 1 if quarter > 1 else 4
                prev_year = now.year if quarter > 1 else now.year - 1
                
                events.append({
                    "event_type": "gdp",
                    "title": f"GDP Report - Q{prev_quarter} {prev_year}",
                    "description": "Quarterly Gross Domestic Product growth rate",
                    "event_date": release_date,
                    "country": "US",
                    "impact": "high",
                    "source": "bureau_of_economic_analysis"
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
                "source": event.get("source", "calculated"),
                "auto_generated": True,
                "calculation_method": "fixed_schedule"
            }
            
            values.append((
                "economic_calendar",  # source
                event["event_type"],
                event["title"],
                event["country"],
                event["event_date"],
                event["impact"],
                event.get("description"),
                json.dumps(metadata)
            ))
        
        if not values:
            return 0
        
        # 批次插入
        query = """
            INSERT INTO events (
                source, event_type, title, country, event_date, 
                impact, description, metadata
            ) VALUES %s
            ON CONFLICT (source, event_type, event_date, title) 
            DO UPDATE SET
                description = EXCLUDED.description,
                impact = EXCLUDED.impact,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
        """
        
        try:
            execute_values(cursor, query, values)
            self.db_conn.commit()
            logger.info(f"Successfully saved {len(values)} economic calendar events")
            return len(values)
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Error saving economic calendar events: {e}")
            return 0
        finally:
            cursor.close()
    
    def run(self, months_ahead: int = 3) -> int:
        """執行收集任務"""
        logger.info("Starting economic calendar generation")
        events = self.generate_events(months_ahead=months_ahead)
        saved_count = self.save_events(events)
        logger.info(f"Economic calendar generation completed: {saved_count} events saved")
        return saved_count


def run_economic_calendar_collection(db_conn, months_ahead: int = 3) -> int:
    """
    執行經濟日曆收集
    
    Args:
        db_conn: 資料庫連線
        months_ahead: 生成未來幾個月的事件
        
    Returns:
        成功儲存的事件數量
    """
    collector = EconomicCalendarCollector(db_conn)
    return collector.run(months_ahead=months_ahead)
