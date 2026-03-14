# Phase 4 Implementation Context

## Component 4.1 - NiceGUI App Entry Point & Routing
- Implemented `AppState` in `app/src/ui/state.py` as the shared runtime container for UI screens.
- Eagerly wired token-independent services: `Settings`, `ConfigManager`, `WebhookService`, `ActionGenerator`, `PayloadResolver`, and `AutopilotExecutor`.
- Added lazy factory methods `get_github_client(token)` and `get_project_service(token)` so GitHub-dependent services are created only when a token is available.
- Added config gate properties:
  - `is_executor_configured`
  - `is_action_types_configured`
  - `is_fully_configured`
  These now return `False` when config files are missing and validate persisted files when present.
- Replaced `app/src/main.py` stub with full NiceGUI app routing for all required paths:
  - `/`
  - `/config/executor`
  - `/config/action-types`
  - `/config/secrets`
  - `/project/link`
  - `/project/load`
  - `/project/{project_id}`
- Registered FastAPI webhook endpoints on the NiceGUI app:
  - `POST /webhook/callback` stores payloads by `run_id` via `WebhookService`
  - `GET /webhook/poll/{run_id}` returns stored payloads or `404` pending payload when absent
- Added `_ensure_run_config()` so ASGI lifespan startup works for automated tests that use `TestClient` without launching a real server process.
- Updated `app/src/ui/__init__.py` to export `AppState`.
- Added focused tests:
  - `tests/test_app_state.py` for state/service initialization and config gate checks
  - `tests/test_main.py` for route registration and webhook endpoint behavior

### Decisions
- Chose a module-level singleton `app_state` in `main.py` to match the single-process NiceGUI runtime model.
- Kept route renderers as lightweight placeholders (`ui.label`) per Component 4.1 scope; full screens are implemented in Components 4.2+.
- Kept GitHub token handling runtime-only; no `.env/.env.local` dependency was introduced in repository code paths.

### Deviations
- Validation and execution ran under Python 3.12 in this sandbox; project CI target remains Python 3.13+.

## Component 4.2 - Initial Screen
- Implemented `render_initial_screen(app_state)` in `app/src/ui/initial_screen.py`.
- Added centered initial-screen layout using NiceGUI cards/columns with the title `Dispatch`.
- Added configuration status indicators driven by `AppState`:
  - Executor Config
  - Action Type Defaults
- Added navigation buttons for:
  - `/config/executor`
  - `/config/action-types`
  - `/config/secrets`
  - `/project/link`
  - `/project/load`
- Implemented config gatekeeping for project operations:
  - `Link New Project` and `Load Project` are disabled unless `app_state.is_fully_configured` is `True`.
- Updated `/` route in `app/src/main.py` to call `render_initial_screen(app_state)` instead of the placeholder label.
- Added focused tests:
  - `tests/test_initial_screen.py` verifies project button disable/enable logic by stubbing NiceGUI primitives.
  - `tests/test_main.py` now asserts root response contains initial-screen content and expected navigation actions.

### Decisions
- Kept disable logic at render time (not reactive state mutation) so revisiting `/` naturally reflects latest persisted configuration.
- Encapsulated repeated UI fragments into internal helpers (`_status_row`, `_project_button`) for readability without expanding public API surface.

### Deviations
- None.

## Component 4.7 - Main Screen Layout & Action List
- Implemented `render_main_screen(app_state, project_id)` in `app/src/ui/main_screen.py`.
- Added project bootstrap-on-route-load behavior:
  - Loads project from storage when `current_project` is missing or route `project_id` differs.
  - Redirects to `/` with clear error notifications when project loading fails.
- Added main-screen header controls:
  - Project name display
  - `Save` button wired to `ProjectService.save_project(...)`
  - `Home` button wired to `/`
- Added split-panel workspace using NiceGUI `ui.splitter(value=40)` with:
  - Left panel: scrollable phase-grouped action list
  - Right panel: placeholder card reserved for Component 4.8 response rendering
- Implemented left-panel action rendering:
  - Grouped by phase with expansion sections (`Phase X: Name`)
  - Action icon mapping per type (`implement`, `test`, `review`, `document`, `debug`)
  - Implement-action labels resolve human-friendly component names from phase metadata
  - Status badges with required colors (`grey`, `blue`, `green`)
