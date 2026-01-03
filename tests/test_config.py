"""Tests for configuration module."""

import pytest

from mcp_gh_reviewer.config import Settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_default_mode_is_github_com(self):
        """Default mode should be github.com."""
        settings = Settings(
            github_token="test",
            openrouter_api_key="test",
        )
        assert settings.github_mode == "github.com"

    def test_is_github_com_property(self):
        """is_github_com should return True for github.com mode."""
        settings = Settings(
            github_mode="github.com",
            github_token="test",
            openrouter_api_key="test",
        )
        assert settings.is_github_com is True
        assert settings.is_ghes is False

    def test_is_ghes_property(self):
        """is_ghes should return True for ghes mode."""
        settings = Settings(
            github_mode="ghes",
            ghes_hostname="github.example.com",
            openrouter_api_key="test",
        )
        assert settings.is_ghes is True
        assert settings.is_github_com is False

    def test_github_token_for_github_com(self):
        """github.com mode should use github_token."""
        settings = Settings(
            github_mode="github.com",
            github_token="ghp_my_token",
            openrouter_api_key="test",
        )
        assert settings.github_token == "ghp_my_token"

    def test_ghes_hostname_for_ghes_mode(self):
        """GHES mode should use ghes_hostname."""
        settings = Settings(
            github_mode="ghes",
            ghes_hostname="github.mycompany.com",
            openrouter_api_key="test",
        )
        assert settings.ghes_hostname == "github.mycompany.com"

    def test_default_review_model(self):
        """Default review model should be claude-sonnet-4."""
        settings = Settings(
            github_token="test",
            openrouter_api_key="test",
        )
        assert settings.review_model == "anthropic/claude-sonnet-4"

    def test_custom_review_model(self):
        """Review model can be customized."""
        settings = Settings(
            github_token="test",
            openrouter_api_key="test",
            review_model="openai/gpt-4",
        )
        assert settings.review_model == "openai/gpt-4"

    def test_default_server_port(self):
        """Default server port should be 8000."""
        settings = Settings(
            github_token="test",
            openrouter_api_key="test",
        )
        assert settings.mcp_server_port == 8000

    def test_invalid_mode_raises_error(self):
        """Invalid github_mode should raise validation error."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            Settings(
                github_mode="invalid",
                openrouter_api_key="test",
            )


class TestSettingsFromEnv:
    """Tests for loading settings from environment."""

    def test_loads_from_env(self, monkeypatch):
        """Settings should load from environment variables."""
        monkeypatch.setenv("GITHUB_MODE", "github.com")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_env_token")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-env")

        # Clear the lru_cache to reload settings
        from mcp_gh_reviewer.config import get_settings
        get_settings.cache_clear()

        settings = Settings()
        assert settings.github_token == "ghp_env_token"

    def test_ghes_mode_from_env(self, monkeypatch):
        """GHES mode should load from environment."""
        monkeypatch.setenv("GITHUB_MODE", "ghes")
        monkeypatch.setenv("GHES_HOSTNAME", "github.corp.com")
        monkeypatch.setenv("GITHUB_CLIENT_ID", "client123")
        monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret456")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-env")

        settings = Settings()
        assert settings.github_mode == "ghes"
        assert settings.ghes_hostname == "github.corp.com"
        assert settings.github_client_id == "client123"
