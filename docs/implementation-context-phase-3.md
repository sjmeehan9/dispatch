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

## Component 3.2 - Project Service: Linking & Scanning
- Implemented `ProjectService` and `ProjectLinkError` in `app/src/services/project_service.py` for the repository-linking workflow.
- Added strict repository validation for `owner/repo` format via regex and explicit, user-facing errors.
- Implemented `link_project(repository, token_env_key)` orchestration to:
  - validate repository and token env key presence,
  - verify token availability using `Settings.get_secret()` (supports `GITHUB_TOKEN`/`TOKEN` aliasing),
  - fetch and parse `docs/phase-progress.json`,
  - parse phase/component structures into `PhaseData` models,
  - discover agent files under `.claude/agents/` and `.github/agents/`,
  - return a populated `Project` model with UUID, timestamps, and empty actions list.
- Added robust phase-progress validation with descriptive errors for missing `phases`, missing phase fields, missing component fields, and non-object entries.
- Mapped GitHub client failures to domain-level errors:
  - `GitHubNotFoundError` → required file missing message,
  - `GitHubAuthError` → authentication failure message.
- Added INFO-level link summary logging: phases count, component count, and agent file count.
- Updated `app/src/services/__init__.py` exports to include `ProjectService` and `ProjectLinkError`.
- Added focused unit tests in `tests/test_project_service.py` covering success flow, invalid repository, missing/unauthorized phase-progress, camelCase mapping, and agent directory discovery behavior.

### Decisions
- Kept linking concerns isolated from persistence concerns to align with Component 3.2 scope; CRUD remains for Component 3.3.
- Required token env key resolution during link to fail fast when secrets are not configured in local env or CI secret mapping.

### Deviations
- Could not execute the full validation toolchain in this sandbox because Python 3.13 and pre-provisioned venv tooling were unavailable; implementation remains aligned with CI runtime expectations.
