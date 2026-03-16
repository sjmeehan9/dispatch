"""Login screen for optional remote access authentication."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import app, ui


def render_login_screen(expected_token: str, on_success: Callable[[], None]) -> None:
    """Render a simple access-token login form.

    Args:
        expected_token: Access token required for authentication.
        on_success: Callback invoked after successful authentication.
    """

    with ui.column().classes("absolute-center items-center q-gutter-md"):
        ui.icon("lock").props('size="3rem" color="primary"')
        ui.label("Dispatch").classes("text-h4")
        token_input = ui.input(
            "Access Token",
            password=True,
            password_toggle_button=True,
        ).classes("w-64")

        def _authenticate() -> None:
            value = token_input.value
            if isinstance(value, str) and value == expected_token:
                app.storage.user["authenticated"] = True
                on_success()
                return

            ui.notify("Invalid access token", type="negative")

        ui.button("Sign In", on_click=_authenticate, color="primary").classes(
            "w-64 dispatch-touch-target"
        )
