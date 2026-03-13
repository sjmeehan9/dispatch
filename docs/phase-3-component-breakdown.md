# Phase 3: Core Backend Services

## Phase Overview

**Objective**: Implement all backend service logic — GitHub API integration, project management (link/save/load), action generation from `phase-progress.json`, payload variable resolution, executor dispatch (with modular protocol), and webhook handling. After this phase, the complete business logic is testable independently from the UI.

**Deliverables**:
- GitHub API client (`app/src/services/github_client.py`) — httpx-based, authenticated requests, file/directory reading, base64 content decoding
- Project service (`app/src/services/project_service.py`) — link new project (scan repo for `phase-progress.json` and agent files), save/load/list/delete projects
- Action generator (`app/src/services/action_generator.py`) — derive ordered Execute Action items from phase-progress data, support Debug insertion
- Payload resolver (`app/src/services/payload_resolver.py`) — `{{variable}}` interpolation against project context map
- Executor module (`app/src/services/executor.py`) — `Executor` Protocol definition plus `AutopilotExecutor` concrete implementation
- Webhook service (`app/src/services/webhook_service.py`) — in-memory store for callback data keyed by `run_id`
- Unit tests covering all services with ≥ 30% coverage on new code

**Dependencies**:
- Phase 2 complete (data models in `app/src/models/`, config manager in `app/src/services/config_manager.py`, settings module in `app/src/config/`)
- Python 3.13+ virtual environment activated
- `.env/.env.local` exists with at least `DISPATCH_DATA_DIR` set
- `~/.dispatch/` data directory initialised (by Phase 2 settings module)

## Phase Goals

- GitHub API client can authenticate and retrieve file contents, directory listings, and base64-decoded content from any target repository
- Project service can link a new project by scanning a remote repo for `docs/phase-progress.json` (blocking with a descriptive error if not found) and discovering agent files in `.claude/agents/` and `.github/agents/`
- Projects can be saved, loaded, listed, and deleted from the `~/.dispatch/projects/` directory
- Action generator produces correctly ordered Execute Action items: Implement per component → Test → Review → Document per phase, with Debug insertion at any position
- Payload resolver correctly replaces all `{{variable}}` placeholders with concrete values from the project context map
- Executor module dispatches payloads via HTTP POST with `X-API-Key` auth and returns structured responses
- Webhook service stores and retrieves callback data by `run_id`
- All new code passes Black, isort, evals, and achieves ≥ 30% test coverage

---

## Components

### Component 3.1 — GitHub API Client

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 2.2: `Settings` module must be implemented (provides `get_secret()` for token retrieval)

**Features**:
- [AI Agent] Create `app/src/services/github_client.py` with `GitHubClient` class
- [AI Agent] Implement authenticated HTTP requests to GitHub REST API via httpx
- [AI Agent] Implement file existence check and content retrieval (`GET /repos/{owner}/{repo}/contents/{path}`)
- [AI Agent] Implement directory listing for agent file discovery
- [AI Agent] Implement base64 content decoding for file contents
- [AI Agent] Implement structured error handling for GitHub API responses (401, 403, 404, 5xx)

**Description**:
This component creates the GitHub API client that underpins project linking. It uses httpx to make authenticated requests to the GitHub REST API, supporting file existence checks, content retrieval (with base64 decoding), and directory listing. The client is designed for the specific endpoints Dispatch needs: reading `docs/phase-progress.json` and listing agent files in `.claude/agents/` and `.github/agents/`. Error handling is explicit — 404s produce a clear "file not found" error, auth failures surface actionable messages, and 5xx errors are retried once before failing.

**Acceptance Criteria**:
- [ ] `GitHubClient` can be instantiated with a GitHub token
- [ ] `get_file_contents(owner, repo, path)` returns decoded file contents as a string
- [ ] `get_file_contents()` raises a descriptive error if the file is not found (404)
- [ ] `get_file_contents()` raises an auth error on 401/403 with actionable message
- [ ] `list_directory(owner, repo, path)` returns a list of file/directory entries
- [ ] `list_directory()` returns an empty list for a non-existent directory (not an error — agent dirs are optional)
- [ ] `check_file_exists(owner, repo, path)` returns `True`/`False` without raising on 404
- [ ] All GitHub API calls include `Authorization: Bearer {token}` and `Accept: application/vnd.github.v3+json` headers
- [ ] 5xx responses trigger one automatic retry before raising
- [ ] `from app.src.services.github_client import GitHubClient` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/services/github_client.py`
  - `app/src/services/__init__.py` (update with exports)
- **Key Functions/Classes**:
  - `GitHubClient.__init__(token: str)`
  - `GitHubClient.get_file_contents(owner: str, repo: str, path: str) -> str`
  - `GitHubClient.list_directory(owner: str, repo: str, path: str) -> list[GitHubFileEntry]`
  - `GitHubClient.check_file_exists(owner: str, repo: str, path: str) -> bool`
  - `GitHubFileEntry` — lightweight dataclass with `name: str`, `path: str`, `type: str` (file/dir)
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: httpx>=0.27 (already declared in `pyproject.toml`)

**Detailed Implementation Requirements**:

- **File 1: `app/src/services/github_client.py`**: Define a `GitHubFileEntry` dataclass with fields `name: str`, `path: str`, `type: str` (values: `"file"` or `"dir"`), and `size: int`. Define a `GitHubClientError` exception base class and subclasses `GitHubAuthError`(for 401/403), `GitHubNotFoundError` (for 404), and `GitHubAPIError` (for other errors). Create a `GitHubClient` class that: (1) Accepts `token: str` on `__init__` and creates an `httpx.Client` (sync) with base URL `https://api.github.com`, headers `{"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "X-GitHub-Api-Version": "2022-11-28"}`, and a 30-second timeout. (2) `get_file_contents(owner, repo, path)` sends `GET /repos/{owner}/{repo}/contents/{path}`, checks the response status — 404 raises `GitHubNotFoundError` with path context, 401/403 raises `GitHubAuthError` with "check your token" message, 5xx retries once then raises `GitHubAPIError`. On success, parses the JSON response, base64-decodes the `content` field (`base64.b64decode(response_json["content"]).decode("utf-8")`), and returns the decoded string. (3) `list_directory(owner, repo, path)` sends the same GET endpoint — if the response is a JSON array (directory listing), maps each entry to a `GitHubFileEntry`. If 404, returns an empty list (agent directories may not exist). (4) `check_file_exists(owner, repo, path)` calls `get_file_contents` in a try/except, returning `True` on success, `False` on `GitHubNotFoundError`, and re-raising other errors. (5) Implement a `_request(method, url)` private method that handles the retry-once-on-5xx logic and status code checking, used by all public methods. (6) Implement a `close()` method and `__enter__`/`__exit__` for context manager support to properly close the httpx client. Use structured logging at DEBUG level for requests (URL only, no tokens) and WARNING for retries.

