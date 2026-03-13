# Phase 2: Data Models, Configuration & Secrets Management

## Phase Overview

**Objective**: Build the complete data foundation — all Pydantic and dataclass models, application settings, configuration management, and secrets handling. This phase creates the layer that every subsequent service and UI component depends on.

**Deliverables**:
- Core data models (Project, Phase, Component, Action, ExecutorConfig, ExecutorResponse, PayloadTemplate) in `app/src/models/`
- Application settings module (`app/src/config/settings.py`) with environment loading and data directory management
- Config & Secrets manager service (`app/src/services/config_manager.py`) for reading/writing executor config, action type defaults, and secrets
- Default executor configuration in `app/config/defaults.yaml` with Autopilot defaults and all five action type payload templates
- Unit tests covering models, settings, and config manager with ≥ 30% coverage on new code

**Dependencies**:
- Phase 1 complete (repository structure, `pyproject.toml` with editable install, quality tooling)
- Python 3.13+ virtual environment activated
- `.env/.env.local` exists with at least `DISPATCH_DATA_DIR` set

## Phase Goals

- All data models are defined, importable, and validated with Pydantic v2 / dataclasses
- `Settings` class loads configuration from `.env/.env.local` with sensible defaults
- Data directory (`~/.dispatch/`) is created and structured on first application run
- Config manager can persist and retrieve executor configuration, action type defaults, and secrets
- Default Autopilot executor config loads automatically when no user config exists yet
- Secrets are read/written to `.env/.env.local` without being logged or exposed
- All new code passes Black, isort, evals, and achieves ≥ 30% test coverage

---

## Components

### Component 2.1 — Core Data Models

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.2: Repository structure and `pyproject.toml` must exist (package installable, `app/src/models/` directory exists)

**Features**:
- [AI Agent] Create `app/src/models/project.py` with Project, PhaseData, ComponentData, and Action dataclass/Pydantic models
- [AI Agent] Create `app/src/models/executor.py` with ExecutorConfig, ExecutorResponse, and ActionTypeDefaults Pydantic models
- [AI Agent] Create `app/src/models/payload.py` with PayloadTemplate and ResolvedPayload Pydantic models
- [AI Agent] Update `app/src/models/__init__.py` with public exports

**Description**:
This component defines every data structure the application will use — from the project and phase data loaded from `phase-progress.json` to executor configuration, payload templates, and action items. Pydantic v2 `BaseModel` is used for models requiring validation (executor config, API payloads, responses), while `dataclasses` with type hints are used for internal state objects. All models must handle expected edge cases (empty collections, optional fields, boundary values) and use comprehensive type hints per project conventions.

