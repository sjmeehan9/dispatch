# Phase 4 Component 4.2 Overview — Initial Screen

## Scope
Implemented the Dispatch startup UI at `/` with configuration-aware navigation and status visibility.

## What Was Built
- Added `render_initial_screen(app_state)` in `app/src/ui/initial_screen.py`.
- Rendered a centered initial layout with:
  - App title (`Dispatch`)
  - Configuration status panel
  - Navigation/action panel
- Implemented configuration status rows for:
  - Executor configuration (`app_state.is_executor_configured`)
  - Action type defaults (`app_state.is_action_types_configured`)
- Added navigation buttons to all required routes:
  - Configure Executor → `/config/executor`
  - Action Type Defaults → `/config/action-types`
  - Manage Secrets → `/config/secrets`
  - Link New Project → `/project/link`
  - Load Project → `/project/load`
- Implemented gatekeeping:
  - `Link New Project` and `Load Project` render disabled unless `app_state.is_fully_configured` is true.

## Integration Changes
- Updated `app/src/main.py` root page handler to call `render_initial_screen(app_state)`.

## Test Coverage Added
- `tests/test_initial_screen.py`
  - Verifies project buttons are disabled when config is incomplete.
  - Verifies project buttons are enabled when config is complete.
- `tests/test_main.py`
  - Verifies `/` returns content for the new initial screen (`Dispatch`, navigation labels).

## Design Notes
- UI composition follows NiceGUI declarative patterns and existing app-state singleton usage.
- Gatekeeping is evaluated at render time, which keeps behavior simple and consistent with persisted config reads.
