"""Executor configuration UI module."""

from __future__ import annotations

import re
from pathlib import Path

from nicegui import ui
from pydantic import ValidationError

from app.src.config import EXECUTOR_CONFIG_FILENAME
from app.src.models import ExecutorConfig
from app.src.ui.components import page_layout
from app.src.ui.state import AppState

_URL_VALIDATION_MESSAGE = "URL must start with http:// or https://"


def _is_non_empty(value: str) -> bool:
    """Return whether a text value contains non-whitespace content."""
    return bool(value.strip())


def _is_valid_url(value: str) -> bool:
    """Return whether value is a URL accepted by the screen validator."""
    cleaned = value.strip()
    return cleaned.startswith("http://") or cleaned.startswith("https://")


def _is_valid_optional_url(value: str) -> bool:
    """Return whether value is empty or a valid URL."""
    cleaned = value.strip()
    return cleaned == "" or _is_valid_url(cleaned)


def _derive_executor_id(executor_name: str) -> str:
    """Derive a stable slug identifier from a provided executor name."""
    slug = re.sub(r"[^a-z0-9]+", "-", executor_name.strip().lower())
    slug = slug.strip("-")
    return slug or "executor"


def _existing_executor_config_path(app_state: AppState) -> Path:
    """Return the persisted executor config path."""
    return app_state.settings.config_dir / EXECUTOR_CONFIG_FILENAME


def render_executor_config(app_state: AppState) -> None:
    """Render the executor configuration screen."""
    existing = None
    config_path = _existing_executor_config_path(app_state)
    if config_path.exists():
        existing = app_state.config_manager.get_executor_config()

    page_layout("Configure Executor", back_url="/", ui_module=ui)
    with ui.column().classes(
        "items-center mx-auto justify-center q-pa-xl q-gutter-md w-full max-w-xl"
    ):
        with ui.card().classes("w-full q-pa-md q-gutter-sm"):
            ui.label("Executor Configuration").classes("text-h5 q-mb-md")

            executor_name = ui.input(
                "Executor Name",
                value=(existing.executor_name if existing else "autopilot"),
                validation={"Required": _is_non_empty},
            ).classes("w-full")

            api_endpoint = ui.input(
                "API Endpoint URL",
                value=(str(existing.api_endpoint) if existing else ""),
                validation={
                    "Required": _is_non_empty,
                    _URL_VALIDATION_MESSAGE: _is_valid_url,
                },
            ).classes("w-full")

            api_key_env_var = ui.input(
                "API Key Environment Variable",
                value=(existing.api_key_env_key if existing else "AUTOPILOT_API_KEY"),
                validation={"Required": _is_non_empty},
            ).classes("w-full")
            ui.label(
                "Name of the environment variable that holds the API key."
            ).classes("text-caption text-grey-7")

            webhook_url = ui.input(
                "Webhook URL (optional)",
                value=(
                    str(existing.webhook_url)
                    if existing and existing.webhook_url
                    else ""
                ),
                validation={_URL_VALIDATION_MESSAGE: _is_valid_optional_url},
            ).classes("w-full")
            ui.label("The URL the executor will call back to with results.").classes(
                "text-caption text-grey-7"
            )

            def _save_config() -> None:
                if not executor_name.validate():
                    ui.notify("Executor Name is required", type="negative")
                    return
                if not api_endpoint.validate():
                    ui.notify(
                        f"API Endpoint URL is required and {_URL_VALIDATION_MESSAGE.lower()}",
                        type="negative",
                    )
                    return
                if not api_key_env_var.validate():
                    ui.notify(
                        "API Key Environment Variable is required", type="negative"
                    )
                    return
                if not webhook_url.validate():
                    ui.notify(
                        f"Webhook URL is optional, but when provided {_URL_VALIDATION_MESSAGE.lower()}",
                        type="negative",
                    )
                    return

                try:
                    config = ExecutorConfig(
                        executor_id=_derive_executor_id(executor_name.value),
                        executor_name=executor_name.value.strip(),
                        api_endpoint=api_endpoint.value.strip(),
                        api_key_env_key=api_key_env_var.value.strip(),
                        webhook_url=webhook_url.value.strip() or None,
                    )
                    app_state.config_manager.save_executor_config(config)
                    app_state.reload_config()
                except (ValidationError, ValueError) as exc:
                    ui.notify(
                        f"Unable to save executor configuration: {exc}",
                        type="negative",
                    )
                    return

                ui.notify("Executor configuration saved", type="positive")

            with ui.row().classes("w-full justify-end q-gutter-sm q-mt-md"):
                ui.button("Save", on_click=_save_config, color="primary")
