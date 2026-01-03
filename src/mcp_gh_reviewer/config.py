"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # GitHub mode: "github.com" or "ghes"
    github_mode: Literal["github.com", "ghes"] = "github.com"

    # For github.com (PAT mode)
    github_token: str = ""  # Personal Access Token

    # For GHES (OAuth mode)
    ghes_hostname: str = "github.example.com"
    github_client_id: str = ""
    github_client_secret: str = ""

    # OpenRouter
    openrouter_api_key: str = ""
    review_model: str = "anthropic/claude-sonnet-4"

    # MCP Server
    mcp_server_base_url: str = "http://localhost:8000"
    mcp_server_port: int = 8000

    @property
    def is_github_com(self) -> bool:
        """Check if using github.com mode."""
        return self.github_mode == "github.com"

    @property
    def is_ghes(self) -> bool:
        """Check if using GHES mode."""
        return self.github_mode == "ghes"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience alias for direct access
settings = get_settings()
