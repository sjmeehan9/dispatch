# Phase 4 Component 4.7 Overview: Main Screen Layout & Action List

## Summary
Component 4.7 delivers the core project workspace in NiceGUI. The `/project/{project_id}` route now renders a split-panel main screen with a project header, a phase-grouped action list, and dispatch behavior wired to backend services.

## What Was Implemented
- Main screen renderer in `app/src/ui/main_screen.py`:
  - `render_main_screen(app_state, project_id)`
  - `_render_action_list(app_state, project_service)`
  - `_dispatch_action(app_state, project_service, action)`
  - helper functions for project-service token resolution, action labels, status colors, and phase grouping
- Route update in `app/src/main.py`:
  - `/project/{project_id}` now calls `render_main_screen(...)`.

## Main Screen Behavior
- Header area shows:
  - current project name
  - `Save` button to persist project state
  - `Home` button to return to `/`
- Body uses `ui.splitter(value=40)`:
  - left panel (40%): scrollable action list grouped by phase
  - right panel (60%): placeholder card for response UI (Component 4.8)

## Action List Details
- Actions are grouped into expandable sections by phase (`Phase X: Name`).
- Each action row shows:
  - type icon (implement/test/review/document/debug)
  - readable label (including component name for implement actions)
  - status badge
- Status badge colors:
  - `not_started` -> grey
  - `dispatched` -> blue
  - `completed` -> green
- Each action has a `Dispatch` control.

## Dispatch Flow
When dispatch is triggered:
1. Executor config is loaded from `ConfigManager`.
2. Payload context is built using `PayloadResolver.build_context(...)`.
3. Payload template is resolved with `PayloadResolver.resolve_payload(...)`.
4. Resolved payload is sent through `AutopilotExecutor.dispatch(...)`.
5. Action is updated with:
   - resolved payload
   - `executor_response`
   - status `dispatched`
6. Project is auto-saved through `ProjectService.save_project(...)`.

## State and Integration Notes
- Route-level load logic ensures `AppState.current_project` is loaded from disk when needed.
- Missing project or load failures redirect safely to `/` with notifications.
- Dispatch uses a per-action loading state (`dispatching_action_id`) and refreshable rendering to keep UI responsive.
- Token resolution follows existing project conventions and supports CI aliasing (`TOKEN` for `GITHUB_TOKEN`).

## Tests Added
- `tests/test_main_screen.py`
  - validates phase grouping and order preservation
  - validates dispatch behavior end-to-end at unit level (resolver call -> executor call -> action updates -> project save)

## Scope Boundary
Component 4.7 intentionally leaves right-panel API/webhook response rendering to Component 4.8; a placeholder panel is now in place for that extension point.
