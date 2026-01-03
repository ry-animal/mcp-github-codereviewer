"""Tests for GitHub data providers."""

import pytest

from mcp_gh_reviewer.providers.base import GitHubDataProvider
from mcp_gh_reviewer.providers.github_mcp import GitHubMCPProvider


class TestGitHubDataProvider:
    """Tests for the abstract GitHubDataProvider interface."""

    def test_is_abstract_class(self):
        """GitHubDataProvider should be abstract and not instantiable."""
        with pytest.raises(TypeError):
            GitHubDataProvider()

    def test_defines_required_methods(self):
        """GitHubDataProvider should define all required abstract methods."""
        # Check that the abstract methods exist
        assert hasattr(GitHubDataProvider, "list_prs")
        assert hasattr(GitHubDataProvider, "get_pr")
        assert hasattr(GitHubDataProvider, "get_pr_diff")
        assert hasattr(GitHubDataProvider, "get_pr_files")
        assert hasattr(GitHubDataProvider, "create_review")


class TestGitHubMCPProvider:
    """Tests for GitHubMCPProvider."""

    def test_init_stores_token(self):
        """Provider should store the GitHub token."""
        provider = GitHubMCPProvider(github_token="ghp_test123")
        assert provider.token == "ghp_test123"

    def test_init_creates_api_client(self):
        """Provider should create an internal API client."""
        provider = GitHubMCPProvider(github_token="ghp_test123")
        assert provider._api_client is not None
        assert provider._api_client.mode == "github.com"
        assert provider._api_client.token == "ghp_test123"

    def test_implements_github_data_provider(self):
        """GitHubMCPProvider should implement GitHubDataProvider interface."""
        provider = GitHubMCPProvider(github_token="test")
        assert isinstance(provider, GitHubDataProvider)

    def test_mcp_client_initially_none(self):
        """MCP client should be None until first use."""
        provider = GitHubMCPProvider(github_token="test")
        assert provider._client is None


class TestGitHubMCPProviderIntegration:
    """Integration tests for GitHubMCPProvider."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_prs_real(self, real_github_token):
        """Test listing PRs via provider."""
        if not real_github_token:
            pytest.skip("No GitHub token available")

        provider = GitHubMCPProvider(github_token=real_github_token.value)
        prs = await provider.list_prs("octocat", "Hello-World", state="all")

        assert isinstance(prs, list)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_pr_real(self, real_github_token):
        """Test getting a PR via provider."""
        if not real_github_token:
            pytest.skip("No GitHub token available")

        provider = GitHubMCPProvider(github_token=real_github_token.value)

        try:
            pr = await provider.get_pr("jlowin", "fastmcp", 1)
            assert pr.number == 1
        except Exception as e:
            if "404" in str(e):
                pytest.skip("PR #1 not found")
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_pr_diff_real(self, real_github_token):
        """Test getting PR diff via provider."""
        if not real_github_token:
            pytest.skip("No GitHub token available")

        provider = GitHubMCPProvider(github_token=real_github_token.value)

        try:
            diff = await provider.get_pr_diff("jlowin", "fastmcp", 1)
            assert isinstance(diff, str)
        except Exception as e:
            if "404" in str(e):
                pytest.skip("PR #1 not found")
            raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_pr_files_real(self, real_github_token):
        """Test getting PR files via provider."""
        if not real_github_token:
            pytest.skip("No GitHub token available")

        provider = GitHubMCPProvider(github_token=real_github_token.value)

        try:
            files = await provider.get_pr_files("jlowin", "fastmcp", 1)
            assert isinstance(files, list)
        except Exception as e:
            if "404" in str(e):
                pytest.skip("PR #1 not found")
            raise
