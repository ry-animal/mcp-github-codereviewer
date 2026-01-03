#!/bin/bash
# Wrapper script to run gh-review in Docker

docker run --rm \
  --env-file .env \
  mcp-gh-reviewer:latest \
  uv run gh-review "$@"
