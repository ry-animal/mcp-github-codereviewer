# Use Python 3.13 slim image
FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY README.md ./

# Install dependencies
RUN uv sync --frozen

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"

# Docker MCP Toolkit metadata label
# This allows the image to be used with `docker mcp gateway run --servers docker://mcp-gh-reviewer:latest`
LABEL io.docker.server.metadata='{ \
  "name": "mcp-gh-reviewer", \
  "description": "AI-powered GitHub PR code review tool. Review PRs, list open PRs, and post reviews with inline comments.", \
  "command": ["uv", "run", "mcp-gh-reviewer"], \
  "env": [ \
    {"name": "GITHUB_MODE", "value": "{{mcp-gh-reviewer.github-mode}}"}, \
    {"name": "REVIEW_MODEL", "value": "{{mcp-gh-reviewer.review-model}}"} \
  ], \
  "secrets": [ \
    {"name": "mcp-gh-reviewer.GITHUB_TOKEN", "env": "GITHUB_TOKEN"}, \
    {"name": "mcp-gh-reviewer.OPENROUTER_API_KEY", "env": "OPENROUTER_API_KEY"} \
  ], \
  "config": [{ \
    "name": "mcp-gh-reviewer", \
    "type": "object", \
    "properties": { \
      "github-mode": {"type": "string", "default": "github.com", "description": "GitHub mode: github.com or ghes"}, \
      "review-model": {"type": "string", "default": "anthropic/claude-sonnet-4", "description": "OpenRouter model for reviews"} \
    } \
  }] \
}'

# No ENTRYPOINT - allows Docker MCP Toolkit to pass its own command
# For CLI usage: docker run --rm --env-file .env mcp-gh-reviewer:latest uv run gh-review <url>
# For MCP usage: Docker MCP Toolkit uses the command from the label
CMD ["uv", "run", "gh-review", "--help"]
