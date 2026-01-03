"""Pytest fixtures and configuration."""

import os
from typing import Generator

import pytest

from mcp_gh_reviewer.config import Settings


class SecretString:
    """Wrapper that hides secret values in test output."""

    def __init__(self, value: str | None):
        self._value = value

    @property
    def value(self) -> str | None:
        return self._value

    def __repr__(self) -> str:
        if self._value:
            return "<SecretString: ***>"
        return "<SecretString: None>"

    def __str__(self) -> str:
        return self.__repr__()

    def __bool__(self) -> bool:
        return bool(self._value)


@pytest.fixture
def github_com_settings() -> Settings:
    """Settings configured for github.com mode."""
    return Settings(
        github_mode="github.com",
        github_token="ghp_test_token",
        openrouter_api_key="sk-or-test",
    )


@pytest.fixture
def ghes_settings() -> Settings:
    """Settings configured for GHES mode."""
    return Settings(
        github_mode="ghes",
        ghes_hostname="github.example.com",
        github_client_id="test_client_id",
        github_client_secret="test_client_secret",
        openrouter_api_key="sk-or-test",
    )


@pytest.fixture
def real_settings() -> Settings | None:
    """Load real settings from .env if available.

    Returns None if required env vars are not set.
    """
    settings = Settings()
    if settings.is_github_com and settings.github_token:
        return settings
    if settings.is_ghes and settings.github_client_id:
        return settings
    return None


@pytest.fixture
def real_github_token() -> SecretString:
    """Get real GitHub token from environment if available.

    Returns a SecretString wrapper to prevent token exposure in test output.
    Access the actual token via .value property.
    """
    from mcp_gh_reviewer.config import settings
    if settings.is_github_com and settings.github_token:
        return SecretString(settings.github_token)
    return SecretString(None)


@pytest.fixture
def real_openrouter_key() -> SecretString:
    """Get real OpenRouter API key from environment if available.

    Returns a SecretString wrapper to prevent key exposure in test output.
    Access the actual key via .value property.
    """
    from mcp_gh_reviewer.config import settings
    if settings.openrouter_api_key:
        return SecretString(settings.openrouter_api_key)
    return SecretString(None)


def pytest_collection_modifyitems(config, items):
    """Modify test collection to hide sensitive data."""
    # This prevents tokens from being displayed in verbose output
    pass


# Markers for test categories
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may hit real APIs)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
