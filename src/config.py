"""Configuration management for InboxIntel."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Guesty API Configuration
    GUESTY_API_KEY: str = os.getenv("GUESTY_API_KEY", "")
    GUESTY_API_SECRET: str = os.getenv("GUESTY_API_SECRET", "")
    GUESTY_API_BASE_URL: str = os.getenv("GUESTY_API_BASE_URL", "https://api.guesty.com/v1")

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/inbox_intel.db")

    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai:gpt-4-turbo")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Notification Configuration
    PUSHOVER_TOKEN: str = os.getenv("PUSHOVER_TOKEN", "")
    PUSHOVER_USER: str = os.getenv("PUSHOVER_USER", "")
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")
    EMAIL_TO: str = os.getenv("EMAIL_TO", "")
    EMAIL_SMTP_HOST: str = os.getenv("EMAIL_SMTP_HOST", "")
    EMAIL_SMTP_PORT: int = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    EMAIL_SMTP_USER: str = os.getenv("EMAIL_SMTP_USER", "")
    EMAIL_SMTP_PASSWORD: str = os.getenv("EMAIL_SMTP_PASSWORD", "")

    # Scheduler Configuration
    POLLING_INTERVAL_MINUTES: int = int(os.getenv("POLLING_INTERVAL_MINUTES", "5"))
    PROCESSING_INTERVAL_SECONDS: int = int(os.getenv("PROCESSING_INTERVAL_SECONDS", "30"))
    REPORT_HOUR: int = int(os.getenv("REPORT_HOUR", "7"))

    # Historical Data Configuration
    BACKFILL_DAYS: int = int(os.getenv("BACKFILL_DAYS", "365"))

    # Application Configuration
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8000"))

    # Alert Configuration
    ALERT_CATEGORIES: list[str] = os.getenv(
        "ALERT_CATEGORIES", "EARLY_CHECKIN,LATE_CHECKOUT,MAINTENANCE_ISSUE,SPECIAL_REQUEST"
    ).split(",")
    MIN_CONFIDENCE_THRESHOLD: float = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.7"))

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration variables."""
        errors = []

        if not cls.GUESTY_API_KEY:
            errors.append("GUESTY_API_KEY is required")
        if not cls.GUESTY_API_SECRET:
            errors.append("GUESTY_API_SECRET is required")

        return errors


config = Config()
