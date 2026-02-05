"""
簡化版 ETF Collector - 使用公開 CSV 或手動數據

考慮到 Farside Investors 有嚴格的 Cloudflare 保護，
本實作提供三種方案：

方案 1: 手動 CSV 匯入（推薦，最穩定）
- 每日從 Farside 手動下載 CSV
- 放入 `data/etf_flows/` 目錄
- 自動解析並匯入資料庫

方案 2: 使用 GitHub 開源數據集
- 社群維護的 ETF 資料庫（例如：https://github.com/bitcoin-etf-tracker）
- 每日自動同步

方案 3: 使用 Selenium/Playwright（複雜但自動化）
- 需安裝瀏覽器驅動
- 可繞過 Cloudflare
- 維護成本較高

當前實作：方案 1（CSV 匯入）
"""

from typing import List, Dict
from datetime import date, datetime
from loguru import logger
import pandas as pd
import glob
import os


class SimpleETFCollector:
    """
    簡化版 ETF Collector
    
    使用 CSV 檔案匯入（手動或自動下載）
    
    CSV 格式範例：
    ```
    Date,Product,Issuer,Asset,NetFlow_USD,AUM_USD
    2026-01-15,IBIT,BlackRock,BTC,125000000,5000000000
    2026-01-15,GBTC,Grayscale,BTC,-80000000,18000000000
    ```
    """
    
    def __init__(self, csv_directory: str = "data/etf_flows"):
        self.csv_directory = csv_directory
        
        # 確保目錄存在
        os.makedirs(csv_directory, exist_ok=True)
        
        logger.info(f"ETF Collector initialized. CSV directory: {csv_directory}")
        logger.info(f"💡 To add data: Place CSV files in {csv_directory}/")
    
    def load_csv_files(self) -> List[Dict]:
        """載入所有 CSV 檔案"""
        csv_pattern = os.path.join(self.csv_directory, "*.csv")
        csv_files = glob.glob(csv_pattern)
        
        if not csv_files:
            logger.warning(f"No CSV files found in {self.csv_directory}")
            logger.info("💡 Please download ETF data from https://farside.co.uk/ and save as CSV")
            return []
        
        logger.info(f"Found {len(csv_files)} CSV file(s)")
        
        all_data = []
        
        for csv_file in csv_files:
            try:
                logger.info(f"Loading {os.path.basename(csv_file)}...")
                df = pd.read_csv(csv_file)
                
                # 標準化欄位名稱
                df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
                
                # 轉換為字典列表
                for _, row in df.iterrows():
                    record = self._parse_csv_row(row)
                    if record:
                        all_data.append(record)
                
                logger.info(f"  ✅ Loaded {len(df)} records")
                
            except Exception as e:
                logger.error(f"  ❌ Failed to load {csv_file}: {e}")
                continue
        
        logger.info(f"Total records loaded: {len(all_data)}")
        return all_data
    
    def _parse_csv_row(self, row) -> Dict:
        """解析 CSV 行"""
        try:
            # 解析日期（支援多種格式）
            date_value = row.get('date') or row.get('flow_date')
            if pd.isna(date_value):
                return None
            
            if isinstance(date_value, str):
                parsed_date = pd.to_datetime(date_value).date()
            else:
                parsed_date = date_value
            
            # 解析產品資訊
            product_code = str(row.get('product') or row.get('product_code', 'UNKNOWN'))
            issuer = str(row.get('issuer', 'Unknown'))
            asset_type = str(row.get('asset') or row.get('asset_type', 'BTC')).upper()
            
            # 解析流向（可能包含 $ 符號或逗號）
            net_flow_raw = row.get('netflow_usd') or row.get('net_flow') or row.get('flow')
            if pd.isna(net_flow_raw):
                net_flow_usd = 0.0
            else:
                net_flow_usd = float(str(net_flow_raw).replace('$', '').replace(',', ''))
            
            # 解析 AUM（可選）
            aum_raw = row.get('aum_usd') or row.get('aum')
            if pd.isna(aum_raw):
                aum_usd = None
            else:
                aum_usd = float(str(aum_raw).replace('$', '').replace(',', ''))
            
            return {
                'date': parsed_date,
                'product_code': product_code,
                'product_name': product_code,  # CSV 通常不包含完整名稱
                'issuer': issuer,
                'asset_type': asset_type,
                'net_flow_usd': net_flow_usd,
                'total_aum_usd': aum_usd
            }
            
        except Exception as e:
            logger.debug(f"Failed to parse row: {e}")
            return None
    
    def fetch_all_etf_flows(self, days: int = 7) -> List[Dict]:
        """抓取所有 ETF 流向（從 CSV 檔案）"""
        all_data = self.load_csv_files()
        
        if not all_data:
            logger.warning("⚠️  No ETF CSV data available. Returning empty result.")
            return []
        
        # 篩選最近 N 天
        cutoff_date = date.today() - pd.Timedelta(days=days)
        filtered_data = [d for d in all_data if d['date'] >= cutoff_date]
        
        logger.info(f"Filtered to {len(filtered_data)} records (last {days} days)")
        return filtered_data
    
    
    def run_collection(self, db_loader, days: int = 7) -> int:
        """執行收集任務"""
        logger.info("🚀 Starting Simple ETF collection...")
        
        data = self.fetch_all_etf_flows(days)
        
        if not data:
            logger.warning("No data to insert")
            return 0
        
        inserted_count = db_loader.insert_etf_flows_batch(data)
        
        logger.info(f"✅ ETF collection complete: {inserted_count} records inserted")
        return inserted_count
    
    def create_sample_csv(self):
        """建立範例 CSV 檔案（供參考）"""
        sample_file = os.path.join(self.csv_directory, "sample_etf_data.csv")
        
        sample_data = {
            'Date': ['2026-01-15', '2026-01-15', '2026-01-14'],
            'Product': ['IBIT', 'GBTC', 'IBIT'],
            'Issuer': ['BlackRock', 'Grayscale', 'BlackRock'],
            'Asset': ['BTC', 'BTC', 'BTC'],
            'NetFlow_USD': [125000000, -80000000, 95000000],
            'AUM_USD': [5000000000, 18000000000, 4900000000]
        }
        
        df = pd.DataFrame(sample_data)
        df.to_csv(sample_file, index=False)
        
        logger.info(f"✅ Sample CSV created: {sample_file}")
        logger.info(f"💡 Use this format for your own data")
