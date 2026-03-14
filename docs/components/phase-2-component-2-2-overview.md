# Phase 2 Component 2.2 Overview — Application Settings Module

## Summary
Component 2.2 establishes the shared configuration/settings layer used by Dispatch services. It introduces typed constants, an environment-aware settings class, and a singleton accessor so all modules resolve paths and secrets consistently.

## Implemented Scope
- Added `app/src/config/constants.py` with application and repository path constants:
  - Data/config directory defaults (`DEFAULT_DATA_DIR`, `PROJECTS_DIR_NAME`, `CONFIG_DIR_NAME`)
  - Config filenames (`EXECUTOR_CONFIG_FILENAME`, `ACTION_DEFAULTS_FILENAME`, `DEFAULTS_YAML_FILENAME`)
  - Env naming (`ENV_DIR_NAME`, `ENV_FILE_NAME`)
  - Repo scan paths for Phase 3 integration (`PHASE_PROGRESS_PATH`, `CLAUDE_AGENTS_PATH`, `GITHUB_AGENTS_PATH`)
- Implemented `app/src/config/settings.py`:
  - Loads dotenv from `Path(__file__).resolve().parents[3] / ".env" / ".env.local"` with `override=False`
  - Resolves `DISPATCH_DATA_DIR` with fallback to `~/.dispatch/`
  - Exposes `data_dir`, `projects_dir`, `config_dir`, and `env_file_path`
  - Provides `initialise_data_dir()` for first-run directory creation
  - Provides `get_secret(env_key)` for on-demand secret lookup
  - Supports GitHub CI alias fallback: `GITHUB_TOKEN` → `TOKEN`
  - Adds lazy singleton accessor `get_settings()`
- Updated `app/src/config/__init__.py` exports for package-level imports.

## Validation Added
`tests/test_settings.py` now covers:
- `DISPATCH_DATA_DIR` override behavior
- default data dir fallback
- directory creation via `initialise_data_dir()`
- `get_secret()` present/missing behavior
- `TOKEN` alias support when requesting `GITHUB_TOKEN`
- singleton stability of `get_settings()`

## Design Notes
- `.env/.env.local` remains a local optional file path, but the settings loader does not require it to exist in-repo.
- Runtime environment variables still take precedence over dotenv values, enabling GitHub Secrets/Environment Secrets usage in CI and hosted automation.
- Secret values are never persisted in settings object attributes and are only read on demand.
