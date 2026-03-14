# Phase 2 Implementation Context

## Component 2.1 - Core Data Models
- Implemented all required Phase 2 core models in `app/src/models/project.py`, `app/src/models/executor.py`, and `app/src/models/payload.py`.
- Added `ActionType` and `ActionStatus` enums plus validated `ComponentData`, `PhaseData`, `Action`, and `Project` models for phase-progress and action tracking data.
- Added repository format validation on `Project` (`owner/repo`) and default action lifecycle fields (`not_started`, null response payloads).
- Implemented validated executor models (`ExecutorConfig`, `ExecutorResponse`, `ActionTypeDefaults`) including URL validation for executor endpoints.
- Implemented payload models (`PayloadTemplate`, `ResolvedPayload`) with recursive placeholder extraction via `PayloadTemplate.get_variables()`.
- Updated `app/src/models/__init__.py` to export all public model classes for package-level imports.
- Added focused model tests in `tests/test_models.py` covering acceptance-criteria paths and validation failures.

### Decisions
- Used Pydantic v2 `BaseModel` consistently for all Component 2.1 models to provide uniform validation and serialization behavior.
- Added alias support for phase-progress keys (`phaseId`, `componentId`, etc.) while exposing Pythonic snake_case field names internally.
- Stored secret *environment key names* in models (`github_token_env_key`, `api_key_env_key`) rather than secret values.

### Deviations
- None.

## Component 2.2 - Application Settings Module
- Implemented configuration constants in `app/src/config/constants.py` covering data directory defaults, config filenames, env file naming, and phase/agent repository paths required by downstream services.
- Implemented `Settings` in `app/src/config/settings.py` to load environment values via `python-dotenv` from `.env/.env.local` without requiring that file to exist in the repository.
- Added typed directory properties (`data_dir`, `projects_dir`, `config_dir`) and `env_file_path`, plus `initialise_data_dir()` to create the dispatch data directory tree.
- Added secure secret resolution through `get_secret(env_key)` with no secret value logging.
- Added compatibility fallback so `get_secret("GITHUB_TOKEN")` reads `TOKEN` when running in GitHub environments that use restricted secret names.
- Added lazy singleton accessor `get_settings()` to provide one shared settings instance across modules.
- Updated `app/src/config/__init__.py` exports so `from app.src.config import Settings, get_settings` and constants imports work directly.
- Added focused tests in `tests/test_settings.py` validating environment override, default fallback, directory initialization, secret retrieval behavior, and singleton semantics.

### Decisions
- Kept `.env/.env.local` as a local runtime path reference while treating it as optional, preserving local-first behavior and compatibility with CI/repository secrets.
- Resolved token aliasing in `Settings` instead of duplicating logic across services, keeping secret-key translation centralized.

### Deviations
- Validation was executed with host Python 3.12 because the repository's Python 3.13 `.venv` is not present in this sandbox; tests passed and formatting checks were run on changed files.

## Component 2.3 - Config & Secrets Manager Service
- Implemented `ConfigManager` in `app/src/services/config_manager.py` to manage executor config, action type defaults, and local secrets.
- Added JSON persistence for `ExecutorConfig` and `ActionTypeDefaults` under `~/.dispatch/config/` with atomic write semantics (`.tmp` then replace) to reduce sync corruption risk.
- Implemented default bootstrap flow: when config files are missing, manager loads bundled defaults from `app/config/defaults.yaml`, persists them, and returns validated model instances.
- Implemented secrets write/update via `python-dotenv` `set_key()` against `.env/.env.local`, creating parent directories/files as needed so committed env files are not required.
- Implemented `list_secret_keys()` returning key names only (no values) and `has_config()` to verify both config JSON files are present.
- Added INFO-level structured logs for config/default file operations using file paths only; secret values are never logged.
- Added bundled defaults file `app/config/defaults.yaml` with Autopilot executor defaults and all five action-type payload templates.
- Added focused tests in `tests/test_config_manager.py` for round-trip persistence, default bootstrap, secret write/update behavior, key listing, config presence checks, and atomic JSON write behavior.

### Decisions
- Kept secrets optional and local-file-based at runtime while preserving CI compatibility with GitHub repository/environment secrets (`TOKEN` alias handled in `Settings`).
- Used model validation (`model_validate`) at all load boundaries to fail fast on malformed JSON/YAML.

### Deviations
- None.

## Component 2.4 - Default Executor Configuration
- Updated `app/config/defaults.yaml` to the Component 2.4 schema with top-level `executor` and `action_type_defaults` keys.
- Added complete Autopilot executor defaults (`executor_id`, `executor_name`, `api_endpoint`, `api_key_env_key`, `webhook_url`) with an empty webhook value for user-provided callbacks.
- Reworked all five action templates (`implement`, `test`, `review`, `document`, `debug`) to match the documented Autopilot payload shape from `docs/sample-payload.json`.
- Standardized template placeholders (`{{repository}}`, `{{branch}}`, `{{agent_paths}}`, `{{webhook_url}}`) and added component/phase placeholders where required by the component spec.
- Set role mapping to Autopilot-compatible values: `implement` for implement/test/document/debug and `review` for review.
- Added `pr_number: "{{pr_number}}"` in the review template and kept debug `agent_instructions` empty for user-supplied troubleshooting prompts.
- Added YAML comments documenting each placeholder so defaults remain understandable and editable by users.
- Updated `ConfigManager._load_defaults()` to read the new `executor` key (while keeping compatibility with legacy `executor_config`) and fail fast if required sections are missing.
- Added focused tests in `tests/test_config_manager.py` validating: YAML parse success, model validation (`ExecutorConfig`, `ActionTypeDefaults`), and required placeholders/roles across all templates.

### Decisions
- Kept backward compatibility in `_load_defaults()` for `executor_config` to avoid breaking existing local persisted defaults during upgrade.
- Kept `agent_paths` as the `{{agent_paths}}` placeholder value to align with spec guidance that the resolver injects the discovered path array.

### Deviations
- None.