- Implemented dispatch workflow in `_dispatch_action(...)`:
  - Loads executor config
  - Builds payload context from project + action + executor settings
  - Resolves payload placeholders via `PayloadResolver`
  - Dispatches through `AutopilotExecutor`
  - Stores normalized executor response on action
  - Marks action as `dispatched`
  - Auto-saves updated project state
- Added per-item loading state while dispatch is in progress using `dispatching_action_id` and refreshable list rendering.
- Updated route wiring in `app/src/main.py` so `/project/{project_id}` now renders the real main screen module.
- Added `tests/test_main_screen.py` with focused coverage for:
  - Phase grouping correctness and in-phase action order preservation
  - Dispatch path behavior (payload resolution, executor call, status update, response persistence, save call)

### Decisions
- Reused the same token fallback pattern used in load/link flows (`current project token -> GITHUB_TOKEN -> TOKEN -> local-project-access`) for local project file operations.
- Kept response panel implementation intentionally minimal in this component per phase scope, with an explicit placeholder for Component 4.8.

### Deviations
- None.

## Component 4.9 - Debug Action Insertion & Payload Editing
- Extended `app/src/ui/main_screen.py` with debug insertion and payload editing workflows.
- Added new helper functions:
  - `_insert_debug_action(app_state, phase_id, position)`
  - `_show_insert_debug_dialog(app_state, phase_id, phase_action_count, ...)`
  - `_show_payload_editor(app_state, project_service, action, ...)`
  - `_save_edited_payload(action, new_payload_json)`
  - `_find_unresolved_variables(payload_json)`
- Added an **Add Debug** control to each phase group in the action list.
- Implemented insertion-position dialog with bounded input (`0..N`) per phase.
- Wired debug insertion to `ActionGenerator.insert_debug_action(...)` and immediate project persistence.
- Added best-effort payload resolution for newly inserted debug actions via `PayloadResolver`.
- Added an **Edit Payload** action control on each action row.
- Implemented payload editor dialog with:
  - JSON textarea pre-populated from current action payload
  - Save/Cancel actions
  - strict JSON-object validation before save
  - unresolved placeholder detection (`{{variable}}`) displayed as warning labels
- Saving a payload now updates the action payload in memory, persists project state, and refreshes both action/response panels.
- Added focused tests in `tests/test_main_screen.py` for:
  - `_save_edited_payload()` invalid JSON rejection
  - `_save_edited_payload()` valid JSON update
  - `_insert_debug_action()` insertion position, payload resolution, and persistence

### Decisions
- Kept payload editing as raw JSON to stay executor-agnostic and support variable payload shapes.
- Persisted debug insertion and payload edits immediately to avoid losing mid-session changes.
- Displayed unresolved placeholders as warnings (not hard errors) so users can intentionally keep late-bound template variables.

### Deviations
- None.

## Component 4.3 - Executor Configuration Screen
- Implemented `render_executor_config(app_state)` in `app/src/ui/executor_config.py`.
- Built a full executor configuration form at `/config/executor` with fields for:
  - Executor Name
  - API Endpoint URL
  - API Key Environment Variable
  - Webhook URL (optional)
- Added inline input validation using NiceGUI `validation` callbacks:
  - Required checks for executor name, API endpoint, and API key env var.
  - URL format checks (`http://` or `https://`) for API endpoint and optional webhook.
- Added save workflow:
  - Validates inputs before save and shows negative notifications for invalid fields.
  - Builds an `ExecutorConfig` model and persists it through `ConfigManager.save_executor_config`.
  - Reloads application config via `app_state.reload_config()` after successful save.
  - Shows positive notification after successful persistence.
- Added pre-population behavior:
  - Loads existing config values when `executor.json` is already persisted.
  - Falls back to defaults (`autopilot`, `AUTOPILOT_API_KEY`, empty URLs) when no file exists yet.
- Added executor ID derivation from executor name to keep persisted IDs stable and URL-safe.
- Added navigation control:
  - "Back to Home" button routes users to `/`.
- Updated route wiring in `app/src/main.py`:
  - Replaced `/config/executor` placeholder label with `render_executor_config(app_state)`.
- Added focused tests:
  - `tests/test_executor_config.py` for pre-populate, valid save, validation failure, and back navigation.
  - `tests/test_main.py` route-content assertion for executor config form labels.

### Decisions
- Kept API key handling as env-var *name only* in UI/model, preserving the security boundary (no key values stored in executor config JSON).
- Avoided introducing any repository dependency on `.env/.env.local`; screen persists only non-secret config metadata.

### Deviations
- None.

