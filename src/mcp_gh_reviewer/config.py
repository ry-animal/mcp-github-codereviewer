"""Application configuration using pydantic-settings."""

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # GitHub Enterprise Server
    ghes_hostname: str  # e.g., "github.mycompany.com"
    github_client_id: str
    github_client_secret: str

    # OpenRouter
    openrouter_api_key: str
    review_model: str = "anthropic/claude-sonnet-4"

    # MCP Server
    mcp_server_base_url: str = "http://localhost:8000"
    mcp_server_port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
