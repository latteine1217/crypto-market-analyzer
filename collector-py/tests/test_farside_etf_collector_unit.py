"""
Farside ETF Collector 單元測試（無網路依賴）
"""

from unittest.mock import patch

import connectors.farside_etf_collector as farside_mod
from connectors.farside_etf_collector import FarsideInvestorsETFCollector


def test_parse_flow_value_normalization():
    collector = FarsideInvestorsETFCollector(use_playwright=False)

    assert collector._parse_flow_value("(123.4)") == -123_400_000.0
    assert collector._parse_flow_value("$45.6M") == 45_600_000.0
    assert collector._parse_flow_value("1.2B") == 1_200_000_000.0
    assert collector._parse_flow_value("987654") == 987_654.0
    assert collector._parse_flow_value("-") is None


def test_parse_etf_table_with_pandas_html():
    collector = FarsideInvestorsETFCollector(use_playwright=False)
    collector.current_url = "https://farside.co.uk/btc/"
    collector.last_fetch_method["BTC"] = "playwright"

    html = """
    <html>
      <body>
        <div>Last updated: 13 Feb 2026 18:10 ET</div>
        <table>
          <thead>
            <tr><th>Date</th><th>IBIT</th><th>FBTC</th><th>Total</th></tr>
          </thead>
          <tbody>
            <tr><td>13 Feb 2026</td><td>123.4</td><td>(45.6)</td><td>77.8</td></tr>
            <tr><td>12 Feb 2026</td><td>10</td><td>20</td><td>30</td></tr>
          </tbody>
        </table>
      </body>
    </html>
    """

    rows = collector._parse_etf_table(html, "BTC")

    assert len(rows) == 4
    assert {row["product_code"] for row in rows} == {"IBIT", "FBTC"}
    assert all(row["asset_type"] == "BTC" for row in rows)
    assert all(row["source_url"] == "https://farside.co.uk/btc/" for row in rows)
    assert all(row["source_last_updated"] for row in rows)
    assert all(row["schema_fingerprint"] for row in rows)
    assert all(row["fetch_method"] == "playwright" for row in rows)


def test_resolve_stealth_mode_prefer_sync_api():
    with patch.object(farside_mod, "playwright_stealth_sync", object()), patch.object(
        farside_mod, "PlaywrightStealth", object()
    ):
        assert FarsideInvestorsETFCollector._resolve_stealth_mode() == "stealth_sync"


def test_apply_stealth_with_class_api():
    class DummyStealth:
        called = False

        def apply_stealth_sync(self, context):
            self.called = True
            context["applied"] = True

    collector = FarsideInvestorsETFCollector(use_playwright=False)
    collector.use_stealth = True
    collector.stealth_mode = "stealth_class"

    context = {"applied": False}
    with patch.object(farside_mod, "PlaywrightStealth", DummyStealth), patch.object(
        farside_mod, "playwright_stealth_sync", None
    ):
        ok = collector._apply_stealth(page=object(), context=context)

    assert ok is True
    assert context["applied"] is True
