#!/bin/bash
# Wrapper script to run gh-review in Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "Error: .env file not found at $SCRIPT_DIR/.env" >&2
  exit 1
fi

docker run --rm \
  --env-file .env \
  mcp-gh-reviewer:latest \
  uv run gh-review "$@"