**Acceptance Criteria**:
- [ ] `Project` model can be instantiated from valid project data and serialised to JSON
- [ ] `PhaseData` and `ComponentData` models correctly represent the `phase-progress.json` structure
- [ ] `Action` model supports all five action types: implement, test, review, document, debug
- [ ] `Action` model tracks status (not-started, dispatched, completed), executor response, and webhook response
- [ ] `ExecutorConfig` validates required fields (executor_id, api_endpoint) and optional fields (webhook_url)
- [ ] `ExecutorResponse` captures status_code, message, and optional run_id
- [ ] `ActionTypeDefaults` holds payload templates for all five action types
- [ ] `PayloadTemplate` stores template strings with `{{variable}}` placeholders
- [ ] `ResolvedPayload` represents a fully resolved payload ready for dispatch
- [ ] All models reject invalid data with clear Pydantic validation errors
- [ ] `from app.src.models import Project, Action, ExecutorConfig` imports succeed

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/models/project.py`
  - `app/src/models/executor.py`
  - `app/src/models/payload.py`
  - `app/src/models/__init__.py` (update with exports)
- **Key Functions/Classes**:
  - `project.py`: `ActionType(StrEnum)`, `ActionStatus(StrEnum)`, `ComponentData(BaseModel)`, `PhaseData(BaseModel)`, `Action(BaseModel)`, `Project(BaseModel)`
  - `executor.py`: `ExecutorConfig(BaseModel)`, `ExecutorResponse(BaseModel)`, `ActionTypeDefaults(BaseModel)`
  - `payload.py`: `PayloadTemplate(BaseModel)`, `ResolvedPayload(BaseModel)`
- **Human/AI Agent**: AI Agent implements all models
- **Database Changes**: None — file-based storage
- **Dependencies**: pydantic>=2.0 (already declared in `pyproject.toml`)

**Detailed Implementation Requirements**:

- **File 1: `app/src/models/project.py`**: Define `ActionType` as a `StrEnum` with values `implement`, `test`, `review`, `document`, `debug`. Define `ActionStatus` as a `StrEnum` with values `not_started`, `dispatched`, `completed`. Define `ComponentData` as a Pydantic `BaseModel` mirroring the `phase-progress.json` component fields: `component_id: str`, `component_name: str`, `owner: str`, `priority: str`, `estimated_effort: str`, `status: str`. Define `PhaseData` as a `BaseModel` with `phase_id: int`, `phase_name: str`, `status: str`, `component_breakdown_doc: str`, `components: list[ComponentData]`. Define `Action` as a `BaseModel` with `action_id: str` (UUID string), `phase_id: int`, `component_id: str | None` (None for phase-level actions like test/review/document), `action_type: ActionType`, `payload: dict[str, Any]` (the resolved or edited payload), `status: ActionStatus` (default `not_started`), `executor_response: dict[str, Any] | None` (default None), `webhook_response: dict[str, Any] | None` (default None). Define `Project` as a `BaseModel` with `project_id: str` (UUID string), `project_name: str`, `repository: str` (owner/repo format), `github_token_env_key: str`, `phase_progress: dict[str, Any]` (raw parsed phase-progress.json), `phases: list[PhaseData]`, `agent_files: list[str]`, `actions: list[Action]` (default empty list), `created_at: str` (ISO 8601), `updated_at: str` (ISO 8601). Use `model_config = ConfigDict(use_enum_values=True)` on models containing enums so serialisation produces strings. Add a `model_validator` on `Project` to validate that `repository` matches the `owner/repo` format pattern.

- **File 2: `app/src/models/executor.py`**: Define `ExecutorConfig` as a Pydantic `BaseModel` with: `executor_id: str` (e.g. "autopilot"), `executor_name: str`, `api_endpoint: str` (validated as a URL), `api_key_env_key: str` (name of the env var holding the API key — never the key itself), `webhook_url: str | None` (optional). Define `ActionTypeDefaults` as a `BaseModel` with: `implement: dict[str, Any]`, `test: dict[str, Any]`, `review: dict[str, Any]`, `document: dict[str, Any]`, `debug: dict[str, Any]` — each holding the default payload template for that action type, where values may contain `{{variable}}` placeholder strings. Define `ExecutorResponse` as a `BaseModel` with: `status_code: int`, `message: str`, `run_id: str | None` (optional — returned by some executors like Autopilot), `raw_response: dict[str, Any] | None` (optional for full response body).

- **File 3: `app/src/models/payload.py`**: Define `PayloadTemplate` as a Pydantic `BaseModel` with: `template_fields: dict[str, Any]` — a dict where string values may contain `{{variable}}` placeholders. Add a `get_variables()` method that scans all string values in `template_fields` and returns a `set[str]` of variable names found (using regex `r'\{\{(\w+)\}\}'`). Define `ResolvedPayload` as a `BaseModel` with: `payload: dict[str, Any]` — the fully resolved payload with all placeholders replaced by concrete values, `unresolved_variables: list[str]` (default empty list) — any `{{variable}}` placeholders that could not be resolved (useful for signalling to the UI that manual editing is needed).

- **File 4: `app/src/models/__init__.py`**: Update to export all public classes: `ActionType`, `ActionStatus`, `ComponentData`, `PhaseData`, `Action`, `Project`, `ExecutorConfig`, `ExecutorResponse`, `ActionTypeDefaults`, `PayloadTemplate`, `ResolvedPayload`.

**Test Requirements**:
- [ ] Unit tests: `Project` instantiation with valid data, serialisation to/from JSON
- [ ] Unit tests: `Project` rejects invalid repository format (no slash)
- [ ] Unit tests: `Action` defaults (`status=not_started`, `executor_response=None`)
- [ ] Unit tests: `ExecutorConfig` validates API endpoint format
- [ ] Unit tests: `ActionTypeDefaults` holds all five action types
- [ ] Unit tests: `PayloadTemplate.get_variables()` correctly extracts `{{variable}}` names
- [ ] Unit tests: `ResolvedPayload` with empty unresolved_variables list

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-2-component-2-1-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-2.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
Use `from __future__ import annotations` at the top of each module for cleaner forward references. The `phase_progress` field on `Project` stores the raw JSON dict from the target repo (for reference and re-generation), while `phases` stores the parsed `PhaseData` list for structured access. Store environment variable *key names* (e.g. `GITHUB_TOKEN_project_id`) rather than actual secret values in models — secrets are resolved from the environment at runtime, never serialised.

---

### Component 2.2 — Application Settings Module

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.2: `.env/.env.example` and `.env/.env.local` must exist
- Component 2.1: Data models must be defined (settings references model types for type safety)

**Features**:
- [AI Agent] Create `app/src/config/settings.py` with `Settings` class for environment loading and data directory management
- [AI Agent] Create `app/src/config/constants.py` with application constants (directory names, file paths, defaults)
- [AI Agent] Update `app/src/config/__init__.py` with public exports
- [AI Agent] Implement data directory initialisation logic (`~/.dispatch/projects/`, `~/.dispatch/config/`)

**Description**:
This component creates the centralised settings module that loads environment variables from `.env/.env.local` via `python-dotenv`, manages the application data directory (`DISPATCH_DATA_DIR`), and provides typed access to all configuration values. The settings module is a singleton-style class used throughout the application to access paths, environment keys, and flags. It also handles first-run initialisation of the data directory structure.

**Acceptance Criteria**:
- [ ] `Settings` loads `DISPATCH_DATA_DIR` from environment with fallback to `~/.dispatch/`
- [ ] `Settings` provides typed properties for all directory paths: `projects_dir`, `config_dir`
- [ ] `Settings.initialise_data_dir()` creates `~/.dispatch/`, `~/.dispatch/projects/`, and `~/.dispatch/config/` if they don't exist
- [ ] `Settings` loads `.env/.env.local` on instantiation via `python-dotenv`
- [ ] `Settings` provides a method to retrieve a secret by env var name without logging the value
- [ ] `Settings` provides the `.env/.env.local` file path for the secrets manager to write to
- [ ] Constants are defined for default values (default data dir, config filenames, etc.)
- [ ] `from app.src.config import Settings` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/config/settings.py`
  - `app/src/config/constants.py`
  - `app/src/config/__init__.py` (update with exports)