**Test Requirements**:
- [ ] Unit tests: `get_file_contents()` returns decoded content (mocked httpx with base64-encoded response)
- [ ] Unit tests: `get_file_contents()` raises `GitHubNotFoundError` on 404
- [ ] Unit tests: `get_file_contents()` raises `GitHubAuthError` on 401
- [ ] Unit tests: `list_directory()` returns `GitHubFileEntry` list from directory response
- [ ] Unit tests: `list_directory()` returns empty list on 404
- [ ] Unit tests: `check_file_exists()` returns `True`/`False` correctly
- [ ] Unit tests: 5xx triggers one retry then raises `GitHubAPIError`

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-3-component-3-1-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-3.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
Use `httpx.Client` (sync) rather than `httpx.AsyncClient` — NiceGUI runs on an asyncio event loop but the GitHub API calls are infrequent and can block briefly. Async would add complexity for no practical benefit given the usage pattern (a few calls during project linking only). The GitHub REST API returns file content as base64-encoded in the `content` field of the response JSON. For files larger than 1 MB, the `content` field is empty and you'd need the blob API — but `phase-progress.json` and agent files will never be this large, so the standard contents endpoint is sufficient. Always validate that `owner/repo` format is correct before making API calls — a simple `"/" in repo_string` check is enough.

---

### Component 3.2 — Project Service: Linking & Scanning

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 3.1: `GitHubClient` must be implemented for repo scanning
- Component 2.1: `Project`, `PhaseData`, `ComponentData` models must be defined
- Component 2.2: `Settings` module for data directory paths and secret retrieval
- Component 2.3: `ConfigManager` for checking executor config exists

**Features**:
- [AI Agent] Create `app/src/services/project_service.py` with `ProjectService` class (linking portion)
- [AI Agent] Implement repository format validation (`owner/repo`)
- [AI Agent] Implement `phase-progress.json` scanning, retrieval, and parsing
- [AI Agent] Implement agent file discovery in `.claude/agents/` and `.github/agents/`
- [AI Agent] Implement project config generation with UUID and parsed phase data

**Description**:
This component implements the project linking workflow — the core business logic that connects Dispatch to a target GitHub repository. When a user provides a repository and token, the service validates the input, uses the GitHub client to scan for `docs/phase-progress.json` (blocking with a clear error if not found), parses the phase-progress data into the `PhaseData`/`ComponentData` models, discovers agent files in the standard directories, and assembles a complete `Project` model ready for persistence. This is the "brain" of the Link New Project flow.

