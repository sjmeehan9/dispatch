"""NiceGUI application entry point for Dispatch."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from nicegui import app, ui

from app.src.ui.action_type_defaults import render_action_type_defaults
from app.src.ui.executor_config import render_executor_config
from app.src.ui.initial_screen import render_initial_screen
from app.src.ui.link_project import render_link_project
from app.src.ui.secrets_screen import render_secrets_screen
from app.src.ui.state import AppState

app_state = AppState()


def _ensure_run_config() -> None:
    """Ensure NiceGUI run configuration exists for ASGI lifespan startup."""
    if app.config.has_run_config:
        return

    app.config.add_run_config(
        reload=True,
        title="Dispatch",
        viewport="width=device-width, initial-scale=1",
        favicon=None,
        dark=False,
        language="en-US",
        binding_refresh_interval=0.1,
        reconnect_timeout=3.0,
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


@ui.page("/")
def initial_screen_page() -> None:
    """Render the initial screen."""
    render_initial_screen(app_state)


@ui.page("/config/executor")
def executor_config_page() -> None:
    """Render the executor configuration screen."""
    render_executor_config(app_state)


@ui.page("/config/action-types")
def action_types_page() -> None:
    """Render the action-type defaults screen."""
    render_action_type_defaults(app_state)


@ui.page("/config/secrets")
def secrets_page() -> None:
    """Render the secrets management screen."""
    render_secrets_screen(app_state)


@ui.page("/project/link")
def link_project_page() -> None:
    """Render the link project screen."""
    render_link_project(app_state)


@ui.page("/project/load")
def load_project_page() -> None:
    """Render the load project route placeholder."""
    ui.label("Load project route")


@ui.page("/project/{project_id}")
def main_project_page(project_id: str) -> None:
    """Render the main project route placeholder."""
    ui.label(f"Project route: {project_id}")


@app.post("/webhook/callback")
async def webhook_callback(request: Request) -> dict[str, bool]:
    """Store incoming webhook payload by run ID."""
    payload = await request.json()
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise HTTPException(
            status_code=400, detail="Webhook payload must include run_id"
        )

    app_state.webhook_service.store(run_id=run_id, data=payload)
    return {"received": True}


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
    ui.run(port=8080, reload=True, title="Dispatch")