- **Key Functions/Classes**:
  - `settings.py`: `Settings` class with `data_dir`, `projects_dir`, `config_dir` properties, `initialise_data_dir()`, `get_secret(env_key: str) -> str | None`
  - `constants.py`: `DEFAULT_DATA_DIR`, `PROJECTS_DIR_NAME`, `CONFIG_DIR_NAME`, `EXECUTOR_CONFIG_FILENAME`, `ACTION_DEFAULTS_FILENAME`, `ENV_FILE_PATH`
- **Human/AI Agent**: AI Agent implements all files
- **Dependencies**: python-dotenv>=1.0 (already declared in `pyproject.toml`)

**Detailed Implementation Requirements**:

- **File 1: `app/src/config/settings.py`**: Create a `Settings` class that: (1) On `__init__`, calls `load_dotenv()` with the path to `.env/.env.local` (resolved relative to the project root using `Path(__file__).resolve().parents[3] / ".env" / ".env.local"`). (2) Reads `DISPATCH_DATA_DIR` from `os.environ` with a fallback to `~/.dispatch/` (expanded via `Path.expanduser()`). (3) Exposes `data_dir: Path`, `projects_dir: Path` (data_dir / "projects"), `config_dir: Path` (data_dir / "config"), and `env_file_path: Path` (path to `.env/.env.local`). (4) Provides `initialise_data_dir()` method that creates `data_dir`, `projects_dir`, and `config_dir` using `Path.mkdir(parents=True, exist_ok=True)`. (5) Provides `get_secret(env_key: str) -> str | None` that reads the value from `os.environ.get(env_key)` — no logging of the return value. (6) Provides a module-level function `get_settings() -> Settings` that returns a lazily created singleton instance, so all modules reference the same settings.

