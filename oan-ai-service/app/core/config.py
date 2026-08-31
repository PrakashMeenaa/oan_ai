from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    groq_api_key: str
    oan_model: str = "openai/gpt-oss-120b"
    oan_max_tokens: int = 1024
    supabase_url: str
    supabase_service_role_key: str
    resend_api_key: str
    oan_sales_email: str = "info@oangroup.in"
    cors_allowed_origins: str = "http://localhost:3000,https://oan-ai.vercel.app"

    model_config = {"env_file": ".env"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()