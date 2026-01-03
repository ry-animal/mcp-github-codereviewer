"""Pydantic models for the MCP GitHub PR Reviewer."""

from mcp_gh_reviewer.models.github import (
    GitHubUser,
    PullRequest,
    PullRequestFile,
    PullRequestHead,
    PullRequestListItem,
)
from mcp_gh_reviewer.models.openrouter import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
)
from mcp_gh_reviewer.models.review import (
    AIReviewResult,
    CommentSide,
    DiffHunk,
    DiffLine,
    FileDiff,
    InlineComment,
    ParsedDiff,
    ReviewAction,
    ReviewResponse,
)

__all__ = [
    # GitHub models
    "GitHubUser",
    "PullRequest",
    "PullRequestFile",
    "PullRequestHead",
    "PullRequestListItem",
    # OpenRouter models
    "ChatCompletionChoice",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatMessage",
    # Review models
    "AIReviewResult",
    "CommentSide",
    "DiffHunk",
    "DiffLine",
    "FileDiff",
    "InlineComment",
    "ParsedDiff",
    "ReviewAction",
    "ReviewResponse",
]
