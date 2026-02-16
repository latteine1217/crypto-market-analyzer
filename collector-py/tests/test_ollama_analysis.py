import pytest

from datetime import datetime, timezone

from tasks.ollama_analysis import MarketSnapshot, build_prompt, call_ollama, parse_json_object


def test_parse_json_object_with_wrapped_text():
    raw = '分析如下:\n{"trend":"sideways","risk_level":"medium","confidence":0.62,"signals":["A"],"rationale":"B"}\n完成'
    parsed = parse_json_object(raw)
    assert parsed["trend"] == "sideways"
    assert parsed["risk_level"] == "medium"
    assert parsed["confidence"] == 0.62


def test_call_ollama_contract(monkeypatch):
    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": (
                        '{"trend":"bearish","risk_level":"high","confidence":0.77,'
                        '"signals":["funding>0","vol up"],"rationale":"test"}'
                    )
                }
            }

    def fake_post(url, json, timeout):
        assert url.endswith("/api/chat")
        assert json["stream"] is False
        assert json["messages"][0]["role"] == "user"
        assert timeout == 12
        return DummyResponse()

    monkeypatch.setattr("tasks.ollama_analysis.requests.post", fake_post)
    result = call_ollama(
        model="glm-4.7:cloud",
        prompt="hello",
        base_url="http://127.0.0.1:11434",
        timeout_seconds=12,
    )
    assert result["trend"] == "bearish"
    assert result["risk_level"] == "high"
    assert result["_model"] == "glm-4.7:cloud"
    assert "_generated_at" in result


def test_parse_json_object_invalid():
    with pytest.raises(ValueError):
        parse_json_object("not a json")


def test_build_prompt_contains_news_context():
    snapshot = MarketSnapshot(
        symbol="BTCUSDT",
        timeframe="1m",
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
        candle_count=10,
        close_first=100.0,
        close_last=101.0,
        pct_change=1.0,
        intrawindow_range_pct=2.0,
        realized_volatility_pct=0.2,
        volume_sum=999.0,
        latest_funding_rate=0.0001,
        latest_open_interest=10000.0,
        fear_greed_value=30.0,
        fear_greed_classification="Fear",
        etf_net_flow_24h_usd=12000000.0,
    )
    prompt = build_prompt(snapshot, news_context={"items_count": 1, "top_events": [{"title": "x"}]})
    assert '"news_context"' in prompt
    assert '"news_impact_assessment"' in prompt
