"""Client for GitHub Enterprise Server API."""

from typing import Any, Optional

import httpx

from mcp_gh_reviewer.models.github import (
    PullRequest,
    PullRequestFile,
    PullRequestListItem,
)
from mcp_gh_reviewer.models.review import ReviewResponse


class GitHubClient:
    """Client for GitHub Enterprise Server API."""

    def __init__(self, hostname: str, token: Optional[str] = None):
        """Initialize the GitHub client.

        Args:
            hostname: GHES hostname (e.g., "github.mycompany.com")
            token: OAuth access token for authentication
        """
        self.base_url = f"https://{hostname}/api/v3"
        self.token = token

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        """Build request headers."""
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
    ) -> list[PullRequestListItem]:
        """List pull requests in a repository.

        Args:
            owner: Repository owner (user or organization)
            repo: Repository name
            state: PR state filter - "open", "closed", or "all"

        Returns:
            List of pull requests with basic metadata
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls",
                params={"state": state, "per_page": 100},
                headers=self._headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            return [PullRequestListItem.model_validate(pr) for pr in response.json()]

    async def get_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> PullRequest:
        """Get a single pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            Pull request details
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self._headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            return PullRequest.model_validate(response.json())

    async def get_pull_request_diff(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> str:
        """Get the unified diff for a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            Unified diff as a string
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self._headers(accept="application/vnd.github.v3.diff"),
                timeout=60.0,
            )
            response.raise_for_status()
            return response.text

    async def get_pull_request_files(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> list[PullRequestFile]:
        """List files changed in a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            List of changed files with stats and patches
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                params={"per_page": 100},
                headers=self._headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            return [PullRequestFile.model_validate(f) for f in response.json()]

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
        """Create a pull request review with inline comments.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            commit_id: SHA of the commit to review
            event: Review event - "APPROVE", "REQUEST_CHANGES", or "COMMENT"
            body: Overall review summary
            comments: List of inline comments with path, line, side, body

        Returns:
            Review response with ID and URL
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                headers=self._headers(),
                json={
                    "commit_id": commit_id,
                    "event": event,
                    "body": body,
                    "comments": comments,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            return ReviewResponse.model_validate(response.json())
