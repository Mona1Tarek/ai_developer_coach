from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Developer Coach"
    log_level: str = "INFO"
    groq_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    llm_provider: Optional[str] = None
    generation_model_name: Optional[str] = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

