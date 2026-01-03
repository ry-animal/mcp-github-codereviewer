"""Tests for the diff parser service."""

import pytest

from mcp_gh_reviewer.services.diff_parser import DiffParser


SAMPLE_DIFF = """\
diff --git a/src/example.py b/src/example.py
index 1234567..abcdefg 100644
--- a/src/example.py
+++ b/src/example.py
@@ -1,5 +1,7 @@
 def hello():
-    print("Hello")
+    print("Hello, World!")
+    return True

 def goodbye():
     print("Goodbye")
+    return False
"""


class TestDiffParser:
    """Tests for DiffParser."""

    def test_parse_simple_diff(self):
        """Test parsing a simple diff."""
        parser = DiffParser()
        parsed = parser.parse(SAMPLE_DIFF)

        assert len(parsed.files) == 1
        file_diff = parsed.files[0]
        assert file_diff.path == "src/example.py"
        assert not file_diff.is_new
        assert not file_diff.is_deleted

    def test_parse_hunks(self):
        """Test that hunks are parsed correctly."""
        parser = DiffParser()
        parsed = parser.parse(SAMPLE_DIFF)

        file_diff = parsed.files[0]
        assert len(file_diff.hunks) == 1

        hunk = file_diff.hunks[0]
        assert hunk.source_start == 1
        assert hunk.target_start == 1

    def test_line_types(self):
        """Test that line types are identified correctly."""
        parser = DiffParser()
        parsed = parser.parse(SAMPLE_DIFF)

        file_diff = parsed.files[0]
        lines = file_diff.hunks[0].lines

        # Count line types
        additions = [l for l in lines if l.line_type == "addition"]
        removals = [l for l in lines if l.line_type == "removal"]
        context = [l for l in lines if l.line_type == "context"]

        assert len(additions) == 3
        assert len(removals) == 1
        assert len(context) == 4

    def test_commentable_lines(self):
        """Test getting commentable lines."""
        parser = DiffParser()
        parsed = parser.parse(SAMPLE_DIFF)

        file_diff = parsed.files[0]
        commentable = file_diff.get_commentable_lines()

        # Commentable lines are additions + context
        assert len(commentable) == 7  # 3 additions + 4 context

    def test_get_file(self):
        """Test getting a file by path."""
        parser = DiffParser()
        parsed = parser.parse(SAMPLE_DIFF)

        file_diff = parsed.get_file("src/example.py")
        assert file_diff is not None
        assert file_diff.path == "src/example.py"

        missing = parsed.get_file("nonexistent.py")
        assert missing is None

    def test_validate_comment_position(self):
        """Test validating comment positions."""
        parser = DiffParser()
        parsed = parser.parse(SAMPLE_DIFF)

        file_diff = parsed.files[0]

        # Line 2 is an addition, should be valid
        assert parser.validate_comment_position(file_diff, 2)

        # Line 100 doesn't exist in diff
        assert not parser.validate_comment_position(file_diff, 100)

    def test_find_nearest_valid_line(self):
        """Test finding the nearest valid line."""
        parser = DiffParser()
        parsed = parser.parse(SAMPLE_DIFF)

        file_diff = parsed.files[0]

        # Request line 100, should find nearest
        nearest = parser.find_nearest_valid_line(file_diff, 100)
        assert nearest is not None
        assert nearest <= 8  # Should be within the diff range