- **File 2: `app/src/config/constants.py`**: Define application constants: `DEFAULT_DATA_DIR = "~/.dispatch/"`, `PROJECTS_DIR_NAME = "projects"`, `CONFIG_DIR_NAME = "config"`, `EXECUTOR_CONFIG_FILENAME = "executor.json"`, `ACTION_DEFAULTS_FILENAME = "action-type-defaults.json"`, `DEFAULTS_YAML_FILENAME = "defaults.yaml"`, `ENV_FILE_NAME = ".env.local"`, `ENV_DIR_NAME = ".env"`. Also define `PHASE_PROGRESS_PATH = "docs/phase-progress.json"` (the expected location in target repos), `CLAUDE_AGENTS_PATH = ".claude/agents/"`, `GITHUB_AGENTS_PATH = ".github/agents/"` for use by the project service in Phase 3.

- **File 3: `app/src/config/__init__.py`**: Update to export `Settings`, `get_settings`, and all constants.

**Test Requirements**:
- [ ] Unit tests: `Settings` with `DISPATCH_DATA_DIR` env var set uses that path
- [ ] Unit tests: `Settings` without `DISPATCH_DATA_DIR` falls back to `~/.dispatch/`
- [ ] Unit tests: `initialise_data_dir()` creates the expected directory structure in a temp directory
- [ ] Unit tests: `get_secret()` returns the value for a set env var and `None` for an unset one
- [ ] Unit tests: `get_settings()` returns the same instance on repeated calls (singleton)

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-2-component-2-2-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-2.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
The `Settings` singleton pattern avoids repeatedly loading `.env` files. Use `python-dotenv`'s `load_dotenv(override=False)` so that actual environment variables (set by the OS or CI) take precedence over `.env` file values. The path resolution for `.env/.env.local` uses the project root relative to the settings module file — this works because the package is installed in editable mode and the file layout is fixed. Never store secret values in the `Settings` object as attributes — only read them on demand via `get_secret()`.

---

### Component 2.3 — Config & Secrets Manager Service

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 2.1: Core data models (`ExecutorConfig`, `ActionTypeDefaults`) must be defined
- Component 2.2: `Settings` module must be implemented (provides directory paths and env file path)

**Features**:
- [AI Agent] Create `app/src/services/config_manager.py` with `ConfigManager` class
- [AI Agent] Implement read/write for executor configuration JSON
- [AI Agent] Implement read/write for action type defaults JSON
- [AI Agent] Implement read/write/update for secrets in `.env/.env.local`
- [AI Agent] Implement default config loading from `app/config/defaults.yaml` when no user config exists

**Description**:
This component implements the central configuration and secrets management service. It provides a clean API for the UI and other services to read and write executor configuration, action type default payload templates, and user secrets (GitHub tokens, API keys). Configuration is persisted as JSON files in the `~/.dispatch/config/` directory. Secrets are persisted to `.env/.env.local` using a safe read-modify-write approach. When no user configuration exists (first run), the manager loads sensible defaults from the bundled `app/config/defaults.yaml`.

