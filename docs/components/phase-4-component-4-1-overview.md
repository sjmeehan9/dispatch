# Component 4.1 Overview: NiceGUI App Entry Point & Routing

## Summary
Component 4.1 establishes the application runtime shell for Dispatch. It introduces a concrete NiceGUI entry point, registers all required page routes, and exposes webhook API endpoints on the shared FastAPI app.

## What Was Implemented
- **Application state container** (`app/src/ui/state.py`)
  - Added `AppState` as the shared, in-memory runtime state object.
  - Eager initialization of token-independent services:
    - `Settings`
    - `ConfigManager`
    - `WebhookService`
    - `ActionGenerator`
    - `PayloadResolver`
    - `AutopilotExecutor`
  - Lazy factories for token-dependent services:
    - `get_github_client(token)`
    - `get_project_service(token)`
  - Added config-readiness properties for UI gatekeeping:
    - `is_executor_configured`
    - `is_action_types_configured`
    - `is_fully_configured`
  - Added `reload_config()` to re-validate persisted config.

- **Main NiceGUI entry point** (`app/src/main.py`)
  - Added module-level singleton `app_state`.
  - Added required UI routes:
    - `/`
    - `/config/executor`
    - `/config/action-types`
    - `/config/secrets`
    - `/project/link`
    - `/project/load`
    - `/project/{project_id}`
  - Added webhook API endpoints:
    - `POST /webhook/callback`
      - Validates `run_id` and stores payload in `WebhookService`.
    - `GET /webhook/poll/{run_id}`
      - Returns stored payload with `200` or pending payload with `404`.
  - Added `_ensure_run_config()` to satisfy NiceGUI lifespan requirements in ASGI test execution.
  - Preserved startup entrypoint with `ui.run(port=8080, reload=True, title="Dispatch")`.

- **UI exports** (`app/src/ui/__init__.py`)
  - Exported `AppState` for use by upcoming UI components.

## Tests Added
- `tests/test_app_state.py`
  - Validates AppState initialization.
  - Validates missing-config behavior for config gate properties.
  - Validates project service factory wiring.

- `tests/test_main.py`
  - Validates all required routes return success.
  - Validates webhook callback stores payloads.
  - Validates webhook poll success and pending behaviors.

## Verification Notes
- `python -m app.src.main` starts successfully and serves routes on `localhost:8080`.
- Webhook callback/poll workflow verified manually with `curl`.
- UI screenshots captured during manual verification:
  - `/tmp/dispatch-ui-root.png`
  - `/tmp/dispatch-ui-project.png`

## Security & Secrets
- No secrets are committed or hardcoded.
- Token usage remains runtime/env based.
- CI compatibility with GitHub secret naming (`TOKEN` alias for `GITHUB_TOKEN`) remains unchanged.
