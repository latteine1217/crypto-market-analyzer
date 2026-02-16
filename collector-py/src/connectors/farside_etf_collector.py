"""
Farside Investors ETF Data Scraper

設計目標：
1. 以 Playwright 作為主抓取路徑（更接近真實瀏覽器）。
2. curl_cffi 作為防故障 fallback。
3. 使用 pandas.read_html 解析表格，降低 HTML 結構微調風險。
4. 輸出可觀測 metadata（schema fingerprint、source last updated）。
"""

from typing import Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta, time as dtime, timezone
import hashlib
import json
import os
import re
import time as time_module
from io import StringIO

import pandas as pd
from bs4 import BeautifulSoup
from curl_cffi.requests import Session
from loguru import logger

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except Exception:
    sync_playwright = None
    PlaywrightTimeoutError = Exception

try:
    from playwright_stealth import stealth_sync as playwright_stealth_sync
except Exception:
    playwright_stealth_sync = None

try:
    from playwright_stealth import Stealth as PlaywrightStealth
except Exception:
    PlaywrightStealth = None

class FarsideInvestorsETFCollector:
    """
    Farside Investors ETF 資料爬蟲
    """

    BTC_PRODUCTS = {
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
    ETH_PRODUCTS = {
        'ETHE': ('Grayscale', 'Grayscale Ethereum Trust'),
        'FETH': ('Fidelity', 'Fidelity Ethereum Fund'),
        'ETHA': ('BlackRock', 'iShares Ethereum Trust'),
        'ETHW': ('Bitwise', 'Bitwise Ethereum ETF'),
    }

    BASE_URL_BTC = "https://farside.co.uk/btc/"
    BASE_URL_ETH = "https://farside.co.uk/eth/"
    MAX_UNKNOWN_CODES = 200

    def __init__(
        self,
        use_playwright: bool = True,
        use_stealth: bool = True
    ):
        """
        初始化 Farside ETF Collector
        """
        self.use_playwright = use_playwright and os.getenv("ETF_ENABLE_PLAYWRIGHT", "1") != "0"
        self.stealth_mode = self._resolve_stealth_mode()
        self.use_stealth = use_stealth and self.stealth_mode != "none"
        self.market_tz = ZoneInfo("America/New_York") if ZoneInfo else timezone.utc
        self.last_unknown_codes: Dict[str, set] = {}
        self.last_fetch_method: Dict[str, str] = {}
        self.current_url: Optional[str] = None
        self.playwright_executable = os.getenv("ETF_PLAYWRIGHT_EXECUTABLE", "/usr/bin/chromium")
        self.blocked_resource_types = {"image", "font", "media"}
        if os.getenv("ETF_BLOCK_STYLESHEET", "0") == "1":
            self.blocked_resource_types.add("stylesheet")

        # Hybrid Cookie Reuse:
        # - Playwright 只負責拿 Cloudflare cookies + UA
        # - curl_cffi 進行實際抓取（大量抓取更快，且可重用身份）
        self.hybrid_cookie_enabled = os.getenv("ETF_HYBRID_COOKIE", "1") == "1"
        self.cookie_cache_path = os.getenv(
            "ETF_COOKIE_CACHE_PATH", os.path.join("logs", "etf_cookie_cache.json")
        )
        self.cookie_cache_ttl_sec = int(os.getenv("ETF_COOKIE_CACHE_TTL_SEC", "43200"))  # 12h
        self.playwright_headless = os.getenv("ETF_PLAYWRIGHT_HEADLESS", "1") != "0"
        self.curl_impersonate = os.getenv("ETF_CURL_IMPERSONATE", "chrome110")
        self.session = Session(impersonate=self.curl_impersonate)
        self._identity_cache: Optional[Dict] = None

        logger.info(
            "Farside ETF Collector initialized "
            f"(playwright={self.use_playwright}, stealth={self.use_stealth}, "
            f"stealth_mode={self.stealth_mode})"
        )

    @staticmethod
    def _resolve_stealth_mode() -> str:
        """判斷當前環境可用的 stealth API 版本"""
        if playwright_stealth_sync is not None:
            return "stealth_sync"
        if PlaywrightStealth is not None:
            return "stealth_class"
        return "none"

    def _apply_stealth(self, page, context) -> bool:
        """對 Playwright page/context 套用 stealth"""
        if not self.use_stealth:
            return False
        try:
            if self.stealth_mode == "stealth_sync" and playwright_stealth_sync is not None:
                playwright_stealth_sync(page)
                return True
            if self.stealth_mode == "stealth_class" and PlaywrightStealth is not None:
                PlaywrightStealth().apply_stealth_sync(context)
                return True
        except Exception as exc:
            logger.warning(f"Failed to apply stealth ({self.stealth_mode}): {exc}")
        return False

    def _load_identity_from_env(self) -> Optional[Dict]:
        """
        允許用戶手動注入身份（實務上最穩定）：
        - ETF_COOKIES_JSON='{\"cf_clearance\":\"...\",\"__cf_bm\":\"...\"}'
        - ETF_USER_AGENT='Mozilla/5.0 ...'
        - ETF_CF_CLEARANCE='...' （最低限度）
        """
        cookies_json = os.getenv("ETF_COOKIES_JSON", "").strip()
        ua = os.getenv("ETF_USER_AGENT", "").strip() or None
        cf_clearance = os.getenv("ETF_CF_CLEARANCE", "").strip()

        cookies: Dict[str, str] = {}
        if cookies_json:
            try:
                parsed = json.loads(cookies_json)
                if isinstance(parsed, dict):
                    cookies = {str(k): str(v) for k, v in parsed.items() if v is not None}
            except Exception as exc:
                logger.warning(f"Invalid ETF_COOKIES_JSON, ignore: {exc}")
        if cf_clearance and "cf_clearance" not in cookies:
            cookies["cf_clearance"] = cf_clearance

        if not cookies and not ua:
            return None

        return {
            "cookies": cookies,
            "user_agent": ua,
            "source": "env",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

    def _load_identity_from_cache(self) -> Optional[Dict]:
        try:
            if not os.path.exists(self.cookie_cache_path):
                return None
            with open(self.cookie_cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return None
            captured_at = data.get("captured_at")
            if captured_at:
                try:
                    dt = datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))
                    age = (datetime.now(timezone.utc) - dt).total_seconds()
                    if age > self.cookie_cache_ttl_sec:
                        return None
                except Exception:
                    pass
            return data
        except Exception as exc:
            logger.warning(f"Failed to read identity cache: {exc}")
            return None

    def _save_identity_cache(self, identity: Dict) -> None:
        try:
            os.makedirs(os.path.dirname(self.cookie_cache_path) or ".", exist_ok=True)
            payload = dict(identity)
            payload["captured_at"] = payload.get("captured_at") or datetime.now(timezone.utc).isoformat()
            with open(self.cookie_cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning(f"Failed to write identity cache: {exc}")

    def _get_identity(self) -> Optional[Dict]:
        if self._identity_cache is not None:
            return self._identity_cache
        identity = self._load_identity_from_env()
        if identity:
            self._identity_cache = identity
            return identity
        identity = self._load_identity_from_cache()
        if identity:
            self._identity_cache = identity
            return identity
        return None

    def _acquire_identity_with_playwright(self, url: str) -> Optional[Dict]:
        """嘗試用 Playwright 拿到 cookies + UA（若成功，供 curl_cffi 使用）"""
        if not self.use_playwright or sync_playwright is None:
            return None
        try:
            logger.info(f"Acquiring Cloudflare identity via Playwright (headless={self.playwright_headless})...")
            with sync_playwright() as p:
                launch_kwargs = {
                    "headless": self.playwright_headless,
                    "args": [
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                }
                if self.playwright_executable and os.path.exists(self.playwright_executable):
                    launch_kwargs["executable_path"] = self.playwright_executable

                browser = p.chromium.launch(**launch_kwargs)
                context = browser.new_context()
                page = context.new_page()

                def _route_handler(route):
                    if route.request.resource_type in self.blocked_resource_types:
                        return route.abort()
                    return route.continue_()

                page.route("**/*", _route_handler)
                if self.use_stealth:
                    self._apply_stealth(page, context)

                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                try:
                    page.wait_for_selector("table", timeout=60000)
                except PlaywrightTimeoutError:
                    logger.warning("Playwright identity acquisition timed out waiting for table")

                html = page.content()
                if self._is_challenge_page(html, None):
                    logger.warning("Cloudflare challenge still present; identity not acquired")
                    page.close()
                    context.close()
                    browser.close()
                    return None

                try:
                    ua = page.evaluate("navigator.userAgent")
                except Exception:
                    ua = None
                cookies_list = context.cookies()
                cookies = {c.get("name"): c.get("value") for c in cookies_list if c.get("name") and c.get("value")}

                page.close()
                context.close()
                browser.close()

            if not cookies and not ua:
                return None
            identity = {
                "cookies": cookies,
                "user_agent": ua,
                "source": "playwright",
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
            self._identity_cache = identity
            self._save_identity_cache(identity)
            logger.info(f"✅ Acquired identity (cookies={len(cookies)}, ua={'yes' if ua else 'no'})")
            return identity
        except Exception as exc:
            logger.warning(f"Failed to acquire identity via Playwright: {exc}")
            return None

    def _market_close_timestamp(self, flow_date: date) -> datetime:
        """將 ETF 日期對齊到美股收盤（16:00 ET）並轉為 UTC"""
        if isinstance(flow_date, datetime):
            flow_date = flow_date.date()
        close_dt = datetime.combine(flow_date, dtime(16, 0), tzinfo=self.market_tz)
        return close_dt.astimezone(timezone.utc)

    def _known_products(self, asset_type: str) -> set:
        return set(self.BTC_PRODUCTS.keys()) if asset_type == 'BTC' else set(self.ETH_PRODUCTS.keys())

    def _trim_unknown_codes(self, asset_type: str) -> None:
        """限制未知代碼集合大小，避免長期佔用記憶體"""
        codes = self.last_unknown_codes.get(asset_type)
        if not codes or len(codes) <= self.MAX_UNKNOWN_CODES:
            return

        trimmed = set()
        for code in codes:
            trimmed.add(code)
            if len(trimmed) >= self.MAX_UNKNOWN_CODES:
                break
        self.last_unknown_codes[asset_type] = trimmed

    def _record_schema_change(
        self,
        asset_type: str,
        reason: str,
        html: str,
        product_codes: List[str],
        url: Optional[str] = None
    ) -> None:
        """當偵測到欄位變動或新品種時，保留 HTML 快照與欄位資訊"""
        try:
            if url is None:
                url = self.current_url
            snapshot_dir = os.path.join("logs", "etf_snapshots")
            os.makedirs(snapshot_dir, exist_ok=True)
            suffix = f"{asset_type.lower()}_{date.today().isoformat()}_{reason}"
            html_path = os.path.join(snapshot_dir, f"{suffix}.html")
            meta_path = os.path.join(snapshot_dir, f"{suffix}.json")
            if os.path.exists(html_path) and os.path.exists(meta_path):
                return

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html or "")

            metadata = {
                "asset_type": asset_type,
                "reason": reason,
                "product_codes": product_codes,
                "url": url,
                "captured_at": datetime.now(timezone.utc).isoformat()
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            logger.warning(f"ETF schema change snapshot saved: {meta_path}")
        except Exception as e:
            logger.error(f"Failed to write ETF schema snapshot: {e}")

    @staticmethod
    def _is_challenge_page(html: str, status_code: Optional[int] = None) -> bool:
        if status_code == 403:
            return True
        lower = (html or "").lower()
        indicators = [
            "just a moment",
            "challenge-platform",
            "cf-chl",
            "cf-browser-verification",
        ]
        return any(flag in lower for flag in indicators)

    @staticmethod
    def _flatten_columns(columns) -> List[str]:
        if isinstance(columns, pd.MultiIndex):
            return [
                " ".join(str(part).strip() for part in tup if str(part).strip() and str(part).strip().lower() != "nan").strip()
                for tup in columns
            ]
        return [str(col).strip() for col in columns]

    @staticmethod
    def _extract_product_code(raw_name: str) -> Optional[str]:
        text = str(raw_name or "").upper()
        if not text:
            return None
        if any(keyword in text for keyword in ["DATE", "FEE", "TOTAL"]):
            return None
        match = re.search(r"\b([A-Z]{3,6})\b", text)
        if not match:
            return None
        code = match.group(1)
        if code in {"USD", "AUM", "NAV", "FLOW", "FLOWS"}:
            return None
        return code

    @staticmethod
    def _build_schema_fingerprint(product_codes: List[str], columns: List[str]) -> str:
        payload = {
            "products": sorted({code.upper() for code in product_codes}),
            "columns": [str(col).strip() for col in columns],
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _extract_last_updated_text(html: str) -> Optional[str]:
        try:
            soup = BeautifulSoup(html, "html.parser")
            tokens = [t.strip() for t in soup.stripped_strings if t.strip()]
            for idx, token in enumerate(tokens):
                if "last updated" not in token.lower():
                    continue
                if ":" in token:
                    return token
                if idx + 1 < len(tokens) and len(tokens[idx + 1]) <= 48:
                    return f"{token}: {tokens[idx + 1]}"
                return token

            raw_text = " ".join(tokens)
            match = re.search(r"(last\s+updated[^.;]{0,100})", raw_text, flags=re.IGNORECASE)
            return match.group(1).strip() if match else None
        except Exception:
            return None

    def _fetch_with_playwright(self, url: str, max_retries: int = 2) -> Optional[str]:
        """主路徑：Playwright 抓取（可啟用 stealth）"""
        if not self.use_playwright or sync_playwright is None:
            return None

        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching {url} (playwright, attempt {attempt + 1}/{max_retries})...")
                with sync_playwright() as p:
                    launch_kwargs = {
                        "headless": self.playwright_headless,
                        "args": [
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-blink-features=AutomationControlled",
                        ],
                    }
                    if self.playwright_executable and os.path.exists(self.playwright_executable):
                        launch_kwargs["executable_path"] = self.playwright_executable

                    browser = p.chromium.launch(**launch_kwargs)
                    context = browser.new_context()
                    page = context.new_page()

                    def _route_handler(route):
                        if route.request.resource_type in self.blocked_resource_types:
                            return route.abort()
                        return route.continue_()

                    page.route("**/*", _route_handler)
                    if self.use_stealth and not self._apply_stealth(page, context):
                        logger.warning("Stealth is enabled but was not applied")

                    response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(3000)
                    try:
                        page.wait_for_selector("table", timeout=15000)
                    except PlaywrightTimeoutError:
                        logger.warning("Playwright did not find table within timeout, continue with current HTML")

                    html = page.content()
                    status_code = response.status if response else None

                    # 若已經拿到正常頁面，也順手把 cookie/UA 存起來給 curl_cffi reuse
                    if self.hybrid_cookie_enabled and not self._is_challenge_page(html, status_code):
                        try:
                            ua = page.evaluate("navigator.userAgent")
                        except Exception:
                            ua = None
                        cookies_list = context.cookies()
                        cookies = {c.get("name"): c.get("value") for c in cookies_list if c.get("name") and c.get("value")}
                        if cookies or ua:
                            identity = {
                                "cookies": cookies,
                                "user_agent": ua,
                                "source": "playwright",
                                "captured_at": datetime.now(timezone.utc).isoformat(),
                            }
                            self._identity_cache = identity
                            self._save_identity_cache(identity)

                    page.close()
                    context.close()
                    browser.close()

                if self._is_challenge_page(html, status_code):
                    logger.warning(f"⚠️ Cloudflare challenge detected in Playwright path (status={status_code})")
                    if attempt < max_retries - 1:
                        time_module.sleep(2 * (attempt + 1))
                        continue
                    return None

                if len(html) < 6000:
                    logger.warning(f"Playwright content too short ({len(html)} bytes)")
                    if attempt < max_retries - 1:
                        time_module.sleep(2)
                        continue
                    return None

                logger.info(f"✅ Successfully fetched with Playwright ({len(html)} bytes)")
                return html
            except Exception as e:
                logger.error(f"Playwright fetch failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time_module.sleep(2)
                else:
                    return None
        return None

    def _fetch_with_curl_cffi(self, url: str, max_retries: int = 3) -> Optional[str]:
        """備援：使用 curl_cffi Session 抓取頁面"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching {url} (curl_cffi, attempt {attempt + 1}/{max_retries})...")
                identity = self._get_identity() if self.hybrid_cookie_enabled else None
                headers = {}
                cookies = None
                if identity:
                    ua = identity.get("user_agent")
                    if ua:
                        headers["User-Agent"] = ua
                    cookies = identity.get("cookies") or None

                response = self.session.get(url, timeout=30, headers=headers or None, cookies=cookies)
                html = response.text

                if self._is_challenge_page(html, response.status_code):
                    logger.warning(f"⚠️ Cloudflare challenge detected in curl_cffi path (status={response.status_code})")
                    # Hybrid：嘗試用 Playwright 拿到 cookies/UA 後再重試
                    if self.hybrid_cookie_enabled and attempt == 0:
                        refreshed = self._acquire_identity_with_playwright(url)
                        if refreshed:
                            logger.info("Retry curl_cffi after identity refresh...")
                            continue
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        logger.info(f"Waiting {wait_time}s before next curl_cffi retry...")
                        time_module.sleep(wait_time)
                        continue
                    return None

                response.raise_for_status()
                if len(html) < 6000:
                    logger.warning(f"curl_cffi content too short ({len(html)} bytes)")
                    if attempt < max_retries - 1:
                        time_module.sleep(2)
                        continue
                    return None

                logger.info(f"✅ Successfully fetched with curl_cffi ({len(html)} bytes)")
                return html
            except Exception as e:
                logger.error(f"curl_cffi fetch failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time_module.sleep(3)
                else:
                    return None
        return None

    def _fetch_page_with_retry(self, url: str, max_retries: int = 3) -> Tuple[Optional[str], str]:
        """階梯式抓取策略：Playwright -> curl_cffi（Selenium 已移除）"""
        html = self._fetch_with_playwright(url, max_retries=min(max_retries, 2))
        if html:
            return html, "playwright"

        html = self._fetch_with_curl_cffi(url, max_retries=max_retries)
        if html:
            return html, "curl_cffi"

        return None, "none"

    def _select_etf_table(self, html: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """從 read_html 結果中選出最可能的 ETF 主表"""
        try:
            tables = pd.read_html(StringIO(html))
        except ValueError:
            return None, None

        best_df: Optional[pd.DataFrame] = None
        best_date_col: Optional[str] = None
        best_score = -1

        for table in tables:
            if table.empty or table.shape[1] < 3:
                continue

            candidate = table.copy()
            candidate.columns = self._flatten_columns(candidate.columns)
            date_col = next((c for c in candidate.columns if "date" in c.lower()), candidate.columns[0])

            sample = candidate[date_col].head(20).tolist()
            parsed_count = sum(1 for item in sample if self._parse_date(item) is not None)
            if parsed_count < 2:
                continue

            score = parsed_count * 10 + candidate.shape[1]
            if score > best_score:
                best_score = score
                best_df = candidate
                best_date_col = date_col

        return best_df, best_date_col

    def _parse_etf_table(self, html: str, asset_type: str) -> List[Dict]:
        """使用 pandas.read_html 解析 ETF 主表"""
        try:
            df, date_col = self._select_etf_table(html)
            if df is None or date_col is None:
                self._record_schema_change(asset_type, "missing_table", html, [], url=None)
                return []

            columns = [str(col).strip() for col in df.columns]
            product_columns: List[Tuple[str, str]] = []
            for col in columns:
                if col == date_col:
                    continue
                lower_col = col.lower()
                if any(flag in lower_col for flag in ["fee", "total"]):
                    continue
                code = self._extract_product_code(col)
                if code:
                    product_columns.append((col, code))

            if not product_columns:
                self._record_schema_change(asset_type, "missing_product_codes", html, [], url=None)
                return []

            product_codes = [code for _, code in product_columns]
            known_codes = self._known_products(asset_type)
            unknown_codes = [code for code in product_codes if code.upper() not in known_codes]
            if unknown_codes:
                self.last_unknown_codes.setdefault(asset_type, set()).update([c.upper() for c in unknown_codes])
                self._trim_unknown_codes(asset_type)
                logger.warning(f"Detected unknown ETF product codes ({asset_type}): {sorted(set(unknown_codes))}")
                self._record_schema_change(asset_type, "unknown_product_codes", html, product_codes, url=None)

            last_updated = self._extract_last_updated_text(html)
            schema_fingerprint = self._build_schema_fingerprint(product_codes, columns)
            fetch_method = self.last_fetch_method.get(asset_type, "unknown")

            results = []
            for _, row in df.iterrows():
                flow_date = self._parse_date(row.get(date_col))
                if not flow_date:
                    continue
                timestamp = self._market_close_timestamp(flow_date)

                for column_name, code in product_columns:
                    flow_usd = self._parse_flow_value(row.get(column_name))
                    if flow_usd is None:
                        continue
                    issuer, canonical_code = self._extract_product_info(code, asset_type)
                    results.append({
                        'date': flow_date,
                        'timestamp': timestamp,
                        'product_code': canonical_code,
                        'product_name': code,
                        'issuer': issuer,
                        'asset_type': asset_type,
                        'net_flow_usd': flow_usd,
                        'total_aum_usd': None,
                        'source_url': self.current_url,
                        'source_last_updated': last_updated,
                        'schema_fingerprint': schema_fingerprint,
                        'fetch_method': fetch_method,
                    })

            return results
        except Exception as e:
            logger.error(f"Table parsing error: {e}")
            self._record_schema_change(asset_type, "parse_exception", html, [], url=None)
            return []

    def _extract_product_info(self, product_name: str, asset_type: str) -> tuple:
        products = self.BTC_PRODUCTS if asset_type == 'BTC' else self.ETH_PRODUCTS
        for code, (issuer, _) in products.items():
            if code.upper() in str(product_name).upper():
                return issuer, code
        return 'Unknown', str(product_name).upper()[:10]

    def _parse_flow_value(self, value) -> Optional[float]:
        """統一解析 Farside 金額欄位，輸出 USD"""
        if value is None:
            return None
        if isinstance(value, float) and pd.isna(value):
            return None

        if isinstance(value, (int, float)):
            numeric = float(value)
            if numeric == 0:
                return 0.0
            return numeric * 1_000_000

        raw = str(value).strip()
        if not raw or raw.lower() in {'nan', 'none', '-', '—', '–'}:
            return None

        is_negative = False
        if raw.startswith("(") and raw.endswith(")"):
            is_negative = True
            raw = raw[1:-1]
        if raw.startswith("-"):
            is_negative = True
            raw = raw[1:]
        if raw.startswith("+"):
            raw = raw[1:]

        raw = raw.replace("$", "").replace(",", "").strip()
        lower = raw.lower()

        multiplier = 1_000_000
        explicit_unit = False
        for suffix, factor in [("billion", 1_000_000_000), ("million", 1_000_000), ("thousand", 1_000)]:
            if suffix in lower:
                multiplier = factor
                lower = lower.replace(suffix, "").strip()
                explicit_unit = True
                break

        if not explicit_unit and lower.endswith("b"):
            multiplier = 1_000_000_000
            lower = lower[:-1].strip()
            explicit_unit = True
        elif not explicit_unit and lower.endswith("m"):
            multiplier = 1_000_000
            lower = lower[:-1].strip()
            explicit_unit = True
        elif not explicit_unit and lower.endswith("k"):
            multiplier = 1_000
            lower = lower[:-1].strip()
            explicit_unit = True

        try:
            numeric = float(lower)
        except ValueError:
            return None

        # 若來源已是絕對美元級（>= 100k）且沒有顯式單位，避免再乘 1e6
        if not explicit_unit and abs(numeric) >= 100_000:
            multiplier = 1

        amount = numeric * multiplier
        return -amount if is_negative else amount

    def _parse_date(self, date_value) -> Optional[date]:
        if date_value is None:
            return None
        if isinstance(date_value, date) and not isinstance(date_value, datetime):
            return date_value
        if isinstance(date_value, datetime):
            return date_value.date()
        if isinstance(date_value, pd.Timestamp):
            return date_value.to_pydatetime().date()

        text = str(date_value).strip()
        if not text:
            return None
        text = text.replace(".", "/")

        formats = [
            '%d %b %Y',
            '%d %B %Y',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y-%m-%d',
            '%Y/%m/%d',
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(text, fmt).date()
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now().year)
                return dt
            except ValueError:
                continue

        fallback = pd.to_datetime(text, errors='coerce')
        if pd.isna(fallback):
            return None
        return fallback.to_pydatetime().date()

    def run_collection(self, db_loader, days: int = 7) -> int:
        logger.info(f"=== ETF Collection Start === (lookback_days={days})")
        self.last_unknown_codes = {}
        self.last_fetch_method = {}

        results = []
        source_stats = {}
        for url, asset in [(self.BASE_URL_BTC, 'BTC'), (self.BASE_URL_ETH, 'ETH')]:
            self.current_url = url
            html, method = self._fetch_page_with_retry(url)
            self.last_fetch_method[asset] = method
            source_stats[asset] = method
            if html:
                parsed = self._parse_etf_table(html, asset)
                logger.info(f"Parsed {len(parsed)} ETF rows for {asset} (method={method})")
                results.extend(parsed)
            else:
                logger.warning(f"No HTML retrieved for {asset} (method={method})")

        if not results:
            logger.warning("No ETF data retrieved from Farside")
            return 0

        cutoff = datetime.now(self.market_tz).date() - timedelta(days=days)
        filtered = [r for r in results if r['date'] >= cutoff]
        inserted = db_loader.insert_etf_flows_batch(filtered)

        logger.info(
            "=== ETF Collection Done === "
            f"inserted={inserted}, total_parsed={len(results)}, "
            f"filtered={len(filtered)}, source_stats={source_stats}"
        )
        return inserted

    def get_last_unknown_codes(self) -> Dict[str, List[str]]:
        """返回最近一次收集偵測到的未知產品代碼"""
        return {k: sorted(list(v)) for k, v in self.last_unknown_codes.items()}

    def __del__(self):
        """確保釋放資源"""
        if hasattr(self, 'session'):
            self.session.close()
