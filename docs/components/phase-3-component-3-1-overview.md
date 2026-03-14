# Phase 3 Component 3.1 Overview — GitHub API Client

## Summary
Component 3.1 introduces the production GitHub REST client used by Dispatch to scan repositories for `docs/phase-progress.json` and discover agent files under `.claude/agents/` and `.github/agents/`.

## Implemented Scope
- Added `app/src/services/github_client.py`:
  - `GitHubFileEntry` dataclass for typed directory listings.
  - `GitHubClient` with sync `httpx.Client` configured for:
    - base URL: `https://api.github.com`
    - `Authorization: Bearer <token>`
    - `Accept: application/vnd.github.v3+json`
    - `X-GitHub-Api-Version: 2022-11-28`
    - timeout: 30 seconds
  - Public methods:
    - `get_file_contents(owner, repo, path) -> str`
    - `list_directory(owner, repo, path) -> list[GitHubFileEntry]`
    - `check_file_exists(owner, repo, path) -> bool`
    - `close()`, `__enter__`, `__exit__`
  - Exception classes:
    - `GitHubClientError`
    - `GitHubAuthError` (401/403)
    - `GitHubNotFoundError` (404)
    - `GitHubAPIError` (other failures)

## Behavior Notes
- `get_file_contents()` decodes GitHub contents API base64 payloads into UTF-8 strings.
- `list_directory()` returns empty list on 404 to support optional agent directories.
- `check_file_exists()` returns `False` only for `GitHubNotFoundError`; all other failures propagate.
- `_request()` retries exactly once for 5xx responses before raising `GitHubAPIError`.

## Integration Updates
- Updated `app/src/services/__init__.py` exports so imports like
  `from app.src.services.github_client import GitHubClient`
  and package-level service imports are supported.

## Test Coverage
- Added `tests/test_github_client.py` covering:
  - Client header configuration
  - Base64 content decoding
  - 404/401 error mapping
  - Directory listing mapping
  - Optional directory 404 behavior
  - File existence checks
  - Retry-once behavior for 5xx errors

## Security and Secrets
- The client never logs tokens.
- Token usage is header-based only; secret retrieval remains centralized in settings/config layers (`GITHUB_TOKEN` with `TOKEN` alias support for GitHub secrets environments).
