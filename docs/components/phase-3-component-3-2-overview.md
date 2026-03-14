# Phase 3 Component 3.2 Overview — Project Service: Linking & Scanning

## Summary
Component 3.2 delivers the core project-linking workflow in `ProjectService`. It validates repository input, loads and validates `docs/phase-progress.json` from GitHub, discovers agent files, and returns a fully populated `Project` model for downstream persistence and action generation.

## Implemented Scope
- Added `app/src/services/project_service.py`:
  - `ProjectLinkError` for link-domain failures.
  - `ProjectService` constructor with `Settings` and `GitHubClient` dependencies.
  - `link_project(repository, token_env_key) -> Project` orchestration method.
  - `_validate_repository(repository) -> tuple[str, str]` with strict `owner/repo` regex.
  - `_scan_phase_progress(owner, repo)` for required file fetch + JSON parsing.
  - `_parse_phase_progress(raw_data)` for structural validation and `PhaseData` parsing.
  - `_discover_agent_files(owner, repo)` for `.claude/agents/` and `.github/agents/` scanning.

## Key Behavior
- Fails early when:
  - repository format is invalid,
  - `token_env_key` is empty or unresolved via `Settings.get_secret()`,
  - `docs/phase-progress.json` is missing or invalid JSON,
  - required phase/component fields are absent.
- Translates GitHub errors into user-facing link errors:
  - not found → required phase-progress message,
  - auth failure → token/authentication guidance.
- Creates `Project` with:
  - UUID `project_id`,
  - raw `phase_progress` payload,
  - parsed `phases`,
  - discovered `agent_files`,
  - empty `actions`,
  - UTC ISO-8601 timestamps (`created_at`, `updated_at`).
- Logs link completion at INFO with phase/component/agent-file counts.

## Integration Updates
- Updated `app/src/services/__init__.py` to export:
  - `ProjectService`
  - `ProjectLinkError`

## Tests Added
- `tests/test_project_service.py` covering:
  - successful `link_project()` model construction,
  - invalid repository rejection,
  - missing `phase-progress.json` handling,
  - auth error handling,
  - camelCase-to-model field mapping in phase parsing,
  - agent file discovery from both directories,
  - empty discovery when directories are absent.

## Security Notes
- No secrets are persisted in the project model.
- The service stores only `github_token_env_key` and resolves token presence through environment-backed settings.
- CI compatibility is preserved through existing `Settings` support for `GITHUB_TOKEN` with `TOKEN` aliasing.
