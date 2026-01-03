"""End-to-end integration tests."""

import pytest

from mcp_gh_reviewer.clients.github_client import GitHubClient
from mcp_gh_reviewer.config import settings
from mcp_gh_reviewer.services.diff_parser import DiffParser


class TestEndToEndGitHubCom:
    """End-to-end tests for github.com mode."""

    @pytest.mark.integration
    def test_settings_loaded_correctly(self):
        """Verify settings are loaded from .env."""
        # This test verifies your .env is configured
        assert settings.github_mode in ["github.com", "ghes"]

        if settings.is_github_com:
            assert settings.github_token, "GITHUB_TOKEN must be set for github.com mode"
        else:
            assert settings.ghes_hostname, "GHES_HOSTNAME must be set for ghes mode"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fetch_real_pr_and_parse_diff(self, real_github_token):
        """Test fetching a real PR and parsing its diff."""
        if not real_github_token:
            pytest.skip("No GitHub token available")

        client = GitHubClient(token=real_github_token.value, mode="github.com")
        parser = DiffParser()

        # Find a repo with open PRs - let's try anthropics/anthropic-sdk-python
        # which usually has open PRs
        try:
            prs = await client.list_pull_requests(
                "anthropics", "anthropic-sdk-python", state="open"
            )

            if not prs:
                pytest.skip("No open PRs found")

            # Get the first PR
            pr = prs[0]
            pr_number = pr.number

            # Fetch full PR details
            full_pr = await client.get_pull_request(
                "anthropics", "anthropic-sdk-python", pr_number
            )
            assert full_pr.number == pr_number
            assert full_pr.title

            # Fetch diff
            diff = await client.get_pull_request_diff(
                "anthropics", "anthropic-sdk-python", pr_number
            )
            assert isinstance(diff, str)

            # Parse the diff
            if diff.strip():
                parsed = parser.parse(diff)
                assert parsed.files is not None

                # If there are files, verify structure
                if parsed.files:
                    first_file = parsed.files[0]
                    assert first_file.path
                    assert first_file.hunks is not None

            # Fetch files
            files = await client.get_pull_request_files(
                "anthropics", "anthropic-sdk-python", pr_number
            )
            assert isinstance(files, list)

        except Exception as e:
            if "404" in str(e) or "403" in str(e):
                pytest.skip(f"Could not access repo: {e}")
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_diff_parsing_with_real_diff(self, real_github_token):
        """Test diff parsing with a real GitHub diff."""
        if not real_github_token:
            pytest.skip("No GitHub token available")

        client = GitHubClient(token=real_github_token.value, mode="github.com")
        parser = DiffParser()

        # Use a repo we know has merged PRs with diffs
        try:
            # Get closed/merged PRs which definitely have diffs
            prs = await client.list_pull_requests(
                "fastmcp", "fastmcp", state="closed"
            )

            if not prs:
                # Try another repo
                prs = await client.list_pull_requests(
                    "jlowin", "fastmcp", state="closed"
                )

            if not prs:
                pytest.skip("No closed PRs found")

            # Find a PR with a diff
            for pr in prs[:5]:  # Check first 5
                diff = await client.get_pull_request_diff(
                    "jlowin", "fastmcp", pr.number
                )

                if diff.strip():
                    parsed = parser.parse(diff)

                    if parsed.files:
                        # Found a PR with actual changes
                        file = parsed.files[0]

                        # Verify we can get commentable lines
                        commentable = file.get_commentable_lines()
                        assert isinstance(commentable, dict)

                        # Verify hunks have lines
                        if file.hunks:
                            hunk = file.hunks[0]
                            assert hunk.lines is not None

                        return  # Test passed

            pytest.skip("No PRs with parseable diffs found")

        except Exception as e:
            if "404" in str(e) or "403" in str(e):
                pytest.skip(f"Could not access repo: {e}")
            raise


class TestReviewGeneratorIntegration:
    """Integration tests for the review generator."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_generate_review_with_openrouter(self, real_github_token):
        """Test generating a review using OpenRouter API."""
        if not real_github_token:
            pytest.skip("No GitHub token available")

        if not settings.openrouter_api_key:
            pytest.skip("No OpenRouter API key available")

        from mcp_gh_reviewer.clients.openrouter_client import OpenRouterClient
        from mcp_gh_reviewer.services.review_generator import ReviewGenerator

        client = GitHubClient(token=real_github_token.value, mode="github.com")
        ai_client = OpenRouterClient(settings.openrouter_api_key)
        parser = DiffParser()

        # Get a real PR
        try:
            prs = await client.list_pull_requests(
                "jlowin", "fastmcp", state="closed"
            )

            if not prs:
                pytest.skip("No PRs found")

            # Find a small PR to review (to save API costs)
            for pr_item in prs[:3]:
                files = await client.get_pull_request_files(
                    "jlowin", "fastmcp", pr_item.number
                )

                # Skip large PRs
                total_changes = sum(f.additions + f.deletions for f in files)
                if total_changes > 100:
                    continue

                pr = await client.get_pull_request(
                    "jlowin", "fastmcp", pr_item.number
                )
                diff = await client.get_pull_request_diff(
                    "jlowin", "fastmcp", pr_item.number
                )

                if not diff.strip():
                    continue

                parsed_diff = parser.parse(diff)

                # Generate review
                generator = ReviewGenerator(ai_client, settings.review_model)
                try:
                    result = await generator.generate_review(
                        pr=pr,
                        diff=diff,
                        files=files,
                        parsed_diff=parsed_diff,
                    )
                except Exception as e:
                    if "402" in str(e):
                        pytest.skip("OpenRouter requires payment - insufficient credits")
                    raise

                # Verify result structure
                assert result.summary
                assert result.decision in ["APPROVE", "REQUEST_CHANGES", "COMMENT"]
                assert 0.0 <= result.confidence <= 1.0
                assert isinstance(result.inline_comments, list)
                assert isinstance(result.key_issues, list)

                return  # Test passed

            pytest.skip("No suitable small PRs found")

        except Exception as e:
            if "404" in str(e) or "403" in str(e):
                pytest.skip(f"Could not access repo: {e}")
            if "402" in str(e):
                pytest.skip("OpenRouter requires payment - insufficient credits")
            raise
