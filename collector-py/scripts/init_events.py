import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import json
from datetime import datetime, timedelta
from loguru import logger
from loaders.db_loader import DatabaseLoader
import psycopg2
from psycopg2.extras import execute_values

def init_events():
    db = DatabaseLoader()
    
    # 2026 年 FOMC 關鍵日期 (預置，確保無 API Key 也能顯示)
    events = [
        {
            "source": "federal_reserve",
            "event_type": "fed",
            "title": "FOMC Meeting - Interest Rate Decision",
            "time": "2026-01-28 19:00:00",
            "country": "US",
            "impact": "high",
            "description": "Federal Open Market Committee meets to decide monetary policy and interest rates"
        },
        {
            "source": "federal_reserve",
            "event_type": "fed",
            "title": "FOMC Meeting - Interest Rate Decision",
            "time": "2026-03-17 19:00:00",
            "country": "US",
            "impact": "high",
            "description": "Federal Open Market Committee meets to decide monetary policy and interest rates"
        },
        {
            "source": "federal_reserve",
            "event_type": "fed",
            "title": "FOMC Meeting - Interest Rate Decision",
            "time": "2026-04-28 19:00:00",
            "country": "US",
            "impact": "high",
            "description": "Federal Open Market Committee meets to decide monetary policy and interest rates"
        }
    ]
    
    # 模擬一些 CPI 發布 (每月中旬)
    for month in [1, 2, 3, 4]:
        events.append({
            "source": "fred_calendar",
            "event_type": "cpi",
            "title": f"Consumer Price Index (CPI) - {datetime(2026, month, 1).strftime('%B %Y')}",
            "time": f"2026-{month:02d}-12 13:30:00",
            "country": "US",
            "impact": "high",
            "description": "Monthly inflation data measuring changes in consumer prices"
        })

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # 批次插入
                values = []
                for e in events:
                    values.append((
                        e["source"], e["event_type"], e["title"], e["country"],
                        e["time"], e["impact"], e["description"], json.dumps({"is_preset": True})
                    ))
                
                query = """
                    INSERT INTO events (source, event_type, title, country, time, impact, description, metadata)
                    VALUES %s
                    ON CONFLICT (source, event_type, time, title) DO NOTHING
                """
                execute_values(cur, query, values)
                conn.commit()
                logger.success(f"Successfully initialized {len(events)} major market events for 2026")
            
    except Exception as e:
        logger.error(f"Failed to initialize events: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_events()
