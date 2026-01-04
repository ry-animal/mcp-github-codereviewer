# mcp-gh-reviewer

AI-powered GitHub PR code review tool with CLI and MCP server modes. Uses Claude via OpenRouter to generate intelligent, actionable code reviews with inline comments.

## Features

- **AI-Powered Reviews**: Generates detailed code reviews using Claude models via OpenRouter
- **Inline Comments**: Posts contextual comments directly on changed lines with code suggestions
- **Pre-Commit Hook**: Review staged changes before every commit (advisory mode)
- **Dual Mode Operation**:
  - **CLI** (`gh-review`): Standalone command-line tool for quick reviews
  - **MCP Server** (`mcp-gh-reviewer`): FastMCP server for Claude Desktop integration
- **Multi-Platform GitHub Support**: Works with both github.com and GitHub Enterprise Server (GHES)
- **Focus Areas**: Target specific aspects like security, performance, or best practices
- **Docker Support**: Full containerization with Docker MCP Toolkit compatibility

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- GitHub Personal Access Token (PAT) with `repo` scope
- [OpenRouter API key](https://openrouter.ai/)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/mcp-gh-reviewer.git
cd mcp-gh-reviewer

# Install dependencies
uv sync

# Copy and configure environment
cp .env.example .env
# Edit .env with your tokens
git clone https://github.com/ry-animal/mcp-github-codereviewer.git
cd mcp-github-codereviewer

### Basic Usage

```bash
# Review a PR (preview only - doesn't post to GitHub)
uv run gh-review https://github.com/owner/repo/pull/123

# Review and post comments to GitHub
uv run gh-review https://github.com/owner/repo/pull/123 --post

# List open PRs for a repository
uv run gh-review --list owner/repo

# Review with specific focus areas
uv run gh-review https://github.com/owner/repo/pull/123 --focus security --focus performance
```

## Configuration

Create a `.env` file in the project root:

```bash
# GitHub Mode: "github.com" or "ghes"
GITHUB_MODE=github.com

# For github.com (PAT authentication)
# Create at https://github.com/settings/tokens with 'repo' scope
GITHUB_TOKEN=ghp_your_personal_access_token

# For GitHub Enterprise Server (OAuth authentication)
# Only needed if GITHUB_MODE=ghes
GHES_HOSTNAME=github.mycompany.com
GITHUB_CLIENT_ID=your_oauth_app_client_id
GITHUB_CLIENT_SECRET=your_oauth_app_client_secret

# OpenRouter (required for AI reviews)
OPENROUTER_API_KEY=sk-or-v1-your-api-key
REVIEW_MODEL=anthropic/claude-sonnet-4

# MCP Server (optional, for server mode)
MCP_SERVER_PORT=8000
MCP_SERVER_BASE_URL=http://localhost:8000
```

### Available Models

Any model available on [OpenRouter](https://openrouter.ai/models) can be used. Recommended:

- `anthropic/claude-sonnet-4` (default, best balance of speed/quality)
- `anthropic/claude-opus-4` (highest quality)
- `anthropic/claude-3.5-sonnet` (fast, cost-effective)

## Pre-Commit Hook

Review staged changes with AI before every commit. The hook runs in advisory mode - it shows the review and lets you decide whether to proceed.

### Installation

```bash
# Install the pre-commit hook
uv run install-review-hook

# Uninstall
uv run install-review-hook --uninstall
```

### How It Works

```
git commit
    │
    ▼
┌─────────────────────────────────────┐
│  1. Get staged diff                 │
│  2. AI reviews changes              │
│  3. Display results with issues     │
│  4. Prompt: "Proceed? [y/N]"        │
└─────────────────────────────────────┘
    │
    ├── y → commit proceeds
    └── N → commit aborted
```

### Example Output

```
Reviewing staged changes...
Found 2 files with +45/-12 lines

──────────────────────────────────────────────────
Review Summary
──────────────────────────────────────────────────
Decision: COMMENT (confidence: 85%)

Changes add input validation to the user handler.

Key Issues
──────────────────────────────────────────────────
  * Consider adding error handling for edge cases

Inline Comments (1)
──────────────────────────────────────────────────
src/handlers/user.py:45
  Consider adding a try/catch here:

  ```python
  try:
      user = get_user(user_id)
  except UserNotFoundError:
      return None
  ```

──────────────────────────────────────────────────

Proceed with commit? [y/N]:
```

### Manual Review

Run the review without committing:

```bash
uv run review-staged
```

### Skipping the Hook

```bash
git commit --no-verify
```

## CLI Usage

The `gh-review` command provides a full-featured CLI for reviewing pull requests.

```bash
# Basic review (outputs to terminal)
uv run gh-review https://github.com/owner/repo/pull/123

# Post review to GitHub
uv run gh-review https://github.com/owner/repo/pull/123 --post

# Alternative syntax using owner/repo#number
uv run gh-review owner/repo 123 --post

# List open PRs
uv run gh-review --list owner/repo

# Focus on specific areas
uv run gh-review https://github.com/owner/repo/pull/123 \
  --focus security \
  --focus performance \
  --focus "error handling"
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--post` | Post the review to GitHub (default: preview only) |
| `--list REPO` | List open PRs for owner/repo |
| `--focus AREA` | Focus review on specific areas (can be repeated) |

## MCP Server Mode

Run as an MCP server for integration with Claude Desktop or other MCP clients.

### Starting the Server

```bash
# Start MCP server (stdio transport, default)
uv run mcp-gh-reviewer

# Or explicitly run the module
uv run python -m mcp_gh_reviewer.server
```

### MCP Tools

The server exposes these tools:

| Tool | Description |
|------|-------------|
| `list_prs` | List open pull requests for a repository |
| `get_pr` | Get details of a specific pull request |
| `get_pr_diff` | Get the unified diff for a pull request |
| `get_pr_files` | Get list of files changed in a pull request |
| `review_pr` | Generate an AI-powered code review (optionally post to GitHub) |

### Claude Desktop Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "gh-reviewer": {
      "command": "uv",
      "args": ["run", "mcp-gh-reviewer"],
      "cwd": "/path/to/mcp-gh-reviewer",
      "env": {
        "GITHUB_MODE": "github.com",
        "GITHUB_TOKEN": "ghp_your_token",
        "OPENROUTER_API_KEY": "sk-or-v1-your_key",
        "REVIEW_MODEL": "anthropic/claude-sonnet-4"
      }
    }
  }
}
```

## Docker Usage

### Building the Image

```bash
docker build -t mcp-gh-reviewer:latest .
```

### Running with Docker

#### Using docker run

```bash
# Review a PR (preview only)
docker run --rm --env-file .env mcp-gh-reviewer:latest \
  uv run gh-review https://github.com/owner/repo/pull/123

