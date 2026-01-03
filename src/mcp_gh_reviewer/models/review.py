"""Pydantic models for code review operations."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ReviewAction(str, Enum):
    """GitHub review action types."""

    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"


class CommentSide(str, Enum):
    """Which side of the diff the comment applies to."""

    LEFT = "LEFT"  # Deletions (old code)
    RIGHT = "RIGHT"  # Additions (new code)


class InlineComment(BaseModel):
    """A review comment on a specific line."""

    path: str = Field(..., description="Relative file path")
    body: str = Field(..., description="Comment text (markdown supported)")
    line: int = Field(..., description="Line number in the new file")
    side: CommentSide = Field(default=CommentSide.RIGHT, description="Side of diff")
    start_line: Optional[int] = Field(
        None, description="Start line for multi-line comments"
    )
    start_side: Optional[CommentSide] = Field(None, description="Side for start_line")


class ReviewResponse(BaseModel):
    """Response from creating a review."""

    id: int
    html_url: str
    state: str
    body: Optional[str] = None
    submitted_at: Optional[str] = None


class AIReviewResult(BaseModel):
    """Result from AI review generation."""

    summary: str = Field(..., description="Overall review summary")
    decision: ReviewAction = Field(..., description="Recommended action")
    inline_comments: list[InlineComment] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the review")
    key_issues: list[str] = Field(default_factory=list, description="Top issues found")


class DiffLine(BaseModel):
    """A single line in a diff hunk."""

    line_type: Literal["context", "addition", "removal"]
    content: str
    source_line_no: Optional[int] = None  # Line in old file
    target_line_no: Optional[int] = None  # Line in new file
    diff_position: int  # Position in diff (for legacy API)


class DiffHunk(BaseModel):
    """A hunk from a unified diff."""

    source_start: int
    source_length: int
    target_start: int
    target_length: int
    section_header: Optional[str] = None
    lines: list[DiffLine] = Field(default_factory=list)


class FileDiff(BaseModel):
    """Parsed diff for a single file."""

    path: str
    is_new: bool = False
    is_deleted: bool = False
    is_renamed: bool = False
    old_path: Optional[str] = None
    hunks: list[DiffHunk] = Field(default_factory=list)

    def get_target_line_position(self, target_line: int) -> Optional[int]:
        """Map a target file line number to diff position."""
        for hunk in self.hunks:
            for line in hunk.lines:
                if line.target_line_no == target_line:
                    return line.diff_position
        return None

    def get_commentable_lines(self) -> dict[int, DiffLine]:
        """Get all lines that can receive comments (additions and context)."""
        commentable: dict[int, DiffLine] = {}
        for hunk in self.hunks:
            for line in hunk.lines:
                if line.target_line_no is not None:
                    commentable[line.target_line_no] = line
        return commentable


class ParsedDiff(BaseModel):
    """Complete parsed diff for a PR."""

    files: list[FileDiff] = Field(default_factory=list)

    def get_file(self, path: str) -> Optional[FileDiff]:
        """Get diff for a specific file."""
        for f in self.files:
            if f.path == path:
                return f
        return None
