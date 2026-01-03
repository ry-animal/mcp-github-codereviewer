"""Pydantic models for OpenRouter API."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """OpenRouter chat message."""

    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenRouter chat completion request."""

    model: str = Field(default="anthropic/claude-sonnet-4")
    messages: list[ChatMessage]
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=4096)


class ChatCompletionChoice(BaseModel):
    """A single completion choice."""

    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """OpenRouter chat completion response."""

    id: str
    choices: list[ChatCompletionChoice]
    model: str
    usage: Optional[dict] = None
