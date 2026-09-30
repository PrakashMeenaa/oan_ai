import asyncio
import json
from types import SimpleNamespace

import httpx
import openai
import pytest

from app.routers import chat


def make_settings():
    return SimpleNamespace(oan_model="primary-model", oan_max_tokens=64, fallback_llm_model="fallback-model", daily_chat_cap=150)


def rate_limit_error():
    response = httpx.Response(429, request=httpx.Request("POST", "http://test"))
    return openai.RateLimitError("rate limited", response=response, body=None)


class FakeClient:
    def __init__(self, tokens=None, error=None):
        self.tokens = tokens or []
        self.error = error
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self._stream()

    async def _stream(self):
        for token in self.tokens:
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=token))])


@pytest.fixture(autouse=True)
def stub_dependencies(monkeypatch):
    chat.daily_cap.reset()
    monkeypatch.setattr(chat, "get_settings", make_settings)
    monkeypatch.setattr(chat, "retrieve_relevant_chunks", lambda message: [])
    monkeypatch.setattr(chat, "build_system_prompt", lambda chunks: "system")


def run_stream(client, fallback=None):
    async def collect():
        return [event async for event in chat.stream_oan_response(client, "hi", [], fallback)]

    events = asyncio.run(collect())
    return [json.loads(e[len("data: "):]) for e in events if e.strip() != "data: [DONE]"], events


def test_primary_ok_does_not_touch_fallback():
    primary, fallback = FakeClient(["Hel", "lo"]), FakeClient(["nope"])
    texts, events = run_stream(primary, fallback)
    assert texts == ["Hel", "lo"]
    assert fallback.calls == 0
    assert events[-1] == "data: [DONE]\n\n"


def test_primary_fails_then_fallback_answers():
    primary, fallback = FakeClient(error=rate_limit_error()), FakeClient(["from fallback"])
    texts, _ = run_stream(primary, fallback)
    assert texts == ["from fallback"]
    assert primary.calls == 1 and fallback.calls == 1


def test_both_fail_streams_busy_message():
    primary, fallback = FakeClient(error=rate_limit_error()), FakeClient(error=rate_limit_error())
    texts, events = run_stream(primary, fallback)
    assert texts == [chat.BUSY_MESSAGE]
    assert events[-1] == "data: [DONE]\n\n"


def test_primary_fails_without_fallback_streams_busy_message():
    texts, _ = run_stream(FakeClient(error=rate_limit_error()))
    assert texts == [chat.BUSY_MESSAGE]
