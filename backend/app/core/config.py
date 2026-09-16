from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "University Event Platform"
    environment: str = "development"
    database_url: str = "sqlite:///./university_event.db"
    frontend_url: str = "http://localhost:5173"
    jwt_secret: str = "change-this-development-secret"
    jwt_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
