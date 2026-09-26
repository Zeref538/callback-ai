import json
import socket
from contextlib import contextmanager

import httpx
import pytest

from callback_ai.ingest import portfolio_parser
from conftest import FakeChat

# Saved before any test fakes it: portfolio_parser.socket is this same module.
REAL_GETADDRINFO = socket.getaddrinfo

HTML = """<html><head><style>.x{}</style></head>
<body><script>var x=1;</script><h1>Jane Doe</h1><p>Built a recommendation engine using Python and Redis.</p></body></html>"""

RESPONSE = json.dumps({
    "claims": [
        {"claim_id": "p1", "subject": "project", "text": "Built a recommendation engine", "tech": ["Python", "Redis"], "metric_value": None},
    ]
})


def _mock_get(html: str = None, status: int = 200, raise_error: Exception = None, redirects: dict = None):
    """Stands in for httpx.stream. redirects maps a url to where it 302s."""
    @contextmanager
    def fake_stream(method, url, timeout=None, follow_redirects=False):
        if raise_error:
            raise raise_error
        request = httpx.Request(method, url)
        if redirects and url in redirects:
            yield httpx.Response(302, headers={"location": redirects[url]}, request=request)
        else:
            yield httpx.Response(status, text=html, request=request)
    return fake_stream


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    # example.com etc. resolve to a public address without touching the network
    monkeypatch.setattr(portfolio_parser.socket, "getaddrinfo", lambda host, port: [(2, 1, 6, "", ("93.184.215.14", port))])


def test_fetch_portfolio_text_strips_script_and_style(monkeypatch):
    monkeypatch.setattr(httpx, "stream", _mock_get(HTML))
    text = portfolio_parser.fetch_portfolio_text("https://example.com/portfolio")

    assert "Jane Doe" in text
    assert "recommendation engine" in text
    assert "var x=1" not in text


def test_parse_portfolio_link_returns_claims_tagged_portfolio(monkeypatch):
    monkeypatch.setattr(httpx, "stream", _mock_get(HTML))
    chat = FakeChat([RESPONSE])

    claims = portfolio_parser.parse_portfolio_link("https://example.com/portfolio", chat)

    assert len(claims) == 1
    assert claims[0].source == "portfolio"


def test_parse_portfolio_link_fails_gracefully_on_fetch_error(monkeypatch):
    monkeypatch.setattr(httpx, "stream", _mock_get(raise_error=httpx.ConnectError("boom")))
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
    monkeypatch.setattr(httpx, "stream", _mock_get(html))
    text = portfolio_parser.fetch_portfolio_text("https://example.com/p")

    assert "Jane's Portfolio" in text
    assert "Backend engineer, payments systems." in text
    assert "idempotent retry service" in text
    assert "Login" not in text          # nav stripped
    assert "cookie policy" not in text   # footer stripped


def test_parse_portfolio_link_fails_gracefully_on_spa_page(monkeypatch):
    monkeypatch.setattr(httpx, "stream", _mock_get("<html><body><div id='root'></div></body></html>"))
    chat = FakeChat([])

    claims = portfolio_parser.parse_portfolio_link("https://example.com/spa", chat)

    assert claims == []


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/admin",
    "http://localhost:8080/",
    "http://169.254.169.254/latest/meta-data/",   # cloud metadata
    "http://10.0.0.5/",
    "http://[::1]/",
    "http://[::ffff:127.0.0.1]/",
    "file:///etc/passwd",
    "ftp://example.com/x",
])
def test_fetch_refuses_non_public_addresses(monkeypatch, url):
    monkeypatch.setattr(portfolio_parser.socket, "getaddrinfo", REAL_GETADDRINFO)   # real lookup; all of these are literal or local
    monkeypatch.setattr(httpx, "stream", _mock_get(HTML))
    with pytest.raises(portfolio_parser.PortfolioFetchError):
        portfolio_parser.fetch_portfolio_text(url)


def test_redirect_into_private_network_is_refused(monkeypatch):
    monkeypatch.setattr(portfolio_parser.socket, "getaddrinfo",
                        lambda host, port: [(2, 1, 6, "", ("10.0.0.7" if host == "internal" else "93.184.215.14", port))])
    monkeypatch.setattr(httpx, "stream", _mock_get(HTML, redirects={"https://example.com/p": "http://internal/secret"}))
    with pytest.raises(portfolio_parser.PortfolioFetchError, match="not a public address"):
        portfolio_parser.fetch_portfolio_text("https://example.com/p")


def test_oversized_page_is_cut_off(monkeypatch):
    big = "<p>" + "Built things with Python. " * 200_000 + "</p>"   # ~5 MB
    monkeypatch.setattr(httpx, "stream", _mock_get(big))
    text = portfolio_parser.fetch_portfolio_text("https://example.com/big")
    assert len(text.encode()) <= portfolio_parser.MAX_PAGE_BYTES
