"""
SoSoValue OpenAPI v2 - ETF Flow Collector (BTC only)

目標：
- 使用 SoSoValue 對外公布的「網站原值」ETF flow（聚合總流向）
- 避免 Web Scraping/Cloudflare 風險
- 控制呼叫頻率（免費版每月 1000 次限制）

資料來源：
POST https://api.sosovalue.xyz/openapi/v2/etf/historicalInflowChart
headers: x-soso-api-key
body: {"type": "us-btc-spot"}
"""

from __future__ import annotations

from typing import Dict, List, Optional
from datetime import date, datetime, time, timezone
import hashlib
import json
import os

import requests
import certifi
from loguru import logger

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


class SoSoValueOpenAPIETFFlowsCollector:
    ENDPOINT = "https://api.sosovalue.xyz/openapi/v2/etf/historicalInflowChart"
    TYPE_US_BTC_SPOT = "us-btc-spot"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.getenv("SOSOVALUE_API_KEY") or "").strip()
        self.market_tz = ZoneInfo("America/New_York") if ZoneInfo else timezone.utc
        self.last_fetch_method = "sosovalue_openapi"
        self.last_schema_fingerprint: Optional[str] = None
        self.last_source_last_updated: Optional[str] = None

        if not self.api_key:
            logger.warning("SOSOVALUE_API_KEY is not set; SoSoValue ETF collector will return 0 records.")

        # SSL verify: 某些環境下 certifi 可能缺少 issuer（會導致 CERTIFICATE_VERIFY_FAILED）。
        # 容器通常有 /etc/ssl/certs/ca-certificates.crt，可優先使用。
        self.verify_ssl = True
        self.ca_file = os.getenv("SOSOVALUE_CA_FILE", "").strip() or None
        if not self.ca_file:
            self.ca_file = "/etc/ssl/certs/ca-certificates.crt" if os.path.exists("/etc/ssl/certs/ca-certificates.crt") else certifi.where()

    def get_last_unknown_codes(self) -> Dict[str, List[str]]:
        # 保持與 Farside collector 相同介面，避免下游壞掉
        return {}

    def _market_close_timestamp(self, flow_date: date) -> datetime:
        close_dt = datetime.combine(flow_date, time(16, 0), tzinfo=self.market_tz)
        return close_dt.astimezone(timezone.utc)

    @staticmethod
    def _schema_fingerprint(payload: dict) -> str:
        keys = []
        data = payload.get("data")
        if isinstance(data, dict):
            lst = data.get("list") or []
        else:
            lst = data or []
        if isinstance(lst, list) and lst:
            item = lst[0] if isinstance(lst[0], dict) else {}
            keys = sorted([str(k) for k in item.keys()])
        canonical = json.dumps({"keys": keys}, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _fetch_chart(self) -> Optional[dict]:
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

    @staticmethod
    def _parse_date(d: str) -> Optional[date]:
        try:
            return datetime.strptime(str(d), "%Y-%m-%d").date()
        except Exception:
            return None

    def _to_rows(self, payload: dict, lookback_days: int) -> List[Dict]:
        data = payload.get("data")
        if isinstance(data, dict):
            items = data.get("list") or []
        else:
            items = data or []
        if not isinstance(items, list):
            return []

        cutoff = datetime.now(self.market_tz).date()
        if lookback_days and lookback_days > 0:
            from datetime import timedelta
            cutoff = cutoff - timedelta(days=lookback_days)

        rows: List[Dict] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            d = self._parse_date(it.get("date"))
            if not d or d < cutoff:
                continue

            net = it.get("totalNetInflow")
            if net is None:
                continue

            try:
                net_flow = float(net)
            except Exception:
                continue

            total_assets = it.get("totalNetAssets")
            total_value_traded = it.get("totalValueTraded")
            cum_net = it.get("cumNetInflow")

            def _f(v):
                try:
                    return float(v) if v is not None else None
                except Exception:
                    return None

            rows.append(
                {
                    "date": d,
                    "timestamp": self._market_close_timestamp(d),
                    "product_code": "TOTAL",
                    "product_name": "US BTC Spot ETF (Total)",
                    "issuer": "All",
                    "asset_type": "BTC",
                    "net_flow_usd": net_flow,
                    "total_aum_usd": _f(total_assets),
                    "source_url": self.ENDPOINT,
                    "source_last_updated": None,
                    "schema_fingerprint": self.last_schema_fingerprint,
                    "fetch_method": "api",
                    # 額外欄位（寫入 metadata）
                    "total_value_traded_usd": _f(total_value_traded),
                    "cum_net_inflow_usd": _f(cum_net),
                    "source": "sosovalue",
                }
            )
        return rows

    def run_collection(self, db_loader, days: int = 7) -> int:
        """
        days: 只用於落庫 lookback 範圍；SoSoValue 端點固定回傳 ~300 天。
        """
        payload = self._fetch_chart()
        if not payload:
            return 0
        rows = self._to_rows(payload, lookback_days=int(days or 7))
        if not rows:
            return 0
        return db_loader.insert_etf_flows_batch(rows)
