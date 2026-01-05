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

    # Personal Access Token for github.com
    github_token: str = ""

    # For GHES mode
    ghes_hostname: str = ""  # e.g., "github.mycompany.com"
    ghes_token: str = ""  # PAT for GHES (falls back to github_token if not set)
    # OAuth credentials (optional - only needed if not using PAT)
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

    @property
    def effective_token(self) -> str:
        """Get the effective token for the current mode.

        For GHES: returns ghes_token if set, otherwise github_token.
        For github.com: returns github_token.
        """
        if self.is_ghes:
            return self.ghes_token or self.github_token
        return self.github_token

    @property
    def ghes_use_pat(self) -> bool:
        """Check if GHES mode should use PAT instead of OAuth."""
        return self.is_ghes and bool(self.ghes_hostname) and bool(self.ghes_token or self.github_token)

    @property
    def ghes_use_oauth(self) -> bool:
        """Check if GHES mode should use OAuth."""
        return self.is_ghes and bool(self.ghes_hostname) and not (self.ghes_token or self.github_token) and bool(self.github_client_id)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience alias for direct access
settings = get_settings()
