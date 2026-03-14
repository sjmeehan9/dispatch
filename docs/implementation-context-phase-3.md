# Phase 3 Implementation Context

## Component 3.1 - GitHub API Client
- Implemented `GitHubClient` in `app/src/services/github_client.py` with sync `httpx.Client` integration, GitHub API base URL, and required headers (`Authorization`, `Accept`, `X-GitHub-Api-Version`).
- Added `GitHubFileEntry` dataclass for directory entry mapping with `name`, `path`, `type`, and `size`.
- Added structured exception hierarchy: `GitHubClientError`, `GitHubAuthError`, `GitHubNotFoundError`, and `GitHubAPIError`.
- Implemented `get_file_contents(owner, repo, path)` to call the contents endpoint, decode base64 file content, and raise descriptive errors for 401/403/404/5xx and malformed payloads.
- Implemented `list_directory(owner, repo, path)` to return typed entries, treating missing directories (404) as optional and returning an empty list.
- Implemented `check_file_exists(owner, repo, path)` with boolean semantics (`False` only on not-found, re-raise other errors).
- Added `_request()` private helper with retry-once behavior for 5xx responses and request-level logging (DEBUG for requests, WARNING for retry).
- Added `close()`, `__enter__`, and `__exit__` for explicit and context-managed client cleanup.
- Updated `app/src/services/__init__.py` to export GitHub client symbols.
- Added focused tests in `tests/test_github_client.py` covering header configuration, base64 decoding, not-found/auth errors, directory listing behavior, exists checks, and 5xx retry behavior.

### Decisions
- Used a sync client (`httpx.Client`) per component spec and expected low-frequency GitHub scan usage.
- Centralized status handling in `_request()` so all service methods enforce identical retry and error semantics.
- Kept directory 404 handling in `list_directory()` only, because agent directories are optional while `phase-progress` file lookups are mandatory.

### Deviations
- Validation ran in a Python 3.12 sandbox (project targets 3.13); checks were executed with installed tooling and passed for the updated scope.
