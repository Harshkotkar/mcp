"""
Centralized Configuration and Logging for MCP Task Assistant.
Loads environment variables safely and configures structured logging.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env file
load_dotenv()


class SecretMaskingFormatter(logging.Formatter):
    """Logging formatter that redacts known secret strings from log records."""

    def __init__(self, fmt: Optional[str] = None, secrets: Optional[list[str]] = None):
        super().__init__(fmt)
        self.secrets = [s for s in (secrets or []) if s and len(s) > 4]

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for secret in self.secrets:
            msg = msg.replace(secret, "[REDACTED]")
        return msg


def setup_logger(name: str = "mcp_app") -> logging.Logger:
    """Configures and returns a production-safe logger."""
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(log_level)

        # Collect secrets to redact
        secrets_to_mask = [
            os.getenv("GROQ_API_KEY", ""),
            os.getenv("groq_api", ""),
            os.getenv("HF_TOKEN", ""),
            os.getenv("LANGSMITH_API_KEY", ""),
        ]

        formatter = SecretMaskingFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            secrets=secrets_to_mask,
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger("mcp_task_assistant")


@dataclass(frozen=True)
class AppConfig:
    """Application configuration parameters."""

    # Groq Settings
    groq_api_key: str
    primary_model: str
    fallback_model: str

    # MCP Settings
    mcp_url: str

    # Database Settings
    database_path: Path

    # LangSmith Settings
    langsmith_tracing: bool
    langsmith_project: str

    # Optional Cost Settings (per 1M tokens)
    input_price_per_1m: Optional[float]
    output_price_per_1m: Optional[float]


def load_config() -> AppConfig:
    """Loads and validates configuration from the environment."""
    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("groq_api")
    if not groq_key:
        raise ValueError(
            "GROQ_API_KEY (or groq_api) is not set in the environment or .env file."
        )

    # Models
    primary_model = os.getenv("GROQ_MODEL", os.getenv("HF_MODEL", "openai/gpt-oss-120b"))
    fallback_model = os.getenv("GROQ_FALLBACK_MODEL", "qwen/qwen3.6-27b")

    # MCP Server URL
    mcp_url = os.getenv("MCP_URL", "http://127.0.0.1:8000/mcp")

    # Database Path
    db_env = os.getenv("DATABASE_PATH", "./data/tasks.db")
    db_path = Path(db_env)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # LangSmith Tracing
    langsmith_tracing = os.getenv("LANGSMITH_TRACING", "true").lower() in ("true", "1", "yes")
    langsmith_project = os.getenv("LANGSMITH_PROJECT", "new_trace")

    # Pricing (optional)
    raw_in_price = os.getenv("GROQ_INPUT_PRICE_PER_1M_TOKENS") or os.getenv("HF_INPUT_PRICE_PER_1M_TOKENS")
    raw_out_price = os.getenv("GROQ_OUTPUT_PRICE_PER_1M_TOKENS") or os.getenv("HF_OUTPUT_PRICE_PER_1M_TOKENS")

    input_price = float(raw_in_price) if raw_in_price else None
    output_price = float(raw_out_price) if raw_out_price else None

    return AppConfig(
        groq_api_key=groq_key,
        primary_model=primary_model,
        fallback_model=fallback_model,
        mcp_url=mcp_url,
        database_path=db_path,
        langsmith_tracing=langsmith_tracing,
        langsmith_project=langsmith_project,
        input_price_per_1m=input_price,
        output_price_per_1m=output_price,
    )
