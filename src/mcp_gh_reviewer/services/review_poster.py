"""Service for posting AI-generated reviews to GitHub."""

from typing import Any

from mcp_gh_reviewer.clients.github_client import GitHubClient
from mcp_gh_reviewer.models.review import AIReviewResult, ParsedDiff, ReviewResponse


class ReviewPoster:
    """Post AI-generated reviews to GitHub."""

    def __init__(self, client: GitHubClient, parsed_diff: ParsedDiff):
        """Initialize the review poster.

        Args:
            client: GitHub API client
            parsed_diff: Parsed diff for line validation
        """
        self.client = client
        self.parsed_diff = parsed_diff

    async def post_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        result: AIReviewResult,
        commit_id: str,
    ) -> ReviewResponse:
        """Post a review with inline comments to GitHub.

        Uses the batch review API to submit all comments at once,
        which is more efficient and creates a single notification.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            result: AI review result with comments
            commit_id: SHA of the commit to review

        Returns:
            ReviewResponse with ID and URL
        """
        # Build GitHub API comment format
        comments = self._format_comments(result)

        # Build review body with summary
        body = self._format_review_body(result)

        # Submit review
        return await self.client.create_review(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            commit_id=commit_id,
            event=result.decision.value,
            body=body,
            comments=comments,
        )

    def _format_comments(self, result: AIReviewResult) -> list[dict[str, Any]]:
        """Format inline comments for GitHub API.

        Args:
            result: AI review result

        Returns:
            List of comment dictionaries for the API
        """
        comments = []
        for inline in result.inline_comments:
            comment: dict[str, Any] = {
                "path": inline.path,
                "body": inline.body,
                "line": inline.line,
                "side": inline.side.value,  # "LEFT" or "RIGHT"
            }

            # Add multi-line support if applicable
            if inline.start_line:
                comment["start_line"] = inline.start_line
                comment["start_side"] = (inline.start_side or inline.side).value

            comments.append(comment)

        return comments

    def _format_review_body(self, result: AIReviewResult) -> str:
        """Format the review summary for GitHub.

        Args:
            result: AI review result

        Returns:
            Formatted review body with summary and issues
        """
        lines = [result.summary]

        if result.key_issues:
            lines.append("\n### Key Issues\n")
            for issue in result.key_issues:
                lines.append(f"- {issue}")

        lines.append(f"\n---\n*AI Review (confidence: {result.confidence:.0%})*")

        return "\n".join(lines)
