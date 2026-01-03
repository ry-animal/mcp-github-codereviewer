"""Client for OpenRouter API."""

from typing import Optional

import httpx

from mcp_gh_reviewer.models.openrouter import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
)


class OpenRouterClient:
    """Client for OpenRouter API."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        site_url: Optional[str] = None,
        site_name: Optional[str] = None,
    ):
        """Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key
            site_url: URL for HTTP-Referer header (for rankings)
            site_name: App name for X-Title header
        """
        self.api_key = api_key
        self.site_url = site_url or "https://github.com/mcp-gh-reviewer"
        self.site_name = site_name or "MCP GitHub Reviewer"

    async def chat_completion(
        self,
        messages: list[ChatMessage],
        model: str = "anthropic/claude-sonnet-4",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> ChatCompletionResponse:
        """Send a chat completion request to OpenRouter.

        Args:
            messages: List of chat messages
            model: Model identifier (e.g., "anthropic/claude-sonnet-4")
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Chat completion response with generated content
        """
        request = ChatCompletionRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name,
                    "Content-Type": "application/json",
                },
                json=request.model_dump(),
                timeout=120.0,
            )
            response.raise_for_status()
            return ChatCompletionResponse.model_validate(response.json())

    async def generate_review(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "anthropic/claude-sonnet-4",
    ) -> str:
        """Generate a review response.

        Args:
            system_prompt: System instructions for the AI
            user_prompt: User message with PR context
            model: Model identifier

        Returns:
            Generated review content as a string
        """
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]
        response = await self.chat_completion(messages, model=model)
        return response.choices[0].message.content