## Component 4.4 - Action Type Defaults & Secrets Screens
- Implemented `render_action_type_defaults(app_state)` in `app/src/ui/action_type_defaults.py`.
- Added full `/config/action-types` editor with:
  - Five action-type tabs (`implement`, `test`, `review`, `document`, `debug`)
  - Per-type payload field controls for all template keys in persisted defaults
  - Typed controls (`ui.textarea` for `agent_instructions`, `ui.number` for `timeout_minutes`, `ui.input` for other keys)
  - Variable hint expansion panel documenting all supported `{{placeholders}}`
  - Save workflow to `ConfigManager.save_action_type_defaults(...)` plus `app_state.reload_config()`
- Implemented `render_secrets_screen(app_state)` in `app/src/ui/secrets_screen.py`.
- Added `/config/secrets` form with masked inputs for:
  - `GITHUB_TOKEN`
  - `AUTOPILOT_API_KEY`
  - `OPENAI_API_KEY` (optional)
- Added masked “already set” placeholders via `Settings.get_secret(...)` without exposing secret values.
- Implemented selective secret persistence:
  - Saves only non-empty values via `ConfigManager.set_secret(...)`
  - Avoids overwriting existing secrets with empty strings
  - Shows warning when no new values are provided
- Updated route wiring in `app/src/main.py`:
  - `/config/action-types` now renders `render_action_type_defaults(app_state)`
  - `/config/secrets` now renders `render_secrets_screen(app_state)`
- Added focused tests:
  - `tests/test_action_type_defaults.py`
  - `tests/test_secrets_screen.py`
  - `tests/test_main.py` route-content assertions for both new screens

### Decisions
- Kept the persistence boundary in `ConfigManager` (JSON defaults + local env secrets), so UI remains a thin adapter over existing services.
- Retained local `.env/.env.local` secret writes for app runtime while continuing to support CI secret injection (`TOKEN` alias for `GITHUB_TOKEN`) through existing `Settings.get_secret` behavior.

### Deviations
- Validation and test execution ran on Python 3.12 in this sandbox; project target remains Python 3.13+.

## Component 4.5 - Link New Project Screen
- Implemented `render_link_project(app_state)` and async `_scan_and_link(...)` in `app/src/ui/link_project.py`.
- Added full `/project/link` UI with:
  - Repository input (`owner/repo` format validation)
  - Token env-var input (default `GITHUB_TOKEN`)
  - Helper guidance for GitHub repository/environment secrets and `TOKEN` alias usage in GitHub Actions
  - Visible spinner during scan/link operations
  - Inline result area for success summaries and actionable errors
- Integrated project-link workflow to existing services:
  - Reads token via `Settings.get_secret(...)`
  - Links/scans repository via token-bound `ProjectService`
  - Generates actions via `ActionGenerator.generate_actions(...)`
  - Resolves initial payload templates via `PayloadResolver`
  - Persists linked project via `ProjectService.save_project(...)`
  - Sets `app_state.current_project` and navigates to `/project/{project_id}` on success
- Added error normalization to ensure required user-facing messages for:
  - Missing `docs/phase-progress.json`
  - Authentication failures
- Updated route wiring in `app/src/main.py`:
  - `/project/link` now renders `render_link_project(app_state)` instead of a placeholder label
- Added focused tests in `tests/test_link_project.py` for:
  - Successful scan/link + action generation/payload resolution/save flow
  - Missing token error path
  - Error message normalization behavior

### Decisions
- Executed network/file-bound link and save operations via `run.io_bound(...)` so UI remains responsive while scanning.
- Kept token handling secret-safe by reading env values at runtime only; UI stores env key names, never secret values.

### Deviations
- Updated guidance/error text to prioritize GitHub Secrets usage (repository/environment secrets and `TOKEN` alias) rather than requiring `.env/.env.local` in remote contexts.

## Component 4.6 - Load Project Screen
- Implemented `render_load_project(app_state)` in `app/src/ui/load_project.py`.
- Added `/project/load` screen rendering with:
  - Title: `Load Project`
  - Empty-state text: `No saved projects. Link a new project to get started.`
  - Link action button to `/project/link`
  - Back navigation button to `/`
- Added saved-project list rendering from `ProjectService.list_projects()`:
  - One card per project summary
  - Clickable project-name button to load via `ProjectService.load_project(project_id)`
  - Repository and updated timestamp labels per card
  - Navigation to `/project/{project_id}` on successful load
