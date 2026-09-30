import asyncio
import json
import logging
import time
from typing import Literal
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import openai
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.core.daily_cap import daily_cap
from app.core.limiter import limiter
from app.services.retrieval import retrieve_relevant_chunks
from app.services.prompts import build_system_prompt

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger("oan_ai_service.chat")


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=800)
    history: list[HistoryMessage] = Field(default_factory=list)


DAILY_LIMIT_MESSAGE = "Today's demo limit has been reached. Please come back tomorrow, or contact info@oangroup.in for help."
BUSY_MESSAGE = "Our demo is busy right now. Please try again in a minute."


def is_retryable_llm_error(exc: Exception) -> bool:
    if isinstance(exc, (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError)):
        return True
    return isinstance(exc, openai.APIStatusError) and exc.status_code >= 500


async def stream_llm_text(client: AsyncOpenAI, model: str, max_tokens: int, conversation: list[dict]):
    stream = await client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=conversation,
        stream=True,
    )
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


async def stream_oan_response(
    client: AsyncOpenAI,
    message: str,
    history: list[HistoryMessage],
    fallback_client: AsyncOpenAI | None = None,
):
    settings = get_settings()
    started_at = time.monotonic()

    if not daily_cap.try_acquire(settings.daily_chat_cap):
        logger.warning(f"daily chat cap reached, cap={settings.daily_chat_cap}")
        yield f"data: {json.dumps(DAILY_LIMIT_MESSAGE)}\n\n"
        yield "data: [DONE]\n\n"
        return

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

    for msg in history[-6:]:
        conversation.append({"role": msg.role, "content": msg.content[:1000]})

    conversation.append({"role": "user", "content": message})

    providers = [("primary", client, settings.oan_model)]
    if fallback_client is not None:
        providers.append(("fallback", fallback_client, settings.fallback_llm_model or settings.oan_model))

    streamed = False
    try:
        for name, provider_client, model in providers:
            try:
                async for text in stream_llm_text(provider_client, model, settings.oan_max_tokens, conversation):
                    streamed = True
                    yield f"data: {json.dumps(text)}\n\n"
                logger.info(f"llm provider answered: {name}, model={model}")
                break
            except Exception as exc:
                if streamed:
                    logger.exception(f"llm provider {name} failed mid-stream")
                    yield f"data: {json.dumps('Sorry, I lost connection while generating that answer. Please try asking again.')}\n\n"
                    break
                if not is_retryable_llm_error(exc):
                    logger.exception(f"llm provider {name} failed with non-retryable error")
                    yield f"data: {json.dumps('Sorry, I lost connection while generating that answer. Please try asking again.')}\n\n"
                    break
                logger.warning(f"llm provider {name} failed before streaming ({type(exc).__name__}: {exc})")
        else:
            logger.error("all llm providers failed before streaming")
            yield f"data: {json.dumps(BUSY_MESSAGE)}\n\n"

    finally:
        yield "data: [DONE]\n\n"
        logger.info(f"request complete, total_elapsed_ms={int((time.monotonic() - started_at) * 1000)}")


@router.post("/chat")
@limiter.limit("6/minute;40/day")
async def chat(body: ChatRequest, request: Request) -> StreamingResponse:
    return StreamingResponse(
        stream_oan_response(
            request.app.state.llm_client,
            body.message,
            body.history,
            request.app.state.fallback_llm_client,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )