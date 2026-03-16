"""NiceGUI application entry point for Dispatch."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from nicegui import app, ui
from nicegui.storage import set_storage_secret

from app.src.ui.action_type_defaults import render_action_type_defaults
from app.src.ui.components import notify_error
from app.src.ui.executor_config import render_executor_config
from app.src.ui.initial_screen import render_initial_screen
from app.src.ui.link_project import render_link_project
from app.src.ui.load_project import render_load_project
from app.src.ui.login_screen import render_login_screen
from app.src.ui.main_screen import render_main_screen
from app.src.ui.secrets_screen import render_secrets_screen
from app.src.ui.state import AppState

app_state = AppState()
_LOGGER = logging.getLogger(__name__)


async def _store_webhook_payload(request: Request) -> dict[str, bool]:
    """Validate and store an incoming webhook payload by run ID."""
    payload = await request.json()
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise HTTPException(
            status_code=400, detail="Webhook payload must include run_id"
        )

    app_state.webhook_service.store(run_id=run_id, data=payload)
    return {"received": True}


def _ensure_run_config() -> None:
    """Ensure NiceGUI run configuration exists for ASGI lifespan startup."""
    if app.config.has_run_config:
        return

    app.config.add_run_config(
        reload=app_state.settings.reload_enabled,
        title="Dispatch",
        viewport="width=device-width, initial-scale=1",
        favicon=None,
        dark=False,
        language="en-US",
        binding_refresh_interval=0.1,
        reconnect_timeout=10.0,
        message_history_length=1000,
        cache_control_directives=(
            "public, max-age=31536000, immutable, stale-while-revalidate=31536000"
        ),
        tailwind=True,
        unocss=None,
        prod_js=True,
        show_welcome_message=True,
    )


_ensure_run_config()

_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.exists():
    app.add_static_files("/static", str(_STATIC_DIR))
    ui.add_head_html('<link rel="stylesheet" href="/static/styles.css">', shared=True)


def _register_global_exception_handler() -> None:
    """Register a global exception callback for unexpected UI errors."""

    def _handle_exception(exc: Exception) -> None:
        _LOGGER.exception("Unhandled application error", exc_info=exc)
        try:
            notify_error("An unexpected error occurred. Check the console for details.")
        except RuntimeError:
            pass  # No UI context (background task) — already logged above

    on_exception = getattr(app, "on_exception", None)
    if callable(on_exception):
        on_exception(_handle_exception)


_register_global_exception_handler()


set_storage_secret(app_state.settings.access_token or "dispatch-local-dev")


@app.middleware("http")
async def _auth_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Enforce token auth for non-page webhook poll endpoint when enabled."""
    access_token = app_state.settings.access_token
    if not access_token:
        return await call_next(request)

    if request.url.path.startswith("/webhook/poll/"):
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {access_token}":
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    return await call_next(request)


def _require_auth() -> bool:
    """Require login for UI pages when access token protection is enabled."""
    if not app_state.settings.access_token:
        return True

    if app.storage.user.get("authenticated"):
        return True

    app.storage.user["redirect"] = ui.context.client.page.path
    ui.navigate.to("/login")
    return False


def _redirect_after_login() -> None:
    """Navigate to the user-requested page after successful authentication."""
    redirect_path = app.storage.user.get("redirect", "/")
    if not isinstance(redirect_path, str) or not redirect_path:
        redirect_path = "/"
    ui.navigate.to(redirect_path)


@ui.page("/login")
def login_page() -> None:
    """Render login page when token auth is configured."""
    access_token = app_state.settings.access_token
    if not access_token:
        ui.navigate.to("/")
        return

    render_login_screen(expected_token=access_token, on_success=_redirect_after_login)


@ui.page("/")
def initial_screen_page() -> None:
    """Render the initial screen."""
    if not _require_auth():
        return
    render_initial_screen(app_state)


@ui.page("/config/executor")
def executor_config_page() -> None:
    """Render the executor configuration screen."""
    if not _require_auth():
        return
    render_executor_config(app_state)


@ui.page("/config/action-types")
def action_types_page() -> None:
    """Render the action-type defaults screen."""
    if not _require_auth():
        return
    render_action_type_defaults(app_state)


@ui.page("/config/secrets")
def secrets_page() -> None:
    """Render the secrets management screen."""
    if not _require_auth():
        return
    render_secrets_screen(app_state)


@ui.page("/project/link")
def link_project_page() -> None:
    """Render the link project screen."""
    if not _require_auth():
        return
    render_link_project(app_state)


@ui.page("/project/load")
def load_project_page() -> None:
    """Render the load project screen."""
    if not _require_auth():
        return
    render_load_project(app_state)


@ui.page("/project/{project_id}")
def main_project_page(project_id: str) -> None:
    """Render the main project screen."""
    if not _require_auth():
        return
    render_main_screen(app_state, project_id)


@app.post("/")
async def root_webhook_callback(request: Request) -> dict[str, bool]:
    """Accept webhook POSTs at the app root for callback URL compatibility."""
    return await _store_webhook_payload(request)


@app.post("/webhook/callback")
async def webhook_callback(request: Request) -> dict[str, bool]:
    """Store incoming webhook payload by run ID."""
    return await _store_webhook_payload(request)


@app.get("/webhook/poll/{run_id}")
async def webhook_poll(run_id: str) -> JSONResponse:
    """Return stored webhook payload for a run or pending status."""
    data = app_state.webhook_service.retrieve(run_id)
    if data is None:
        return JSONResponse(
            status_code=404,
            content={"run_id": run_id, "status": "pending"},
        )

    response_data: dict[str, Any] = data
    return JSONResponse(status_code=200, content=response_data)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        host="0.0.0.0",
        port=8080,
        reload=app_state.settings.reload_enabled,
        title="Dispatch",
    )
