from typing import Literal
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.services.retrieval import retrieve_relevant_chunks
from app.services.prompts import build_system_prompt

router = APIRouter(prefix="/api", tags=["chat"])


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[HistoryMessage] = Field(default_factory=list)


def build_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=get_settings().groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )


async def stream_oan_response(message: str, history: list[HistoryMessage]):
    settings = get_settings()
    client = build_client()

    try:
        context_chunks = retrieve_relevant_chunks(message)
        system_prompt = build_system_prompt(context_chunks)
    except Exception as e:
        yield f"data: Sorry, I encountered an error. Please try again. ({str(e)})\n\n"
        yield "data: [DONE]\n\n"
        return

    conversation = [{"role": "system", "content": system_prompt}]

    for msg in history[-12:]:
        conversation.append({"role": msg.role, "content": msg.content})

    conversation.append({"role": "user", "content": message})

    stream = await client.chat.completions.create(
        model=settings.oan_model,
        max_tokens=settings.oan_max_tokens,
        messages=conversation,
        stream=True,
    )

    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield f"data: {content}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(body: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_oan_response(body.message, body.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )