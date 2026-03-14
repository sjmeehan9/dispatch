# Phase 4 Component 4.6 Overview — Load Project Screen

## Component Summary

Component 4.6 delivers the full saved-project loading experience at `/project/load`, replacing the route placeholder with a production-ready NiceGUI screen for listing, loading, and deleting persisted projects.

## What Was Implemented

### 1) New Load Project UI Module
- Added `app/src/ui/load_project.py` with:
  - `render_load_project(app_state)`
  - Internal `_project_service_for_saved_projects(app_state)` for local project operations
- Screen elements:
  - Title: **Load Project**
  - Empty-state message: `No saved projects. Link a new project to get started.`
  - **Link New Project** button (navigates to `/project/link`)
  - **Back to Home** button (navigates to `/`)

### 2) Project Listing and Load Workflow
- Uses `ProjectService.list_projects()` to render saved projects.
- Displays per-project summary details:
  - project name (clickable)
  - repository
  - updated timestamp
- Clicking a project name calls `ProjectService.load_project(project_id)`, updates `app_state.current_project`, and navigates to `/project/{project_id}`.

### 3) Delete Workflow with Confirmation
- Added per-project delete icon button.
- Clicking delete opens a confirmation dialog:
  - `Delete project {name}?`
- Confirm action calls `ProjectService.delete_project(project_id)` and refreshes the project list.

### 4) Refreshable List Behavior
- Project list section uses `@ui.refreshable`.
- Deletion refreshes only the listing region, avoiding a full page rerender.

### 5) Route Integration
- Updated `app/src/main.py`:
  - Imported `render_load_project`
  - Replaced `/project/load` placeholder content with the new screen renderer

## Secret/Environment Handling Notes

- The load screen does not require direct `.env/.env.local` file presence in the repository.
- Runtime token resolution prioritizes `GITHUB_TOKEN`, then `TOKEN` (GitHub Actions alias), then current-project token key, with a safe non-empty fallback for local-only list/load/delete operations.

## Testing

- Added `tests/test_load_project.py`:
  - Empty saved-project list rendering
  - Multiple saved-project summaries rendering
- Updated `tests/test_main.py`:
  - `/project/load` route now asserts expected screen content
- Verified via targeted test run:
  - `pytest -q tests/test_load_project.py tests/test_main.py`
