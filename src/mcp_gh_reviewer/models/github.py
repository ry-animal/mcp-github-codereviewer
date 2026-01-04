"""Pydantic models for GitHub API responses."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class GitHubUserBasic(BaseModel):
    """Minimal GitHub user (for list responses to avoid MCP secret detection)."""

    login: str


class GitHubUser(GitHubUserBasic):
    """GitHub user representation."""

    id: int
    avatar_url: Optional[str] = None
    html_url: Optional[str] = None


class PullRequestHeadBasic(BaseModel):
    """PR head/base branch info without SHA (for list responses)."""

    ref: str
    label: str


class PullRequestHead(PullRequestHeadBasic):
    """PR head/base branch info with SHA."""

    sha: str


class PullRequestFile(BaseModel):
    """File changed in a PR (excludes SHA to avoid MCP secret detection)."""

    filename: str
    status: Literal[
        "added", "removed", "modified", "renamed", "copied", "changed", "unchanged"
    ]
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None
    previous_filename: Optional[str] = None


class PullRequest(BaseModel):
    """Pull request details."""

    number: int
    title: str
    body: Optional[str] = None
    state: Literal["open", "closed"]
    html_url: str
    user: GitHubUser
    head: PullRequestHead
    base: PullRequestHead
    created_at: datetime
    updated_at: datetime
    draft: bool = False
    mergeable: Optional[bool] = None
    additions: Optional[int] = None
    deletions: Optional[int] = None
    changed_files: Optional[int] = None


class PullRequestListItem(BaseModel):
    """Lightweight PR for listing (excludes SHA/URLs to avoid MCP secret detection)."""

    number: int
    title: str
    state: Literal["open", "closed"]
    user: GitHubUserBasic
    head: PullRequestHeadBasic
    base: PullRequestHeadBasic
    created_at: datetime
    draft: bool = False
