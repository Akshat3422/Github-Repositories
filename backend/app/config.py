# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str = str(os.getenv("DATABASE_URL", ""))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6380")

    # LLM Settings
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    LLM_PROVIDER: str = "groq"  # "groq" or "openai"

    # Security
    ENCRYPTION_KEY: str = str(os.getenv("ENCRYPTION_KEY",None))

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = str(os.getenv("GITHUB_CLIENT_ID", None))
    GITHUB_CLIENT_SECRET: str = str(os.getenv("GITHUB_CLIENT_SECRET", None))
    GITHUB_REDIRECT_URI: str = str(
        os.getenv(
            "GITHUB_REDIRECT_URI",None
        )
    )

    # Frontend URL for CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")


settings = Settings()
