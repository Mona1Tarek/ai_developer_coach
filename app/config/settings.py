from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Developer Coach"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
