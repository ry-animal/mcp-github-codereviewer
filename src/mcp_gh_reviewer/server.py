"""FastMCP server for AI-powered GitHub PR code reviews.

Supports both github.com (PAT auth) and GitHub Enterprise Server (OAuth).
"""

from typing import Optional

from fastmcp import Context, FastMCP

from mcp_gh_reviewer.clients.github_client import GitHubClient
from mcp_gh_reviewer.clients.openrouter_client import OpenRouterClient
from mcp_gh_reviewer.config import settings
from mcp_gh_reviewer.models.github import PullRequest, PullRequestFile, PullRequestListItem
from mcp_gh_reviewer.models.review import AIReviewResult, ReviewAction
from mcp_gh_reviewer.services.diff_parser import DiffParser
from mcp_gh_reviewer.services.review_generator import ReviewGenerator
from mcp_gh_reviewer.services.review_poster import ReviewPoster


def _create_mcp_server() -> FastMCP:
    """Create the MCP server based on configuration mode."""
    if settings.is_github_com:
        # github.com mode: No OAuth, uses PAT from config
        return FastMCP(
            name="GitHub PR Reviewer",
            instructions="AI-powered code review for GitHub PRs (github.com mode)",
        )
    else:
        # GHES mode: Use OAuth
        from mcp_gh_reviewer.auth.ghes_provider import GHESProvider

        auth_provider = GHESProvider(
            client_id=settings.github_client_id,
            client_secret=settings.github_client_secret,
            base_url=settings.mcp_server_base_url,
            ghes_hostname=settings.ghes_hostname,
        )
        return FastMCP(
            name="GitHub PR Reviewer",
            instructions="AI-powered code review for GitHub Enterprise Server PRs",
            auth=auth_provider,
        )


# Create the server
mcp = _create_mcp_server()


def _get_github_client(ctx: Optional[Context]) -> GitHubClient:
    """Create a GitHub client based on mode and context."""
    if settings.is_github_com:
        # Use PAT from settings
        return GitHubClient(
            token=settings.github_token,
            mode="github.com",
        )
    else:
        # Use OAuth token from context for GHES
        token = None
        if ctx is not None:
            try:
                token = ctx.get_access_token()
            except Exception:
                pass
        return GitHubClient(
            hostname=settings.ghes_hostname,
            token=token,
            mode="ghes",
        )


@mcp.tool
async def list_prs(
    owner: str,
    repo: str,
    state: str = "open",
    ctx: Context = None,
) -> list[PullRequestListItem]:
    """List pull requests in a repository.

    Args:
        owner: Repository owner (user or organization)
        repo: Repository name
        state: PR state filter - "open", "closed", or "all"

    Returns:
        List of pull requests with basic metadata
    """
    client = _get_github_client(ctx)
    return await client.list_pull_requests(owner, repo, state)


@mcp.tool
async def get_pr_diff(
    owner: str,
    repo: str,
    pr_number: int,
    ctx: Context = None,
) -> str:
    """Get the unified diff for a pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number

    Returns:
        Unified diff as a string
    """
    client = _get_github_client(ctx)
    return await client.get_pull_request_diff(owner, repo, pr_number)


@mcp.tool
async def get_pr_files(
    owner: str,
    repo: str,
    pr_number: int,
    ctx: Context = None,
) -> list[PullRequestFile]:
    """List files changed in a pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number

    Returns:
        List of changed files with stats and patches
    """
    client = _get_github_client(ctx)
    return await client.get_pull_request_files(owner, repo, pr_number)


@mcp.tool
async def get_pr(
    owner: str,
    repo: str,
    pr_number: int,
    ctx: Context = None,
) -> PullRequest:
    """Get details of a pull request.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number

    Returns:
        Pull request details including title, body, author, and branch info
    """
    client = _get_github_client(ctx)
    return await client.get_pull_request(owner, repo, pr_number)


@mcp.tool
async def review_pr(
    owner: str,
    repo: str,
    pr_number: int,
    action: str = "COMMENT",
    focus_areas: Optional[list[str]] = None,
    ctx: Context = None,
) -> AIReviewResult:
    """Perform an AI-powered code review on a pull request.

    This tool:
    1. Fetches the PR diff and metadata
    2. Analyzes the changes using AI
    3. Generates inline comments for specific issues
    4. Creates a review summary with approval decision
    5. Posts the review to GitHub

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        action: Review action override - "APPROVE", "REQUEST_CHANGES", or "COMMENT"
        focus_areas: Optional areas to focus review (e.g., ["security", "performance"])

    Returns:
        AI review result with summary, decision, and inline comments
    """
    gh_client = _get_github_client(ctx)
    ai_client = OpenRouterClient(settings.openrouter_api_key)

    # Fetch PR data
    if ctx:
        await ctx.info(f"Fetching PR #{pr_number} data...")
    pr = await gh_client.get_pull_request(owner, repo, pr_number)
    diff = await gh_client.get_pull_request_diff(owner, repo, pr_number)
    files = await gh_client.get_pull_request_files(owner, repo, pr_number)

    # Parse diff for line mapping
    if ctx:
        await ctx.info("Parsing diff...")
    parser = DiffParser()
    parsed_diff = parser.parse(diff)

    # Generate AI review
    if ctx:
        await ctx.info("Generating AI review...")
    generator = ReviewGenerator(ai_client, settings.review_model)
    review_result = await generator.generate_review(
        pr=pr,
        diff=diff,
        files=files,
        parsed_diff=parsed_diff,
        focus_areas=focus_areas or [],
    )

    # Override action if specified
    if action != "COMMENT":
        review_result.decision = ReviewAction(action)

    # Post review to GitHub
    if ctx:
        await ctx.info("Posting review to GitHub...")
    poster = ReviewPoster(gh_client, parsed_diff)
    review_response = await poster.post_review(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        result=review_result,
        commit_id=pr.head.sha,
    )

    if ctx:
        await ctx.info(f"Review posted: {review_response.html_url}")

    return review_result


def main() -> None:
    """Run the MCP server.

    Defaults to stdio transport for Docker MCP Toolkit compatibility.
    Set MCP_TRANSPORT=http to run as HTTP server.
    """
    import os

    mode_info = "github.com" if settings.is_github_com else f"GHES ({settings.ghes_hostname})"
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "http":
        print(f"Starting GitHub PR Reviewer in {mode_info} mode (HTTP)...")
        mcp.run(transport="http", host="0.0.0.0", port=settings.mcp_server_port)
    else:
        # stdio for Docker MCP Toolkit
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
