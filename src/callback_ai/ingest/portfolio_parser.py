"""Fetch a portfolio URL and extract project/skill claims (best-effort, no JS rendering).

The scraper drops boilerplate (script/style plus nav/header/footer/aside
chrome) so the model sees the actual portfolio content, and keeps the page
title and meta description since those often carry the headline pitch. Still
best-effort: JS-rendered single-page apps have no server-side text to read,
and those fail gracefully so a session continues on resume + role.
"""
from callback_ai.llm.json_parse import parse_json_response
import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from callback_ai.config import settings
from callback_ai.ingest.schemas import Claim
from callback_ai.llm.client import ChatProvider
from callback_ai.ingest.resume_parser import SYSTEM_PROMPT as _RESUME_PROMPT


class PortfolioFetchError(Exception):
    """Raised when the page can't be fetched or has no usable text (e.g. SPA)."""


# Tags whose text is site chrome, not portfolio content.
_SKIP_TEXT = {"script", "style", "nav", "header", "footer", "aside", "noscript", "svg"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self.title = ""
        self.meta_description = ""
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TEXT:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            a = dict(attrs)
            if a.get("name", "").lower() == "description" and a.get("content"):
                self.meta_description = a["content"].strip()

    def handle_endtag(self, tag):
        if tag in _SKIP_TEXT and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title = text
        elif self._skip_depth == 0 and len(text) > 1:
            self.chunks.append(text)


MAX_PAGE_BYTES = 2_000_000   # a portfolio page, not a download; stops a huge response eating memory
MAX_REDIRECTS = 5


def _check_public_url(url: str) -> None:
    """The URL comes from a stranger and the server fetches it, so refuse
    anything that isn't the public internet: localhost, private networks,
    cloud metadata addresses, non-http schemes. Without this the server can be
    used to reach machines only it can see (SSRF).
    ponytail: checks the address before connecting, so a DNS answer that
    changes between check and connect (rebinding) slips past; pin the resolved
    IP in the connection if this ever guards anything sensitive."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise PortfolioFetchError(f"not an http(s) link: {url}")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
    except (socket.gaierror, UnicodeError) as e:
        raise PortfolioFetchError(f"could not resolve {parts.hostname}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise PortfolioFetchError(f"{parts.hostname} is not a public address")


def fetch_portfolio_text(url: str) -> str:
    try:
        # Redirects are followed by hand so every hop gets the same check.
        for _ in range(MAX_REDIRECTS + 1):
            _check_public_url(url)
            with httpx.stream("GET", url, timeout=settings.request_timeout_s, follow_redirects=False) as resp:
                if resp.is_redirect:
                    url = urljoin(url, resp.headers["location"])
                    continue
                resp.raise_for_status()
                body = b""
                for chunk in resp.iter_bytes():
                    body += chunk
                    if len(body) > MAX_PAGE_BYTES:
                        break
                html = body[:MAX_PAGE_BYTES].decode(resp.charset_encoding or "utf-8", errors="replace")
                break
        else:
            raise PortfolioFetchError(f"too many redirects from {url}")
    except httpx.HTTPError as e:
        raise PortfolioFetchError(f"could not fetch {url}: {e}") from e

    extractor = _TextExtractor()
    extractor.feed(html)

    header = "\n".join(p for p in (extractor.title, extractor.meta_description) if p)
    body = "\n".join(extractor.chunks)
    text = f"{header}\n\n{body}".strip()

    if len(body) < 40:
        raise PortfolioFetchError(f"page at {url} had no usable text (likely JS-rendered)")
    return text


def parse_portfolio_link(url: str, chat: ChatProvider) -> list[Claim]:
    """Returns [] on any fetch/parse failure rather than raising, so a session can
    continue with resume+position only (graceful fallback, see plan risk #2)."""
    try:
        text = fetch_portfolio_text(url)
    except PortfolioFetchError:
        return []

    raw = chat.chat(
        [
            {"role": "system", "content": _RESUME_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.0,
    )
    data = parse_json_response(raw)
    return [Claim(source="portfolio", **c) for c in data["claims"]]
