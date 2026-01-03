"""Pytest fixtures and configuration."""

import os
from typing import Generator

import pytest

from mcp_gh_reviewer.config import Settings


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
def real_github_token() -> str | None:
    """Get real GitHub token from environment if available."""
    from mcp_gh_reviewer.config import settings
    if settings.is_github_com and settings.github_token:
        return settings.github_token
    return None


# Markers for test categories
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may hit real APIs)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
