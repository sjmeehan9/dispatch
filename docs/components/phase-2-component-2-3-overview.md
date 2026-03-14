# Phase 2 Component 2.3 Overview — Config & Secrets Manager Service

## Summary
Component 2.3 adds the persistence layer for executor configuration, action type defaults, and local secrets. It introduces a single service API that downstream UI and services can call without handling filesystem details directly.

## Implemented Scope
- Added `app/src/services/config_manager.py` with `ConfigManager`:
  - `get_executor_config()` / `save_executor_config()`
  - `get_action_type_defaults()` / `save_action_type_defaults()`
  - `set_secret()` / `list_secret_keys()`
  - `has_config()` and `_load_defaults()`
- Added bundled defaults file `app/config/defaults.yaml`:
  - Default Autopilot executor configuration
  - Default templates for implement/test/review/document/debug action types
- Added focused unit tests in `tests/test_config_manager.py`.

## Persistence Behavior
- Executor config and action type defaults are stored in `~/.dispatch/config/` as:
  - `executor.json`
  - `action-type-defaults.json`
- Writes are atomic (`*.tmp` then replace) to reduce corruption risk in synced storage.
- If config files are missing, defaults are loaded from `app/config/defaults.yaml`, saved to JSON, and returned.

## Secret Management Behavior
- Secrets are written to `.env/.env.local` using `python-dotenv` `set_key()`.
- The manager creates missing `.env` directories/files when needed, so no secret file is required in git.
- `list_secret_keys()` returns only key names and ignores comments/blank lines.
- Logging includes file paths for operations but never secret values.

## Validation Coverage
`tests/test_config_manager.py` validates:
- executor config save/load round-trip
- action defaults save/load round-trip
- default bootstrap path when config files are missing
- secret create/update behavior with reloaded settings lookup
- secret key listing behavior
- `has_config()` false/true transitions
- atomic-write temp file replacement behavior

## Design Notes
- The service builds on `Settings` for all path resolution and keeps token alias logic centralized there (`GITHUB_TOKEN` fallback to `TOKEN` in CI).
- Model validation is enforced at load time for YAML and JSON inputs to surface invalid data early.