**Acceptance Criteria**:
- [ ] `ProjectService.link_project(repository, token_env_key)` returns a fully populated `Project` model
- [ ] Service validates repository format ("owner/repo") and rejects invalid formats with a clear error
- [ ] Service scans the target repo for `docs/phase-progress.json` using the GitHub client
- [ ] Service raises a descriptive `ProjectLinkError` if `phase-progress.json` is not found
- [ ] Service parses `phase-progress.json` content into `PhaseData` and `ComponentData` models
- [ ] Service validates the parsed structure (phases array exists, components have required fields)
- [ ] Service scans `.claude/agents/` and `.github/agents/` for agent files (gracefully handles missing directories)
- [ ] Service generates a UUID-based `project_id`
- [ ] Service stores the raw `phase-progress.json` content in `Project.phase_progress` and parsed phases in `Project.phases`
- [ ] `from app.src.services.project_service import ProjectService` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/services/project_service.py`
  - `app/src/services/__init__.py` (update exports)
- **Key Functions/Classes**:
  - `ProjectLinkError(Exception)` — raised when linking fails
  - `ProjectService.__init__(settings: Settings, github_client: GitHubClient)`
  - `ProjectService.link_project(repository: str, token_env_key: str) -> Project`
  - `ProjectService._validate_repository(repository: str) -> tuple[str, str]` — returns (owner, repo)
  - `ProjectService._scan_phase_progress(owner: str, repo: str) -> dict[str, Any]`
  - `ProjectService._parse_phase_progress(raw_data: dict[str, Any]) -> list[PhaseData]`
  - `ProjectService._discover_agent_files(owner: str, repo: str) -> list[str]`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: GitHubClient (Component 3.1), models (Component 2.1), Settings (Component 2.2)

**Detailed Implementation Requirements**:

- **File 1: `app/src/services/project_service.py`** (linking portion — CRUD added in Component 3.3): Define `ProjectLinkError` as a custom exception. Create a `ProjectService` class that accepts `Settings` and `GitHubClient` instances. Implement `link_project(repository, token_env_key)` as the main orchestration method: (1) Call `_validate_repository(repository)` to check the `owner/repo` format using a regex pattern `^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$` — raise `ProjectLinkError` with a descriptive message if invalid. (2) Call `_scan_phase_progress(owner, repo)` which uses `github_client.get_file_contents(owner, repo, "docs/phase-progress.json")`, parses the response as JSON, and returns the raw dict. Catch `GitHubNotFoundError` and re-raise as `ProjectLinkError("phase-progress.json not found at docs/phase-progress.json in {repository}. This file is required.")`. Catch `GitHubAuthError` and re-raise as `ProjectLinkError("Authentication failed for {repository}. Check your GitHub token.")`. (3) Call `_parse_phase_progress(raw_data)` to validate the structure and create `PhaseData`/`ComponentData` model instances. Validate that the JSON has a `phases` array, each phase has required fields (`phaseId`, `phaseName`, `components`), and each component has required fields. Map snake_case model fields from camelCase JSON fields (use Pydantic's `alias` or a manual mapping). (4) Call `_discover_agent_files(owner, repo)` which calls `github_client.list_directory()` for both `.claude/agents/` and `.github/agents/` — concatenate the file paths from both, filtering for files only (not subdirectories). Return empty list if neither directory exists. (5) Assemble and return a `Project` model with `project_id` from `uuid.uuid4()`, `project_name` set to the repository string, `repository`, `github_token_env_key` set to `token_env_key`, `phase_progress` as the raw dict, `phases` as the parsed list, `agent_files` as the discovered paths, empty `actions` list (populated by action generator in Component 3.4), and ISO 8601 timestamps for `created_at` and `updated_at`. Log at INFO level: "Linked project {repository}: {n} phases, {m} components, {k} agent files found".

**Test Requirements**:
- [ ] Unit tests: `link_project()` returns a valid `Project` with correct fields (mocked GitHub client)
- [ ] Unit tests: `link_project()` raises `ProjectLinkError` for invalid repository format ("no-slash")
- [ ] Unit tests: `link_project()` raises `ProjectLinkError` when `phase-progress.json` not found
- [ ] Unit tests: `link_project()` raises `ProjectLinkError` on auth failure
- [ ] Unit tests: `_parse_phase_progress()` correctly maps camelCase JSON to model fields
- [ ] Unit tests: `_discover_agent_files()` returns paths from both agent directories
- [ ] Unit tests: `_discover_agent_files()` returns empty list when directories don't exist

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-3-component-3-2-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-3.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
The `phase-progress.json` file uses camelCase field names (`phaseId`, `phaseName`, `componentId`) while the Pydantic models use snake_case (`phase_id`, `phase_name`, `component_id`). Handle this mapping explicitly — either via Pydantic `Field(alias=...)` with `model_config = ConfigDict(populate_by_name=True)`, or via a manual mapping function. The `_validate_repository` method should be strict — only allow alphanumeric characters, hyphens, underscores, and dots in the owner and repo names (per GitHub's naming rules). The `token_env_key` is the name of the environment variable holding the token (e.g., `GITHUB_TOKEN`), not the token itself — this aligns with the security pattern established in Phase 2 where models store key names, not secret values.

---

### Component 3.3 — Project Service: CRUD & Persistence

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 3.2: `ProjectService` class must exist (this component extends it)
- Component 2.1: `Project` model must be defined
- Component 2.2: `Settings` module for `projects_dir` path

**Features**:
- [AI Agent] Extend `app/src/services/project_service.py` with save, load, list, and delete methods
- [AI Agent] Implement atomic JSON file writes for OneDrive safety
- [AI Agent] Implement project listing from the data directory
- [AI Agent] Implement project loading from a saved JSON file
- [AI Agent] Implement project deletion with file cleanup

**Description**:
This component extends the `ProjectService` with CRUD operations for persisting project state to the local filesystem. Projects are saved as individual JSON files in `~/.dispatch/projects/{project-id}.json`. All write operations use atomic file writes (write to `.tmp`, then rename) to prevent corruption during OneDrive sync. The service supports saving the full project state (including generated actions and execution results), loading a specific project by ID, listing all saved projects (returning summaries, not full data), and deleting a project.

**Acceptance Criteria**:
- [ ] `save_project(project)` writes the project to `{projects_dir}/{project_id}.json`
- [ ] `save_project()` uses atomic file writes (`.tmp` + rename)
- [ ] `save_project()` updates the `updated_at` timestamp
- [ ] `load_project(project_id)` reads and returns a `Project` from the saved JSON file
- [ ] `load_project()` raises `ProjectNotFoundError` if the file doesn't exist
- [ ] `list_projects()` returns a list of project summaries (id, name, repo, updated_at) without loading full project data
- [ ] `delete_project(project_id)` removes the project JSON file
- [ ] `delete_project()` raises `ProjectNotFoundError` if the file doesn't exist
- [ ] All file operations handle `PermissionError` and `OSError` gracefully with descriptive messages

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/services/project_service.py` (extend existing class)
- **Key Functions/Classes**:
  - `ProjectNotFoundError(Exception)` — raised when a project file is missing
  - `ProjectService.save_project(project: Project) -> None`
  - `ProjectService.load_project(project_id: str) -> Project`
  - `ProjectService.list_projects() -> list[ProjectSummary]`
  - `ProjectService.delete_project(project_id: str) -> None`
  - `ProjectSummary` — lightweight dataclass with `project_id`, `project_name`, `repository`, `updated_at`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: Settings (Component 2.2), Project model (Component 2.1)

**Detailed Implementation Requirements**:

- **File 1: `app/src/services/project_service.py`** (extend): Define `ProjectNotFoundError` as a custom exception. Define `ProjectSummary` as a dataclass with `project_id: str`, `project_name: str`, `repository: str`, `updated_at: str`. Add `save_project(project)` to `ProjectService`: (1) Update `project.updated_at` to the current ISO 8601 timestamp. (2) Serialise the project to JSON via `project.model_dump(mode="json")` with `json.dumps(indent=2)`. (3) Write to `{projects_dir}/{project.project_id}.json.tmp` first. (4) Use `os.replace()` to atomically move the `.tmp` file to the final path. (5) Log at INFO level: "Saved project {project_id} ({project_name})". Add `load_project(project_id)` to `ProjectService`: (1) Construct the file path `{projects_dir}/{project_id}.json`. (2) If the file doesn't exist, raise `ProjectNotFoundError(f"Project {project_id} not found")`. (3) Read and parse the JSON file. (4) Construct and return a `Project` via `Project.model_validate(data)`. (5) Log at INFO level: "Loaded project {project_id}". Add `list_projects()` to `ProjectService`: (1) Glob `{projects_dir}/*.json` for all project files. (2) For each file, read only the top-level fields needed for `ProjectSummary` (use `json.load()` and extract `project_id`, `project_name`, `repository`, `updated_at` — do not parse into full `Project` to avoid loading large action lists). (3) Return sorted by `updated_at` descending (most recent first). (4) Return an empty list if no project files exist. Add `delete_project(project_id)` to `ProjectService`: (1) Construct the file path. (2) If it doesn't exist, raise `ProjectNotFoundError`. (3) Remove the file via `Path.unlink()`. (4) Log at INFO level: "Deleted project {project_id}".

**Test Requirements**:
- [ ] Unit tests: `save_project()` creates a valid JSON file in a temp directory
- [ ] Unit tests: `save_project()` + `load_project()` round-trip (save then load returns equivalent project)
- [ ] Unit tests: `load_project()` raises `ProjectNotFoundError` for non-existent ID
- [ ] Unit tests: `list_projects()` returns summaries for saved projects, sorted by most recent
- [ ] Unit tests: `list_projects()` returns empty list when no projects exist
- [ ] Unit tests: `delete_project()` removes the file
- [ ] Unit tests: `delete_project()` raises `ProjectNotFoundError` for non-existent ID
- [ ] Unit tests: Atomic write — verify `.tmp` file is used (mock `os.replace`)

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-3-component-3-3-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-3.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
The `list_projects()` method deliberately avoids full `Project.model_validate()` to keep directory scanning fast — it only needs the four summary fields. If a JSON file is malformed (e.g., corrupted during OneDrive sync), `list_projects()` should log a WARNING and skip that file rather than crashing. For `save_project()`, `os.replace()` is atomic on POSIX systems (macOS) — it overwrites the destination in a single operation, which is safe for OneDrive sync. The `ProjectSummary` dataclass is kept separate from the `Project` model to avoid importing the full model when only summaries are needed.

