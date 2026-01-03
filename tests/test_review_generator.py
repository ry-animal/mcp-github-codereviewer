"""Tests for review generator service."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_gh_reviewer.models.github import (
    GitHubUser,
    PullRequest,
    PullRequestFile,
    PullRequestHead,
)
from mcp_gh_reviewer.models.review import (
    CommentSide,
    DiffHunk,
    DiffLine,
    FileDiff,
    ParsedDiff,
    ReviewAction,
)
from datetime import datetime
from mcp_gh_reviewer.services.review_generator import ReviewGenerator, SYSTEM_PROMPT


class TestReviewGeneratorInit:
    """Tests for ReviewGenerator initialization."""

    def test_stores_client(self):
        """Generator should store the AI client."""
        mock_client = MagicMock()
        generator = ReviewGenerator(client=mock_client, model="test-model")
        assert generator.client == mock_client

    def test_stores_model(self):
        """Generator should store the model name."""
        mock_client = MagicMock()
        generator = ReviewGenerator(client=mock_client, model="anthropic/claude-sonnet-4")
        assert generator.model == "anthropic/claude-sonnet-4"


class TestParseAIResponse:
    """Tests for AI response parsing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.generator = ReviewGenerator(client=self.mock_client, model="test")

    def test_parse_valid_json(self):
        """Should parse valid JSON response."""
        response = json.dumps({
            "summary": "Good PR",
            "decision": "APPROVE",
            "confidence": 0.9,
            "key_issues": [],
            "inline_comments": [],
        })

        result = self.generator._parse_ai_response(response)

        assert result["summary"] == "Good PR"
        assert result["decision"] == "APPROVE"
        assert result["confidence"] == 0.9

    def test_parse_json_in_markdown_block(self):
        """Should extract JSON from markdown code block."""
        response = """Here's my review:

```json
{
    "summary": "Needs work",
    "decision": "REQUEST_CHANGES",
    "confidence": 0.8,
    "key_issues": ["Bug found"],
    "inline_comments": []
}
```

Let me know if you have questions."""

        result = self.generator._parse_ai_response(response)

        assert result["summary"] == "Needs work"
        assert result["decision"] == "REQUEST_CHANGES"
        assert result["key_issues"] == ["Bug found"]

    def test_parse_json_in_plain_code_block(self):
        """Should extract JSON from plain code block without json specifier."""
        response = """Review:

```
{
    "summary": "LGTM",
    "decision": "APPROVE",
    "confidence": 0.95,
    "key_issues": [],
    "inline_comments": []
}
```"""

        result = self.generator._parse_ai_response(response)

        assert result["summary"] == "LGTM"
        assert result["decision"] == "APPROVE"

    def test_fallback_for_invalid_json(self):
        """Should return fallback result for unparseable response."""
        response = "This is just plain text, not JSON at all."

        result = self.generator._parse_ai_response(response)

        assert result["summary"] == response
        assert result["decision"] == "COMMENT"
        assert result["confidence"] == 0.5
        assert result["inline_comments"] == []


