"""GitHub MCP proxy provider for github.com."""

import os
from typing import Any, Optional

from fastmcp import Client

from mcp_gh_reviewer.clients.github_client import GitHubClient
from mcp_gh_reviewer.models.github import (
    PullRequest,
    PullRequestFile,
    PullRequestListItem,
)
from mcp_gh_reviewer.models.review import ReviewResponse
from mcp_gh_reviewer.providers.base import GitHubDataProvider


class GitHubMCPProvider(GitHubDataProvider):
    """Provider that uses the official GitHub MCP server for PR data.

    For github.com, we use:
    - GitHub MCP server for reading PR data (via FastMCP proxy)
    - Direct GitHubClient for posting reviews (MCP server may not support this)
    """

    def __init__(self, github_token: str):
        """Initialize the GitHub MCP provider.

        Args:
            github_token: Personal Access Token for GitHub
        """
        self.token = github_token
        self._client: Optional[Client] = None
        # Direct client for operations not supported by MCP server
        self._api_client = GitHubClient(token=github_token, mode="github.com")

    async def _get_client(self) -> Client:
        """Get or create the MCP client connection."""
        if self._client is None:
            # Create client for GitHub MCP server
            self._client = Client(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={
                    **os.environ,
                    "GITHUB_PERSONAL_ACCESS_TOKEN": self.token,
                },
            )
        return self._client

    async def _call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool on the GitHub MCP server."""
        client = await self._get_client()
        async with client:
            result = await client.call_tool(tool_name, arguments)
            return result

    async def list_prs(
        self, owner: str, repo: str, state: str = "open"
    ) -> list[PullRequestListItem]:
        """List pull requests using GitHub MCP server."""
        # Use direct API client - more reliable for listing
        return await self._api_client.list_pull_requests(owner, repo, state)

    async def get_pr(self, owner: str, repo: str, pr_number: int) -> PullRequest:
        """Get PR details using GitHub MCP server."""
        # Use direct API client for structured data
        return await self._api_client.get_pull_request(owner, repo, pr_number)

    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Get PR diff using GitHub MCP server."""
        # Use direct API client - MCP server may not return raw diff
        return await self._api_client.get_pull_request_diff(owner, repo, pr_number)

    async def get_pr_files(
        self, owner: str, repo: str, pr_number: int
    ) -> list[PullRequestFile]:
        """Get PR files using GitHub MCP server."""
        return await self._api_client.get_pull_request_files(owner, repo, pr_number)

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
        """Create a review - always uses direct API client."""
        # Reviews must use direct API for proper formatting
        return await self._api_client.create_review(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            commit_id=commit_id,
            event=event,
            body=body,
            comments=comments,
        )
