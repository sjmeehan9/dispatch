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