class TestBuildReviewPrompt:
    """Tests for review prompt building."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.generator = ReviewGenerator(client=self.mock_client, model="test")

        # Create test PR
        self.pr = PullRequest(
            number=123,
            title="Add new feature",
            body="This PR adds a cool feature",
            state="open",
            user=GitHubUser(login="testuser", id=1, avatar_url=""),
            head=PullRequestHead(ref="feature-branch", sha="abc123", label="testuser:feature-branch"),
            base=PullRequestHead(ref="main", sha="def456", label="testuser:main"),
            html_url="https://github.com/test/repo/pull/123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.files = [
            PullRequestFile(
                sha="abc123",
                filename="src/main.py",
                status="modified",
                additions=10,
                deletions=5,
                changes=15,
                patch="@@ -1,5 +1,10 @@",
            ),
            PullRequestFile(
                sha="def456",
                filename="tests/test_main.py",
                status="added",
                additions=20,
                deletions=0,
                changes=20,
            ),
        ]

    def test_includes_pr_title(self):
        """Prompt should include PR title."""
        prompt = self.generator._build_review_prompt(
            self.pr, "diff content", self.files
        )
        assert "Add new feature" in prompt

    def test_includes_author(self):
        """Prompt should include PR author."""
        prompt = self.generator._build_review_prompt(
            self.pr, "diff content", self.files
        )
        assert "testuser" in prompt

    def test_includes_branch_info(self):
        """Prompt should include branch information."""
        prompt = self.generator._build_review_prompt(
            self.pr, "diff content", self.files
        )
        assert "feature-branch" in prompt
        assert "main" in prompt

    def test_includes_files_summary(self):
        """Prompt should include files summary with stats."""
        prompt = self.generator._build_review_prompt(
            self.pr, "diff content", self.files
        )
        assert "src/main.py" in prompt
        assert "+10/-5" in prompt
        assert "modified" in prompt
        assert "tests/test_main.py" in prompt
        assert "added" in prompt

    def test_includes_diff(self):
        """Prompt should include the diff content."""
        prompt = self.generator._build_review_prompt(
            self.pr, "diff --git a/file.py b/file.py", self.files
        )
        assert "diff --git a/file.py b/file.py" in prompt

    def test_includes_focus_areas(self):
        """Prompt should include focus areas if provided."""
        prompt = self.generator._build_review_prompt(
            self.pr, "diff", self.files, focus_areas=["security", "performance"]
        )
        assert "security" in prompt
        assert "performance" in prompt

    def test_handles_missing_body(self):
        """Prompt should handle PR with no body."""
        self.pr.body = None
        prompt = self.generator._build_review_prompt(
            self.pr, "diff", self.files
        )
        assert "No description provided" in prompt


class TestValidateComments:
    """Tests for comment validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.generator = ReviewGenerator(client=self.mock_client, model="test")

        # Create a parsed diff with valid lines
        self.parsed_diff = ParsedDiff(
            files=[
                FileDiff(
                    path="src/main.py",
                    old_path="src/main.py",
                    hunks=[
                        DiffHunk(
                            source_start=1,
                            source_length=5,
                            target_start=1,
                            target_length=10,
                            lines=[
                                DiffLine(
                                    content="def hello():",
                                    line_type="context",
                                    source_line_no=1,
                                    target_line_no=1,
                                    diff_position=1,
                                ),
                                DiffLine(
                                    content="    return 'world'",
                                    line_type="addition",
                                    target_line_no=2,
                                    diff_position=2,
                                ),
                                DiffLine(
                                    content="",
                                    line_type="context",
                                    source_line_no=2,
                                    target_line_no=3,
                                    diff_position=3,
                                ),
                            ],
                        )
                    ],
                )
            ]
        )

    def test_validates_correct_line(self):
        """Should accept comment on valid line."""
        comments = [
            {"path": "src/main.py", "line": 2, "body": "Good change!"}
        ]

        result = self.generator._validate_comments(comments, self.parsed_diff)

        assert len(result) == 1
        assert result[0].path == "src/main.py"
        assert result[0].line == 2
        assert result[0].body == "Good change!"
        assert result[0].side == CommentSide.RIGHT

    def test_filters_invalid_path(self):
        """Should filter comments with invalid file path."""
        comments = [
            {"path": "nonexistent.py", "line": 1, "body": "Comment"}
        ]

        result = self.generator._validate_comments(comments, self.parsed_diff)

        assert len(result) == 0

    def test_snaps_to_nearest_valid_line(self):
        """Should snap invalid line to nearest valid line."""
        comments = [
            {"path": "src/main.py", "line": 100, "body": "Far away comment"}
        ]

        result = self.generator._validate_comments(comments, self.parsed_diff)

        # Should snap to nearest valid line (1, 2, or 3)
        assert len(result) == 1
        assert result[0].line in [1, 2, 3]

    def test_filters_incomplete_comments(self):
        """Should filter comments missing required fields."""
        comments = [
            {"path": "src/main.py", "body": "No line"},  # missing line
            {"path": "src/main.py", "line": 1},  # missing body
            {"line": 1, "body": "No path"},  # missing path
        ]

        result = self.generator._validate_comments(comments, self.parsed_diff)

        assert len(result) == 0


class TestGenerateReview:
    """Tests for the full generate_review method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.generator = ReviewGenerator(client=self.mock_client, model="test-model")

        self.pr = PullRequest(
            number=1,
            title="Test PR",
            body="Test body",
            state="open",
            user=GitHubUser(login="user", id=1, avatar_url=""),
            head=PullRequestHead(ref="feature", sha="abc", label="user:feature"),
            base=PullRequestHead(ref="main", sha="def", label="user:main"),
            html_url="https://github.com/test/repo/pull/1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.files = [
            PullRequestFile(
                sha="abc123",
                filename="test.py",
                status="modified",
                additions=1,
                deletions=0,
                changes=1,
            )
        ]

        self.parsed_diff = ParsedDiff(files=[])

    @pytest.mark.asyncio
    async def test_returns_ai_review_result(self):
        """Should return AIReviewResult with parsed data."""
        self.mock_client.generate_review.return_value = json.dumps({
            "summary": "Great work!",
            "decision": "APPROVE",
            "confidence": 0.95,
            "key_issues": [],
            "inline_comments": [],
        })

        result = await self.generator.generate_review(
            pr=self.pr,
            diff="diff content",
            files=self.files,
            parsed_diff=self.parsed_diff,
        )

        assert result.summary == "Great work!"
        assert result.decision == ReviewAction.APPROVE
        assert result.confidence == 0.95
        assert result.key_issues == []
        assert result.inline_comments == []

    @pytest.mark.asyncio
    async def test_calls_client_with_correct_model(self):
        """Should call client with configured model."""
        self.mock_client.generate_review.return_value = json.dumps({
            "summary": "OK",
            "decision": "COMMENT",
            "confidence": 0.8,
        })

        await self.generator.generate_review(
            pr=self.pr,
            diff="diff",
            files=self.files,
            parsed_diff=self.parsed_diff,
        )

        self.mock_client.generate_review.assert_called_once()
        call_args = self.mock_client.generate_review.call_args
        assert call_args.kwargs["model"] == "test-model"
        assert SYSTEM_PROMPT in call_args.kwargs["system_prompt"]


class TestSystemPrompt:
    """Tests for the system prompt."""

    def test_prompt_requests_json_output(self):
        """System prompt should request JSON output."""
        assert "JSON" in SYSTEM_PROMPT or "json" in SYSTEM_PROMPT

    def test_prompt_defines_schema(self):
        """System prompt should define expected schema fields."""
        assert "summary" in SYSTEM_PROMPT
        assert "decision" in SYSTEM_PROMPT
        assert "confidence" in SYSTEM_PROMPT
        assert "inline_comments" in SYSTEM_PROMPT

    def test_prompt_defines_decision_values(self):
        """System prompt should define valid decision values."""
        assert "APPROVE" in SYSTEM_PROMPT
        assert "REQUEST_CHANGES" in SYSTEM_PROMPT
        assert "COMMENT" in SYSTEM_PROMPT