---

### Component 3.4 — Action Generator Service

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 2.1: `Action`, `ActionType`, `ActionStatus`, `PhaseData`, `ComponentData` models must be defined
- Component 2.1: `ActionTypeDefaults` model must be defined (for payload template assignment)
- Component 2.3: `ConfigManager.get_action_type_defaults()` for loading default templates

**Features**:
- [AI Agent] Create `app/src/services/action_generator.py` with `ActionGenerator` class
- [AI Agent] Implement action derivation from `PhaseData` list — Implement per Component, then Test, Review, Document per Phase
- [AI Agent] Implement Debug action insertion at any position within a phase
- [AI Agent] Implement UUID assignment for all generated actions
- [AI Agent] Implement payload template assignment from action type defaults

**Description**:
This component generates the ordered list of Execute Action items from parsed `phase-progress.json` data. The generation logic follows the specification: for each Phase, create one Implement action per Component (ordered by `component_id`), followed by one Test, one Review, and one Document action for the Phase. Each action is assigned a UUID and inherits its payload template from the action type default configuration. The generator also supports inserting Debug actions at any position within a phase's action list — a user-driven operation for ad-hoc troubleshooting.

**Acceptance Criteria**:
- [ ] `generate_actions(phases, action_type_defaults)` returns a correctly ordered list of `Action` items
- [ ] For each Phase: Implement actions appear first (one per Component, ordered by `component_id`), then Test, Review, Document
- [ ] Implement actions have `component_id` set to the component's ID; phase-level actions (Test, Review, Document) have `component_id` as `None`
- [ ] Each action has a unique UUID `action_id`
- [ ] Each action's `payload` field is populated with a copy of the corresponding type's default template from `ActionTypeDefaults`
- [ ] All actions start with `status = not_started`
- [ ] `insert_debug_action(actions, phase_id, position)` inserts a Debug action at the specified position within the phase's action sublist
- [ ] `insert_debug_action()` raises `ValueError` if `position` is out of range for the phase
- [ ] Multi-phase projects generate actions for all phases in phase order
- [ ] `from app.src.services.action_generator import ActionGenerator` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/services/action_generator.py`
  - `app/src/services/__init__.py` (update exports)
- **Key Functions/Classes**:
  - `ActionGenerator` class (stateless — all methods can be static or classmethod)
  - `ActionGenerator.generate_actions(phases: list[PhaseData], action_type_defaults: ActionTypeDefaults) -> list[Action]`
  - `ActionGenerator.insert_debug_action(actions: list[Action], phase_id: int, position: int, action_type_defaults: ActionTypeDefaults) -> list[Action]`
  - `ActionGenerator._create_action(action_type: ActionType, phase_id: int, component_id: str | None, template: dict[str, Any]) -> Action`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: models (Component 2.1)

**Detailed Implementation Requirements**:

- **File 1: `app/src/services/action_generator.py`**: Create an `ActionGenerator` class. Implement `generate_actions(phases, action_type_defaults)`: (1) Iterate over `phases` sorted by `phase_id`. (2) For each phase, iterate over `components` sorted by `component_id` (natural string sort, e.g., "1.1" < "1.2" < "1.10" — use a custom sort key that splits on "." and converts segments to integers). (3) For each component, call `_create_action(ActionType.IMPLEMENT, phase.phase_id, component.component_id, action_type_defaults.implement)`. (4) After all components, create one Test action (`_create_action(ActionType.TEST, phase.phase_id, None, action_type_defaults.test)`), one Review action, and one Document action. (5) Collect all actions into a flat list preserving the per-phase ordering and return it. Implement `_create_action(action_type, phase_id, component_id, template)`: (1) Generate a UUID via `str(uuid.uuid4())`. (2) Deep-copy the template dict so modifications don't affect the defaults. (3) Return an `Action` with `action_id=uuid`, `phase_id=phase_id`, `component_id=component_id`, `action_type=action_type`, `payload=copied_template`, `status=ActionStatus.NOT_STARTED`, `executor_response=None`, `webhook_response=None`. Implement `insert_debug_action(actions, phase_id, position, action_type_defaults)`: (1) Find all actions for the given `phase_id` and their indices in the main list. (2) Validate that `position` is between 0 and `len(phase_actions)` inclusive — raise `ValueError` if not. (3) Calculate the insertion index in the main `actions` list (the index of the first phase action + `position`). (4) Create a Debug action via `_create_action(ActionType.DEBUG, phase_id, None, action_type_defaults.debug)`. (5) Insert at the calculated index and return the modified list. Log at INFO level: "Generated {n} actions for {m} phases" and "Inserted debug action at position {p} in phase {phase_id}".

**Test Requirements**:
- [ ] Unit tests: Single phase with 3 components generates 7 actions (3 Implement + Test + Review + Document + order verified)
- [ ] Unit tests: Action ordering within a phase — Implements first (sorted by component_id), then Test, Review, Document
- [ ] Unit tests: Multi-phase (2 phases) generates correct total and ordering across phases
- [ ] Unit tests: Each action has a unique `action_id`
- [ ] Unit tests: Implement actions have `component_id` set, phase actions have `component_id` as `None`
- [ ] Unit tests: `insert_debug_action()` at position 0 (before first action), middle, and end of phase
- [ ] Unit tests: `insert_debug_action()` raises `ValueError` for out-of-range position
- [ ] Unit tests: Component ID natural sort ordering ("1.1", "1.2", "1.10" sorts correctly)

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-3-component-3-4-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-3.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
The natural sort for `component_id` is important — string sorting would order "1.10" before "1.2", which is wrong. Split on "." and convert each segment to `int` for proper numeric ordering. The `insert_debug_action` method returns the modified list (it mutates in place and also returns for chaining convenience). The payload template assigned to each action is a deep copy — this is critical because users will edit individual action payloads, and those edits must not propagate back to the defaults. The action list is flat (not nested per phase) because the UI displays all actions in a single scrollable list with phase grouping handled via display logic.

---

### Component 3.5 — Payload Resolver Service

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 2.1: `PayloadTemplate`, `ResolvedPayload`, `Project`, `Action` models must be defined
- Component 2.1: `ExecutorConfig` model for webhook URL
- Component 2.2: `Settings` module (for potential path resolution)

**Features**:
- [AI Agent] Create `app/src/services/payload_resolver.py` with `PayloadResolver` class
- [AI Agent] Implement `{{variable}}` placeholder parsing across all string values in a payload dict
- [AI Agent] Implement context map building from project data, phase data, component data, and executor config
- [AI Agent] Implement recursive variable resolution (handles nested dicts and lists)
- [AI Agent] Implement unresolved variable tracking for UI notification

**Description**:
This component resolves `{{variable}}` placeholders in payload templates to concrete values using a context map derived from the project, phase, component, and executor configuration. Resolution is recursive — it traverses all string values in nested dicts and lists, replacing `{{variable}}` patterns with values from the context map. Any variables that cannot be resolved (no matching key in the context map) are tracked and returned as `unresolved_variables` for the UI to surface. This service is the bridge between generic payload templates and the specific data for each action.

**Acceptance Criteria**:
- [ ] `build_context(project, phase_id, component_id, executor_config)` returns a complete context map dict
- [ ] Context map contains all expected variables: `repository`, `branch`, `phase_id`, `phase_name`, `component_id`, `component_name`, `component_breakdown_doc`, `agent_paths`, `webhook_url`, `pr_number`
- [ ] `resolve_payload(payload_template, context)` replaces all `{{variable}}` placeholders with values from the context
- [ ] Resolution is recursive — handles nested dicts and lists containing `{{variable}}` strings
- [ ] Non-string values in the payload (ints, bools, nested dicts) are preserved unchanged
- [ ] Unresolved variables (no key in context) are tracked and returned in `ResolvedPayload.unresolved_variables`
- [ ] Unresolved `{{variable}}` placeholders are left in the string (not removed) so the user can see and edit them
- [ ] `agent_paths` is resolved as a JSON-serialised list string (e.g., `'[".claude/agents/impl.md", ".github/agents/review.md"]'`)
- [ ] `from app.src.services.payload_resolver import PayloadResolver` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/services/payload_resolver.py`
  - `app/src/services/__init__.py` (update exports)
