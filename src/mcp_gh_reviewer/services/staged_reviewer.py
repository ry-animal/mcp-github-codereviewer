"""Service for reviewing staged git changes."""

import json
import re
import subprocess
from dataclasses import dataclass

from mcp_gh_reviewer.clients.openrouter_client import OpenRouterClient
from mcp_gh_reviewer.models.review import (
    AIReviewResult,
    CommentSide,
    InlineComment,
    ParsedDiff,
    ReviewAction,
)
from mcp_gh_reviewer.services.diff_parser import DiffParser

STAGED_REVIEW_SYSTEM_PROMPT = """You are an expert code reviewer reviewing staged changes before a commit.

Your review should:
1. Identify bugs, security issues, and logic errors
2. Suggest improvements for code quality and maintainability
3. Note any missing tests or documentation
4. Check for debug code, console.logs, or TODO comments that shouldn't be committed

IMPORTANT: Only create inline_comments for ACTIONABLE feedback. Each comment MUST include:
- A specific problem or improvement opportunity
- A concrete code suggestion showing how to fix/improve it

DO NOT create comments that:
- Only praise the code ("Good job!", "Nice pattern!")
- State observations without suggestions ("This handles errors")
- Lack specific code examples

Output your review as JSON matching this schema:
{
  "summary": "Brief review summary (1-2 sentences)",
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

Guidelines:
- Use REQUEST_CHANGES for blocking issues (bugs, security problems, debug code)
- Use APPROVE if changes look good
- Use COMMENT for minor suggestions
- Line numbers must refer to the NEW file (right side of diff)
- Fewer high-quality comments are better than many low-quality ones
- If code is good and needs no changes, return empty inline_comments array
"""


@dataclass
class StagedChangesContext:
    """Context about staged changes."""

    diff: str
    file_count: int
    additions: int
    deletions: int
    branch: str
    files: list[str]


class StagedReviewer:
    """Review staged git changes before commit."""

    def __init__(self, client: OpenRouterClient, model: str):
        """Initialize the staged reviewer.

        Args:
            client: OpenRouter API client
            model: Model identifier (e.g., "anthropic/claude-sonnet-4")
        """
        self.client = client
        self.model = model
        self.parser = DiffParser()

    def get_staged_context(self) -> StagedChangesContext:
        """Get context about staged changes.

        Returns:
            StagedChangesContext with diff and metadata

        Raises:
            ValueError: If no staged changes exist or git commands fail
        """
        try:
            # Get staged diff
            diff_result = subprocess.run(
                ["git", "diff", "--cached"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
        except FileNotFoundError:
            raise ValueError("git not found. Please install git and try again.")
        except subprocess.TimeoutExpired:
            raise ValueError("git diff timed out. Repository may be too large.")
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to get staged diff: {e.stderr or e}")

        diff = diff_result.stdout

        if not diff.strip():
            raise ValueError("No staged changes to review")

        try:
            # Get list of staged files
            files_result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            files = [f for f in files_result.stdout.strip().split("\n") if f]

            # Get current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            branch = branch_result.stdout.strip() or "HEAD"

            # Count additions/deletions
            numstat_result = subprocess.run(
                ["git", "diff", "--cached", "--numstat"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            raise ValueError("git command timed out. Repository may be too large.")
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to get git information: {e.stderr or e}")

        additions = 0
        deletions = 0
        for line in numstat_result.stdout.strip().split("\n"):
            if line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    try:
                        additions += int(parts[0]) if parts[0] != "-" else 0
                        deletions += int(parts[1]) if parts[1] != "-" else 0
                    except ValueError:
                        pass  # Binary file

        return StagedChangesContext(
            diff=diff,
            file_count=len(files),
            additions=additions,
            deletions=deletions,
            branch=branch,
            files=files,
        )

    async def review_staged_changes(
        self,
        focus_areas: list[str] | None = None,
    ) -> AIReviewResult:
        """Review staged changes.

        Args:
            focus_areas: Optional areas to focus review on

        Returns:
            AIReviewResult with summary, decision, and inline comments
        """
        context = self.get_staged_context()
        parsed_diff = self.parser.parse(context.diff)

        # Build prompt
        user_prompt = self._build_prompt(context, focus_areas)

        # Call AI for review
        response = await self.client.generate_review(
            system_prompt=STAGED_REVIEW_SYSTEM_PROMPT,
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

    def _build_prompt(
        self,
        context: StagedChangesContext,
        focus_areas: list[str] | None = None,
    ) -> str:
        """Build the prompt for the AI reviewer."""
        files_list = "\n".join(f"- {f}" for f in context.files)

        focus_text = ""
        if focus_areas:
            focus_text = f"\n\nFocus areas requested: {', '.join(focus_areas)}"

        return f"""# Staged Changes Review Request

## Context
- **Branch**: {context.branch}
- **Files**: {context.file_count} files
- **Changes**: +{context.additions}/-{context.deletions} lines

## Files Changed
{files_list}
{focus_text}

## Diff
```diff
{context.diff}
```

Please review these staged changes before commit."""

    def _parse_ai_response(self, response: str) -> dict:
        """Parse AI response, handling potential JSON extraction."""
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

        # Try to find JSON object in response
        brace_match = re.search(r"\{[\s\S]*\}", response)
        if brace_match:
            try:
                parsed = json.loads(brace_match.group(0))
                required_fields = ["summary", "decision", "confidence", "key_issues", "inline_comments"]
                if all(field in parsed for field in required_fields):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Fallback
        return {
            "summary": response,
            "decision": "COMMENT",
            "confidence": 0.5,
            "key_issues": [],
            "inline_comments": [],
        }

    def _validate_comments(
        self,
        comments: list[dict],
        parsed_diff: ParsedDiff,
    ) -> list[InlineComment]:
        """Validate and filter comments to valid line positions."""
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
                    side=CommentSide.RIGHT,
                )
            )

        return validated
