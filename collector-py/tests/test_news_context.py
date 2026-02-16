from tasks.news_context import fetch_news_context


def test_fetch_news_context_with_mocked_rss(monkeypatch):
    sample_rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Breaking: SEC ETF approval boosts Bitcoin rally</title>
      <link>https://example.com/1</link>
      <pubDate>Thu, 06 Feb 2026 06:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Crypto exchange hack raises security concern</title>
      <link>https://example.com/2</link>
      <pubDate>Thu, 06 Feb 2026 07:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

    class DummyResponse:
        text = sample_rss

        def raise_for_status(self):
            return None

    def fake_get(url, timeout):
        assert "news.google.com/rss/search" in url
        assert timeout == 9
        return DummyResponse()

    monkeypatch.setattr("tasks.news_context.requests.get", fake_get)
    result = fetch_news_context(
        symbol="BTCUSDT",
        lookback_hours=99999,
        max_items=5,
        timeout_seconds=9,
    )
    assert result["items_count"] >= 2
    assert isinstance(result["aggregate_sentiment"], float)
    assert "top_events" in result
    assert any("regulation" in e["tags"] for e in result["top_events"])
