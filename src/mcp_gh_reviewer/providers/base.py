"""Abstract interface for GitHub data providers."""

from abc import ABC, abstractmethod
from typing import Any

from mcp_gh_reviewer.models.github import (
    PullRequest,
    PullRequestFile,
    PullRequestListItem,
)
from mcp_gh_reviewer.models.review import ReviewResponse


class GitHubDataProvider(ABC):
    """Abstract interface for fetching GitHub PR data.

    This allows different implementations:
    - Direct API calls (for GHES)
    - GitHub MCP server proxy (for github.com)
    """

    @abstractmethod
    async def list_prs(
        self, owner: str, repo: str, state: str = "open"
    ) -> list[PullRequestListItem]:
        """List pull requests in a repository."""
        pass

    @abstractmethod
    async def get_pr(self, owner: str, repo: str, pr_number: int) -> PullRequest:
        """Get details of a pull request."""
        pass

    @abstractmethod
    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Get the unified diff for a pull request."""
        pass

    @abstractmethod
    async def get_pr_files(
        self, owner: str, repo: str, pr_number: int
    ) -> list[PullRequestFile]:
        """List files changed in a pull request."""
        pass

    @abstractmethod
    async def create_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_id: str,
        event: str,
        body: str,
        comments: list[dict[str, Any]],
    ) -> ReviewResponse:
        """Create a pull request review with inline comments."""
        pass
