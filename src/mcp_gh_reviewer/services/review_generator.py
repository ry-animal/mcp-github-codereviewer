"""Service for generating AI-powered code reviews."""

import json
import re

from mcp_gh_reviewer.clients.openrouter_client import OpenRouterClient
from mcp_gh_reviewer.models.github import PullRequest, PullRequestFile
from mcp_gh_reviewer.models.review import (
    AIReviewResult,
    CommentSide,
    InlineComment,
    ParsedDiff,
    ReviewAction,
)

SYSTEM_PROMPT = """You are an expert code reviewer. Analyze the provided pull request diff and generate a comprehensive code review.

Your review should:
1. Identify bugs, security issues, and logic errors
2. Suggest improvements for code quality and maintainability
3. Note any missing tests or documentation

IMPORTANT: Only create inline_comments for ACTIONABLE feedback. Each comment MUST include:
- A specific problem or improvement opportunity
- A concrete code suggestion showing how to fix/improve it

DO NOT create comments that:
- Only praise the code ("Good job!", "Nice pattern!")
- State observations without suggestions ("This handles errors")
- Lack specific code examples

Output your review as JSON matching this schema:
{
  "summary": "Overall review summary (2-3 paragraphs)",
  "decision": "APPROVE" | "REQUEST_CHANGES" | "COMMENT",
  "confidence": 0.0-1.0,
  "key_issues": ["Issue 1", "Issue 2"],
  "inline_comments": [
    {
      "path": "relative/file/path.py",
      "line": 42,
      "body": "Problem description.\\n\\nSuggested fix:\\n```python\\n# code example here\\n```"
    }
  ]
}

Example of a GOOD inline comment:
{
  "path": "src/client.py",
  "line": 45,
  "body": "This catches all exceptions which may hide bugs. Consider catching specific exceptions.\\n\\nSuggested fix:\\n```python\\ntry:\\n    response = await client.post(url)\\nexcept httpx.TimeoutException:\\n    logger.warning('Request timed out')\\n    raise\\nexcept httpx.HTTPStatusError as e:\\n    logger.error(f'HTTP error: {e.response.status_code}')\\n    raise\\n```"
}

Example of a BAD inline comment (don't do this):
{
  "path": "src/client.py",
  "line": 45,
  "body": "Good error handling pattern here!"
}

Guidelines:
- Use REQUEST_CHANGES only for blocking issues (bugs, security problems)
- Use APPROVE if changes are good or only have minor suggestions
- Use COMMENT for neutral observations
- Line numbers must refer to the NEW file (right side of diff)
- Fewer high-quality comments are better than many low-quality ones
- If code is good and needs no changes, return empty inline_comments array
"""


class ReviewGenerator:
    """Generate AI-powered code reviews."""

    def __init__(self, client: OpenRouterClient, model: str):
        """Initialize the review generator.

        Args:
            client: OpenRouter API client
            model: Model identifier (e.g., "anthropic/claude-sonnet-4")
        """
        self.client = client
        self.model = model

    async def generate_review(
        self,
        pr: PullRequest,
        diff: str,
        files: list[PullRequestFile],
        parsed_diff: ParsedDiff,
        focus_areas: list[str] | None = None,
    ) -> AIReviewResult:
        """Generate a complete code review for a PR.

        Args:
            pr: Pull request metadata
            diff: Raw unified diff string
            files: List of changed files with stats
            parsed_diff: Parsed diff for line validation
            focus_areas: Optional areas to focus review on

        Returns:
            AIReviewResult with summary, decision, and inline comments
        """
        # Build context for the AI
        user_prompt = self._build_review_prompt(pr, diff, files, focus_areas)

        # Call AI for review
        response = await self.client.generate_review(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=self.model,
        )

        # Parse AI response
        review_data = self._parse_ai_response(response)

        # Validate and adjust inline comments
        validated_comments = self._validate_comments(
            review_data.get("inline_comments", []),
            parsed_diff,
        )

        return AIReviewResult(
            summary=review_data.get("summary", "Review completed."),
            decision=ReviewAction(review_data.get("decision", "COMMENT")),
            confidence=review_data.get("confidence", 0.8),
            key_issues=review_data.get("key_issues", []),
            inline_comments=validated_comments,
        )

    def _build_review_prompt(
        self,
        pr: PullRequest,
        diff: str,
        files: list[PullRequestFile],
        focus_areas: list[str] | None = None,
    ) -> str:
        """Build the prompt for the AI reviewer.

        Args:
            pr: Pull request metadata
            diff: Raw unified diff
            files: Changed files with stats
            focus_areas: Optional focus areas

        Returns:
            Formatted prompt string
        """
        files_summary = "\n".join(
            [
                f"- {f.filename}: +{f.additions}/-{f.deletions} ({f.status})"
                for f in files
            ]
        )

        focus_text = ""
        if focus_areas:
            focus_text = f"\n\nFocus areas requested: {', '.join(focus_areas)}"

        return f"""# Pull Request Review Request

## PR Information
- **Title**: {pr.title}
- **Author**: {pr.user.login}
- **Branch**: {pr.head.ref} -> {pr.base.ref}
- **Description**: {pr.body or 'No description provided'}

## Files Changed
{files_summary}
{focus_text}

## Diff
```diff
{diff}
```

Please review this pull request and provide your analysis."""

    def _parse_ai_response(self, response: str) -> dict:
        """Parse AI response, handling potential JSON extraction.

        Args:
            response: Raw AI response string

        Returns:
            Parsed dictionary with review data
        """
        # Try direct JSON parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in response (starts with { ends with })
        brace_match = re.search(r"\{[\s\S]*\}", response)
        if brace_match:
            try:
                parsed = json.loads(brace_match.group(0))
                # Validate required fields exist
                required_fields = ['summary', 'decision', 'confidence', 'key_issues', 'inline_comments']
                if all(field in parsed for field in required_fields):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Fallback: return minimal result
        return {
            "summary": response,
            "decision": "COMMENT",
            "confidence": 0.5,
            "inline_comments": [],
        }

    def _validate_comments(
        self,
        comments: list[dict],
        parsed_diff: ParsedDiff,
    ) -> list[InlineComment]:
        """Validate and filter comments to valid line positions.

        Args:
            comments: Raw comment dictionaries from AI
            parsed_diff: Parsed diff for validation

        Returns:
            List of validated InlineComment objects
        """
        validated = []

        for comment in comments:
            path = comment.get("path")
            line = comment.get("line")
            body = comment.get("body")

            if not all([path, line, body]):
                continue

            # Find file in parsed diff
            file_diff = parsed_diff.get_file(path)
            if not file_diff:
                continue

            # Check if line is commentable
            commentable_lines = file_diff.get_commentable_lines()

            if line not in commentable_lines:
                # Try to find nearest valid line
                valid_lines = sorted(commentable_lines.keys())
                if not valid_lines:
                    continue
                nearest = min(valid_lines, key=lambda x: abs(x - line))
                line = nearest

            validated.append(
                InlineComment(
                    path=path,
                    body=body,
                    line=line,
                    side=CommentSide.RIGHT,  # Comments on new file side
                )
            )

        return validated
