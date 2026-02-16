"""
SoSoValue OpenAPI v2 - Current ETF Data Metrics Collector (BTC only)

目標：
- 抓取「單檔」US BTC Spot ETF 的每日流入/累積流入等指標，支援 issuer 比較與單檔比較
- 以 API 取代脆弱的 Web Scraping，降低維運成本

資料來源：
POST https://api.sosovalue.xyz/openapi/v2/etf/currentEtfDataMetrics
headers: x-soso-api-key
body: {"type": "us-btc-spot"}

注意：
- 此端點回傳的是「目前最新的一天」的各檔 ETF 指標，並非歷史序列。
- 我們會把該日快照寫入 DB，長期累積後即可形成 issuer/product 的歷史序列。
"""

from __future__ import annotations

from typing import Dict, List, Optional
from datetime import date, datetime, time, timezone
import hashlib
import json
import os

import certifi
from loguru import logger
import requests

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


class SoSoValueOpenAPIETFProductsCollector:
    ENDPOINT = "https://api.sosovalue.xyz/openapi/v2/etf/currentEtfDataMetrics"
    TYPE_US_BTC_SPOT = "us-btc-spot"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.getenv("SOSOVALUE_API_KEY") or "").strip()
        self.market_tz = ZoneInfo("America/New_York") if ZoneInfo else timezone.utc
        self.last_fetch_method = "sosovalue_openapi"
        self.last_schema_fingerprint: Optional[str] = None

        if not self.api_key:
            logger.warning("SOSOVALUE_API_KEY is not set; SoSoValue ETF products collector will return 0 records.")

        # SSL verify: 某些環境下 certifi 可能缺少 issuer（會導致 CERTIFICATE_VERIFY_FAILED）。
        self.verify_ssl = True
        self.ca_file = os.getenv("SOSOVALUE_CA_FILE", "").strip() or None
        if not self.ca_file:
            self.ca_file = "/etc/ssl/certs/ca-certificates.crt" if os.path.exists("/etc/ssl/certs/ca-certificates.crt") else certifi.where()

    def get_last_unknown_codes(self) -> Dict[str, List[str]]:
        # 保持介面一致，避免下游壞掉
        return {}

    def _market_close_timestamp(self, flow_date: date) -> datetime:
        close_dt = datetime.combine(flow_date, time(16, 0), tzinfo=self.market_tz)
        return close_dt.astimezone(timezone.utc)

    @staticmethod
    def _schema_fingerprint(payload: dict) -> str:
        keys = []
        data = payload.get("data")
        lst = []
        if isinstance(data, dict):
            lst = data.get("list") or []
        if isinstance(lst, list) and lst:
            item = lst[0] if isinstance(lst[0], dict) else {}
            keys = sorted([str(k) for k in item.keys()])
        canonical = json.dumps({"keys": keys}, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_date(d: str) -> Optional[date]:
        try:
            return datetime.strptime(str(d), "%Y-%m-%d").date()
        except Exception:
            return None

    @staticmethod
    def _to_float(v):
        try:
            return float(v) if v is not None else None
        except Exception:
            return None

    @classmethod
    def _extract_metric_value(cls, it: dict, key: str) -> Optional[float]:
        """
        SoSoValue 的單一欄位常見形態：
        - {"value": 123.45, "lastUpdateDate": "..."}
        - 123.45 / "123.45"
        """
        try:
            v = it.get(key)
            if isinstance(v, dict):
                return cls._to_float(v.get("value"))
            return cls._to_float(v)
        except Exception:
            return None

    @staticmethod
    def _normalize_institute(name: Optional[str]) -> str:
        if not name:
            return "Unknown"
        raw = str(name).strip()
        low = raw.lower()
        # 讓 dashboard 的 issuerKeyMap 可以命中
        if "blackrock" in low:
            return "BlackRock"
        if "grayscale" in low:
            return "Grayscale"
        # 常見發行商大小寫
        mapping = {
            "fidelity": "Fidelity",
            "ark": "ARK",
            "bitwise": "Bitwise",
            "vaneck": "VanEck",
            "valkyrie": "Valkyrie",
            "invesco": "Invesco",
            "franklin": "Franklin",
            "wisdomtree": "WisdomTree",
            "hashdex": "Hashdex",
        }
        for k, v in mapping.items():
            if k in low:
                return v
        return raw

    def _fetch_metrics(self) -> Optional[dict]:
        if not self.api_key:
            return None
        headers = {
            "x-soso-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = {"type": self.TYPE_US_BTC_SPOT}
        try:
            resp = requests.post(self.ENDPOINT, headers=headers, json=body, timeout=30, verify=self.ca_file)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            logger.error(f"SoSoValue OpenAPI request failed: {exc}")
            return None

        if not isinstance(payload, dict) or payload.get("code") != 0:
            logger.error(f"SoSoValue OpenAPI returned failure: {payload.get('code')} msg={payload.get('msg')}")
            return None
        self.last_schema_fingerprint = self._schema_fingerprint(payload)
        return payload

    def _to_rows(self, payload: dict) -> List[Dict]:
        data = payload.get("data") or {}
        items = data.get("list") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []

        rows: List[Dict] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            ticker = (it.get("ticker") or "").strip()
            if not ticker:
                continue

            institute = self._normalize_institute(it.get("institute"))
            product_name = it.get("name") or ticker

            daily = it.get("dailyNetInflow") or {}
            net_flow = self._to_float((daily.get("value") if isinstance(daily, dict) else None))
            last_update = daily.get("lastUpdateDate") if isinstance(daily, dict) else None
            flow_date = self._parse_date(last_update) if last_update else None
            if flow_date is None:
                # 沒有日期就無法落到正確的日序列，直接跳過
                continue

            # dailyNetInflow 可能為 null（資料未更新），此時不落庫避免污染
            if net_flow is None:
                continue

            cum = it.get("cumNetInflow") or {}
            cum_net = self._to_float((cum.get("value") if isinstance(cum, dict) else None))

            # AUM / Net Assets：SoSoValue 常用欄位是 netAssets（不是 netAssetValue）
            net_assets = it.get("netAssets") or it.get("netAssetValue") or {}
            total_aum = self._to_float((net_assets.get("value") if isinstance(net_assets, dict) else None))

            # 成交金額（USD）：SoSoValue 常用欄位是 dailyValueTraded
            dv = it.get("dailyValueTraded") or it.get("volume") or {}
            traded = self._to_float((dv.get("value") if isinstance(dv, dict) else None))

            # 溢價率（Premium/Discount to NAV）
            # SoSoValue 目前直接提供 discountPremiumRate（ratio，例如 -0.0029 = -0.29%）
            premium_rate = None
            for k in ("discountPremiumRate", "premiumRate", "premium_rate"):
                premium_rate = self._extract_metric_value(it, k)
                if premium_rate is not None:
                    break

            # 若 API 沒給 premium rate，才嘗試用 market_price/nav_per_share 自行計算（多 key fallback）
            nav_per_share = None
            market_price = None
            if premium_rate is None:
                for k in ("navPerShare", "nav", "nav_price", "navPrice", "netAssetValuePerShare"):
                    nav_per_share = self._extract_metric_value(it, k)
                    if nav_per_share is not None:
                        break
                for k in ("price", "marketPrice", "sharePrice", "closePrice", "lastPrice"):
                    market_price = self._extract_metric_value(it, k)
                    if market_price is not None:
                        break
                if nav_per_share is not None and market_price is not None and nav_per_share != 0:
                    premium_rate = (market_price - nav_per_share) / nav_per_share

            rows.append(
                {
                    "date": flow_date,
                    "timestamp": self._market_close_timestamp(flow_date),
                    "product_code": ticker,
                    "product_name": product_name,
                    "issuer": institute,
                    "asset_type": "BTC",
                    "net_flow_usd": net_flow,
                    "total_aum_usd": total_aum,
                    "source_url": self.ENDPOINT,
                    "source_last_updated": last_update,
                    "schema_fingerprint": self.last_schema_fingerprint,
                    "fetch_method": "api",
                    "total_value_traded_usd": traded,
                    "cum_net_inflow_usd": cum_net,
                    "premium_rate": premium_rate,
                    "source": "sosovalue",
                }
            )
        return rows

    def run_collection(self, db_loader, days: int = 7) -> int:
        # days 參數保留介面一致；此端點只回傳最新日快照。
        payload = self._fetch_metrics()
        if not payload:
            return 0
        rows = self._to_rows(payload)
        if not rows:
            return 0
        return db_loader.insert_etf_flows_batch(rows)
