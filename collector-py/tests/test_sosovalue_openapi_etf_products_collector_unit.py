from datetime import date

from connectors.sosovalue_openapi_etf_products_collector import SoSoValueOpenAPIETFProductsCollector


def test_sosovalue_openapi_products_parse_basic():
    c = SoSoValueOpenAPIETFProductsCollector(api_key="test")
    payload = {
        "code": 0,
        "msg": None,
        "data": {
            "list": [
                {
                    "ticker": "IBIT",
                    "name": "iShares Bitcoin Trust",
                    "institute": "Blackrock",
                    "dailyNetInflow": {"value": 123.0, "lastUpdateDate": "2026-02-12"},
                    "cumNetInflow": {"value": 999.0, "lastUpdateDate": "2026-02-12"},
                    "netAssetValue": {"value": 1000.0, "lastUpdateDate": "2026-02-12"},
                    "volume": {"value": 555.0, "lastUpdateDate": "2026-02-12"},
                },
                {
                    "ticker": "GBTC",
                    "name": "Grayscale Bitcoin Trust",
                    "institute": "Grayscale",
                    "dailyNetInflow": {"value": -50.0, "lastUpdateDate": "2026-02-12"},
                    "cumNetInflow": {"value": -100.0, "lastUpdateDate": "2026-02-12"},
                },
                # dailyNetInflow.value null -> skip
                {
                    "ticker": "FBTC",
                    "name": "Fidelity Wise Origin Bitcoin Fund",
                    "institute": "Fidelity",
                    "dailyNetInflow": {"value": None, "lastUpdateDate": "2026-02-12"},
                },
            ]
        },
    }

    rows = c._to_rows(payload)  # type: ignore[attr-defined]
    assert len(rows) == 2
    assert rows[0]["product_code"] == "IBIT"
    assert rows[0]["issuer"] == "BlackRock"
    assert rows[0]["date"] == date(2026, 2, 12)
    assert rows[0]["net_flow_usd"] == 123.0
    assert rows[0]["cum_net_inflow_usd"] == 999.0

    assert rows[1]["product_code"] == "GBTC"
    assert rows[1]["issuer"] == "Grayscale"
    assert rows[1]["net_flow_usd"] == -50.0

