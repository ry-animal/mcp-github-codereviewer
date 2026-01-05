"""Command-line interface for GitHub PR Reviewer."""

import argparse
import asyncio
import re
import sys

from mcp_gh_reviewer.clients.github_client import GitHubClient
from mcp_gh_reviewer.clients.openrouter_client import OpenRouterClient
from mcp_gh_reviewer.config import settings
from mcp_gh_reviewer.services.diff_parser import DiffParser
from mcp_gh_reviewer.services.review_generator import ReviewGenerator
from mcp_gh_reviewer.services.review_poster import ReviewPoster


def parse_github_url(url_or_repo: str) -> tuple[str | None, str, str, int | None]:
    """Parse a GitHub URL or owner/repo string.

    Accepts:
        - https://github.com/owner/repo/pull/123
        - https://github.mycompany.com/owner/repo/pull/123 (GHES)
        - github.com/owner/repo/pull/123
        - owner/repo/pull/123
        - owner/repo (for list command)

    Returns:
        Tuple of (hostname or None, owner, repo, pr_number or None)
        hostname is None for owner/repo shorthand (uses config default)
    """
    if len(url_or_repo) > 500:  # Reasonable limit for GitHub URLs
        raise ValueError(f"Input too long: {len(url_or_repo)} characters")

    # Full URL pattern: https://hostname/owner/repo/pull/123
    # Hostname must be valid domain (e.g., github.com, github.mycompany.com)
    hostname_pattern = r"[a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z0-9][-a-zA-Z0-9]*)+"
    url_pr_pattern = rf"(?:https?://)?({hostname_pattern})/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(url_pr_pattern, url_or_repo)
    if match:
        hostname = match.group(1).removeprefix("www.")
        return hostname, match.group(2), match.group(3), int(match.group(4))

    # Full URL pattern without PR: https://hostname/owner/repo
    url_repo_pattern = rf"(?:https?://)?({hostname_pattern})/([^/]+)/([^/]+)/?$"
    match = re.match(url_repo_pattern, url_or_repo)
    if match:
        hostname = match.group(1).removeprefix("www.")
        return hostname, match.group(2), match.group(3), None

    # owner/repo/pull/123 pattern (no hostname - use config)
    short_pr_pattern = r"([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(short_pr_pattern, url_or_repo)
    if match:
        return None, match.group(1), match.group(2), int(match.group(3))

    # owner/repo pattern (no PR number, no hostname)
    repo_pattern = r"([^/]+)/([^/]+)$"
    match = re.match(repo_pattern, url_or_repo)
    if match:
        return None, match.group(1), match.group(2), None

    raise ValueError(
        f"Invalid format: {url_or_repo}\n"
        "Expected: https://github.com/owner/repo/pull/123 or owner/repo"
    )


def _create_github_client(hostname: str | None) -> GitHubClient:
    """Create GitHub client for the given hostname.

    Args:
        hostname: GitHub hostname from URL, or None to use config default

    Returns:
        Configured GitHubClient
    """
    # Determine if this is github.com or GHES based on hostname
    effective_hostname = hostname or (
        "github.com" if settings.is_github_com else settings.ghes_hostname
    )

    if effective_hostname == "github.com":
        if not settings.github_token:
            print("Error: GitHub token not configured. Set GITHUB_TOKEN environment variable.")
            sys.exit(1)
        return GitHubClient(token=settings.github_token, mode="github.com")
    else:
        # GHES - use GHES_TOKEN if set, else GITHUB_TOKEN
        token = settings.effective_token
        if not token:
            print("Error: GHES token not configured. Set GHES_TOKEN or GITHUB_TOKEN environment variable.")
            sys.exit(1)
        if not effective_hostname:
            print("Error: GHES hostname not configured. Set GHES_HOSTNAME or provide full URL.")
            sys.exit(1)
        return GitHubClient(
            hostname=effective_hostname,
            token=token,
            mode="ghes",
        )


async def list_prs_cmd(owner: str, repo: str, hostname: str | None, state: str = "open") -> None:
    """List pull requests in a repository."""
    client = _create_github_client(hostname)
    prs = await client.list_pull_requests(owner, repo, state)

    if not prs:
        print(f"No {state} PRs found in {owner}/{repo}")
        return

    print(f"\n{state.upper()} PRs in {owner}/{repo}:\n")
    for pr in prs:
        draft = " [DRAFT]" if pr.draft else ""
        print(f"  #{pr.number}: {pr.title}{draft}")
        print(f"         by @{pr.user.login} | {pr.head.ref} -> {pr.base.ref}")
        print()


