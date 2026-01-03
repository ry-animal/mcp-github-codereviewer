"""GitHub data providers for different modes."""

from mcp_gh_reviewer.providers.base import GitHubDataProvider
from mcp_gh_reviewer.providers.github_mcp import GitHubMCPProvider

__all__ = ["GitHubDataProvider", "GitHubMCPProvider"]
