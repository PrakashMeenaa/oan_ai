from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat, enquiry
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title="OAN Global-Sync AI Service",
        version="1.0.0",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    application.include_router(chat.router)
    application.include_router(enquiry.router)

    return application


app = create_app()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "oan-ai-service"}