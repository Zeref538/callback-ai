"""Fetch a portfolio URL and extract project/skill claims (best-effort, no JS rendering)."""
from callback_ai.llm.json_parse import parse_json_response
from html.parser import HTMLParser

import httpx

from callback_ai.config import settings
from callback_ai.ingest.schemas import Claim
from callback_ai.llm.client import ChatProvider
from callback_ai.ingest.resume_parser import SYSTEM_PROMPT as _RESUME_PROMPT


class PortfolioFetchError(Exception):
    """Raised when the page can't be fetched or has no usable text (e.g. SPA)."""


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip = False
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.chunks.append(data.strip())


def fetch_portfolio_text(url: str) -> str:
    try:
        resp = httpx.get(url, timeout=settings.request_timeout_s, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise PortfolioFetchError(f"could not fetch {url}: {e}") from e

    extractor = _TextExtractor()
    extractor.feed(resp.text)
    text = "\n".join(extractor.chunks)
    if len(text) < 40:
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
