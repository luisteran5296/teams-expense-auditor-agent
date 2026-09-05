from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Microsoft Bot Framework
    BOT_ID: str = ""
    BOT_PASSWORD: str = ""
    BOT_TENANT_ID: str = ""
    PORT: int = 3978
    PUBLIC_BASE_URL: str = "http://localhost:3978"

    # Google Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.7-flash"

    # Enterprise Policy Defaults
    MAX_MEAL_LIMIT_PER_PERSON: float = 75.0
    MAX_UNAPPROVED_PURCHASE_AMOUNT: float = 1000.0
    RESTRICT_ALCOHOL: bool = True
    ALLOW_FOREIGN_CURRENCY: bool = True

    # Storage Paths
    LEDGERS_DIR: Path = Path(__file__).resolve().parent.parent / "generated_ledgers"
    SAMPLES_DIR: Path = Path(__file__).resolve().parent.parent / "samples"

    # Runtime
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
settings.LEDGERS_DIR.mkdir(parents=True, exist_ok=True)
settings.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
