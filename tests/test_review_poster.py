"""Tests for review poster service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_gh_reviewer.models.review import (
    AIReviewResult,
    CommentSide,
    InlineComment,
    ParsedDiff,
    ReviewAction,
    ReviewResponse,
)
from mcp_gh_reviewer.services.review_poster import ReviewPoster


class TestReviewPosterInit:
    """Tests for ReviewPoster initialization."""

    def test_stores_client(self):
        """Poster should store the GitHub client."""
        mock_client = MagicMock()
        parsed_diff = ParsedDiff(files=[])
        poster = ReviewPoster(client=mock_client, parsed_diff=parsed_diff)
        assert poster.client == mock_client

    def test_stores_parsed_diff(self):
        """Poster should store the parsed diff."""
        mock_client = MagicMock()
        parsed_diff = ParsedDiff(files=[])
        poster = ReviewPoster(client=mock_client, parsed_diff=parsed_diff)
        assert poster.parsed_diff == parsed_diff


class TestFormatComments:
    """Tests for comment formatting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.parsed_diff = ParsedDiff(files=[])
        self.poster = ReviewPoster(client=self.mock_client, parsed_diff=self.parsed_diff)

    def test_format_single_comment(self):
        """Should format a single inline comment."""
        result = AIReviewResult(
            summary="Test",
            decision=ReviewAction.COMMENT,
            confidence=0.8,
            inline_comments=[
                InlineComment(
                    path="src/main.py",
                    body="Consider refactoring this",
                    line=42,
                    side=CommentSide.RIGHT,
                )
            ],
        )

        comments = self.poster._format_comments(result)

        assert len(comments) == 1
        assert comments[0]["path"] == "src/main.py"
        assert comments[0]["body"] == "Consider refactoring this"
        assert comments[0]["line"] == 42
        assert comments[0]["side"] == "RIGHT"

    def test_format_multiple_comments(self):
        """Should format multiple inline comments."""
        result = AIReviewResult(
            summary="Test",
            decision=ReviewAction.REQUEST_CHANGES,
            confidence=0.9,
            inline_comments=[
                InlineComment(path="file1.py", body="Fix this", line=10, side=CommentSide.RIGHT),
                InlineComment(path="file2.py", body="Fix that", line=20, side=CommentSide.LEFT),
            ],
        )

        comments = self.poster._format_comments(result)

        assert len(comments) == 2
        assert comments[0]["path"] == "file1.py"
        assert comments[0]["side"] == "RIGHT"
        assert comments[1]["path"] == "file2.py"
        assert comments[1]["side"] == "LEFT"

    def test_format_multiline_comment(self):
        """Should format multiline comment with start_line."""
        result = AIReviewResult(
            summary="Test",
            decision=ReviewAction.COMMENT,
            confidence=0.8,
            inline_comments=[
                InlineComment(
                    path="src/main.py",
                    body="This whole block needs work",
                    line=50,
                    side=CommentSide.RIGHT,
                    start_line=40,
                    start_side=CommentSide.RIGHT,
                )
            ],
        )

        comments = self.poster._format_comments(result)

        assert len(comments) == 1
        assert comments[0]["line"] == 50
        assert comments[0]["start_line"] == 40
        assert comments[0]["start_side"] == "RIGHT"

    def test_format_empty_comments(self):
        """Should return empty list when no comments."""
        result = AIReviewResult(
            summary="LGTM",
            decision=ReviewAction.APPROVE,
            confidence=0.95,
            inline_comments=[],
        )

        comments = self.poster._format_comments(result)

        assert comments == []


