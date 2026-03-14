# Phase 4 Component 4.5 Overview — Link New Project Screen

## Component Summary

Component 4.5 delivers the full Link New Project workflow at `/project/link`, replacing the placeholder route with a production-ready NiceGUI screen that links a GitHub repository, generates actions, resolves payload templates, saves the project, and navigates to the project main screen.

## What Was Implemented

### 1) New Link Project UI Module
- Added `app/src/ui/link_project.py` with:
  - `render_link_project(app_state)`
  - Internal async `_scan_and_link(app_state, repository, token_env_key)`
  - Internal `_normalise_link_error(...)` for user-facing error text mapping
- Screen elements:
  - **GitHub Repository** input with `owner/repo` validation
  - **GitHub Token Env Var** input (default `GITHUB_TOKEN`)
  - Secret guidance text referencing repository/environment secrets and `TOKEN` alias behavior in GitHub Actions
  - **Scan & Link** action button
  - **Back to Home** button (`/`)
  - Hidden-by-default spinner row that becomes visible during scan
  - Hidden-by-default result label for success/error output

### 2) Scan/Link Workflow
- `_scan_and_link(...)` now performs:
  1. Runtime token lookup from `Settings.get_secret(token_env_key)`
  2. Token-bound project service creation via `AppState.get_project_service(token)`
  3. Repository scan/link via `ProjectService.link_project(...)`
  4. Action generation from phases via `ActionGenerator.generate_actions(...)`
  5. Initial payload resolution per action via `PayloadResolver`
  6. Project persistence via `ProjectService.save_project(...)`
  7. Runtime state update (`app_state.current_project`)
- On success, UI shows summary counts and navigates to `/project/{project_id}`.

### 3) Error Handling
- Added required friendly message normalization for:
  - Missing `docs/phase-progress.json`
  - GitHub auth/token failures
- Added explicit token-missing guidance when configured env key is not available.

### 4) Route Integration
- Updated `app/src/main.py`:
  - Imported `render_link_project`
  - Replaced `/project/link` placeholder label with `render_link_project(app_state)`

## Testing

- Added `tests/test_link_project.py` with focused coverage for:
  - Successful scan/link + action generation/payload resolution/save flow
  - Missing token error path
  - Error normalization to required user-facing text
- Verified with:
  - `pytest -q tests/test_link_project.py tests/test_main.py`

## Design Notes

- Blocking link/save operations are executed via `run.io_bound(...)` to keep the NiceGUI event loop responsive.
- The component preserves secret-safety boundaries: only env-key names are entered in UI; secret values are never persisted or rendered.
- Integration is intentionally thin and reuses existing services/models without duplicating linking or payload logic.