# Review and post to GitHub
docker run --rm --env-file .env mcp-gh-reviewer:latest \
  uv run gh-review https://github.com/owner/repo/pull/123 --post

# List PRs
docker run --rm --env-file .env mcp-gh-reviewer:latest \
  uv run gh-review --list owner/repo

# With focus areas
docker run --rm --env-file .env mcp-gh-reviewer:latest \
  uv run gh-review https://github.com/owner/repo/pull/123 --focus security --focus performance
```

#### Using the Wrapper Script

```bash
# Make it executable (first time only)
chmod +x gh-review-docker.sh

# Use it like the regular CLI
./gh-review-docker.sh https://github.com/owner/repo/pull/123
./gh-review-docker.sh https://github.com/owner/repo/pull/123 --post
./gh-review-docker.sh --list owner/repo
```

#### Using docker-compose

```bash
# Review a PR
docker-compose run --rm gh-review https://github.com/owner/repo/pull/123

# Post review
docker-compose run --rm gh-review https://github.com/owner/repo/pull/123 --post

# List PRs
docker-compose run --rm gh-review --list owner/repo
```

### Running MCP Server in Docker

```bash
# Run as HTTP MCP server
docker run --rm -p 8000:8000 --env-file .env -e MCP_TRANSPORT=http \
  mcp-gh-reviewer:latest uv run mcp-gh-reviewer