- Added delete workflow on each project card:
  - Delete icon opens confirmation dialog (`Delete project {name}?`)
  - Confirm calls `ProjectService.delete_project(project_id)`
  - List refreshes immediately after deletion
- Added robust local-operation service wiring:
  - Load/list/delete use a token from `GITHUB_TOKEN`, then `TOKEN`, then current-project token key, with safe non-empty fallback
  - Keeps component functional in local and CI/GitHub-secrets contexts without requiring committed `.env/.env.local`
- Updated `app/src/main.py`:
  - Imported `render_load_project`
  - Replaced `/project/load` placeholder with `render_load_project(app_state)`
- Added focused tests:
  - `tests/test_load_project.py` for empty-list and multi-project rendering flows
  - `tests/test_main.py` route-content assertion for `/project/load`

### Decisions
- Used `@ui.refreshable` for the project list region so deletion updates are isolated and instant.
- Kept GitHub token usage out of UI inputs for this screen; local project operations rely on runtime secret resolution only.

### Deviations
- None.

## Component 4.8 - Main Screen Response Display & Controls
- Extended `app/src/ui/main_screen.py` to implement the full right-panel response experience for the main workspace.
- Added refreshable response rendering via `_render_response_panel(app_state, project_service, refresh_action_list)` with:
  - Executor response card (status, message, run ID)
  - Empty-state text when no action has been dispatched yet
  - Status color mapping for successful, failed, and connection-error responses
- Added conditional webhook section rendering based on configured webhook URL in executor config.
- Implemented manual webhook polling flow:
  - Added `_poll_webhook(app_state, run_id)` helper (reads from `WebhookService`)
  - Added `Refresh` button when run ID exists and webhook payload is pending
  - Stores retrieved webhook payload on the currently displayed action and persists project updates
- Added completion controls:
  - Added `Mark Complete` button on each action row in the left panel
  - Added `Mark Complete` button for the current action in the right panel
  - Added `_mark_complete(app_state, action)` helper to set `completed` status and keep response context in sync
  - Persists status updates and refreshes both panels after completion
- Updated dispatch flow:
  - `_dispatch_action(...)` now records `app_state.last_dispatched_action`
  - Response panel refreshes after dispatch to show latest executor response without page reload
- Added helper `_extract_run_id(action)` to centralize safe run ID parsing from executor response payloads.
- Expanded tests in `tests/test_main_screen.py` for:
  - Tracking of latest dispatched action
  - Webhook poll helper behavior (present/missing)
  - Completion helper behavior
  - Run ID extraction behavior

### Decisions
- Kept webhook retrieval manual (button-triggered polling) to match scope and avoid background task complexity.
- Reused existing project persistence paths so response/completion updates are durable across reloads.

### Deviations
- None.

## Component 4.10 - Integration Testing & Phase Validation
- Added integration startup coverage in `tests/test_app_startup.py`:
  - validates `app.src.main` import + `AppState` initialization
  - verifies required UI and webhook routes are registered
  - verifies webhook callback/poll round-trip behavior and pending response semantics
- Added full workflow integration coverage in `tests/test_ui_integration.py`:
  - saves executor config and action defaults through `ConfigManager`
  - validates `AppState.is_fully_configured` gate success
  - links a project using `ProjectService` with a mocked GitHub client
  - generates ordered actions via `ActionGenerator`
  - resolves payload templates via `PayloadResolver` and asserts no unresolved placeholders
  - dispatches payload via `AutopilotExecutor` with mocked `httpx.Client`
  - stores and retrieves callback payload through `WebhookService`
  - marks action completion and verifies save/load round-trip persistence
- Updated `docs/autopilot-runbook-dispatch.md` with:
  - explicit app launch command and UI access URL
  - first-time setup flow (Executor -> Action Types -> Secrets -> Link Project)
  - quality validation command set (pytest/black/isort/evals)
  - E2E readiness guidance for E2E-001 through E2E-003
  - remote secret guidance: do not rely on `.env/.env.local` in GitHub; use repository/environment secrets and `TOKEN` alias for `GITHUB_TOKEN`

### Decisions
- Kept Component 4.10 integration tests at the service-chain boundary to maximize determinism while still proving end-to-end behavior.
- Mocked external integrations (GitHub API and executor HTTP dispatch) and validated only Dispatch-owned transformations/state transitions.
- Added a dedicated startup test module even though route checks exist elsewhere, to keep Phase 4 validation intent explicit and auditable.

### Deviations
- None.
