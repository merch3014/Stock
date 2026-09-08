from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from stock_analyzer.sentiment import (
    fetch_news_headlines,
    score_sentiment_and_catalyst,
)


def test_fetch_news_headlines_flat_shape():
    yf_ticker = MagicMock()
    yf_ticker.news = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
    assert fetch_news_headlines(yf_ticker, limit=2) == ["A", "B"]


def test_fetch_news_headlines_nested_content_shape():
    yf_ticker = MagicMock()
    yf_ticker.news = [{"content": {"title": "Nested headline"}}]
    assert fetch_news_headlines(yf_ticker) == ["Nested headline"]


class _BrokenNewsTicker:
    """A minimal double whose `.news` property raises, without touching
    MagicMock's shared class (which a property patch on `type(mock)` would)."""

    @property
    def news(self):
        raise RuntimeError("boom")


def test_fetch_news_headlines_handles_missing_or_broken_news():
    yf_ticker = MagicMock()
    yf_ticker.news = None
    assert fetch_news_headlines(yf_ticker) == []

    assert fetch_news_headlines(_BrokenNewsTicker()) == []


def test_score_sentiment_no_headlines():
    result = score_sentiment_and_catalyst("AAPL", [], api_key="fake-key")
    assert result["sentiment"] == 0
    assert "No recent headlines" in result["catalyst"]


def test_score_sentiment_falls_back_without_api_key():
    result = score_sentiment_and_catalyst("AAPL", ["Some headline"], api_key=None, client=None)
    assert result["sentiment"] == 0
    assert result["catalyst"] == "Some headline"
    assert any("ANTHROPIC_API_KEY" in w for w in result["warnings"])


def _fake_client(response_text: str):
    block = MagicMock()
    block.type = "text"
    block.text = response_text
    response = MagicMock()
    response.content = [block]
    client = MagicMock()
    client.create.return_value = response
    return client


def test_score_sentiment_parses_model_json():
    client = _fake_client('{"sentiment": 2, "catalyst": "Beat on earnings, raised guidance"}')

    result = score_sentiment_and_catalyst("AAPL", ["Q3 beat"], client=client)

    assert result["sentiment"] == 2
    assert result["catalyst"] == "Beat on earnings, raised guidance"
    assert result["warnings"] == []


def test_score_sentiment_strips_markdown_fences():
    client = _fake_client('```json\n{"sentiment": -1, "catalyst": "Guidance cut"}\n```')
    result = score_sentiment_and_catalyst("AAPL", ["Guidance cut"], client=client)
    assert result["sentiment"] == -1
    assert result["catalyst"] == "Guidance cut"


def test_score_sentiment_clamps_out_of_range_values():
    client = _fake_client('{"sentiment": 99, "catalyst": "Huge move"}')
    result = score_sentiment_and_catalyst("AAPL", ["Huge move"], client=client)
    assert result["sentiment"] == 2


def test_score_sentiment_falls_back_on_malformed_response():
    client = _fake_client("not json at all")
    result = score_sentiment_and_catalyst("AAPL", ["headline"], client=client)
    assert result["sentiment"] == 0
    assert result["catalyst"] == "headline"
    assert any("Sentiment scoring failed" in w for w in result["warnings"])


def test_score_sentiment_falls_back_when_client_raises():
    client = MagicMock()
    client.create.side_effect = RuntimeError("rate limited")
    result = score_sentiment_and_catalyst("AAPL", ["headline"], client=client)
    assert result["sentiment"] == 0
    assert any("rate limited" in w for w in result["warnings"])
