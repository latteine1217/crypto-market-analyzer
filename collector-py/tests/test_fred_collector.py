"""
FRED Collector 測試腳本
測試從 FRED API 抓取經濟數據並寫入資料庫
"""

import os
import sys
from datetime import datetime, timedelta

# 加入專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.connectors.fred_collector import FREDCollector
from src.loaders.db_loader import DatabaseLoader


def test_fred_collector():
    """測試 FRED Collector 基本功能"""
    
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        print("❌ 錯誤：未設定 FRED_API_KEY 環境變數")
        sys.exit(1)
    
    print(f"✓ FRED API Key 已設定: {api_key[:10]}...")
    
    # 初始化 Collector
    collector = FREDCollector(api_key=api_key)
    db_loader = DatabaseLoader()
    
    # 測試指標列表
    test_series = {
        'UNRATE': '失業率',
        'CPIAUCSL': '消費者物價指數 (CPI)',
        'FEDFUNDS': '聯邦基金利率',
        'GDP': '國內生產毛額 (GDP)'
    }
    
    print(f"\n📊 開始測試 {len(test_series)} 個 FRED 指標...\n")
    
    # 測試資料抓取
    days = 90
    all_observations = collector.fetch_all_indicators(lookback_days=days)
    
    # 按 series_id 分組統計
    observations_by_series = {}
    for obs in all_observations:
        series_id = obs['series_id']
        if series_id not in observations_by_series:
            observations_by_series[series_id] = []
        observations_by_series[series_id].append(obs)
    
    total_count = len(all_observations)
    for series_id, data_list in observations_by_series.items():
        series_name = test_series.get(series_id, series_id)
        count = len(data_list)
        
        print(f"  • {series_name} ({series_id}): {count} 筆資料")
        
        if count > 0:
            latest = data_list[0]
            print(f"    └─ 最新值: {latest['value']} ({latest['timestamp'].strftime('%Y-%m-%d')})")
    
    print(f"\n✓ 總共抓取 {total_count} 筆 FRED 資料\n")
    
    # 測試資料庫寫入
    print("💾 開始寫入資料庫...")
    inserted_count = 0
    
    for data in all_observations:
        try:
            result = db_loader.insert_fred_indicator({
                'series_id': data['series_id'],
                'series_name': data['series_name'],  # 加入 series_name
                'timestamp': data['timestamp'],
                'value': data['value'],
                'forecast_value': data.get('forecast_value'),
                'unit': data.get('unit', 'Index'),
                'frequency': data.get('frequency', 'Monthly')
            })
            if result > 0:
                inserted_count += 1
        except Exception as e:
            print(f"    ⚠️  寫入失敗 ({data['series_id']}, {data['timestamp']}): {e}")
    
    print(f"✓ 成功寫入 {inserted_count} 筆資料到資料庫\n")
    
    # 驗證資料庫中的資料
    print("🔍 驗證資料庫資料...")
    
    with db_loader.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT series_id, COUNT(*) as count, MAX(timestamp) as latest
                FROM fred_indicators
                WHERE series_id = ANY(%s)
                GROUP BY series_id
                ORDER BY series_id
            """, (list(test_series.keys()),))
            
            results = cur.fetchall()
            
            print("\n資料庫統計：")
            for row in results:
                series_name = test_series.get(row[0], row[0])
                print(f"  • {series_name} ({row[0]}): {row[1]} 筆，最新時間: {row[2]}")
    
    print("\n" + "="*60)
    print("✅ FRED Collector 測試完成！")
    print("="*60)
    
    return {
        'total_fetched': total_count,
        'total_inserted': inserted_count,
        'series_tested': len(test_series)
    }


if __name__ == '__main__':
    try:
        result = test_fred_collector()
        print(f"\n📈 測試結果摘要：")
        print(f"   - 抓取資料: {result['total_fetched']} 筆")
        print(f"   - 寫入成功: {result['total_inserted']} 筆")
        print(f"   - 測試指標: {result['series_tested']} 個")
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
