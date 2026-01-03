"""Tests for GitHub client."""

import pytest

from mcp_gh_reviewer.clients.github_client import GitHubClient


class TestGitHubClientInit:
    """Tests for GitHubClient initialization."""

    def test_github_com_mode_uses_api_github_com(self):
        """github.com mode should use api.github.com base URL."""
        client = GitHubClient(token="test", mode="github.com")
        assert client.base_url == "https://api.github.com"
        assert client.mode == "github.com"

    def test_ghes_mode_uses_hostname_api_v3(self):
        """GHES mode should use hostname/api/v3 base URL."""
        client = GitHubClient(
            hostname="github.mycompany.com",
            token="test",
            mode="ghes",
        )
        assert client.base_url == "https://github.mycompany.com/api/v3"
        assert client.mode == "ghes"

    def test_ghes_mode_requires_hostname(self):
        """GHES mode should raise error if hostname not provided."""
        with pytest.raises(ValueError, match="hostname is required"):
            GitHubClient(token="test", mode="ghes")

    def test_github_com_mode_ignores_hostname(self):
        """github.com mode should ignore hostname parameter."""
        client = GitHubClient(
            hostname="ignored.example.com",
            token="test",
            mode="github.com",
        )
        assert client.base_url == "https://api.github.com"

    def test_token_is_stored(self):
        """Token should be stored for authentication."""
        client = GitHubClient(token="my_token", mode="github.com")
        assert client.token == "my_token"

    def test_token_can_be_none(self):
        """Token can be None for unauthenticated requests."""
        client = GitHubClient(mode="github.com")
        assert client.token is None


class TestGitHubClientHeaders:
    """Tests for GitHubClient header generation."""

    def test_default_headers(self):
        """Default headers should include Accept and API version."""
        client = GitHubClient(token="test", mode="github.com")
        headers = client._headers()

        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert headers["Authorization"] == "Bearer test"

    def test_custom_accept_header(self):
        """Accept header can be customized."""
        client = GitHubClient(token="test", mode="github.com")
        headers = client._headers(accept="application/vnd.github.v3.diff")

        assert headers["Accept"] == "application/vnd.github.v3.diff"

    def test_no_auth_header_without_token(self):
        """No Authorization header if token is None."""
        client = GitHubClient(mode="github.com")
        headers = client._headers()

        assert "Authorization" not in headers


class TestGitHubClientIntegration:
    """Integration tests for GitHubClient (requires real credentials)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_prs_real_repo(self, real_github_token):
        """Test listing PRs from a real public repo."""
        if not real_github_token:
            pytest.skip("No GitHub token available")

        client = GitHubClient(token=real_github_token, mode="github.com")

        # Use a well-known public repo with PRs
        prs = await client.list_pull_requests("octocat", "Hello-World", state="all")

        assert isinstance(prs, list)
        # Hello-World repo might not have PRs, so just check the response format
        # If there are PRs, verify the structure
        if prs:
            assert hasattr(prs[0], "number")
            assert hasattr(prs[0], "title")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_pr_real(self, real_github_token):
        """Test getting a specific PR from a real repo."""
        if not real_github_token:
            pytest.skip("No GitHub token available")

        client = GitHubClient(token=real_github_token, mode="github.com")

        # Use a repo we know has PRs - the fastmcp repo
        try:
            pr = await client.get_pull_request("jlowin", "fastmcp", 1)
            assert pr.number == 1
            assert hasattr(pr, "title")
            assert hasattr(pr, "head")
            assert hasattr(pr, "base")
        except Exception as e:
            # PR might not exist, which is fine
            if "404" in str(e):
                pytest.skip("PR #1 not found in jlowin/fastmcp")
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_pr_diff_real(self, real_github_token):
        """Test getting PR diff from a real repo."""
        if not real_github_token:
            pytest.skip("No GitHub token available")

        client = GitHubClient(token=real_github_token, mode="github.com")

        try:
            diff = await client.get_pull_request_diff("jlowin", "fastmcp", 1)
            assert isinstance(diff, str)
            # Diff should contain diff markers if there are changes
            if diff:
                assert "diff" in diff.lower() or "@@" in diff or len(diff) == 0
        except Exception as e:
            if "404" in str(e):
                pytest.skip("PR #1 not found in jlowin/fastmcp")
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_pr_files_real(self, real_github_token):
        """Test getting PR files from a real repo."""
        if not real_github_token:
            pytest.skip("No GitHub token available")

        client = GitHubClient(token=real_github_token, mode="github.com")

        try:
            files = await client.get_pull_request_files("jlowin", "fastmcp", 1)
            assert isinstance(files, list)
            if files:
                assert hasattr(files[0], "filename")
                assert hasattr(files[0], "status")
                assert hasattr(files[0], "additions")
                assert hasattr(files[0], "deletions")
        except Exception as e:
            if "404" in str(e):
                pytest.skip("PR #1 not found in jlowin/fastmcp")
            raise
