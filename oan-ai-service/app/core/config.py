from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    groq_api_key: str
    oan_model: str = "llama-3.3-70b-versatile"
    oan_max_tokens: int = 1024
    supabase_url: str
    supabase_service_role_key: str
    resend_api_key: str
    oan_sales_email: str = "info@oangroup.in"

    model_config = {"env_file": ".env"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()