async def review_pr_cmd(
    owner: str,
    repo: str,
    pr_number: int,
    hostname: str | None = None,
    post: bool = False,
    focus: list[str] | None = None,
) -> None:
    """Review a pull request with AI."""
    if not settings.openrouter_api_key:
        print("Error: OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable.")
        sys.exit(1)

    gh_client = _create_github_client(hostname)
    ai_client = OpenRouterClient(settings.openrouter_api_key)

    print(f"\nFetching PR #{pr_number} from {owner}/{repo}...")
    pr = await gh_client.get_pull_request(owner, repo, pr_number)
    diff = await gh_client.get_pull_request_diff(owner, repo, pr_number)
    files = await gh_client.get_pull_request_files(owner, repo, pr_number)

    print(f"  Title: {pr.title}")
    print(f"  Author: @{pr.user.login}")
    print(f"  Branch: {pr.head.ref} -> {pr.base.ref}")
    print(f"  Files changed: {len(files)}")

    print("\nParsing diff...")
    parser = DiffParser()
    parsed_diff = parser.parse(diff)

    print(f"Generating AI review using {settings.review_model}...")
    generator = ReviewGenerator(ai_client, settings.review_model)
    result = await generator.generate_review(
        pr=pr,
        diff=diff,
        files=files,
        parsed_diff=parsed_diff,
        focus_areas=focus,
    )

    # Display results
    print("\n" + "=" * 60)
    print("AI REVIEW RESULT")
    print("=" * 60)
    print(f"\nDecision: {result.decision.value}")
    print(f"Confidence: {result.confidence:.0%}")
    print(f"\nSummary:\n{result.summary}")

    if result.key_issues:
        print("\nKey Issues:")
        for issue in result.key_issues:
            print(f"  - {issue}")

    if result.inline_comments:
        print(f"\nInline Comments ({len(result.inline_comments)}):")
        for comment in result.inline_comments:
            print(f"\n  {comment.path}:{comment.line}")
            print(f"  {comment.body}")

    # Post to GitHub if requested
    if post:
        print("\nPosting review to GitHub...")
        poster = ReviewPoster(gh_client, parsed_diff)
        try:
            response = await poster.post_review(
                owner=owner,
                repo=repo,
                pr_number=pr_number,
                result=result,
                commit_id=pr.head.sha,
            )
            print(f"Review posted: {response.html_url}")
        except ValueError as e:
            error_str = str(e).lower()
            # Handle "can't approve/request changes on your own PR" error
            if "your own" in error_str and ("approve" in error_str or "request changes" in error_str):
                print(f"\nNote: Can't {result.decision.value} your own PR - posting as COMMENT instead")
                from mcp_gh_reviewer.models.review import ReviewAction
                result.decision = ReviewAction.COMMENT
                response = await poster.post_review(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number,
                    result=result,
                    commit_id=pr.head.sha,
                )
                print(f"Review posted: {response.html_url}")
            # Handle invalid line positions
            elif "position" in error_str or "line" in error_str:
                print(f"\nError with inline comments: {e}")
                print("Retrying without inline comments...")
                result.inline_comments = []
                response = await poster.post_review(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number,
                    result=result,
                    commit_id=pr.head.sha,
                )
                print(f"Review posted (summary only): {response.html_url}")
            else:
                print(f"\nError posting review: {e}")
                sys.exit(1)
        except Exception as e:
            print(f"\nUnexpected error posting review: {e}")
            sys.exit(1)
    else:
        print("\n(Use --post to submit this review to GitHub)")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI-powered GitHub PR code reviewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review a PR using full URL
  gh-review https://github.com/owner/repo/pull/123

  # Review with posting to GitHub
  gh-review https://github.com/owner/repo/pull/123 --post

  # Review using owner/repo format
  gh-review owner/repo 123

  # List open PRs
  gh-review --list owner/repo

  # Focus review on specific areas
  gh-review https://github.com/owner/repo/pull/123 --focus security

  # GitHub Enterprise Server (GHES) - just use the full URL
  gh-review https://github.mycompany.com/team/project/pull/42 --post
        """,
    )

    parser.add_argument(
        "target",
        nargs="?",
        help="PR URL (https://github.com/owner/repo/pull/123) or owner/repo",
    )
    parser.add_argument(
        "pr_number",
        type=int,
        nargs="?",
        help="Pull request number (if target is owner/repo format)",
    )
    parser.add_argument(
        "--post",
        action="store_true",
        help="Post the review to GitHub (default: preview only)",
    )
    parser.add_argument(
        "--focus",
        action="append",
        help="Focus areas for review (can be used multiple times)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_prs",
        help="List PRs instead of reviewing",
    )
    parser.add_argument(
        "--state",
        choices=["open", "closed", "all"],
        default="open",
        help="PR state filter for --list (default: open)",
    )

    args = parser.parse_args()

    if not args.target:
        parser.print_help()
        sys.exit(1)

    # Parse the target
    try:
        hostname, owner, repo, parsed_pr = parse_github_url(args.target)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Handle list command
    if args.list_prs:
        asyncio.run(list_prs_cmd(owner, repo, hostname, args.state))
        return

    # Use PR number from URL or argument
    final_pr_number = parsed_pr or args.pr_number
    if not final_pr_number:
        print("Error: PR number required. Provide URL with /pull/123 or pass PR number as argument.")
        print("       Or use --list to list PRs in the repo.")
        sys.exit(1)

    asyncio.run(review_pr_cmd(owner, repo, final_pr_number, hostname, args.post, args.focus))


if __name__ == "__main__":
    main()
