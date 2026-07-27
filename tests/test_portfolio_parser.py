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


def test_fetch_strips_nav_footer_and_keeps_title_and_meta(monkeypatch):
    html = """<html><head><title>Jane's Portfolio</title>
    <meta name="description" content="Backend engineer, payments systems.">
    </head><body>
    <nav>Home About Contact Blog Login</nav>
    <header>Menu</header>
    <main><p>Built a Redis-backed idempotent retry service for payment webhooks.</p></main>
    <footer>Copyright 2026 all rights reserved cookie policy</footer>
    </body></html>"""
    monkeypatch.setattr(httpx, "get", _mock_get(html))
    text = portfolio_parser.fetch_portfolio_text("https://example.com/p")

    assert "Jane's Portfolio" in text
    assert "Backend engineer, payments systems." in text
    assert "idempotent retry service" in text
    assert "Login" not in text          # nav stripped
    assert "cookie policy" not in text   # footer stripped


def test_parse_portfolio_link_fails_gracefully_on_spa_page(monkeypatch):
    monkeypatch.setattr(httpx, "get", _mock_get("<html><body><div id='root'></div></body></html>"))
    chat = FakeChat([])

    claims = portfolio_parser.parse_portfolio_link("https://example.com/spa", chat)

    assert claims == []