**Acceptance Criteria**:
- [ ] `ConfigManager` can save an `ExecutorConfig` to `~/.dispatch/config/executor.json` and read it back
- [ ] `ConfigManager` can save `ActionTypeDefaults` to `~/.dispatch/config/action-type-defaults.json` and read it back
- [ ] `ConfigManager` returns the default Autopilot config when no `executor.json` exists
- [ ] `ConfigManager` returns default action type templates when no `action-type-defaults.json` exists
- [ ] `ConfigManager` can write a new secret key-value pair to `.env/.env.local`
- [ ] `ConfigManager` can update an existing secret in `.env/.env.local` without corrupting other entries
- [ ] `ConfigManager` can list all secret key names (not values) from `.env/.env.local`
- [ ] `ConfigManager` never logs secret values at any log level
- [ ] `.env/.env.local` remains excluded from version control after writes

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/services/config_manager.py`
- **Key Functions/Classes**:
  - `ConfigManager.__init__(settings: Settings)`
  - `ConfigManager.get_executor_config() -> ExecutorConfig`
  - `ConfigManager.save_executor_config(config: ExecutorConfig) -> None`
  - `ConfigManager.get_action_type_defaults() -> ActionTypeDefaults`
  - `ConfigManager.save_action_type_defaults(defaults: ActionTypeDefaults) -> None`
  - `ConfigManager.set_secret(key: str, value: str) -> None`
  - `ConfigManager.list_secret_keys() -> list[str]`
  - `ConfigManager.has_config() -> bool` (checks if executor config and action type defaults both exist)
  - `ConfigManager._load_defaults() -> tuple[ExecutorConfig, ActionTypeDefaults]`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: pyyaml>=6.0, pydantic>=2.0, python-dotenv>=1.0 (all already declared)

**Detailed Implementation Requirements**:

- **File 1: `app/src/services/config_manager.py`**: Create a `ConfigManager` class that accepts a `Settings` instance. For **executor config**: `get_executor_config()` reads `{config_dir}/executor.json`, parses it into an `ExecutorConfig` model, and returns it. If the file doesn't exist, call `_load_defaults()` to load from `app/config/defaults.yaml`, save the default to `executor.json`, and return it. `save_executor_config()` serialises the `ExecutorConfig` to JSON and writes it atomically (write to a `.tmp` file first, then rename — prevents corruption on crash or OneDrive sync conflict). For **action type defaults**: identical read/save pattern using `{config_dir}/action-type-defaults.json` and the `ActionTypeDefaults` model. For **secrets**: `set_secret(key, value)` reads the current `.env/.env.local` file, updates or appends the `KEY=VALUE` line, and writes the file back. Use `python-dotenv`'s `set_key()` function for safe writes. `list_secret_keys()` reads `.env/.env.local` and returns a list of all key names (filtering out comments and blank lines). For **default loading**: `_load_defaults()` reads `app/config/defaults.yaml` (resolved relative to the package root), parses the YAML, and constructs `ExecutorConfig` and `ActionTypeDefaults` instances from the parsed data. `has_config()` returns `True` if both `executor.json` and `action-type-defaults.json` exist in the config directory. Add structured logging at INFO level for config read/write operations (file paths only — never values containing secrets). Use `json.dumps(indent=2)` for human-readable JSON output.

**Test Requirements**:
- [ ] Unit tests: Save and load `ExecutorConfig` round-trip in a temp directory
- [ ] Unit tests: Save and load `ActionTypeDefaults` round-trip in a temp directory
- [ ] Unit tests: Default config loaded when no `executor.json` exists
- [ ] Unit tests: `set_secret()` writes to `.env` file and can be read back via `get_secret()`
- [ ] Unit tests: `set_secret()` updates an existing key without corrupting the file
- [ ] Unit tests: `list_secret_keys()` returns expected keys
- [ ] Unit tests: `has_config()` returns `False` before saving, `True` after
- [ ] Unit tests: Atomic file write (verify `.tmp` file handling)

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-2-component-2-3-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-2.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
Atomic file writes are important because the `~/.dispatch/` directory may be synced via OneDrive. A partial write could result in a corrupted JSON file on another device. The pattern is: write to `executor.json.tmp`, then `os.replace("executor.json.tmp", "executor.json")` — `os.replace` is atomic on most filesystems. For secrets, `python-dotenv`'s `set_key()` handles the line-level update safely. Never read the value of a secret into a variable named similarly to the key — use a generic `value` parameter to avoid accidental logging.

---

### Component 2.4 — Default Executor Configuration

**Priority**: Must-have

**Estimated Effort**: 1 hour

**Owner**: AI Agent

**Dependencies**:
- Component 2.1: `ExecutorConfig` and `ActionTypeDefaults` models must be defined
- Component 2.3: `ConfigManager._load_defaults()` must reference this file

**Features**:
- [AI Agent] Create `app/config/defaults.yaml` with full Autopilot executor default configuration
- [AI Agent] Include all five action type payload templates with `{{variable}}` placeholders
- [AI Agent] Align payload templates with the sample payload structure from `docs/sample-payload.json`
- [AI Agent] Align payload templates with the Autopilot API roles documented in `docs/autopilot-runbook.md`

**Description**:
This component creates the bundled default configuration file that provides a working Autopilot executor setup out of the box. When a user first runs Dispatch and no executor configuration has been saved yet, the `ConfigManager` loads these defaults to populate the executor config and action type default templates. The payload templates use `{{variable}}` placeholders that the Payload Resolver (Phase 3) will interpolate with project-specific values. Templates must align with the actual Autopilot API payload structure.

**Acceptance Criteria**:
- [ ] `app/config/defaults.yaml` exists and is valid YAML
- [ ] YAML contains a complete `executor` section with Autopilot defaults (id, name, endpoint, api_key_env_key, webhook_url)
- [ ] YAML contains an `action_type_defaults` section with templates for all five types: implement, test, review, document, debug
- [ ] Implement template includes: `repository`, `branch`, `agent_instructions`, `model`, `role` (= "implement"), `agent_paths`, `callback_url`, `timeout_minutes`
- [ ] Test template includes: `repository`, `branch`, `agent_instructions`, `model`, `role` (= "implement"), `agent_paths`, `callback_url`, `timeout_minutes`
- [ ] Review template includes: `repository`, `branch`, `agent_instructions`, `model`, `role` (= "review"), `pr_number`, `agent_paths`, `callback_url`, `timeout_minutes`
- [ ] Document template includes: `repository`, `branch`, `agent_instructions`, `model`, `role` (= "implement"), `agent_paths`, `callback_url`, `timeout_minutes`
- [ ] Debug template includes: `repository`, `branch`, `agent_instructions` (empty — user fills in), `model`, `role` (= "implement"), `agent_paths`, `callback_url`, `timeout_minutes`
- [ ] All templates use `{{variable}}` placeholders for dynamic values
- [ ] `ConfigManager._load_defaults()` can successfully parse this file into `ExecutorConfig` and `ActionTypeDefaults`

**Technical Details**:
- **Files to Create/Modify**:
  - `app/config/defaults.yaml` (replace `.gitkeep` if present)
- **Key Functions/Classes**: None — YAML configuration file
- **Human/AI Agent**: AI Agent creates the YAML file
- **Dependencies**: PyYAML for parsing (already declared)

**Detailed Implementation Requirements**:

- **File 1: `app/config/defaults.yaml`**: Create a YAML file with two top-level keys: `executor` and `action_type_defaults`. The `executor` section should contain: `executor_id: "autopilot"`, `executor_name: "Autopilot"`, `api_endpoint: "http://localhost:8000/agent/run"`, `api_key_env_key: "AUTOPILOT_API_KEY"`, `webhook_url: ""` (empty string — user sets their ngrok URL). The `action_type_defaults` section should contain five keys (`implement`, `test`, `review`, `document`, `debug`), each being a dict representing the payload template for that action type. Use the following placeholders consistently: `{{repository}}` for the GitHub repo (owner/repo), `{{branch}}` for the target branch (default "main"), `{{phase_id}}` for the phase number, `{{phase_name}}` for the phase name, `{{component_id}}` for the component ID (Implement only), `{{component_name}}` for the component name (Implement only), `{{component_breakdown_doc}}` for the component breakdown doc path, `{{agent_paths}}` for the discovered agent file paths (JSON array), `{{webhook_url}}` for the callback URL, `{{pr_number}}` for the PR number (Review only). The `agent_instructions` field should contain a meaningful default instruction string that incorporates placeholders — e.g., for implement: `"Implement {{component_name}} ({{component_id}}) of Phase {{phase_id}}. Follow the component breakdown in {{component_breakdown_doc}}."`. For test: `"Test Phase {{phase_id}} ({{phase_name}}). Run all tests and validate all components are working correctly."`. For review: `"Review Phase {{phase_id}} ({{phase_name}}). Check code quality, standards compliance, and correctness."`. For document: `"Create documentation for Phase {{phase_id}} ({{phase_name}}). Generate the phase summary and update implementation context."`. For debug: leave `agent_instructions` as an empty string (user fills in the specific debug task). Set `model: "claude-opus-4.6"` for all types. Set `role: "implement"` for implement, test, document, and debug; `role: "review"` for review. Set `timeout_minutes: 30` for implement, test, and debug; `15` for review; `20` for document.

**Test Requirements**:
- [ ] Unit tests: YAML file parses without errors
- [ ] Unit tests: Parsed executor section maps to a valid `ExecutorConfig` instance
- [ ] Unit tests: Parsed action_type_defaults section maps to a valid `ActionTypeDefaults` instance
- [ ] Unit tests: All five action type templates contain expected `{{variable}}` placeholders

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-2-component-2-4-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-2.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
The YAML file is bundled with the package (in `app/config/`) and should be referenced using `importlib.resources` or a path relative to the package root in `ConfigManager._load_defaults()`. This approach ensures the defaults are accessible regardless of where the package is installed. Keep the YAML human-readable with comments explaining each placeholder variable's purpose. The `role` values must align with the Autopilot API's accepted roles: `implement`, `review`, `merge`. For Dispatch's "test" and "document" action types, the Autopilot role is still `implement` (the agent instructions convey the specific task).

---

### Component 2.5 — Unit Tests, Validation & Phase Documentation

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 2.1: All data models defined
- Component 2.2: Settings module implemented
- Component 2.3: Config manager implemented
- Component 2.4: Default YAML configuration created

**Features**:
- [AI Agent] Create comprehensive unit tests for all Phase 2 modules in `tests/`
- [AI Agent] Achieve ≥ 30% test coverage on new `app/src/` code from this phase
- [AI Agent] Run full quality validation (Black, isort, pytest, evals)
- [AI Agent] Validate E2E scenario preconditions — verify that the data foundation supports all five E2E scenarios
- [AI Agent] Create/update phase implementation context documentation

**Description**:
This component completes Phase 2 by writing comprehensive unit tests that exercise all data models, settings, config manager, and default configuration. It validates that the data layer is solid enough to support the service layer in Phase 3. Tests use temporary directories and mock environments to avoid touching the real `~/.dispatch/` directory or `.env` files. After tests pass, the full quality suite is run to confirm compliance with project standards.

**Acceptance Criteria**:
- [ ] Unit tests exist in `tests/test_models.py`, `tests/test_settings.py`, `tests/test_config_manager.py`
- [ ] All unit tests pass: `pytest -q --cov=app/src --cov-report=term-missing`
- [ ] Test coverage on `app/src/` is ≥ 30%
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes
- [ ] `python scripts/evals.py` passes (all public functions have docstrings, no TODO/FIXME)
- [ ] E2E scenario precondition check: models can represent the data needed for all five scenarios
- [ ] `docs/implementation-context-phase-2.md` exists with entries for all Phase 2 components

**Technical Details**:
- **Files to Create/Modify**:
  - `tests/test_models.py`
  - `tests/test_settings.py`
  - `tests/test_config_manager.py`
  - `docs/implementation-context-phase-2.md`
  - `docs/components/phase-2-component-2-5-overview.md`
- **Key Functions/Classes**:
  - `test_models.py`: Test classes for each model (Project, Action, ExecutorConfig, etc.)
  - `test_settings.py`: Test Settings initialisation, directory creation, secret retrieval
  - `test_config_manager.py`: Test config CRUD, secrets CRUD, default loading
- **Human/AI Agent**: AI Agent writes all tests and documentation
- **Dependencies**: pytest, pytest-cov (declared in `pyproject.toml`)

**Detailed Implementation Requirements**:

- **File 1: `tests/test_models.py`**: Create test functions covering: (1) `Project` instantiation with valid data including all fields, serialisation to dict via `model_dump()`, and deserialisation via `model_validate()`. (2) `Project` validation rejects repository without slash character. (3) `Action` defaults — verify `status` defaults to `not_started`, `executor_response` defaults to `None`. (4) `Action` with all five `ActionType` values. (5) `ComponentData` and `PhaseData` from a sample `phase-progress.json` fragment. (6) `ExecutorConfig` with valid data and rejection of missing required fields. (7) `ActionTypeDefaults` with all five action type templates. (8) `PayloadTemplate.get_variables()` correctly extracts `{{repository}}`, `{{branch}}`, `{{component_id}}` from a template string. (9) `ResolvedPayload` with empty `unresolved_variables`. Use `pytest.raises(ValidationError)` for rejection tests.

- **File 2: `tests/test_settings.py`**: Create test functions using the `tmp_data_dir` and `mock_env` fixtures from `conftest.py`. Test: (1) `Settings` reads `DISPATCH_DATA_DIR` from env when set. (2) `Settings` falls back to `~/.dispatch/` when env var is unset. (3) `initialise_data_dir()` creates the expected directory tree in a temp directory. (4) `get_secret()` returns the value for a present env var. (5) `get_secret()` returns `None` for an absent env var. (6) `get_settings()` returns the same instance on repeated calls. Patch `os.environ` and data directory paths to use temp directories — never touch the real `~/.dispatch/`.

- **File 3: `tests/test_config_manager.py`**: Create test functions using temp directories. Test: (1) `save_executor_config()` + `get_executor_config()` round-trip. (2) `get_executor_config()` loads defaults when no file exists. (3) `save_action_type_defaults()` + `get_action_type_defaults()` round-trip. (4) `get_action_type_defaults()` loads defaults when no file exists. (5) `set_secret()` writes a key-value to a temp `.env` file. (6) `set_secret()` updates an existing key without corrupting other entries. (7) `list_secret_keys()` returns expected keys from a populated `.env` file. (8) `has_config()` returns `False` before saves, `True` after both executor config and action type defaults are saved. Create a temp `.env` file and temp config directory for each test using pytest fixtures.

- **File 4: `docs/implementation-context-phase-2.md`**: Create the running log with entries for Components 2.1–2.5. Each entry should include: component ID and name, status (completed), key files created, notable decisions (e.g. "Pydantic v2 for validated models, dataclasses avoided in favour of uniform Pydantic usage", "atomic file writes for OneDrive safety", "env var key names stored in models, not secret values").

**Test Requirements**:
- [ ] All tests in `tests/test_models.py`, `tests/test_settings.py`, `tests/test_config_manager.py` pass
- [ ] `pytest -q --cov=app/src --cov-report=term-missing` reports ≥ 30% coverage
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes
- [ ] `python scripts/evals.py` passes

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing with ≥ 30% coverage
- [ ] All quality checks pass (Black, isort, pytest, evals)
- [ ] Documentation created: Component Overview (`docs/components/phase-2-component-2-5-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-2.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality (Phase 1 tests still pass)
- [ ] Core application is still working post component implementation

