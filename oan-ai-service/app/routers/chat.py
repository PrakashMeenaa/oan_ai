import asyncio
import json
import logging
import time
from typing import Literal
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.core.limiter import limiter
from app.services.retrieval import retrieve_relevant_chunks
from app.services.prompts import build_system_prompt

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger("oan_ai_service.chat")


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[HistoryMessage] = Field(default_factory=list)


async def stream_oan_response(client: AsyncOpenAI, message: str, history: list[HistoryMessage]):
    settings = get_settings()
    started_at = time.monotonic()

    try:
        context_chunks = await asyncio.to_thread(retrieve_relevant_chunks, message)
        system_prompt = build_system_prompt(context_chunks)
    except Exception:
        logger.exception("retrieval failed")
        yield f"data: {json.dumps('Sorry, I ran into an issue looking that up. Please try again in a moment.')}\n\n"
        yield "data: [DONE]\n\n"
        return

    logger.info(
        f"retrieval complete, message_length={len(message)}, chunks_found={len(context_chunks)}, "
        f"elapsed_ms={int((time.monotonic() - started_at) * 1000)}"
    )

    conversation = [{"role": "system", "content": system_prompt}]

    for msg in history[-12:]:
        conversation.append({"role": msg.role, "content": msg.content})

    conversation.append({"role": "user", "content": message})

    try:
        stream = await client.chat.completions.create(
            model=settings.oan_model,
            max_tokens=settings.oan_max_tokens,
            messages=conversation,
            stream=True,
        )

        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield f"data: {json.dumps(content)}\n\n"

    except Exception:
        logger.exception("groq generation failed")
        yield f"data: {json.dumps('Sorry, I lost connection while generating that answer. Please try asking again.')}\n\n"

    finally:
        yield "data: [DONE]\n\n"
        logger.info(f"request complete, total_elapsed_ms={int((time.monotonic() - started_at) * 1000)}")


@router.post("/chat")
@limiter.limit("30/minute")
async def chat(body: ChatRequest, request: Request) -> StreamingResponse:
    return StreamingResponse(
        stream_oan_response(request.app.state.groq_client, body.message, body.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )