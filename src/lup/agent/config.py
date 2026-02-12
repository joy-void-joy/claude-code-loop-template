"""Configuration management using pydantic-settings.

This is a TEMPLATE. Customize for your domain.

Key patterns:
1. Multiple env files (.env, .env.local) - local overrides shared
2. Optional API keys with startup warnings
3. validation_alias for explicit env var names
4. Singleton instance for easy import
5. Export to os.environ for external libraries

Usage:
    from lup.agent.config import settings
    print(settings.model)
"""

import logging
import os
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    External API keys use standard names (e.g., ANTHROPIC_API_KEY) for
    compatibility with external libraries.

    Agent-specific settings use a prefix (e.g., AGENT_MODEL).
    """

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        extra="ignore",
    )

    @model_validator(mode="after")
    def warn_missing_optional_keys(self) -> Self:
        """Warn at startup if optional API keys are missing.

        Customize this for your domain's optional dependencies.
        """
        missing = []

        # TODO: Add checks for your optional API keys
        # if not self.some_api_key:
        #     missing.append("SOME_API_KEY")

        if missing:
            logger.warning(
                "Missing API keys (some tools may fail): %s", ", ".join(missing)
            )
        return self

    # ==========================================================================
    # REQUIRED SETTINGS
    # ==========================================================================

    anthropic_api_key: str = Field(
        validation_alias="ANTHROPIC_API_KEY",
        description="Anthropic API key (required)",
    )

    # ==========================================================================
    # OPTIONAL API KEYS (tools degrade gracefully without these)
    # ==========================================================================

    # TODO: Add optional API keys for your domain
    # exa_api_key: str | None = Field(
    #     default=None,
    #     validation_alias="EXA_API_KEY",
    #     description="Exa search API key",
    # )

    # ==========================================================================
    # MODEL SETTINGS
    # ==========================================================================

    model: str = Field(
        default="claude-sonnet-4-20250514",
        validation_alias="AGENT_MODEL",
        description="Claude model to use",
    )

    max_thinking_tokens: int | None = Field(
        default=None,
        validation_alias="AGENT_MAX_THINKING_TOKENS",
        description="Max thinking tokens (None = model default)",
    )

    # ==========================================================================
    # PATHS
    # ==========================================================================

    notes_path: str = Field(
        default="./notes",
        validation_alias="AGENT_NOTES_PATH",
        description="Base path for notes folders",
    )

    logs_path: str = Field(
        default="./logs",
        validation_alias="AGENT_LOGS_PATH",
        description="Base path for trace logs",
    )

    # ==========================================================================
    # LIMITS
    # ==========================================================================

    max_budget_usd: float | None = Field(
        default=None,
        validation_alias="AGENT_MAX_BUDGET_USD",
        description="Maximum budget per session (None = unlimited)",
    )

    max_turns: int | None = Field(
        default=None,
        validation_alias="AGENT_MAX_TURNS",
        description="Maximum agent turns per session (None = unlimited)",
    )

    http_timeout_seconds: int = Field(
        default=30,
        validation_alias="AGENT_HTTP_TIMEOUT_SECONDS",
        description="Timeout for HTTP requests",
    )

    # ==========================================================================
    # RATE LIMITS / CONCURRENCY
    # ==========================================================================

    max_concurrent_requests: int = Field(
        default=5,
        validation_alias="AGENT_MAX_CONCURRENT_REQUESTS",
        description="Max concurrent external API requests",
    )


# Singleton instance
settings = Settings.model_validate({})

# Export API keys to os.environ for external libraries
# (libraries that read directly from env rather than using settings)
_ENV_EXPORTS = [
    ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
    # TODO: Add other keys your external libraries need
]

for env_name, value in _ENV_EXPORTS:
    if value and env_name not in os.environ:
        os.environ[env_name] = value