**Notes**:
Use pytest's `tmp_path` fixture for creating isolated temp directories for each test. For testing `.env` file operations, create a temporary `.env` file in `tmp_path` and patch `Settings.env_file_path` to point to it. The `conftest.py` from Phase 1 already provides `tmp_data_dir` and `mock_env` fixtures — extend these if needed but don't duplicate functionality. Keep tests focused on the happy path and one or two error cases per model/function — avoid exhaustive edge-case testing (we're targeting 30% coverage, not 90%).

---

## Phase Acceptance Criteria

- [ ] All data models instantiate correctly with valid data and reject invalid data
- [ ] `Settings` loads `DISPATCH_DATA_DIR` from environment with fallback to `~/.dispatch/`
- [ ] Config manager reads/writes executor config JSON to the data directory
- [ ] Config manager reads/writes action type default templates to the data directory
- [ ] Secrets manager writes to `.env/.env.local` and reads them back without exposing values in logs
- [ ] Default Autopilot executor config loads correctly when no user config exists
- [ ] Data directory `~/.dispatch/projects/` and `~/.dispatch/config/` are created on first run
- [ ] Unit tests pass with ≥ 30% coverage on new code
- [ ] `black --check app/src/` and `isort --check-only app/src/` pass
- [ ] `python scripts/evals.py` passes with no violations
- [ ] All models are importable via `from app.src.models import ...`
- [ ] All config classes are importable via `from app.src.config import ...`
- [ ] `docs/implementation-context-phase-2.md` documents all implemented components

---

## Cross-Cutting Concerns

### Testing Strategy
- **E2E Testing Scenarios**: Not yet executable (no UI or services). Data models must support all five E2E scenario data flows — verified structurally in Component 2.5.
- **Unit Testing**: pytest with `tmp_path` fixtures for isolated directory operations. Target ≥ 30% coverage on `app/src/`. Focus on model validation, config round-trips, and settings initialisation.
- **Integration Testing**: Minimal — config manager tests exercise the full read/write/default-loading flow, which is effectively an integration test against the local filesystem.

### Documentation Requirements
- **Developer Context Documentation**: `docs/implementation-context-phase-2.md`, `docs/components/phase-2-component-2-X-overview.md` per component
- **Agent Runbook**: No changes in this phase (no runnable application yet)
- **Code Documentation**: Google-style docstrings on all public functions and classes in `app/src/models/`, `app/src/config/`, `app/src/services/config_manager.py`
- **API Documentation**: Not applicable in this phase (no API endpoints)
- **Architecture Decision Records**: Document decisions in implementation context: Pydantic v2 over dataclasses for all models (uniform validation), atomic file writes for OneDrive compatibility, env var key names in models (not secret values)
