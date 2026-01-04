#!/usr/bin/env python3
"""Install the pre-commit hook for AI-powered code review."""

import os
import stat
import subprocess
import sys
from pathlib import Path

HOOK_SCRIPT = """#!/bin/sh
# AI-powered code review pre-commit hook
# Installed by: uv run install-review-hook

# Validate we're in a git repository
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "Error: Not in a git repository" >&2
    exit 1
fi

# Check if uv is available
UV_PATH=$(command -v uv 2>/dev/null)
if [ -z "$UV_PATH" ]; then
    echo "Error: uv not found in PATH" >&2
    echo "Install uv or skip this hook with: git commit --no-verify" >&2
    exit 1
fi

# Run the review hook
exec "$UV_PATH" run review-staged
"""


def find_git_root() -> Path | None:
    """Find the git repository root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=True,
        )
        git_dir = Path(result.stdout.strip())
        if git_dir.is_absolute():
            return git_dir
        return Path.cwd() / git_dir
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def install_hook() -> int:
    """Install the pre-commit hook.

    Returns:
        0 on success, 1 on failure
    """
    git_dir = find_git_root()
    if not git_dir:
        print("Error: Not in a git repository")
        return 1

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / "pre-commit"

    # Check for existing hook
    if hook_path.exists():
        print(f"Found existing pre-commit hook at {hook_path}")
        response = input("Replace it? [y/N]: ").strip().lower()
        if response not in ("y", "yes"):
            print("Aborted.")
            return 1

        # Backup existing hook
        backup_path = hook_path.with_suffix(".backup")
        hook_path.rename(backup_path)
        print(f"Backed up existing hook to {backup_path}")

    # Write the hook
    hook_path.write_text(HOOK_SCRIPT)

    # Make executable
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Installed pre-commit hook at {hook_path}")
    print("\nThe hook will run AI review on staged changes before each commit.")
    print("To skip the hook, use: git commit --no-verify")

    return 0


def uninstall_hook() -> int:
    """Uninstall the pre-commit hook.

    Returns:
        0 on success, 1 on failure
    """
    git_dir = find_git_root()
    if not git_dir:
        print("Error: Not in a git repository")
        return 1

    hook_path = git_dir / "hooks" / "pre-commit"

    if not hook_path.exists():
        print("No pre-commit hook installed.")
        return 0

    # Check if it's our hook
    content = hook_path.read_text()
    if "review-staged" not in content:
        print("Warning: Pre-commit hook doesn't appear to be the AI review hook.")
        response = input("Remove anyway? [y/N]: ").strip().lower()
        if response not in ("y", "yes"):
            print("Aborted.")
            return 1

    hook_path.unlink()
    print(f"Removed pre-commit hook at {hook_path}")

    # Check for backup
    backup_path = hook_path.with_suffix(".backup")
    if backup_path.exists():
        response = input(f"Restore backup from {backup_path}? [y/N]: ").strip().lower()
        if response in ("y", "yes"):
            backup_path.rename(hook_path)
            print("Restored backup hook.")

    return 0


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        sys.exit(uninstall_hook())
    else:
        sys.exit(install_hook())


if __name__ == "__main__":
    main()
