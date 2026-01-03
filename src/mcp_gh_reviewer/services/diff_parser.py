"""Service for parsing unified diffs and mapping line numbers."""

from unidiff import PatchSet

from mcp_gh_reviewer.models.review import DiffHunk, DiffLine, FileDiff, ParsedDiff


class DiffParser:
    """Parse unified diffs and map line numbers to diff positions.

    GitHub's API requires either:
    1. Modern approach: `line`, `side` (and optionally `start_line`, `start_side`)
    2. Legacy approach: `position` (deprecated but still works)

    We use the modern approach (line/side) which is more intuitive.
    """

    def parse(self, diff_text: str) -> ParsedDiff:
        """Parse a unified diff into structured data.

        Args:
            diff_text: Raw unified diff string

        Returns:
            ParsedDiff with all files and their hunks
        """
        patch_set = PatchSet(diff_text)
        files = []

        for patched_file in patch_set:
            file_diff = FileDiff(
                path=patched_file.path,
                is_new=patched_file.is_added_file,
                is_deleted=patched_file.is_removed_file,
                is_renamed=patched_file.is_rename,
                old_path=(
                    patched_file.source_file if patched_file.is_rename else None
                ),
            )

            diff_position = 0  # Position counter for legacy API

            for hunk in patched_file:
                parsed_hunk = DiffHunk(
                    source_start=hunk.source_start,
                    source_length=hunk.source_length,
                    target_start=hunk.target_start,
                    target_length=hunk.target_length,
                    section_header=hunk.section_header,
                )

                # Track line numbers as we iterate
                source_line = hunk.source_start
                target_line = hunk.target_start

                for line in hunk:
                    diff_position += 1

                    if line.is_context:
                        line_type = "context"
                        src_no = source_line
                        tgt_no = target_line
                        source_line += 1
                        target_line += 1
                    elif line.is_added:
                        line_type = "addition"
                        src_no = None
                        tgt_no = target_line
                        target_line += 1
                    elif line.is_removed:
                        line_type = "removal"
                        src_no = source_line
                        tgt_no = None
                        source_line += 1
                    else:
                        continue  # Skip unknown line types

                    parsed_hunk.lines.append(
                        DiffLine(
                            line_type=line_type,
                            content=line.value.rstrip("\n"),
                            source_line_no=src_no,
                            target_line_no=tgt_no,
                            diff_position=diff_position,
                        )
                    )

                file_diff.hunks.append(parsed_hunk)

            files.append(file_diff)

        return ParsedDiff(files=files)

    def get_commentable_lines(self, file_diff: FileDiff) -> dict[int, DiffLine]:
        """Get all lines in the new file that can receive comments.

        Returns a mapping of target line number -> DiffLine for lines
        that are additions or context (not removals).

        Args:
            file_diff: Parsed diff for a single file

        Returns:
            Dictionary mapping line numbers to DiffLine objects
        """
        commentable: dict[int, DiffLine] = {}
        for hunk in file_diff.hunks:
            for line in hunk.lines:
                if line.target_line_no is not None:
                    commentable[line.target_line_no] = line
        return commentable

    def validate_comment_position(
        self,
        file_diff: FileDiff,
        line: int,
    ) -> bool:
        """Check if a line number is valid for commenting.

        Args:
            file_diff: Parsed diff for a single file
            line: Line number to validate

        Returns:
            True if the line can receive comments
        """
        commentable = self.get_commentable_lines(file_diff)
        return line in commentable

    def find_nearest_valid_line(
        self,
        file_diff: FileDiff,
        target_line: int,
    ) -> int | None:
        """Find the nearest valid line to comment on.

        Args:
            file_diff: Parsed diff for a single file
            target_line: Desired line number

        Returns:
            Nearest valid line number, or None if no valid lines exist
        """
        commentable = self.get_commentable_lines(file_diff)
        if not commentable:
            return None

        valid_lines = sorted(commentable.keys())
        return min(valid_lines, key=lambda x: abs(x - target_line))
