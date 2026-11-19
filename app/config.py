"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "TBC Fleet and Transport Management System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite:///./tbc_ftms.db"

    # Security
    BCRYPT_ROUNDS: int = 12
    SESSION_IDLE_TIMEOUT_MINUTES: int = 480
    SESSION_ABSOLUTE_TIMEOUT_HOURS: int = 24
    ALLOWED_HOSTS: str = "*"

    # Institutional defaults
    DEFAULT_LANGUAGE: str = "sw"
    INSTITUTION_NAME: str = "Tanzania Broadcasting Corporation (TBC)"
    INSTITUTION_SHORT: str = "TBC"
    INSTITUTION_MOTTO: str = "Ukweli na Uhakika"
    TIMEZONE: str = "Africa/Dar_es_Salaam"
    CURRENCY: str = "TZS"

    # Optional integrations
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMS_GATEWAY_URL: str = ""
    SMS_API_KEY: str = ""

    # File storage
    MAX_UPLOAD_MB: int = 10
    UPLOAD_DIR: str = "app/static/uploads"

    # Demo data
    SEED_DEMO_DATA: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
