"""Pydantic models for GitHub API responses."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """GitHub user representation."""

    login: str
    id: int
    avatar_url: Optional[str] = None
    html_url: Optional[str] = None


class PullRequestHead(BaseModel):
    """PR head/base branch info."""

    ref: str
    sha: str
    label: str


class PullRequestFile(BaseModel):
    """File changed in a PR."""

    sha: str
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
    """Lightweight PR for listing."""

    number: int
    title: str
    state: Literal["open", "closed"]
    user: GitHubUser
    head: PullRequestHead
    base: PullRequestHead
    created_at: datetime
    draft: bool = False
