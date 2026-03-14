"""Initial screen UI module."""

from __future__ import annotations

from nicegui import ui

from app.src.ui.components import page_layout
from app.src.ui.state import AppState


def _status_row(label: str, is_configured: bool) -> None:
    """Render one configuration status row."""
    icon_name = "check_circle" if is_configured else "cancel"
    icon_class = "text-positive" if is_configured else "text-negative"
    status_text = "Configured" if is_configured else "Not configured"

    with ui.row().classes("items-center gap-2"):
        ui.icon(icon_name).classes(icon_class)
        ui.label(f"{label}: {status_text}")


def _project_button(label: str, destination: str, enabled: bool) -> None:
    """Render a project navigation button with gatekeeping."""
    button = ui.button(
        label,
        on_click=lambda: ui.navigate.to(destination),
    ).classes("w-full")
    if not enabled:
        button.props("disable")


def render_initial_screen(app_state: AppState) -> None:
    """Render the initial navigation screen and configuration status."""
    page_layout("Home", ui_module=ui)
    with ui.column().classes(
        "items-center mx-auto justify-center q-pa-xl q-gutter-md w-full max-w-md"
    ):
        ui.label("Dispatch").classes("text-h3 q-mb-lg")

        with ui.card().classes("w-full q-pa-md q-gutter-sm"):
            ui.label("Configuration Status").classes("text-subtitle1")
            _status_row("Executor Config", app_state.is_executor_configured)
            _status_row("Action Type Defaults", app_state.is_action_types_configured)

        with ui.card().classes("w-full q-pa-md q-gutter-sm"):
            ui.label("Get Started").classes("text-subtitle1")
            ui.button(
                "Configure Executor",
                on_click=lambda: ui.navigate.to("/config/executor"),
            ).classes("w-full")
            ui.button(
                "Action Type Defaults",
                on_click=lambda: ui.navigate.to("/config/action-types"),
            ).classes("w-full")
            ui.button(
                "Manage Secrets",
                on_click=lambda: ui.navigate.to("/config/secrets"),
            ).classes("w-full")
            ui.separator()
            _project_button(
                "Link New Project",
                "/project/link",
                enabled=app_state.is_fully_configured,
            )
            _project_button(
                "Load Project",
                "/project/load",
                enabled=app_state.is_fully_configured,
            )
