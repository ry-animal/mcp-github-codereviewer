#!/usr/bin/env python3
"""Pre-commit hook for AI-powered code review of staged changes."""

import asyncio
import sys
from typing import NoReturn

from mcp_gh_reviewer.clients.openrouter_client import OpenRouterClient
from mcp_gh_reviewer.config import settings
from mcp_gh_reviewer.models.review import ReviewAction
from mcp_gh_reviewer.services.staged_reviewer import StagedReviewer

# ANSI colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_header(text: str) -> None:
    """Print a styled header."""
    print(f"\n{BOLD}{CYAN}{text}{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")


def print_comment(path: str, line: int, body: str) -> None:
    """Print a formatted inline comment."""
    print(f"\n{BLUE}{path}:{line}{RESET}")
    # Indent the body
    for line_text in body.split("\n"):
        print(f"  {line_text}")


def format_decision(decision: ReviewAction, confidence: float) -> str:
    """Format the review decision with color."""
    color = {
        ReviewAction.APPROVE: GREEN,
        ReviewAction.REQUEST_CHANGES: RED,
        ReviewAction.COMMENT: YELLOW,
    }.get(decision, RESET)
    return f"{color}{BOLD}{decision.value}{RESET} {DIM}(confidence: {confidence:.0%}){RESET}"


async def run_review() -> int:
    """Run the staged changes review.

    Returns:
        0 to allow commit, 1 to block
    """
    # Check for API key
    if not settings.openrouter_api_key:
        print(f"{RED}Error: OPENROUTER_API_KEY not set{RESET}")
        print("Get your API key from https://openrouter.ai/keys")
        print("Then set: export OPENROUTER_API_KEY=your_key_here")
        print(f"\n{DIM}Skipping review...{RESET}")
        return 0  # Don't block if not configured

    client = OpenRouterClient(api_key=settings.openrouter_api_key)
    reviewer = StagedReviewer(client=client, model=settings.review_model)

    try:
        context = reviewer.get_staged_context()
    except ValueError as e:
        # No staged changes
        print(f"{DIM}{e}{RESET}")
        return 0

    print(f"\n{BOLD}Reviewing staged changes...{RESET}")
    print(f"{DIM}Found {context.file_count} files with +{context.additions}/-{context.deletions} lines{RESET}")

    try:
        result = await reviewer.review_staged_changes()
    except Exception as e:
        print(f"{RED}Review failed: {e}{RESET}")
        print(f"\n{DIM}Skipping review due to error...{RESET}")
        return 0  # Don't block on errors

    # Display results
    print_header("Review Summary")
    print(f"Decision: {format_decision(result.decision, result.confidence)}")
    print(f"\n{result.summary}")

    if result.key_issues:
        print_header("Key Issues")
        for issue in result.key_issues:
            print(f"  {YELLOW}*{RESET} {issue}")

    if result.inline_comments:
        print_header(f"Inline Comments ({len(result.inline_comments)})")
        for comment in result.inline_comments:
            print_comment(comment.path, comment.line, comment.body)

    print(f"\n{DIM}{'─' * 50}{RESET}")

    # Advisory prompt
    if result.decision == ReviewAction.REQUEST_CHANGES:
        print(f"\n{YELLOW}{BOLD}Issues found that may need attention.{RESET}")
    elif result.decision == ReviewAction.APPROVE:
        print(f"\n{GREEN}Changes look good!{RESET}")

    # Always prompt for confirmation
    try:
        response = input(f"\n{BOLD}Proceed with commit? [y/N]: {RESET}").strip().lower()
        if response in ("y", "yes"):
            print(f"{GREEN}Continuing with commit...{RESET}")
            return 0
        else:
            print(f"{YELLOW}Commit aborted.{RESET}")
            return 1
    except (EOFError, KeyboardInterrupt):
        print(f"\n{YELLOW}Commit aborted.{RESET}")
        return 1


def main() -> NoReturn:
    """Main entry point for pre-commit hook."""
    exit_code = asyncio.run(run_review())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
