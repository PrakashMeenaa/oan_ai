from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    groq_api_key: str
    oan_model: str = "openai/gpt-oss-120b"
    oan_max_tokens: int = 500
    daily_chat_cap: int = 150
    llm_base_url: str = "https://api.groq.com/openai/v1"
    fallback_llm_base_url: str = ""
    fallback_llm_api_key: str = ""
    fallback_llm_model: str = ""
    supabase_url: str
    supabase_service_role_key: str
    resend_api_key: str
    oan_sales_email: str = ""
    cors_allowed_origins: str = "http://localhost:3000,https://oan-ai.vercel.app"

    model_config = {"env_file": ".env"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()