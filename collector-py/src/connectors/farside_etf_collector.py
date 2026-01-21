"""
Farside Investors ETF Data Scraper (Professional Cloudflare Bypass Version)

技術優化細節：
1. curl_cffi Session: 持久化 cf_clearance cookie 與 TLS 狀態
2. Impersonate Chrome: 模擬最新瀏覽器 TLS 指紋，避免特徵衝突
3. Automatic Header Management: 移除手動 Header，確保與指紋完全匹配
4. Sequential Fallback: 優先 curl_cffi (高效)，失敗才轉 Selenium (JS 渲染)
"""

from typing import List, Dict, Optional
from datetime import date, datetime, timedelta
from loguru import logger
from curl_cffi.requests import Session
from bs4 import BeautifulSoup
import time
import os

# Selenium imports (Fallback)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class FarsideInvestorsETFCollector:
    """
    Farside Investors ETF 資料爬蟲 - 專業級 Cloudflare 穿透版
    """
    
    BASE_URL_BTC = "https://farside.co.uk/btc/"
    BASE_URL_ETH = "https://farside.co.uk/eth/"
    
    def __init__(self, use_selenium: bool = False):
        """
        初始化 Farside ETF Collector
        """
        self.use_selenium = use_selenium
        self.driver = None
        
        # 1. 永遠使用 Session 以保留驗證通過後的 Cookie (cf_clearance)
        # impersonate="chrome110" 會自動處理對應版本的 TLS 指紋與預設 Headers
        self.session = Session(impersonate="chrome110")
        
        logger.info("Farside ETF Collector initialized with curl_cffi Session (chrome110)")
    
    def _fetch_with_curl_cffi(self, url: str, max_retries: int = 3) -> Optional[str]:
        """使用 curl_cffi Session 抓取頁面"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching {url} (curl_cffi Session, attempt {attempt + 1}/{max_retries})...")
                
                # 直接發送請求，不手動添加過多 Header 避免特徵不符
                response = self.session.get(url, timeout=30)
                
                html = response.text
                
                # 檢查是否觸發五秒盾或被擋
                if 'Just a moment' in html or 'challenge-platform' in html or response.status_code == 403:
                    logger.warning(f"⚠️  Cloudflare Challenge detected (Status: {response.status_code})")
                    if attempt < max_retries - 1:
                        # 隨機等待一段時間模擬真人
                        wait_time = 5 * (attempt + 1)
                        logger.info(f"Waiting {wait_time}s before next attempt...")
                        time.sleep(wait_time)
                        continue
                    return None
                
                response.raise_for_status()
                
                if len(html) < 10000:
                    logger.warning(f"Retrieved content too short ({len(html)} bytes)")
                    continue
                
                logger.info(f"✅ Successfully fetched with curl_cffi ({len(html)} bytes)")
                return html
                
            except Exception as e:
                logger.error(f"curl_cffi session error on {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    return None
        return None

    def _init_selenium_driver(self):
        """備援：初始化 Selenium WebDriver"""
        if self.driver is not None:
            return self.driver
        
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            if os.path.exists('/usr/bin/chromium'):
                chrome_options.binary_location = '/usr/bin/chromium'
                service = Service('/usr/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            return self.driver
        except Exception as e:
            logger.error(f"Failed to initialize Selenium fallback: {e}")
            return None

    def _fetch_with_selenium(self, url: str) -> Optional[str]:
        """備援：使用 Selenium 處理 JS 重定向挑戰"""
        driver = self._init_selenium_driver()
        if not driver: return None
        
        try:
            logger.info(f"Loading {url} with Selenium fallback...")
            driver.get(url)
            # 等待表格載入
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(5) 
            return driver.page_source
        except Exception as e:
            logger.error(f"Selenium fallback failed for {url}: {e}")
            return None

    def _fetch_page_with_retry(self, url: str) -> Optional[str]:
        """階梯式抓取策略"""
        # 1. 優先使用高效的 curl_cffi Session
        html = self._fetch_with_curl_cffi(url)
        
        # 2. 如果被擋或失敗，才動用 Selenium
        if not html:
            logger.warning(f"curl_cffi failed, switching to Selenium fallback for {url}")
            html = self._fetch_with_selenium(url)
            
        return html

    def _parse_etf_table(self, html: str, asset_type: str) -> List[Dict]:
        """解析邏輯 (保持原有的穩定解析代碼)"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            tables = soup.find_all('table')
            if len(tables) < 2: return []
            
            data_table = tables[1]
            rows = data_table.find_all('tr')
            if len(rows) < 4: return []
            
            product_codes = []
            for row in rows[:2]:
                cells = [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]
                codes = [c for c in cells if c and c not in ['', 'Fee', 'Total', 'BTC', 'ETH', 'SOL', 'Date']]
                if codes:
                    product_codes = codes
                    break
            
            if not product_codes: return []
            
            results = []
            start_idx = 2
            for i, row in enumerate(rows):
                first_cell = row.find(['td', 'th']).get_text(strip=True)
                if self._parse_date(first_cell):
                    start_idx = i
                    break

            for row in rows[start_idx:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2: continue
                
                date_text = cells[0].get_text(strip=True)
                flow_date = self._parse_date(date_text)
                if not flow_date: continue
                
                for i, code in enumerate(product_codes):
                    if i + 1 >= len(cells): break
                    flow_usd = self._parse_flow_value(cells[i+1].get_text(strip=True))
                    if flow_usd is None: continue
                    
                    issuer, _ = self._extract_product_info(code, asset_type)
                    results.append({
                        'date': flow_date,
                        'product_code': code,
                        'product_name': code,
                        'issuer': issuer,
                        'asset_type': asset_type,
                        'net_flow_usd': flow_usd,
                        'total_aum_usd': None
                    })
            
            return results
        except Exception as e:
            logger.error(f"Table parsing error: {e}")
            return []

    def _extract_product_info(self, product_name: str, asset_type: str) -> tuple:
        btc_products = {
            'IBIT': ('BlackRock', 'iShares Bitcoin Trust'),
            'FBTC': ('Fidelity', 'Fidelity Wise Origin Bitcoin Fund'),
            'GBTC': ('Grayscale', 'Grayscale Bitcoin Trust'),
            'BITB': ('Bitwise', 'Bitwise Bitcoin ETF'),
            'ARKB': ('ARK Invest', 'ARK 21Shares Bitcoin ETF'),
            'BTCO': ('Invesco', 'Invesco Galaxy Bitcoin ETF'),
            'HODL': ('VanEck', 'VanEck Bitcoin Trust'),
            'BRRR': ('Valkyrie', 'Valkyrie Bitcoin Fund'),
            'EZBC': ('Franklin Templeton', 'Franklin Bitcoin ETF'),
        }
        eth_products = {
            'ETHE': ('Grayscale', 'Grayscale Ethereum Trust'),
            'FETH': ('Fidelity', 'Fidelity Ethereum Fund'),
            'ETHA': ('BlackRock', 'iShares Ethereum Trust'),
            'ETHW': ('Bitwise', 'Bitwise Ethereum ETF'),
        }
        
        products = btc_products if asset_type == 'BTC' else eth_products
        for code, (issuer, _) in products.items():
            if code.upper() in product_name.upper():
                return issuer, code
        return 'Unknown', product_name[:10].upper()

    def _parse_flow_value(self, value) -> Optional[float]:
        if not value or value in ['-', '', '—', '–']: return None
        try:
            v = str(value).replace('$', '').replace(',', '').replace('M', '').strip()
            is_neg = False
            if '(' in v and ')' in v:
                v = v.replace('(', '').replace(')', '')
                is_neg = True
            elif v.startswith('-'):
                is_neg = True
                v = v[1:]
            
            res = float(v) * 1_000_000
            return -res if is_neg else res
        except: return None

    def _parse_date(self, date_str: str) -> Optional[date]:
        if not date_str: return None
        formats = ['%d %b %Y', '%d %B %Y', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d']
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt).date()
                if dt.year == 1900: dt = dt.replace(year=datetime.now().year)
                return dt
            except: continue
        return None

    def run_collection(self, db_loader, days: int = 7) -> int:
        logger.info(f"🚀 Starting ETF flow collection (Last {days} days)...")
        
        results = []
        for url, asset in [(self.BASE_URL_BTC, 'BTC'), (self.BASE_URL_ETH, 'ETH')]:
            html = self._fetch_page_with_retry(url)
            if html:
                results.extend(self._parse_etf_table(html, asset))
        
        if not results:
            logger.warning("No ETF data retrieved from Farside")
            return 0
            
        cutoff = date.today() - timedelta(days=days)
        filtered = [r for r in results if r['date'] >= cutoff]
        
        inserted = db_loader.insert_etf_flows_batch(filtered)
        logger.info(f"✅ ETF collection complete: {inserted} records inserted")
        return inserted

    def __del__(self):
        """確保釋放資源"""
        if hasattr(self, 'session'):
            self.session.close()
        if self.driver:
            try: self.driver.quit()
            except: pass