```

Access the MCP server at `http://localhost:8000`

> **Note**: The server defaults to stdio transport for Docker MCP Toolkit compatibility.
> Set `MCP_TRANSPORT=http` to run as an HTTP server.

### Docker MCP Toolkit Integration

Compatible with [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/) (requires Docker Desktop 4.48+).

#### Quick Start

```bash
# Build the image
docker build -t mcp-gh-reviewer:latest .

# Run with Docker MCP Gateway
docker mcp gateway run --servers docker://mcp-gh-reviewer:latest
```

#### Configuration

The MCP Toolkit will prompt you to configure:

1. **Secrets** (configured in Docker Desktop MCP Toolkit UI):
   - `GITHUB_TOKEN` - Your GitHub Personal Access Token
   - `OPENROUTER_API_KEY` - Your OpenRouter API key

2. **Settings** (optional, have defaults):
   - `github-mode` - Either `github.com` (default) or `ghes` for GitHub Enterprise Server
   - `review-model` - OpenRouter model ID (default: `anthropic/claude-sonnet-4`)

#### Connecting to Clients

```bash
# Connect to Claude Desktop
docker mcp client connect claude-desktop

# Or connect to other supported clients
docker mcp client connect cursor
docker mcp client connect vscode
```

### Creating a Shell Alias

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
alias gh-review-docker='/path/to/mcp-gh-reviewer/gh-review-docker.sh'
```

Then use it from anywhere:

```bash
gh-review-docker https://github.com/owner/repo/pull/123 --post
```

## Architecture

```
src/mcp_gh_reviewer/
├── auth/           # OAuth providers for GHES
├── clients/        # External API wrappers (GitHub, OpenRouter)
├── models/         # Pydantic data models
├── providers/      # Abstract data provider interface
├── services/       # Business logic (diff parsing, review generation, posting)
│   └── staged_reviewer.py  # Staged changes review service
├── cli.py          # CLI entry point
├── server.py       # MCP server entry point
├── pre_commit.py   # Pre-commit hook entry point
├── install_hook.py # Hook installer/uninstaller
└── config.py       # Centralized configuration
```

### Review Pipeline

```
GitHubClient → DiffParser → ReviewGenerator → ReviewPoster → GitHubClient
```

1. **Data Fetching**: Retrieves PR metadata, unified diff, and file stats from GitHub
2. **Diff Parsing**: Parses unified diffs into structured data with line mappings
3. **AI Review**: Generates review using Claude via OpenRouter with actionable inline comments
4. **Review Posting**: Validates comments against diff and posts to GitHub

### Authentication Modes

| Mode | Config | Authentication |
|------|--------|----------------|
| github.com | `GITHUB_MODE=github.com` | Personal Access Token (`GITHUB_TOKEN`) |
| GHES | `GITHUB_MODE=ghes` | OAuth via `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` |

## Development

### Setup

```bash
# Install with dev dependencies
uv sync --extra dev
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_diff_parser.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=mcp_gh_reviewer
```

### Test Structure

- `test_config.py` - Settings and environment loading
- `test_github_client.py` - GitHub API interactions
- `test_openrouter_client.py` - OpenRouter API interactions
- `test_diff_parser.py` - Diff parsing and line mapping
- `test_review_generator.py` - AI review generation
- `test_review_poster.py` - Review posting and validation
- `test_integration.py` - End-to-end workflows

## Troubleshooting

### Common Issues

**"Rate limit exceeded"**
- GitHub API has rate limits. Wait and retry, or use a PAT with higher limits.

**"Cannot approve your own pull request"**
- GitHub prevents self-approval. The tool automatically downgrades to COMMENT in this case.

**"Invalid line number in comment"**
- The AI suggested a comment on a line not in the diff. The tool filters these automatically.

**"Authentication failed"**
- Verify your `GITHUB_TOKEN` has `repo` scope
- For GHES, ensure OAuth credentials are correct

## License

MIT

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass (`uv run pytest`)
5. Submit a pull request
