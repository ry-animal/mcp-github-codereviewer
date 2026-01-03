"""Tests for OpenRouter client."""

import pytest

from mcp_gh_reviewer.clients.openrouter_client import OpenRouterClient
from mcp_gh_reviewer.models.openrouter import ChatMessage


class TestOpenRouterClientInit:
    """Tests for OpenRouterClient initialization."""

    def test_stores_api_key(self):
        """Client should store the API key."""
        client = OpenRouterClient(api_key="sk-or-test")
        assert client.api_key == "sk-or-test"

    def test_default_site_url(self):
        """Client should have a default site URL."""
        client = OpenRouterClient(api_key="test")
        assert client.site_url == "https://github.com/mcp-gh-reviewer"

    def test_default_site_name(self):
        """Client should have a default site name."""
        client = OpenRouterClient(api_key="test")
        assert client.site_name == "MCP GitHub Reviewer"

    def test_custom_site_url(self):
        """Client should accept custom site URL."""
        client = OpenRouterClient(
            api_key="test",
            site_url="https://myapp.example.com",
        )
        assert client.site_url == "https://myapp.example.com"

    def test_custom_site_name(self):
        """Client should accept custom site name."""
        client = OpenRouterClient(
            api_key="test",
            site_name="My Custom App",
        )
        assert client.site_name == "My Custom App"

    def test_base_url_constant(self):
        """Client should have correct base URL constant."""
        assert OpenRouterClient.BASE_URL == "https://openrouter.ai/api/v1"


class TestChatMessage:
    """Tests for ChatMessage model."""

    def test_system_message(self):
        """ChatMessage should support system role."""
        msg = ChatMessage(role="system", content="You are helpful.")
        assert msg.role == "system"
        assert msg.content == "You are helpful."

    def test_user_message(self):
        """ChatMessage should support user role."""
        msg = ChatMessage(role="user", content="Hello!")
        assert msg.role == "user"
        assert msg.content == "Hello!"

    def test_assistant_message(self):
        """ChatMessage should support assistant role."""
        msg = ChatMessage(role="assistant", content="Hi there!")
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"

    def test_message_serialization(self):
        """ChatMessage should serialize to dict correctly."""
        msg = ChatMessage(role="user", content="Test")
        data = msg.model_dump()
        assert data == {"role": "user", "content": "Test"}


class TestOpenRouterClientIntegration:
    """Integration tests for OpenRouterClient (requires real API key)."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_chat_completion_real(self, real_openrouter_key):
        """Test real chat completion with OpenRouter."""
        if not real_openrouter_key:
            pytest.skip("No OpenRouter API key available")

        client = OpenRouterClient(api_key=real_openrouter_key.value)

        messages = [
            ChatMessage(role="user", content="Say 'hello' and nothing else."),
        ]

        try:
            response = await client.chat_completion(
                messages=messages,
                model="anthropic/claude-sonnet-4",
                max_tokens=50,
            )

            assert response.choices
            assert len(response.choices) > 0
            assert response.choices[0].message.content
            assert "hello" in response.choices[0].message.content.lower()

        except Exception as e:
            if "402" in str(e):
                pytest.skip("OpenRouter requires payment - insufficient credits")
            raise

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_generate_review_real(self, real_openrouter_key):
        """Test generate_review method with real API."""
        if not real_openrouter_key:
            pytest.skip("No OpenRouter API key available")

        client = OpenRouterClient(api_key=real_openrouter_key.value)

        try:
            response = await client.generate_review(
                system_prompt="You are a helpful assistant.",
                user_prompt="Say 'test passed' and nothing else.",
                model="anthropic/claude-sonnet-4",
            )

            assert isinstance(response, str)
            assert len(response) > 0

        except Exception as e:
            if "402" in str(e):
                pytest.skip("OpenRouter requires payment - insufficient credits")
            raise
