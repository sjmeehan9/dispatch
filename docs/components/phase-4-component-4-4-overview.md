# Phase 4 Component 4.4 Overview — Action Type Defaults & Secrets Screens

## Component Summary

Component 4.4 delivers the remaining configuration UI required before project linking/loading:

1. **Action Type Defaults screen** at `/config/action-types`
2. **Secrets Management screen** at `/config/secrets`

Both screens are integrated into existing `AppState` and `ConfigManager` workflows and follow the same NiceGUI layout/navigation pattern used in Component 4.3.

## What Was Implemented

### 1) Action Type Defaults Editor
- Added `app/src/ui/action_type_defaults.py` with `render_action_type_defaults(app_state)`.
- Loads persisted defaults via `app_state.config_manager.get_action_type_defaults()`.
- Renders:
  - A title section
  - An expandable **Available Variables** hint panel for:
    - `{{repository}}`, `{{branch}}`, `{{phase_id}}`, `{{phase_name}}`
    - `{{component_id}}`, `{{component_name}}`, `{{component_breakdown_doc}}`
    - `{{agent_paths}}`, `{{webhook_url}}`, `{{pr_number}}`
  - Tabs for all five action types: Implement, Test, Review, Document, Debug
  - Field editors per payload key using type-appropriate controls
- Save action:
  - Collects edited values from all tabs
  - Validates with `ActionTypeDefaults`
  - Persists with `save_action_type_defaults`
  - Calls `app_state.reload_config()`
  - Shows success/error notifications

### 2) Secrets Management Screen
- Completed `app/src/ui/secrets_screen.py` with `render_secrets_screen(app_state)`.
- Renders masked inputs for:
  - GitHub Token (`GITHUB_TOKEN`)
  - Autopilot API Key (`AUTOPILOT_API_KEY`)
  - OpenAI API Key (`OPENAI_API_KEY`, optional)
- Uses masked placeholders (`••••••• (set)`) when a secret is already available through `Settings.get_secret(...)`.
- Save action:
  - Writes only non-empty input values via `ConfigManager.set_secret(...)`
  - Does not blank existing secrets when fields are left empty
  - Shows warning when no changes were provided

### 3) Route Integration
- Updated `app/src/main.py`:
  - `/config/action-types` -> `render_action_type_defaults(app_state)`
  - `/config/secrets` -> `render_secrets_screen(app_state)`

## Testing

- Added:
  - `tests/test_action_type_defaults.py`
  - `tests/test_secrets_screen.py`
- Extended:
  - `tests/test_main.py` with route-content assertions for both new screens
- Verified targeted tests:
  - `pytest -q tests/test_action_type_defaults.py tests/test_secrets_screen.py tests/test_main.py`

## Design Notes

- UI remains a thin layer; persistence/validation logic stays centralized in existing service/model classes.
- Secret values are never rendered back into inputs; only masked "set" state is shown.
- Existing CI compatibility for GitHub token aliasing (`TOKEN` fallback for `GITHUB_TOKEN`) is preserved through `Settings`.
