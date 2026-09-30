import asyncio
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.routers import chat
from app.services.prompts import build_system_prompt


class CountingClient:
    def __init__(self):
        self.calls = 0
        self.messages = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.calls += 1
        self.messages = kwargs["messages"]
        return self._stream()

    async def _stream(self):
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))])


@pytest.fixture(autouse=True)
def stub(monkeypatch):
    chat.daily_cap.reset()
    monkeypatch.setattr(chat, "get_settings", lambda: SimpleNamespace(
        oan_model="m", oan_max_tokens=500, fallback_llm_model="", daily_chat_cap=2))
    monkeypatch.setattr(chat, "retrieve_relevant_chunks", lambda message: [])
    monkeypatch.setattr(chat, "build_system_prompt", lambda chunks: "system")
    yield
    chat.daily_cap.reset()


def collect(client, history=None):
    async def run():
        return [e async for e in chat.stream_oan_response(client, "hi", history or [])]
    events = asyncio.run(run())
    return [json.loads(e[6:]) for e in events if e.strip() != "data: [DONE]"], events


def test_daily_cap_blocks_after_limit_and_skips_llm():
    client = CountingClient()
    collect(client)
    collect(client)
    texts, events = collect(client)
    assert texts == [chat.DAILY_LIMIT_MESSAGE]
    assert events[-1] == "data: [DONE]\n\n"
    assert client.calls == 2


def test_message_over_800_chars_rejected():
    chat.ChatRequest(message="a" * 800)
    with pytest.raises(ValidationError):
        chat.ChatRequest(message="a" * 801)


def test_history_limited_to_last_6_and_truncated():
    client = CountingClient()
    history = [chat.HistoryMessage(role="user", content=f"{i}" + "x" * 2000) for i in range(10)]
    collect(client, history)
    sent = client.messages[1:-1]
    assert len(sent) == 6
    assert sent[0]["content"].startswith("4")
    assert all(len(m["content"]) == 1000 for m in sent)


def test_empty_context_prompt_refuses_general_knowledge():
    prompt = build_system_prompt([])
    assert "No documentation was found" in prompt
    assert "info@oangroup.in" in prompt
    assert "use your general knowledge" not in prompt
