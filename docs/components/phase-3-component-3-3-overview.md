# Phase 3 Component 3.3 Overview — Project Service: CRUD & Persistence

## Summary
Component 3.3 extends `ProjectService` with local project persistence APIs so linked projects can be saved, retrieved, listed, and deleted from the Dispatch data directory using OneDrive-safe atomic writes.

## Implemented Scope
- Updated `app/src/services/project_service.py`:
  - Added `ProjectNotFoundError`.
  - Added `ProjectSummary` dataclass (`project_id`, `project_name`, `repository`, `updated_at`).
  - Added `save_project(project: Project) -> None`.
  - Added `load_project(project_id: str) -> Project`.
  - Added `list_projects() -> list[ProjectSummary]`.
  - Added `delete_project(project_id: str) -> None`.
  - Added `_project_file_path(project_id: str) -> Path`.
- Updated `app/src/services/__init__.py` exports:
  - `ProjectNotFoundError`
  - `ProjectSummary`

## Key Behavior
- **Save**:
  - Refreshes `project.updated_at` to current UTC ISO-8601 (`Z` suffix).
  - Serializes with `project.model_dump(mode="json")` and pretty JSON indentation.
  - Writes to `{project_id}.json.tmp`, then atomically promotes via `os.replace`.
- **Load**:
  - Reads `{project_id}.json`, raises `ProjectNotFoundError` when missing.
  - Validates payload via `Project.model_validate(...)`.
- **List**:
  - Scans `projects_dir/*.json`.
  - Extracts summary fields only (no full `Project` validation for performance).
  - Skips malformed/missing-field files with WARNING logs.
  - Returns summaries sorted by `updated_at` descending.
- **Delete**:
  - Removes `{project_id}.json`.
  - Raises `ProjectNotFoundError` when the file does not exist.

## Error Handling
- File operation failures (`PermissionError`, `OSError`) are surfaced with descriptive context including project ID/path.
- Listing remains resilient to corrupt files by logging and continuing.

## Tests Added
- Extended `tests/test_project_service.py` with CRUD coverage:
  - save creates valid JSON file and updates timestamps,
  - save/load round-trip integrity,
  - missing-project load and delete exceptions,
  - list sorting and empty-project-directory behavior,
  - malformed JSON skip behavior in listing,
  - atomic write behavior via `os.replace` capture.

## Security & Secrets
- Persistence stores only the existing `github_token_env_key` reference (not token values).
- Existing secret alias behavior remains intact in `Settings`: `GITHUB_TOKEN` resolves to `TOKEN` in CI/Actions environments.