class TestFormatReviewBody:
    """Tests for review body formatting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.parsed_diff = ParsedDiff(files=[])
        self.poster = ReviewPoster(client=self.mock_client, parsed_diff=self.parsed_diff)

    def test_includes_summary(self):
        """Body should include the summary."""
        result = AIReviewResult(
            summary="This PR looks good overall.",
            decision=ReviewAction.APPROVE,
            confidence=0.9,
        )

        body = self.poster._format_review_body(result)

        assert "This PR looks good overall." in body

    def test_includes_key_issues(self):
        """Body should include key issues when present."""
        result = AIReviewResult(
            summary="Some issues found.",
            decision=ReviewAction.REQUEST_CHANGES,
            confidence=0.8,
            key_issues=["Missing error handling", "No tests for edge cases"],
        )

        body = self.poster._format_review_body(result)

        assert "Key Issues" in body
        assert "Missing error handling" in body
        assert "No tests for edge cases" in body

    def test_excludes_key_issues_when_empty(self):
        """Body should not include key issues section when empty."""
        result = AIReviewResult(
            summary="LGTM",
            decision=ReviewAction.APPROVE,
            confidence=0.95,
            key_issues=[],
        )

        body = self.poster._format_review_body(result)

        assert "Key Issues" not in body

    def test_includes_confidence(self):
        """Body should include confidence percentage."""
        result = AIReviewResult(
            summary="Test",
            decision=ReviewAction.COMMENT,
            confidence=0.87,
        )

        body = self.poster._format_review_body(result)

        assert "87%" in body

    def test_includes_ai_review_marker(self):
        """Body should include AI review marker."""
        result = AIReviewResult(
            summary="Test",
            decision=ReviewAction.COMMENT,
            confidence=0.8,
        )

        body = self.poster._format_review_body(result)

        assert "AI Review" in body


class TestPostReview:
    """Tests for the post_review method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.parsed_diff = ParsedDiff(files=[])
        self.poster = ReviewPoster(client=self.mock_client, parsed_diff=self.parsed_diff)

    @pytest.mark.asyncio
    async def test_calls_client_create_review(self):
        """Should call client.create_review with correct params."""
        self.mock_client.create_review.return_value = ReviewResponse(
            id=123,
            html_url="https://github.com/owner/repo/pull/1#pullrequestreview-123",
            state="APPROVED",
        )

        result = AIReviewResult(
            summary="LGTM",
            decision=ReviewAction.APPROVE,
            confidence=0.95,
        )

        await self.poster.post_review(
            owner="testowner",
            repo="testrepo",
            pr_number=1,
            result=result,
            commit_id="abc123",
        )

        self.mock_client.create_review.assert_called_once()
        call_args = self.mock_client.create_review.call_args
        assert call_args.kwargs["owner"] == "testowner"
        assert call_args.kwargs["repo"] == "testrepo"
        assert call_args.kwargs["pr_number"] == 1
        assert call_args.kwargs["commit_id"] == "abc123"
        assert call_args.kwargs["event"] == "APPROVE"

    @pytest.mark.asyncio
    async def test_returns_review_response(self):
        """Should return ReviewResponse from client."""
        expected_response = ReviewResponse(
            id=456,
            html_url="https://github.com/owner/repo/pull/1#pullrequestreview-456",
            state="CHANGES_REQUESTED",
        )
        self.mock_client.create_review.return_value = expected_response

        result = AIReviewResult(
            summary="Needs work",
            decision=ReviewAction.REQUEST_CHANGES,
            confidence=0.85,
        )

        response = await self.poster.post_review(
            owner="owner",
            repo="repo",
            pr_number=1,
            result=result,
            commit_id="def456",
        )

        assert response.id == 456
        assert response.state == "CHANGES_REQUESTED"

    @pytest.mark.asyncio
    async def test_passes_formatted_comments(self):
        """Should pass formatted comments to client."""
        self.mock_client.create_review.return_value = ReviewResponse(
            id=1, html_url="", state="COMMENTED"
        )

        result = AIReviewResult(
            summary="Review",
            decision=ReviewAction.COMMENT,
            confidence=0.8,
            inline_comments=[
                InlineComment(path="test.py", body="Note", line=5, side=CommentSide.RIGHT),
            ],
        )

        await self.poster.post_review(
            owner="owner",
            repo="repo",
            pr_number=1,
            result=result,
            commit_id="sha123",
        )

        call_args = self.mock_client.create_review.call_args
        comments = call_args.kwargs["comments"]
        assert len(comments) == 1
        assert comments[0]["path"] == "test.py"
        assert comments[0]["line"] == 5

    @pytest.mark.asyncio
    async def test_passes_formatted_body(self):
        """Should pass formatted body to client."""
        self.mock_client.create_review.return_value = ReviewResponse(
            id=1, html_url="", state="APPROVED"
        )

        result = AIReviewResult(
            summary="Great work!",
            decision=ReviewAction.APPROVE,
            confidence=0.95,
            key_issues=["Minor typo"],
        )

        await self.poster.post_review(
            owner="owner",
            repo="repo",
            pr_number=1,
            result=result,
            commit_id="sha",
        )

        call_args = self.mock_client.create_review.call_args
        body = call_args.kwargs["body"]
        assert "Great work!" in body
        assert "Minor typo" in body
        assert "95%" in body
