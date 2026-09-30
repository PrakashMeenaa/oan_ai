import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.routers import chat, enquiry
from app.core.config import get_settings
from app.core.supabase import get_supabase
from app.core.limiter import limiter
from app.services.embeddings import get_embedding_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("oan_ai_service")


@asynccontextmanager
async def lifespan(application: FastAPI):
    await asyncio.to_thread(get_embedding_model)
    settings = get_settings()
    application.state.llm_client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.llm_base_url,
    )
    application.state.fallback_llm_client = None
    if settings.fallback_llm_base_url and settings.fallback_llm_api_key:
        application.state.fallback_llm_client = AsyncOpenAI(
            api_key=settings.fallback_llm_api_key,
            base_url=settings.fallback_llm_base_url,
        )
    logger.info("oan-ai-service startup complete")
    yield
    await application.state.llm_client.close()
    if application.state.fallback_llm_client is not None:
        await application.state.fallback_llm_client.close()


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title="OAN Global-Sync AI Service",
        version="1.0.0",
        lifespan=lifespan,
    )

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    application.include_router(chat.router)
    application.include_router(enquiry.router)

    return application


app = create_app()


@app.api_route("/health", methods=["GET", "HEAD"])
async def health() -> JSONResponse:
    checks = {"embedding_model": False, "supabase": False}

    try:
        await asyncio.to_thread(get_embedding_model)
        checks["embedding_model"] = True
    except Exception as e:
        logger.error(f"health check embedding_model failed: {e}")

    try:
        supabase = get_supabase()
        await asyncio.to_thread(
            lambda: supabase.table("oan_enquiries").select("id").limit(1).execute()
        )
        checks["supabase"] = True
    except Exception as e:
        logger.error(f"health check supabase failed: {e}")

    healthy = all(checks.values())

    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "degraded", "service": "oan-ai-service", "checks": checks},
    )