- **Key Functions/Classes**:
  - `PayloadResolver` class (stateless)
  - `PayloadResolver.build_context(project: Project, phase_id: int, component_id: str | None, executor_config: ExecutorConfig) -> dict[str, str]`
  - `PayloadResolver.resolve_payload(payload: dict[str, Any], context: dict[str, str]) -> ResolvedPayload`
  - `PayloadResolver._resolve_value(value: Any, context: dict[str, str], unresolved: list[str]) -> Any`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: models (Component 2.1), regex for `{{variable}}` parsing

**Detailed Implementation Requirements**:

- **File 1: `app/src/services/payload_resolver.py`**: Create a `PayloadResolver` class. Implement `build_context(project, phase_id, component_id, executor_config)`: (1) Find the `PhaseData` for the given `phase_id` from `project.phases`. (2) If `component_id` is provided, find the `ComponentData` within the phase. (3) Build and return a dict with keys: `"repository"` → `project.repository`, `"branch"` → `"main"` (default — can be extended per project later), `"phase_id"` → `str(phase.phase_id)`, `"phase_name"` → `phase.phase_name`, `"component_id"` → `component.component_id` (or `""` if None), `"component_name"` → `component.component_name` (or `""` if None), `"component_breakdown_doc"` → `phase.component_breakdown_doc`, `"agent_paths"` → `json.dumps(project.agent_files)` (JSON array string), `"webhook_url"` → `executor_config.webhook_url or ""`, `"pr_number"` → `""` (always empty by default — user fills in for Review actions). All values must be strings to support simple string replacement. Implement `resolve_payload(payload, context)`: (1) Create an empty `unresolved` list. (2) Deep-copy the payload dict. (3) Call `_resolve_value()` recursively on the copied dict. (4) Deduplicate the `unresolved` list. (5) Return `ResolvedPayload(payload=resolved_dict, unresolved_variables=unresolved)`. Implement `_resolve_value(value, context, unresolved)`: (1) If `value` is a `str`, use `re.sub(r'\{\{(\w+)\}\}', replacement_fn, value)` where the replacement function checks if the variable name is in `context` — if yes, substitute the value; if no, append the variable name to `unresolved` and return the original `{{variable}}` string unchanged. (2) If `value` is a `dict`, recursively resolve all values. (3) If `value` is a `list`, recursively resolve all elements. (4) For all other types (int, float, bool, None), return unchanged. Use the regex pattern `r'\{\{(\w+)\}\}'` consistently — this matches `{{word_chars}}` only, preventing injection via special characters.

**Test Requirements**:
- [ ] Unit tests: `build_context()` returns all expected keys with correct values
- [ ] Unit tests: `build_context()` with `component_id=None` sets component fields to empty strings
- [ ] Unit tests: `resolve_payload()` replaces `{{repository}}` and `{{branch}}` correctly
- [ ] Unit tests: `resolve_payload()` handles nested dicts (e.g., a payload with a nested config object)
- [ ] Unit tests: `resolve_payload()` handles lists containing `{{variable}}` strings
- [ ] Unit tests: `resolve_payload()` preserves non-string values (int, bool)
- [ ] Unit tests: Unresolved variables are tracked — `{{pr_number}}` with empty context reports it
- [ ] Unit tests: `agent_paths` resolved as JSON array string
- [ ] Unit tests: Multiple `{{variables}}` in a single string are all resolved

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-3-component-3-5-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-3.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
The regex `r'\{\{(\w+)\}\}'` is intentionally strict — only word characters (letters, digits, underscore) are valid variable names. This prevents any injection via `{{malicious_content}}`. The `branch` variable defaults to `"main"` — in a future enhancement, this could be configurable per project, but for now the default is sufficient. The `pr_number` is always empty in the auto-generated context because it's a value the user enters manually for Review-type actions. The `agent_paths` is serialised as a JSON array string because the payload field expects a JSON-compatible list representation — when the executor parses the payload, it will deserialise this string back into a list.

---

### Component 3.6 — Executor Protocol & Autopilot Implementation

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 2.1: `ExecutorConfig`, `ExecutorResponse` models must be defined
- Component 2.2: `Settings` module for secret retrieval (`get_secret()`)
- Component 2.3: `ConfigManager` for loading executor config

**Features**:
- [AI Agent] Create `app/src/services/executor.py` with `Executor` Protocol definition
- [AI Agent] Implement `AutopilotExecutor` class conforming to the `Executor` protocol
- [AI Agent] Implement HTTP POST dispatch with `X-API-Key` authentication
- [AI Agent] Implement response parsing into `ExecutorResponse` model
- [AI Agent] Implement structured error handling for dispatch failures

