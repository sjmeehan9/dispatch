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

## Component 3.3 - Project Service: CRUD & Persistence
- Extended `app/src/services/project_service.py` with project persistence APIs and new types:
  - `ProjectNotFoundError` for missing project files.
  - `ProjectSummary` dataclass for lightweight listing output.
  - `save_project(project)` with timestamp refresh and atomic JSON writes (`.tmp` + `os.replace`).
  - `load_project(project_id)` with file-not-found handling and `Project.model_validate`.
  - `list_projects()` returning summary objects sorted by `updated_at` descending.
  - `delete_project(project_id)` for file deletion with missing-file handling.
- Added filesystem path helper `_project_file_path()` and centralized use of `Settings.projects_dir`.
- Added descriptive file I/O error wrapping for `PermissionError`/`OSError` paths.
- Implemented malformed listing resilience: invalid JSON or missing summary fields are logged at WARNING and skipped.
- Updated `app/src/services/__init__.py` exports to include `ProjectNotFoundError` and `ProjectSummary`.
- Expanded `tests/test_project_service.py` with CRUD-focused coverage:
  - save file creation and timestamp updates,
  - save/load round-trip validation,
  - load missing-project behavior,
  - list sorting and empty-directory behavior,
  - malformed JSON skip behavior,
  - delete success and missing-project behavior,
  - atomic write assertion by capturing `os.replace` source and destination.

### Decisions
- Kept list scanning fast by reading only four summary fields from JSON rather than validating full `Project` objects.
- Used `os.replace` for atomic promotion of temp files to mitigate corruption risk during OneDrive synchronization.
- Preserved existing link workflow behavior by confining changes to persistence concerns and export surface only.

### Deviations
- Validation was executed in a Python 3.12 sandbox with `--ignore-requires-python` due local runtime constraints; tests and quality checks passed for updated scope.

## Component 3.4 - Action Generator Service
- Implemented `ActionGenerator` in `app/src/services/action_generator.py` with:
  - `generate_actions(phases, action_type_defaults)` to produce flat ordered phase actions.
  - `insert_debug_action(actions, phase_id, position, action_type_defaults)` for phase-local Debug insertion.
  - `_create_action(...)` helper that assigns UUIDs and deep-copies payload templates.
  - `_component_sort_key(component_id)` helper for natural dotted numeric ordering (`1.2` < `1.10`).
- Generation behavior now matches phase rules: per phase, all Implement actions (component natural order), then Test, Review, Document.
- All generated actions initialize with `status=not_started`, `executor_response=None`, and `webhook_response=None`.
- Added INFO-level logs for total generated actions/phases and Debug insertion position/phase.
- Updated `app/src/services/__init__.py` to export `ActionGenerator`.
- Added focused tests in `tests/test_action_generator.py` covering:
  - single-phase ordering and component/phase-level `component_id` assignment,
  - natural component sorting (`1.1`, `1.2`, `1.10`),
  - multi-phase ordering and UUID uniqueness,
  - payload deep-copy isolation from defaults,
  - Debug insertion at start, middle, and end positions,
  - out-of-range insertion validation errors.

### Decisions
- Kept `ActionGenerator` stateless via class/static methods to simplify reuse in service and UI layers.
- Chose deep-copy payload cloning at action creation so per-action edits cannot mutate global defaults.
- Added robust sort fallback for non-numeric component segments while preserving numeric natural-order behavior.

### Deviations
- The component breakdown’s “3 components generates 7 actions” count appears inconsistent with required sequence; implementation follows explicit ordering rules (`3 Implement + Test + Review + Document = 6`).

## Component 3.5 - Payload Resolver Service
- Implemented `PayloadResolver` in `app/src/services/payload_resolver.py` with:
  - `build_context(project, phase_id, component_id, executor_config)` for string-only context assembly.
  - `resolve_payload(payload, context)` for deep-copied recursive placeholder replacement.
  - `_resolve_value()` traversal across nested dict/list payload structures.
  - `_replace_match()` strict `{{word_chars}}` substitution with unresolved tracking.
- Implemented context keys required by the component spec:
  `repository`, `branch`, `phase_id`, `phase_name`, `component_id`, `component_name`,
  `component_breakdown_doc`, `agent_paths` (JSON string), `webhook_url`, `pr_number`.
- Added strict lookup errors for invalid `phase_id` or `component_id` to fail loudly on invalid action context.
- Updated `app/src/services/__init__.py` exports to include `PayloadResolver`.
- Added focused tests in `tests/test_payload_resolver.py` covering:
  - context construction with component and without component,
  - phase/component lookup error paths,
  - recursive replacement across nested dicts/lists,
  - multiple placeholders in a single string,
  - non-string passthrough behavior,
  - unresolved variable preservation and deduplicated unresolved list tracking.

### Decisions
- Kept resolver stateless using class methods for easy service-layer reuse.
- Used strict regex `r"\{\{(\w+)\}\}"` exactly as specified to constrain placeholder names.
- Serialized `agent_paths` with `json.dumps(project.agent_files)` so executor payloads receive JSON-compatible list text.

### Deviations
- None.
