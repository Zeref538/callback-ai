import json

import httpx
import pytest

from callback_ai.ingest import portfolio_parser
from conftest import FakeChat

HTML = """<html><head><style>.x{}</style></head>
<body><script>var x=1;</script><h1>Jane Doe</h1><p>Built a recommendation engine using Python and Redis.</p></body></html>"""

RESPONSE = json.dumps({
    "claims": [
        {"claim_id": "p1", "subject": "project", "text": "Built a recommendation engine", "tech": ["Python", "Redis"], "metric_value": None},
    ]
})


def _mock_get(html: str = None, status: int = 200, raise_error: Exception = None):
    def fake_get(url, timeout=None, follow_redirects=True):
        if raise_error:
            raise raise_error
        request = httpx.Request("GET", url)
        return httpx.Response(status, text=html, request=request)
    return fake_get


def test_fetch_portfolio_text_strips_script_and_style(monkeypatch):
    monkeypatch.setattr(httpx, "get", _mock_get(HTML))
    text = portfolio_parser.fetch_portfolio_text("https://example.com/portfolio")

    assert "Jane Doe" in text
    assert "recommendation engine" in text
    assert "var x=1" not in text


def test_parse_portfolio_link_returns_claims_tagged_portfolio(monkeypatch):
    monkeypatch.setattr(httpx, "get", _mock_get(HTML))
    chat = FakeChat([RESPONSE])

    claims = portfolio_parser.parse_portfolio_link("https://example.com/portfolio", chat)

    assert len(claims) == 1
    assert claims[0].source == "portfolio"


def test_parse_portfolio_link_fails_gracefully_on_fetch_error(monkeypatch):
    monkeypatch.setattr(httpx, "get", _mock_get(raise_error=httpx.ConnectError("boom")))
    chat = FakeChat([])  # must not be called

    claims = portfolio_parser.parse_portfolio_link("https://example.com/dead-link", chat)

    assert claims == []


def test_parse_portfolio_link_fails_gracefully_on_spa_page(monkeypatch):
    monkeypatch.setattr(httpx, "get", _mock_get("<html><body><div id='root'></div></body></html>"))
    chat = FakeChat([])

    claims = portfolio_parser.parse_portfolio_link("https://example.com/spa", chat)

    assert claims == []