**Description**:
This component defines the modular executor interface and provides the default Autopilot implementation. The `Executor` Protocol defines the contract: any executor must implement `dispatch(payload) -> ExecutorResponse`. The `AutopilotExecutor` sends the resolved payload as a JSON POST to the configured API endpoint, authenticated with an `X-API-Key` header. It parses the response into a structured `ExecutorResponse` (status code, message, run_id). Error handling covers connection failures, timeouts, auth errors, and malformed responses. The modular design means adding a new executor (e.g., a different AI agent service) requires only a new class implementing the Protocol — no structural changes to the rest of the app.

**Acceptance Criteria**:
- [ ] `Executor` Protocol defines `dispatch(payload: dict[str, Any], config: ExecutorConfig) -> ExecutorResponse`
- [ ] `AutopilotExecutor` conforms to the `Executor` Protocol
- [ ] `AutopilotExecutor.dispatch()` sends HTTP POST to the configured `api_endpoint` with JSON body
- [ ] Request includes `X-API-Key` header with the API key retrieved from the environment via `Settings.get_secret()`
- [ ] Request includes `Content-Type: application/json` header
- [ ] Successful response (2xx) is parsed into `ExecutorResponse` with `status_code`, `message`, and `run_id`
- [ ] Non-2xx responses return an `ExecutorResponse` with the error status code and message from the response body
- [ ] Connection errors (timeouts, unreachable) return an `ExecutorResponse` with descriptive error message (no crash)
- [ ] Request timeout is set to 30 seconds
- [ ] `from app.src.services.executor import Executor, AutopilotExecutor` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/services/executor.py`
  - `app/src/services/__init__.py` (update exports)
- **Key Functions/Classes**:
  - `Executor(Protocol)` — defines `dispatch(payload, config) -> ExecutorResponse`
  - `AutopilotExecutor` — concrete implementation
  - `AutopilotExecutor.__init__(settings: Settings)`
  - `AutopilotExecutor.dispatch(payload: dict[str, Any], config: ExecutorConfig) -> ExecutorResponse`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: httpx>=0.27, models (Component 2.1), Settings (Component 2.2)

**Detailed Implementation Requirements**:

- **File 1: `app/src/services/executor.py`**: Define `Executor` as a `Protocol` class with a single method: `def dispatch(self, payload: dict[str, Any], config: ExecutorConfig) -> ExecutorResponse: ...`. Create `AutopilotExecutor` class: (1) `__init__(self, settings: Settings)` stores the settings reference for runtime secret retrieval. (2) `dispatch(self, payload, config)` — retrieve the API key via `self.settings.get_secret(config.api_key_env_key)`. If the key is `None` or empty, return an `ExecutorResponse(status_code=0, message="API key not configured. Set {config.api_key_env_key} in your environment.", run_id=None)`. Construct headers: `{"X-API-Key": api_key, "Content-Type": "application/json"}`. Use `httpx.Client` (create per-call or reuse — prefer per-call for simplicity) to `POST` to `config.api_endpoint` with `json=payload`, `headers=headers`, and `timeout=30.0`. Wrap the entire HTTP call in a try/except: catch `httpx.ConnectError` → return `ExecutorResponse(status_code=0, message="Connection failed: could not reach {config.api_endpoint}")`, catch `httpx.TimeoutException` → return `ExecutorResponse(status_code=0, message="Request timed out after 30 seconds")`, catch `httpx.HTTPError` → return `ExecutorResponse(status_code=0, message=f"HTTP error: {str(e)}")`. On success: parse `response.json()` for `run_id` and `status` fields. Return `ExecutorResponse(status_code=response.status_code, message=response_json.get("status", response.text), run_id=response_json.get("run_id"), raw_response=response_json)`. On non-2xx: return `ExecutorResponse(status_code=response.status_code, message=response.text, run_id=None, raw_response=None)`. Log at INFO: "Dispatching to {config.api_endpoint}" (no payload or key logging). Log at INFO: "Executor response: {status_code}". Log at WARNING for errors.

**Test Requirements**:
- [ ] Unit tests: `AutopilotExecutor.dispatch()` sends correct POST with headers (mocked httpx)
- [ ] Unit tests: Successful 200 response parsed into `ExecutorResponse` with `run_id`
- [ ] Unit tests: 401 response returns `ExecutorResponse` with error status and message
- [ ] Unit tests: Connection error returns `ExecutorResponse` with descriptive message (no exception raised)
- [ ] Unit tests: Timeout returns `ExecutorResponse` with timeout message
- [ ] Unit tests: Missing API key returns `ExecutorResponse` with configuration error message
- [ ] Unit tests: `AutopilotExecutor` satisfies `Executor` Protocol (structural check)

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-3-component-3-6-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-3.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
The executor never raises exceptions to the caller — all errors are captured and returned as `ExecutorResponse` objects with a `status_code` of `0` for network-level failures. This design keeps error handling clean in the UI layer (always display the response, never catch exceptions). The `X-API-Key` header name aligns with the Autopilot API's authentication scheme as documented in the runbook. Note that the API key is retrieved from the environment at dispatch time (not stored on the executor instance) — this allows key rotation without restarting the app. The `Executor` Protocol uses structural subtyping (duck typing) — `AutopilotExecutor` does not need to explicitly inherit from `Executor`, it just needs to implement the `dispatch` method with a matching signature. However, you may add a `runtime_checkable` decorator for explicit verification in tests.

---

### Component 3.7 — Webhook Service

**Priority**: Must-have

**Estimated Effort**: 1 hour

**Owner**: AI Agent

**Dependencies**:
- None (standalone in-memory service — no model or config dependencies beyond basic types)

**Features**:
- [AI Agent] Create `app/src/services/webhook_service.py` with `WebhookService` class
- [AI Agent] Implement in-memory store for webhook callback data keyed by `run_id`
- [AI Agent] Implement store, retrieve, and clear operations
- [AI Agent] Implement stale entry cleanup (entries older than a configurable threshold)

**Description**:
This component provides a simple in-memory store for webhook callback data received from the executor. When the Autopilot executor (or any executor) completes an agent run, it sends a callback POST to the Dispatch webhook endpoint. The webhook service stores this data keyed by `run_id`, and the UI polls the service to check for new results. The store also supports clearing stale entries to prevent unbounded memory growth in long-running sessions.

**Acceptance Criteria**:
- [ ] `store(run_id, data)` stores webhook callback data in memory
- [ ] `retrieve(run_id)` returns the stored data for a given `run_id`
- [ ] `retrieve()` returns `None` if no data exists for the `run_id`
- [ ] `has_result(run_id)` returns `True`/`False` without returning the data
- [ ] `clear(run_id)` removes a specific entry
- [ ] `clear_stale(max_age_seconds)` removes entries older than the threshold
- [ ] Service is thread-safe (callbacks may arrive on a different thread from UI polls)
- [ ] `from app.src.services.webhook_service import WebhookService` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/services/webhook_service.py`
  - `app/src/services/__init__.py` (update exports)
