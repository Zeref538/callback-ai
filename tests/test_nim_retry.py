import httpx
import pytest

from callback_ai.llm import nim_provider
from callback_ai.llm.client import ProviderError


def _provider(monkeypatch, statuses):
    """A NimProvider whose HTTP calls return these statuses in order."""
    calls = []

    def fake_post(url, **kw):
        status = statuses[len(calls)]
        calls.append(status)
        body = {"choices": [{"message": {"content": '{"ok": true}'}}]} if status == 200 else {"error": "overloaded"}
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(nim_provider.httpx, "post", fake_post)
    monkeypatch.setattr(nim_provider.time, "sleep", lambda s: None)
    p = nim_provider.NimProvider()
    p.api_key = "test-key"
    return p, calls


def test_overloaded_then_ok_is_retried(monkeypatch):
    # NVIDIA's free tier answers 503 "Service temporarily overloaded" now and then.
    p, calls = _provider(monkeypatch, [503, 200])
    assert p.chat([{"role": "user", "content": "hi"}]) == '{"ok": true}'
    assert calls == [503, 200]


def test_gives_up_after_three_tries(monkeypatch):
    p, calls = _provider(monkeypatch, [503, 502, 503])
    with pytest.raises(ProviderError, match="503"):
        p.chat([{"role": "user", "content": "hi"}])
    assert len(calls) == 3


def test_client_errors_are_not_retried(monkeypatch):
    p, calls = _provider(monkeypatch, [400, 200])
    with pytest.raises(ProviderError, match="400"):
        p.chat([{"role": "user", "content": "hi"}])
    assert calls == [400]
