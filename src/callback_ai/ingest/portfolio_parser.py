"""Fetch a portfolio URL and extract project/skill claims (best-effort, no JS rendering).

The scraper drops boilerplate (script/style plus nav/header/footer/aside
chrome) so the model sees the actual portfolio content, and keeps the page
title and meta description since those often carry the headline pitch. Still
best-effort: JS-rendered single-page apps have no server-side text to read,
and those fail gracefully so a session continues on resume + role.
"""
from callback_ai.llm.json_parse import parse_json_response
from html.parser import HTMLParser

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


def fetch_portfolio_text(url: str) -> str:
    try:
        resp = httpx.get(url, timeout=settings.request_timeout_s, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise PortfolioFetchError(f"could not fetch {url}: {e}") from e

    extractor = _TextExtractor()
    extractor.feed(resp.text)

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