- **Key Functions/Classes**:
  - `WebhookService` class (singleton-like — one instance per app)
  - `WebhookService.store(run_id: str, data: dict[str, Any]) -> None`
  - `WebhookService.retrieve(run_id: str) -> dict[str, Any] | None`
  - `WebhookService.has_result(run_id: str) -> bool`
  - `WebhookService.clear(run_id: str) -> None`
  - `WebhookService.clear_stale(max_age_seconds: int = 3600) -> int` (returns count of cleared entries)
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: `threading.Lock` for thread safety, `time.time()` for timestamps

**Detailed Implementation Requirements**:

- **File 1: `app/src/services/webhook_service.py`**: Create a `WebhookService` class with an `__init__` that initialises `self._store: dict[str, tuple[float, dict[str, Any]]]` (maps `run_id` → `(timestamp, data)`) and `self._lock = threading.Lock()`. Implement `store(run_id, data)`: acquire the lock, store `(time.time(), data)` under the `run_id` key. Log at INFO: "Webhook data received for run_id {run_id}". Implement `retrieve(run_id)`: acquire the lock, return the data portion of the tuple (or `None` if the key doesn't exist). Implement `has_result(run_id)`: acquire the lock, return `run_id in self._store`. Implement `clear(run_id)`: acquire the lock, remove the entry if it exists (no error if missing). Implement `clear_stale(max_age_seconds=3600)`: acquire the lock, iterate the store and remove entries where `time.time() - timestamp > max_age_seconds`, return the count of removed entries. Log at INFO: "Cleared {n} stale webhook entries".

**Test Requirements**:
- [ ] Unit tests: `store()` + `retrieve()` round-trip
- [ ] Unit tests: `retrieve()` returns `None` for unknown `run_id`
- [ ] Unit tests: `has_result()` returns `True` after store, `False` before
- [ ] Unit tests: `clear()` removes the entry
- [ ] Unit tests: `clear_stale()` removes old entries and preserves recent ones (use mocked time)

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-3-component-3-7-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-3.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
Thread safety is important because NiceGUI runs on an asyncio event loop, and the webhook callback arrives via a FastAPI route — these may execute on different threads depending on Uvicorn's configuration. A simple `threading.Lock` is sufficient for the minimal contention expected (single user, infrequent callbacks). The stale entry cleanup keeps memory bounded during long sessions — call it periodically (e.g., every time a new entry is stored) or expose it for manual calling. The 1-hour default threshold is generous enough that results won't disappear while the user is reviewing them.

---

### Component 3.8 — Unit Tests, Validation & Phase Documentation

**Priority**: Must-have

**Estimated Effort**: 3 hours

**Owner**: AI Agent

**Dependencies**:
- Component 3.1 through 3.7: All service components must be implemented
- Component 2.5: Phase 2 tests still passing (no regression)

**Features**:
- [AI Agent] Create comprehensive unit tests for all Phase 3 services in `tests/`
- [AI Agent] Achieve ≥ 30% test coverage on new `app/src/` code from this phase
- [AI Agent] Run full quality validation (Black, isort, pytest, evals)
- [AI Agent] Validate E2E scenario preconditions — verify that services support the first three E2E scenarios (E2E-001, E2E-002, E2E-003)
- [AI Agent] Create/update phase implementation context documentation
- [AI Agent] Call out where automated E2E testing scenarios need to be executed after Phase 4 UI integration

**Description**:
This component completes Phase 3 by consolidating test coverage across all services, running the full quality validation suite, and creating the phase documentation. Tests use mocked httpx for GitHub API and executor HTTP calls — no live external calls. The action generator ordering tests are critical as they validate the core business logic of Execute Action item sequencing. After validation, the implementation context document is created/updated to provide downstream components with a clear picture of what was built and any notable decisions.

**Acceptance Criteria**:
- [ ] Unit tests exist in `tests/test_github_client.py`, `tests/test_project_service.py`, `tests/test_action_generator.py`, `tests/test_payload_resolver.py`, `tests/test_executor.py`, `tests/test_webhook_service.py`
- [ ] All unit tests pass: `pytest -q --cov=app/src --cov-report=term-missing`
- [ ] Test coverage on `app/src/` is ≥ 30%
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes
- [ ] `python scripts/evals.py` passes (all public functions have docstrings, no TODO/FIXME)
- [ ] Phase 2 tests still pass (no regression)
- [ ] E2E scenario precondition check: services can support E2E-001 (configure, link, generate, dispatch), E2E-002 (load, run phase), and E2E-003 (debug insertion and dispatch) at the service layer
- [ ] `docs/implementation-context-phase-3.md` exists with entries for all Phase 3 components

**Technical Details**:
- **Files to Create/Modify**:
  - `tests/test_github_client.py`
  - `tests/test_project_service.py`
  - `tests/test_action_generator.py`
  - `tests/test_payload_resolver.py`
  - `tests/test_executor.py`
  - `tests/test_webhook_service.py`
  - `docs/implementation-context-phase-3.md`
  - `docs/components/phase-3-component-3-8-overview.md`
- **Key Functions/Classes**: Test functions covering happy paths and key error cases for each service
- **Human/AI Agent**: AI Agent writes all tests and documentation
- **Dependencies**: pytest, pytest-cov, all Phase 3 service modules

**Detailed Implementation Requirements**:

- **File 1: `tests/test_github_client.py`**: Test functions covering: (1) `get_file_contents()` with mocked httpx returning a base64-encoded JSON response — verify decoded content matches expected. (2) `get_file_contents()` on 404 raises `GitHubNotFoundError`. (3) `get_file_contents()` on 401 raises `GitHubAuthError`. (4) `list_directory()` returns `GitHubFileEntry` list. (5) `list_directory()` returns empty list on 404. (6) `check_file_exists()` returns True/False. (7) 5xx triggers retry. Mock httpx using `unittest.mock.patch` on `httpx.Client.send` or by providing a custom transport via `httpx.MockTransport`.

- **File 2: `tests/test_project_service.py`**: Test functions covering: (1) `link_project()` with fully mocked GitHub client returning valid phase-progress.json and agent file list — verify returned `Project` has correct fields, UUID project_id, parsed phases, agent files. (2) `link_project()` with invalid repository format raises `ProjectLinkError`. (3) `link_project()` when phase-progress.json not found raises `ProjectLinkError`. (4) `save_project()` + `load_project()` round-trip in a temp directory. (5) `list_projects()` returns summaries sorted by updated_at. (6) `delete_project()` removes the file. (7) `load_project()` for non-existent project raises `ProjectNotFoundError`. Use `conftest.py` fixtures for temp directories and mock GitHub client.

- **File 3: `tests/test_action_generator.py`**: Test functions covering: (1) Single phase with 3 components — verify 7 actions in correct order (3 Implement, 1 Test, 1 Review, 1 Document). (2) Multi-phase — correct total count and phase ordering. (3) Implement actions have `component_id` set; Test/Review/Document have `None`. (4) All actions have unique UUIDs. (5) Natural sort for component IDs ("1.1", "1.2", "1.10"). (6) `insert_debug_action()` at start, middle, and end. (7) `insert_debug_action()` out-of-range raises ValueError.

- **File 4: `tests/test_payload_resolver.py`**: Test functions covering: (1) `build_context()` with all fields populated. (2) `build_context()` with `component_id=None`. (3) `resolve_payload()` replaces simple variables. (4) `resolve_payload()` handles nested dicts. (5) `resolve_payload()` handles lists. (6) Unresolved variables tracked in result. (7) `agent_paths` as JSON array string. (8) Multiple variables in one string all resolved.

- **File 5: `tests/test_executor.py`**: Test functions covering: (1) Successful dispatch with mocked 200 response. (2) Auth error (401). (3) Connection error (no crash). (4) Timeout (no crash). (5) Missing API key returns config error. (6) Protocol conformance check.

- **File 6: `tests/test_webhook_service.py`**: Test functions covering: (1) Store + retrieve round-trip. (2) Retrieve unknown returns None. (3) `has_result()`. (4) `clear()` removes entry. (5) `clear_stale()` with mocked time.

- **File 7: `docs/implementation-context-phase-3.md`**: Running log with entries for Components 3.1–3.8. Each entry: component ID and name, status (completed), key files created, notable decisions (e.g., "sync httpx.Client for GitHub API — async unnecessary for infrequent calls", "atomic file writes for project persistence", "executor never raises — all errors returned as ExecutorResponse", "thread-safe webhook store with Lock").

**Test Requirements**:
- [ ] All tests in test files pass
- [ ] `pytest -q --cov=app/src --cov-report=term-missing` reports ≥ 30% coverage on `app/src/`
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes
- [ ] `python scripts/evals.py` passes
- [ ] Phase 2 tests still pass

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing with ≥ 30% coverage
- [ ] All quality checks pass (Black, isort, pytest, evals)
- [ ] Documentation created: Component Overview (`docs/components/phase-3-component-3-8-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-3.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality (Phase 1 and Phase 2 tests still pass)
- [ ] Core application is still working post component implementation

**Notes**:
Mock httpx responses using either `unittest.mock.patch` on the client's `send` method or by using `httpx.MockTransport` with a handler function. The mock transport approach is cleaner and recommended. For project service tests, create a mock `GitHubClient` class (or use `unittest.mock.Mock`) that returns predetermined responses for `get_file_contents`, `list_directory`, etc. Tests should verify the complete flow: link → generate actions → resolve payloads → dispatch (all mocked) → store webhook response. This validates that the service-layer components integrate correctly before the UI is built in Phase 4. Keep test fixtures DRY — add shared fixtures (e.g., sample phase-progress data, sample executor config) to `conftest.py` for reuse.

---

## Phase Acceptance Criteria

- [ ] GitHub client authenticates and retrieves file contents from a target repo (mocked in tests)
- [ ] Project service scans a repo, finds `docs/phase-progress.json`, and parses it correctly
- [ ] Project service blocks with a descriptive error if `docs/phase-progress.json` is not found
- [ ] Agent files are discovered from `.claude/agents/` and `.github/agents/` directories
- [ ] Projects can be saved, loaded, listed, and deleted from the data directory
- [ ] Action generator produces correct ordering: Implement per component → Test → Review → Document per phase
- [ ] Debug actions can be inserted at any position within a phase's action list
- [ ] Payload resolver correctly replaces all `{{variable}}` placeholders with concrete values
- [ ] Executor dispatches a payload via HTTP POST and returns a structured response
- [ ] Executor never raises exceptions — all errors are returned as `ExecutorResponse` objects
- [ ] Webhook service stores and retrieves data by `run_id` with thread safety
- [ ] Unit tests pass with ≥ 30% coverage on new code
- [ ] `black --check app/src/` and `isort --check-only app/src/` pass
- [ ] `python scripts/evals.py` passes with no violations
- [ ] All services are importable via `from app.src.services import ...`
- [ ] Phase 2 tests still pass (no regression)
- [ ] `docs/implementation-context-phase-3.md` documents all implemented components

---

## Cross-Cutting Concerns

### Testing Strategy
- **E2E Testing Scenarios**: Not yet executable at the UI level (no UI in this phase). However, the complete service-layer chain — link project → generate actions → resolve payloads → dispatch → webhook — can be tested programmatically in integration tests. E2E scenarios E2E-001, E2E-002, and E2E-003 are validated at the service layer.
- **Unit Testing**: pytest with mocked httpx (GitHub API, executor API). Target ≥ 30% coverage on `app/src/`. Focus on action generator ordering, payload resolver variable coverage, and executor error handling.
- **Integration Testing**: Chain tests across services — link project with mocked GitHub → generate actions → resolve payloads → dispatch with mocked executor → store webhook data. These tests use temp directories for project persistence.

### Documentation Requirements
- **Developer Context Documentation**: `docs/implementation-context-phase-3.md`, `docs/components/phase-3-component-3-X-overview.md` per component
- **Agent Runbook**: No changes in this phase (services are not yet user-facing)
- **Code Documentation**: Google-style docstrings on all public functions and classes in `app/src/services/`
- **API Documentation**: Not applicable (webhook API endpoints are defined in Phase 4)
- **Architecture Decision Records**: Document decisions in implementation context: sync httpx over async, executor Protocol pattern, thread-safe webhook store, atomic project file writes, no-exception executor design
