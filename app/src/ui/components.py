"""Reusable UI components module."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from nicegui import ui

from app.src.services import (
    ExecutorAuthError,
    ExecutorConnectionError,
    ExecutorDispatchError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)

T = TypeVar("T")


def page_layout(
    title: str,
    back_url: str | None = None,
    ui_module: object | None = None,
    on_back: Callable[[], None] | None = None,
) -> None:
    """Render a consistent page header with breadcrumb-style context."""
    active_ui = ui_module or ui
    with active_ui.header().classes(
        "bg-white text-primary shadow-2 q-px-md q-py-sm dispatch-page-header"
    ):
        with active_ui.row().classes(
            "w-full items-center justify-between wrap dispatch-header-row"
        ):
            with active_ui.row().classes(
                "items-center q-gutter-sm wrap dispatch-header-content"
            ):
                if back_url is not None:
                    active_ui.button(
                        icon="arrow_back",
                        on_click=(
                            on_back
                            if on_back is not None
                            else lambda: active_ui.navigate.to(back_url)
                        ),
                    ).props("flat round").classes("dispatch-touch-target")
                active_ui.button(
                    "Dispatch",
                    on_click=lambda: active_ui.navigate.to("/"),
                ).props("flat no-caps").classes("dispatch-touch-target")
                active_ui.separator().props("vertical")
                active_ui.label(title).classes(
                    "text-subtitle1 text-weight-medium dispatch-header-title"
                )


class LoadingOverlay:
    """Programmatic full-page loading overlay for async operations."""

    def __init__(
        self, message: str = "Loading...", ui_module: object | None = None
    ) -> None:
        """Build a hidden loading dialog that can be shown and hidden."""
        active_ui = ui_module or ui
        self._dialog = active_ui.dialog().props("persistent")
        with (
            self._dialog,
            active_ui.card().classes("q-pa-xl items-center dispatch-loading-dialog"),
        ):
            active_ui.spinner("dots", size="3rem")
            active_ui.label(message).classes("text-subtitle2 q-mt-md")

    def show(self) -> None:
        """Show the loading overlay."""
        self._dialog.open()

    def hide(self) -> None:
        """Hide the loading overlay."""
        self._dialog.close()


def loading_overlay(
    message: str = "Loading...", ui_module: object | None = None
) -> LoadingOverlay:
    """Create a loading overlay instance for the current page context."""
    return LoadingOverlay(message=message, ui_module=ui_module)


def notify_success(message: str) -> None:
    """Show a positive, dismissible toast notification."""
    ui.notify(message, type="positive", close_button=True, timeout=5000)


def notify_error(message: str) -> None:
    """Show a negative, dismissible toast notification."""
    ui.notify(message, type="negative", close_button=True, timeout=8000)


def notify_warning(message: str) -> None:
    """Show a warning, dismissible toast notification."""
    ui.notify(message, type="warning", close_button=True, timeout=5000)


def map_github_error(exc: Exception) -> str:
    """Map GitHub-related exceptions to user-facing error messages."""
    if isinstance(exc, GitHubAuthError):
        return "Authentication failed. Verify your GitHub token in Manage Secrets."
    if isinstance(exc, GitHubNotFoundError):
        return "Repository not found. Check the owner/repo format."
    if isinstance(exc, GitHubRateLimitError):
        return "GitHub API rate limit exceeded. Wait a few minutes and retry."
    return f"GitHub API error: {exc}"


def map_executor_error(exc: Exception) -> str:
    """Map executor exceptions to actionable, user-facing messages."""
    if isinstance(exc, ExecutorConnectionError):
        return f"Cannot reach executor at {exc.endpoint}. Is the executor running?"
    if isinstance(exc, ExecutorAuthError):
        return "Executor API key rejected. Check your API key in Manage Secrets."
    if isinstance(exc, ExecutorDispatchError):
        return f"Executor error ({exc.status_code}): {exc.message}"
    return f"Dispatch error: {exc}"


async def with_loading(
    operation: Callable[[], Awaitable[T]],
    overlay: LoadingOverlay,
) -> T:
    """Run an async operation while showing an overlay, always hiding it after."""
    overlay.show()
    try:
        return await operation()
    finally:
        overlay.hide()
