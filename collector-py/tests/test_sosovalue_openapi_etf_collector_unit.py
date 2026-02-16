"""
SoSoValue OpenAPI ETF Collector 單元測試（無網路依賴）
"""

from connectors.sosovalue_openapi_etf_collector import SoSoValueOpenAPIETFFlowsCollector


def test_sosovalue_openapi_parse_and_filter():
    c = SoSoValueOpenAPIETFFlowsCollector(api_key="dummy")
    payload = {
        "code": 0,
        "msg": None,
        "data": {
            "list": [
                {
                    "date": "2026-02-13",
                    "totalNetInflow": -55066297.0,
                    "totalValueTraded": 4706120449.0,
                    "totalNetAssets": 56216535367.0,
                    "cumNetInflow": 13534833596.095,
                },
                {
                    "date": "2026-02-01",
                    "totalNetInflow": 1.0,
                    "totalValueTraded": 2.0,
                    "totalNetAssets": 3.0,
                    "cumNetInflow": 4.0,
                },
            ]
        },
    }

    rows = c._to_rows(payload, lookback_days=7)
    assert len(rows) == 1
    row = rows[0]
    assert row["asset_type"] == "BTC"
    assert row["product_code"] == "TOTAL"
    assert row["net_flow_usd"] == -55066297.0
    assert row["total_aum_usd"] == 56216535367.0
    assert row["total_value_traded_usd"] == 4706120449.0
    assert row["cum_net_inflow_usd"] == 13534833596.095
    assert row["fetch_method"] == "api"
    assert row["source"] == "sosovalue"

