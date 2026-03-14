"""Secrets management UI module."""

from __future__ import annotations

from nicegui import ui

from app.src.ui.components import page_layout
from app.src.ui.state import AppState


def _secret_placeholder(app_state: AppState, env_key: str) -> str:
    """Return a masked placeholder indicating whether a secret is already set."""
    existing = app_state.settings.get_secret(env_key)
    return "••••••• (set)" if existing else ""


def render_secrets_screen(app_state: AppState) -> None:
    """Render the secrets management screen."""
    page_layout("Manage Secrets", back_url="/", ui_module=ui)
    with ui.column().classes(
        "items-center mx-auto justify-center q-pa-xl q-gutter-md w-full max-w-xl"
    ):
        with ui.card().classes("w-full q-pa-md q-gutter-sm"):
            ui.label("Secrets Management").classes("text-h5 q-mb-sm")
            ui.label(
                "Secrets are stored locally in .env/.env.local and never committed to the repository."
            ).classes("text-body2 text-grey-8")

            github_token = ui.input(
                "GitHub Token",
                password=True,
                password_toggle_button=True,
                placeholder=_secret_placeholder(app_state, "GITHUB_TOKEN"),
            ).classes("w-full")
            autopilot_api_key = ui.input(
                "Autopilot API Key",
                password=True,
                password_toggle_button=True,
                placeholder=_secret_placeholder(app_state, "AUTOPILOT_API_KEY"),
            ).classes("w-full")
            openai_api_key = ui.input(
                "OpenAI API Key (Optional)",
                password=True,
                password_toggle_button=True,
                placeholder=_secret_placeholder(app_state, "OPENAI_API_KEY"),
            ).classes("w-full")

            def _save_secrets() -> None:
                updates = {
                    "GITHUB_TOKEN": str(github_token.value).strip(),
                    "AUTOPILOT_API_KEY": str(autopilot_api_key.value).strip(),
                    "OPENAI_API_KEY": str(openai_api_key.value).strip(),
                }
                saved_keys = 0
                for key, value in updates.items():
                    if not value:
                        continue
                    app_state.config_manager.set_secret(key, value)
                    saved_keys += 1

                if saved_keys == 0:
                    ui.notify("No secret changes to save", type="warning")
                    return

                ui.notify("Secrets saved", type="positive")

            with ui.row().classes("w-full justify-end q-gutter-sm q-mt-md"):
                ui.button("Save", on_click=_save_secrets, color="primary")
