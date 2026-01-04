---
name: github-pr-review
description: Review GitHub pull requests with AI-powered code analysis. Use when the user asks to review a PR, analyze code changes, list open PRs, or generate feedback on pull requests. Supports github.com and GitHub Enterprise Server.
allowed-tools: github-pr-review--*
---

# GitHub PR Review Skill

Use the mcp-gh-reviewer MCP server tools to review GitHub pull requests with AI-powered analysis.

## Available Tools

- **list_prs(owner, repo, state?)**: List pull requests in a repository
- **get_pr(owner, repo, pr_number)**: Fetch PR metadata (title, description, author, branch info)
- **get_pr_diff(owner, repo, pr_number)**: Get the unified diff
- **get_pr_files(owner, repo, pr_number)**: Get changed files with stats and patches
- **review_pr(owner, repo, pr_number, action?, focus_areas?)**: Generate AI-powered review

## Recommended Workflow

When asked to review a PR:

1. **Fetch metadata** with `get_pr` to understand context
2. **Get the diff** with `get_pr_diff` to see what changed
3. **Generate review** with `review_pr` for AI analysis

For quick reviews, you can skip directly to `review_pr` which fetches context automatically.

## Parsing PR URLs

When given a URL like `https://github.com/owner/repo/pull/123`:
- owner = `owner`
- repo = `repo`
- pr_number = `123`

## Focus Areas

Pass `focus_areas` to `review_pr` for targeted analysis:

- `security` - Auth, data handling, vulnerabilities
- `performance` - Efficiency, queries, caching
- `testing` - Coverage, edge cases, test quality
- `documentation` - Comments, docstrings, API docs
- `maintainability` - Clarity, complexity, patterns

Example: `review_pr(owner, repo, 123, focus_areas=["security", "performance"])`

## Review Actions

The `action` parameter controls the review type:
- `APPROVE` - Approve the PR
- `REQUEST_CHANGES` - Request changes before merge
- `COMMENT` - Leave feedback without approval decision

Default is `COMMENT` which is safest.

## Example Tasks

**List open PRs:**
```
list_prs(owner="myorg", repo="myproject", state="open")
```

**Quick PR review:**
```
review_pr(owner="myorg", repo="myproject", pr_number=123)
```

**Security-focused review:**
```
review_pr(owner="myorg", repo="myproject", pr_number=123, focus_areas=["security"])
```

**Analyze changes without generating review:**
```
get_pr(owner="myorg", repo="myproject", pr_number=123)
get_pr_diff(owner="myorg", repo="myproject", pr_number=123)
```

## Output Format

`review_pr` returns:
- **summary**: Overall assessment
- **decision**: APPROVE, REQUEST_CHANGES, or COMMENT
- **confidence**: How confident the AI is in its review
- **key_issues**: Major problems found
- **inline_comments**: Specific feedback with file paths and line numbers

Present inline comments with their file paths and line numbers for easy navigation.
