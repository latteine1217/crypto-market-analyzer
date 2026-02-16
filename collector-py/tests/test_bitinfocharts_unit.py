"""
BitInfoChartsClient 單元測試（無網路依賴）
"""

from connectors.bitinfocharts import BitInfoChartsClient


def test_parse_distribution_rows_basic():
    client = BitInfoChartsClient()

    html = """
    <html>
      <body>
        <div>Last updated: 13 Feb 2026</div>
        <table>
          <thead>
            <tr>
              <th>Balance</th>
              <th>Addresses</th>
              <th>Coins</th>
              <th>USD</th>
              <th>%</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>0.1 - 1</td><td>12,345</td><td>1,234.5 BTC</td><td>$12.3M</td><td>1.23%</td></tr>
            <tr><td>1 - 10</td><td>2,000</td><td>10,000 BTC</td><td>$100M</td><td>5%</td></tr>
          </tbody>
        </table>
      </body>
    </html>
    """

    rows, meta = client._parse_distribution_rows(html)
    assert len(rows) == 2
    assert rows[0]["rank_group"] == "0.1 - 1"
    assert rows[0]["address_count"] == 12345
    assert rows[0]["total_balance"] == 1234.5
    assert rows[0]["symbol"] == "BTC"

    assert rows[0]["schema_fingerprint"]
    assert "columns" in meta
    assert rows[0]["source_last_updated"]


def test_parse_distribution_rows_prefers_btc_total_column_over_balance_btc_range():
    """
    真實頁面常同時有：
    - "Balance, BTC"：range (例如 "[0.01 - 0.1)")
    - "BTC"：該 tier 的總 BTC 持有量
    這個測試要確保我們取的是 "BTC" 欄，而不是誤把 range 的下界當 total_balance。
    """
    client = BitInfoChartsClient()

    html = """
    <html>
      <body>
        <div>Last updated: 15 Feb 2026</div>
        <table>
          <thead>
            <tr>
              <th>Balance, BTC</th>
              <th>Addresses</th>
              <th>% Addresses (Total)</th>
              <th>BTC</th>
              <th>USD</th>
              <th>% BTC (Total)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>[0.01 - 0.1)</td>
              <td>8,166,481</td>
              <td>10%</td>
              <td>4,200,000 BTC</td>
              <td>$123,456</td>
              <td>20%</td>
            </tr>
          </tbody>
        </table>
      </body>
    </html>
    """

    rows, _ = client._parse_distribution_rows(html)
    assert len(rows) == 1
    assert rows[0]["rank_group"] == "[0.01 - 0.1)"
    assert rows[0]["address_count"] == 8166481
    assert rows[0]["total_balance"] == 4200000.0
