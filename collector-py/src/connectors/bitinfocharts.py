"""
BitInfoCharts Connector

設計目標：
1. 抓取層可回退：curl_cffi（主） -> Playwright（身份刷新/備援）
2. 解析層防禦性：pandas.read_html + 以欄位語意選表，避免 DOM 位置漂移
3. 可觀測：輸出 fetch_method/schema_fingerprint/source_last_updated，並在異常時保存 snapshot

備註：
- BitInfoCharts 多數頁面不需 JS 渲染；Playwright 預設只作備援與身份刷新。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from io import StringIO
import hashlib
import json
import os
import re
import time as time_module

import pandas as pd
from bs4 import BeautifulSoup
from curl_cffi.requests import Session
from loguru import logger

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except Exception:
    sync_playwright = None
    PlaywrightTimeoutError = Exception


class BitInfoChartsClient:
    def __init__(self):
        self.base_url = os.getenv(
            "BITINFO_RICH_LIST_URL",
            "https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html",
        )

        # curl_cffi
        self.curl_impersonate = os.getenv("BITINFO_CURL_IMPERSONATE", "chrome110")
        self.session = Session(impersonate=self.curl_impersonate)

        # Hybrid identity cache (optional)
        self.hybrid_cookie_enabled = os.getenv("BITINFO_HYBRID_COOKIE", "0") == "1"
        self.cookie_cache_path = os.getenv(
            "BITINFO_COOKIE_CACHE_PATH", os.path.join("logs", "bitinfo_cookie_cache.json")
        )
        self.cookie_cache_ttl_sec = int(os.getenv("BITINFO_COOKIE_CACHE_TTL_SEC", "86400"))  # 24h
        self._identity_cache: Optional[Dict] = None

        # Playwright (fallback/identity refresh)
        self.playwright_enabled = os.getenv("BITINFO_ENABLE_PLAYWRIGHT", "0") == "1"
        self.playwright_headless = os.getenv("BITINFO_PLAYWRIGHT_HEADLESS", "1") != "0"
        self.playwright_executable = os.getenv("BITINFO_PLAYWRIGHT_EXECUTABLE", "/usr/bin/chromium")
        self.blocked_resource_types = {"image", "font", "media"}
        if os.getenv("BITINFO_BLOCK_STYLESHEET", "0") == "1":
            self.blocked_resource_types.add("stylesheet")

        self.last_fetch_method: str = "unknown"
        self.last_schema_fingerprint: Optional[str] = None
        self.last_columns: Optional[List[str]] = None
        self.last_source_last_updated: Optional[str] = None
        self.last_row_count: Optional[int] = None

        logger.info(
            "BitInfoCharts client initialized "
            f"(hybrid_cookie={self.hybrid_cookie_enabled}, curl_impersonate={self.curl_impersonate}, "
            f"playwright={self.playwright_enabled})"
        )

    # -------------------------
    # Identity (Optional)
    # -------------------------
    def _load_identity_from_env(self) -> Optional[Dict]:
        cookies_json = os.getenv("BITINFO_COOKIES_JSON", "").strip()
        ua = os.getenv("BITINFO_USER_AGENT", "").strip() or None

        cookies: Dict[str, str] = {}
        if cookies_json:
            try:
                parsed = json.loads(cookies_json)
                if isinstance(parsed, dict):
                    cookies = {str(k): str(v) for k, v in parsed.items() if v is not None}
            except Exception as exc:
                logger.warning(f"Invalid BITINFO_COOKIES_JSON, ignore: {exc}")

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
            logger.warning(f"Failed to read BitInfoCharts identity cache: {exc}")
            return None

    def _save_identity_cache(self, identity: Dict) -> None:
        try:
            os.makedirs(os.path.dirname(self.cookie_cache_path) or ".", exist_ok=True)
            payload = dict(identity)
            payload["captured_at"] = payload.get("captured_at") or datetime.now(timezone.utc).isoformat()
            with open(self.cookie_cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning(f"Failed to write BitInfoCharts identity cache: {exc}")

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

    # -------------------------
    # Fetch
    # -------------------------
    @staticmethod
    def _is_challenge_page(html: str, status_code: Optional[int] = None) -> bool:
        if status_code in (401, 403, 429):
            return True
        lower = (html or "").lower()
        indicators = [
            "just a moment",
            "cf-chl",
            "challenge-platform",
            "cloudflare",
            "captcha",
        ]
        return any(flag in lower for flag in indicators)

    def _record_snapshot(self, reason: str, html: str, metadata: Dict) -> None:
        try:
            snapshot_dir = os.path.join("logs", "bitinfo_snapshots")
            os.makedirs(snapshot_dir, exist_ok=True)
            suffix = f"bitinfo_{datetime.now(timezone.utc).date().isoformat()}_{reason}"
            html_path = os.path.join(snapshot_dir, f"{suffix}.html")
            meta_path = os.path.join(snapshot_dir, f"{suffix}.json")
            if not os.path.exists(html_path):
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html or "")
            if not os.path.exists(meta_path):
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            logger.warning(f"BitInfoCharts snapshot saved: {meta_path}")
        except Exception as exc:
            logger.warning(f"Failed to write BitInfoCharts snapshot: {exc}")

    def _fetch_with_curl_cffi(self, url: str, max_retries: int = 3) -> Optional[str]:
        for attempt in range(max_retries):
            try:
                headers = {}
                cookies = None
                if self.hybrid_cookie_enabled:
                    ident = self._get_identity()
                    if ident:
                        if ident.get("user_agent"):
                            headers["User-Agent"] = ident["user_agent"]
                        cookies = ident.get("cookies") or None

                logger.info(f"Fetching {url} (curl_cffi, attempt {attempt + 1}/{max_retries})...")
                resp = self.session.get(url, timeout=30, headers=headers or None, cookies=cookies)
                html = resp.text

                if self._is_challenge_page(html, resp.status_code):
                    logger.warning(
                        f"⚠️ BitInfoCharts challenge detected (curl_cffi, status={resp.status_code})"
                    )
                    if attempt < max_retries - 1:
                        time_module.sleep(2 * (attempt + 1))
                        continue
                    return None

                resp.raise_for_status()
                if len(html) < 4000:
                    logger.warning(f"BitInfoCharts content too short ({len(html)} bytes)")
                    if attempt < max_retries - 1:
                        time_module.sleep(2)
                        continue
                    return None

                self.last_fetch_method = "curl_cffi"
                return html
            except Exception as exc:
                logger.warning(f"BitInfoCharts curl_cffi fetch failed: {exc}")
                if attempt < max_retries - 1:
                    time_module.sleep(2)
                else:
                    return None
        return None

    def _fetch_with_playwright(self, url: str) -> Optional[str]:
        if not self.playwright_enabled or sync_playwright is None:
            return None
        try:
            logger.info(f"Fetching {url} (playwright, headless={self.playwright_headless})...")
            with sync_playwright() as p:
                launch_kwargs = {
                    "headless": self.playwright_headless,
                    "args": ["--no-sandbox", "--disable-dev-shm-usage"],
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
                response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1500)
                html = page.content()
                status = response.status if response else None

                # 若成功且啟用 hybrid，保存身份給 curl_cffi
                if self.hybrid_cookie_enabled and not self._is_challenge_page(html, status):
                    try:
                        ua = page.evaluate("navigator.userAgent")
                    except Exception:
                        ua = None
                    cookies_list = context.cookies()
                    cookies = {c.get("name"): c.get("value") for c in cookies_list if c.get("name") and c.get("value")}
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

            if self._is_challenge_page(html, status):
                logger.warning(f"⚠️ BitInfoCharts challenge detected (playwright, status={status})")
                return None

            self.last_fetch_method = "playwright"
            return html
        except Exception as exc:
            logger.warning(f"BitInfoCharts playwright fetch failed: {exc}")
            return None

    def _fetch_page(self, url: str) -> Optional[str]:
        html = self._fetch_with_curl_cffi(url)
        if html:
            return html
        # 只有在 curl 失敗時才試 playwright（避免浪費）
        html = self._fetch_with_playwright(url)
        return html

    # -------------------------
    # Parse
    # -------------------------
    @staticmethod
    def _flatten_columns(columns) -> List[str]:
        if isinstance(columns, pd.MultiIndex):
            return [
                " ".join(str(part).strip() for part in tup if str(part).strip() and str(part).strip().lower() != "nan").strip()
                for tup in columns
            ]
        return [str(col).strip() for col in columns]

    @staticmethod
    def _build_schema_fingerprint(columns: List[str]) -> str:
        canonical = json.dumps({"columns": [str(c).strip() for c in columns]}, ensure_ascii=False, sort_keys=True)
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
                if idx + 1 < len(tokens) and len(tokens[idx + 1]) <= 64:
                    return f"{token}: {tokens[idx + 1]}"
                return token
            return None
        except Exception:
            return None

    @staticmethod
    def _parse_number(text: str) -> Optional[float]:
        """
        支援：
        - '1,234'
        - '$1.2B', '4.5M', '123k'
        - '(123.4)' -> -123.4
        """
        if text is None:
            return None
        raw = str(text).strip()
        if not raw or raw.lower() in {"nan", "none", "-", "—", "–"}:
            return None

        neg = False
        if raw.startswith("(") and raw.endswith(")"):
            neg = True
            raw = raw[1:-1].strip()
        if raw.startswith("-"):
            neg = True
            raw = raw[1:].strip()
        if raw.startswith("+"):
            raw = raw[1:].strip()

        raw = raw.replace("$", "").replace(",", "").strip()
        lower = raw.lower()

        mult = 1.0
        if lower.endswith("b"):
            mult = 1e9
            lower = lower[:-1].strip()
        elif lower.endswith("m"):
            mult = 1e6
            lower = lower[:-1].strip()
        elif lower.endswith("k"):
            mult = 1e3
            lower = lower[:-1].strip()

        # 只留數字與小數點
        cleaned = re.sub(r"[^0-9.]", "", lower)
        if not cleaned:
            return None
        try:
            val = float(cleaned) * mult
        except ValueError:
            return None
        return -val if neg else val

    @staticmethod
    def _parse_int_count(text: str) -> Optional[int]:
        """專用於 addresses count：必須是純數字（允許逗號/空白），拒絕地址字串等混雜內容。"""
        if text is None:
            return None
        raw = str(text).strip()
        if not raw or raw.lower() in {"nan", "none", "-", "—", "–"}:
            return None
        # 含字母通常是 address/hash，直接拒絕
        if re.search(r"[a-zA-Z]", raw):
            return None
        digits = re.sub(r"[^\d]", "", raw)
        if not digits:
            return None
        try:
            val = int(digits)
        except Exception:
            return None
        # 合理上限：全球 BTC addresses 不會超過 1e12
        if val < 0 or val > 1_000_000_000_000:
            return None
        return val

    @staticmethod
    def _looks_like_range(text: str) -> bool:
        """判斷第一欄是否像 balance range（distribution 表），避免誤選 top addresses 表。"""
        s = str(text or "").strip()
        if not s:
            return False
        # top addresses balance 欄常含 $ 金額，distribution range 通常不會
        if "$" in s:
            return False
        # 常見 range 記號
        markers = ["-", "[", "]", "<", ">", "to"]
        if not any(m in s for m in markers):
            return False
        return any(ch.isdigit() for ch in s)

    def _select_distribution_table(self, html: str) -> Optional[pd.DataFrame]:
        try:
            dfs = pd.read_html(StringIO(html))
        except ValueError:
            return None
        if not dfs:
            return None

        best = None
        best_score = -1
        for df in dfs:
            if df.empty or df.shape[1] < 3:
                continue
            cols = [str(c).strip().lower() for c in self._flatten_columns(df.columns)]
            score = 0
            if any("balance" in c for c in cols):
                score += 3
            if any("address" in c for c in cols):
                score += 3
            if any(("btc" in c) or ("coin" in c) for c in cols):
                score += 2
            if any("%" in c for c in cols):
                score += 1

            # 進一步驗證：distribution 表的 balance 欄多為「range」，addresses 欄多為「純數字」
            df2 = df.copy()
            df2.columns = self._flatten_columns(df2.columns)
            col_map = {str(c).strip().lower(): c for c in df2.columns}
            balance_col = next((col_map[c] for c in col_map if "balance" in c), df2.columns[0])
            address_col = next((col_map[c] for c in col_map if "address" in c), None)
            btc_col = next((col_map[c] for c in col_map if ("btc" in c) or ("coin" in c)), None)

            sample_n = min(int(df2.shape[0] or 0), 12)
            if sample_n <= 0:
                continue

            balance_samples = [df2.iloc[i][balance_col] for i in range(sample_n)]
            range_hits = sum(1 for v in balance_samples if self._looks_like_range(v))
            score += range_hits * 1.5

            if address_col is not None:
                addr_samples = [df2.iloc[i][address_col] for i in range(sample_n)]
                addr_hits = sum(1 for v in addr_samples if self._parse_int_count(v) is not None)
                score += addr_hits * 2.0
                # 若 addresses 欄大多不是數字，通常是 top addresses 表，直接降權
                if addr_hits < max(4, sample_n // 2):
                    score -= 10

            if btc_col is not None:
                btc_samples = [str(df2.iloc[i][btc_col]).strip().split()[0] for i in range(sample_n)]
                btc_vals = [self._parse_number(v) for v in btc_samples]
                btc_hits = sum(1 for v in btc_vals if v is not None and 0 <= float(v) <= 30_000_000)
                score += btc_hits * 0.5

            score += min(df.shape[0], 50) / 100.0
            if score > best_score:
                best_score = score
                best = df.copy()
        return best

    def _parse_distribution_rows(self, html: str) -> Tuple[List[Dict], Dict]:
        df = self._select_distribution_table(html)
        if df is None:
            return [], {"reason": "missing_table"}

        df.columns = self._flatten_columns(df.columns)
        columns = [str(c).strip() for c in df.columns]
        schema_fingerprint = self._build_schema_fingerprint(columns)

        def _norm_col(s: str) -> str:
            # 例: "Balance, BTC" -> "balancebtc", "BTC" -> "btc"
            return re.sub(r"[^a-z0-9%]+", "", str(s).strip().lower())

        col_map = {str(c).strip().lower(): c for c in df.columns}
        balance_col = next((col_map[c] for c in col_map if "balance" in c), df.columns[0])
        address_col = next((col_map[c] for c in col_map if "address" in c), df.columns[min(1, len(df.columns) - 1)])
        # 注意：欄位可能同時存在 "Balance, BTC"（range）與 "BTC"（總量），不能用單純包含 btc 來選
        btc_col = None
        for c in df.columns:
            if c == balance_col:
                continue
            n = _norm_col(c)
            if n == "btc":
                btc_col = c
                break
        if btc_col is None:
            for c in df.columns:
                if c == balance_col:
                    continue
                n = _norm_col(c)
                if n in ("coin", "coins"):
                    btc_col = c
                    break
        if btc_col is None:
            for c in df.columns:
                if c == balance_col:
                    continue
                n = _norm_col(c)
                if (("btc" in n) or ("coin" in n)) and ("balance" not in n):
                    btc_col = c
                    break
        if btc_col is None:
            btc_col = df.columns[min(2, len(df.columns) - 1)]

        usd_col = next((col_map[c] for c in col_map if ("usd" in c) or ("$" in c)), None)
        pct_col = next((col_map[c] for c in col_map if "%" in c), None)

        rows: List[Dict] = []
        for _, row in df.iterrows():
            tier = str(row.get(balance_col, "")).strip()
            if not tier or "balance" in tier.lower() or "total" in tier.lower():
                continue
            # 避免誤選 top addresses 類表：tier 若包含 $，幾乎可判定不是 range
            if "$" in tier:
                continue

            addr_raw = str(row.get(address_col, "")).strip()
            address_count = self._parse_int_count(addr_raw)
            if address_count is None:
                continue

            btc_raw = str(row.get(btc_col, "")).strip()
            # e.g. "4,200,000 BTC" -> take first token
            btc_token = btc_raw.split()[0] if btc_raw else ""
            total_balance = self._parse_number(btc_token)
            if total_balance is None:
                continue
            # 合理上限：BTC 總量不可能超過 30M
            if float(total_balance) < 0 or float(total_balance) > 30_000_000:
                continue

            usd_amount = 0.0
            if usd_col is not None:
                usd_raw = str(row.get(usd_col, "")).strip()
                usd_amount = float(self._parse_number(usd_raw) or 0.0)

            pct_supply = 0.0
            if pct_col is not None:
                pct_raw = str(row.get(pct_col, "")).strip()
                pct_token = pct_raw.split("%")[0] if "%" in pct_raw else pct_raw
                pct_supply = float(self._parse_number(pct_token) or 0.0)

            rows.append(
                {
                    "rank_group": tier,
                    "address_count": address_count,
                    "total_balance": float(total_balance),
                    "total_balance_usd": float(usd_amount),
                    "percentage_of_supply": float(pct_supply),
                    "symbol": "BTC",
                    "source_url": self.base_url,
                    "source_last_updated": self._extract_last_updated_text(html),
                    "schema_fingerprint": schema_fingerprint,
                    "fetch_method": self.last_fetch_method,
                }
            )

        return rows, {"schema_fingerprint": schema_fingerprint, "columns": columns}

    # -------------------------
    # Public API
    # -------------------------
    def fetch_distribution_data(self) -> Optional[List[Dict]]:
        """
        抓取 Bitcoin distribution table（rich list / balance distribution）
        回傳 list[dict]，至少包含：
        - rank_group, address_count, total_balance, symbol
        """
        url = self.base_url
        html = self._fetch_page(url)
        if not html:
            self._record_snapshot(
                "no_html",
                "",
                {"url": url, "fetch_method": self.last_fetch_method},
            )
            return None

        rows, meta = self._parse_distribution_rows(html)
        if not rows:
            self.last_schema_fingerprint = meta.get("schema_fingerprint")
            self.last_columns = meta.get("columns")
            self.last_source_last_updated = None
            self.last_row_count = 0
            self._record_snapshot(
                "parse_empty",
                html,
                {"url": url, "fetch_method": self.last_fetch_method, **meta},
            )
            return None

        self.last_schema_fingerprint = meta.get("schema_fingerprint")
        self.last_columns = meta.get("columns")
        self.last_source_last_updated = rows[0].get("source_last_updated")
        self.last_row_count = len(rows)

        logger.info(
            f"Parsed BitInfoCharts distribution rows={len(rows)} "
            f"(fetch_method={self.last_fetch_method}, schema={meta.get('schema_fingerprint')})"
        )
        return rows

    def __del__(self):
        if hasattr(self, "session"):
            self.session.close()


if __name__ == "__main__":
    client = BitInfoChartsClient()
    data = client.fetch_distribution_data()
    print("rows", len(data or []))
