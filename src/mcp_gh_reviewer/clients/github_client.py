"""Client for GitHub API (supports both github.com and GHES)."""

from typing import Any, Literal, Optional

import httpx

from mcp_gh_reviewer.models.github import (
    PullRequest,
    PullRequestFile,
    PullRequestListItem,
)
from mcp_gh_reviewer.models.review import ReviewResponse


class GitHubClient:
    """Client for GitHub API (supports both github.com and GHES)."""

    def __init__(
        self,
        hostname: Optional[str] = None,
        token: Optional[str] = None,
        mode: Literal["github.com", "ghes"] = "github.com",
    ):
        """Initialize the GitHub client.

        Args:
            hostname: GHES hostname (e.g., "github.mycompany.com"), ignored for github.com
            token: Access token (PAT for github.com, OAuth for GHES)
            mode: "github.com" or "ghes"
        """
        self.mode = mode
        if mode == "github.com":
            self.base_url = "https://api.github.com"
        else:
            if not hostname:
                raise ValueError("hostname is required for GHES mode")
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
            payload = {
                "commit_id": commit_id,
                "event": event,
                "body": body,
                "comments": comments,
            }
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                headers=self._headers(),
                json=payload,
                timeout=60.0,
            )
            if response.status_code == 401:
                raise ValueError("GitHub authentication failed. Check your token.")
            elif response.status_code == 403:
                error_data = response.json()
                if "rate limit" in error_data.get("message", "").lower():
                    raise ValueError("GitHub API rate limit exceeded. Try again later.")
                raise ValueError(f"GitHub API access denied: {error_data.get('message', 'Unknown error')}")
            elif response.status_code == 422:
                # GitHub validation error - show details
                error_data = response.json()
                error_msg = error_data.get("message", "Unknown error")
                errors = error_data.get("errors", [])
                detail = f"GitHub API error: {error_msg}"
                if errors:
                    detail += f"\nErrors: {errors}"
                detail += f"\nComments sent: {len(comments)}"
                raise ValueError(detail)
            response.raise_for_status()
            return ReviewResponse.model_validate(response.json())
