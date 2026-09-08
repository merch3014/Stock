"""News/sentiment: latest headlines + an LLM call to score tone and summarize.

Per the project brief, this is the one step that should use an LLM rather
than hardcoded rules. Headlines come from `yfinance.Ticker.news` (free, no
separate news API key needed); tone scoring and catalyst summarization are
done by a single Claude API call.

If no ANTHROPIC_API_KEY is configured (or the call fails), this degrades
gracefully to a neutral sentiment and the raw top headline as the catalyst,
rather than failing the whole analysis — Phase 1 should be usable without
an Anthropic key configured.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

SENTIMENT_MODEL = "claude-sonnet-5"

_SYSTEM_PROMPT = (
    "You are a terse financial news analyst. Given a stock ticker and its "
    "most recent headlines, respond with ONLY raw JSON (no markdown fences, "
    "no commentary) in exactly this shape: "
    '{"sentiment": integer from -2 to 2, "catalyst": short string summarizing '
    "the most market-relevant headline/event}. "
    "-2 = very bearish, -1 = bearish, 0 = neutral, 1 = bullish, 2 = very bullish. "
    "If headlines are sparse or irrelevant to the stock's near-term price action, "
    "use sentiment 0."
)


class MessagesClient(Protocol):
    """Minimal shape of `anthropic.Anthropic().messages` this module needs."""

    def create(self, **kwargs: Any) -> Any: ...


def fetch_news_headlines(yf_ticker, limit: int = 5) -> list[str]:
    """Latest headline titles for `yf_ticker`, most recent first, best-effort."""
    try:
        news = yf_ticker.news or []
    except Exception:
        return []

    titles: list[str] = []
    for item in news:
        # yfinance has changed its news item shape across versions; support both
        # a flat {"title": ...} and a nested {"content": {"title": ...}}.
        title = item.get("title") or (item.get("content") or {}).get("title")
        if title:
            titles.append(title)
        if len(titles) >= limit:
            break
    return titles


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group(0))
        raise ValueError("No JSON object found in model response")


def _clamp_sentiment(value: Any) -> int:
    try:
        return max(-2, min(2, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def score_sentiment_and_catalyst(
    ticker: str,
    headlines: list[str],
    *,
    api_key: str | None = None,
    client: MessagesClient | None = None,
) -> dict:
    """Score tone (-2..2) and summarize the catalyst from `headlines`.

    `client` (an object with a `.create(**kwargs)` method matching
    `anthropic.Anthropic().messages`) can be injected for testing; otherwise
    one is constructed lazily from `api_key` / the ANTHROPIC_API_KEY env var.
    """
    warnings: list[str] = []

    if not headlines:
        return {"sentiment": 0, "catalyst": "No recent headlines found.", "warnings": ["No headlines available for sentiment scoring."]}

    resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if client is None and not resolved_key:
        warnings.append(
            "ANTHROPIC_API_KEY not set; returning neutral sentiment and the "
            "top headline as the catalyst instead of an LLM-scored summary."
        )
        return {"sentiment": 0, "catalyst": headlines[0], "warnings": warnings}

    if client is None:
        try:
            import anthropic  # imported lazily so it's an optional dependency at runtime

            client = anthropic.Anthropic(api_key=resolved_key).messages
        except Exception as exc:
            warnings.append(f"Could not initialize Anthropic client ({exc}); falling back to neutral sentiment.")
            return {"sentiment": 0, "catalyst": headlines[0], "warnings": warnings}

    user_text = f"Ticker: {ticker}\nHeadlines:\n" + "\n".join(f"- {h}" for h in headlines)

    try:
        response = client.create(
            model=SENTIMENT_MODEL,
            max_tokens=300,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_text}],
        )
        text_block = next(
            (block.text for block in response.content if getattr(block, "type", None) == "text"),
            "",
        )
        if not text_block:
            raise ValueError("Empty response from model")
        parsed = _extract_json(text_block)
        sentiment = _clamp_sentiment(parsed.get("sentiment"))
        catalyst = parsed.get("catalyst") or headlines[0]
        return {"sentiment": sentiment, "catalyst": catalyst, "warnings": warnings}
    except Exception as exc:
        warnings.append(f"Sentiment scoring failed ({exc}); falling back to neutral sentiment.")
        return {"sentiment": 0, "catalyst": headlines[0], "warnings": warnings}
