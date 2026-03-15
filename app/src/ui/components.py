"""Reusable UI components module."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from nicegui import ui

from app.src.models import Action, ActionStatus, ActionType
from app.src.services import (
    ExecutorAuthError,
    ExecutorConnectionError,
    ExecutorDispatchError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)

T = TypeVar("T")

_ACTION_TYPE_ICON_MAP: dict[str, tuple[str, str]] = {
    ActionType.IMPLEMENT.value: ("code", "primary"),
    ActionType.TEST.value: ("science", "purple"),
    ActionType.REVIEW.value: ("rate_review", "orange"),
    ActionType.MERGE.value: ("merge", "green"),
    ActionType.DOCUMENT.value: ("description", "teal"),
    ActionType.DEBUG.value: ("bug_report", "red"),
}

_ACTION_STATUS_BADGE_MAP: dict[str, tuple[str, str]] = {
    ActionStatus.NOT_STARTED.value: ("Pending", "grey"),
    ActionStatus.DISPATCHED.value: ("Dispatched", "blue"),
    ActionStatus.COMPLETED.value: ("Complete", "green"),
}

_REDACTED_QUERY_KEYS = {
    "token",
    "access_token",
    "api_key",
    "apikey",
    "key",
    "secret",
    "password",
    "auth",
}


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


def _sanitize_url(url_value: str) -> str:
    """Redact credential-like URL parts before rendering user-facing messages."""
    parsed = urlsplit(url_value)
    if not parsed.scheme or not parsed.netloc:
        return url_value

    netloc = parsed.netloc
    if "@" in netloc:
        _, host_part = netloc.rsplit("@", 1)
        netloc = f"***@{host_part}"

    redacted_query_items: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in _REDACTED_QUERY_KEYS:
            redacted_query_items.append((key, "***"))
        else:
            redacted_query_items.append((key, value))

    redacted_query = urlencode(redacted_query_items, doseq=True)
    return urlunsplit((parsed.scheme, netloc, parsed.path, redacted_query, ""))


def _sanitize_message(message: str) -> str:
    """Redact URL credentials and sensitive query parameters in a message."""
    words = message.split()
    sanitized_words: list[str] = []
    for word in words:
        if word.startswith(("http://", "https://")):
            sanitized_words.append(
                _sanitize_url(word.rstrip(".,;")) + word[len(word.rstrip(".,;")) :]
            )
            continue
        sanitized_words.append(word)
    return " ".join(sanitized_words)


def map_github_error(exc: Exception) -> str:
    """Map GitHub-related exceptions to user-facing error messages."""
    if isinstance(exc, GitHubAuthError):
        return "Authentication failed. Verify your GitHub token in Manage Secrets."
    if isinstance(exc, GitHubNotFoundError):
        return "Repository not found. Check the owner/repo format."
    if isinstance(exc, GitHubRateLimitError):
        return "GitHub API rate limit exceeded. Wait a few minutes and retry."
    return f"GitHub API error: {_sanitize_message(str(exc))}"


def map_executor_error(exc: Exception) -> str:
    """Map executor exceptions to actionable, user-facing messages."""
    if isinstance(exc, ExecutorConnectionError):
        endpoint = _sanitize_url(exc.endpoint)
        return f"Cannot reach executor at {endpoint}. Is the executor running?"
    if isinstance(exc, ExecutorAuthError):
        return "Executor API key rejected. Check your API key in Manage Secrets."
    if isinstance(exc, ExecutorDispatchError):
        return f"Executor error ({exc.status_code}): {_sanitize_message(exc.message)}"
    return f"Dispatch error: {_sanitize_message(str(exc))}"


def action_type_icon(action_type: ActionType | str) -> tuple[str, str]:
    """Return the icon name and color class for an action type."""
    action_type_value = str(action_type)
    return _ACTION_TYPE_ICON_MAP.get(action_type_value, ("play_arrow", "grey-7"))


def action_status_presentation(status: ActionStatus | str) -> tuple[str, str]:
    """Return badge label and color for an action status."""
    status_value = str(status)
    return _ACTION_STATUS_BADGE_MAP.get(status_value, ("Pending", "grey"))


def action_status_badge(
    status: ActionStatus | str,
    ui_module: object | None = None,
) -> object:
    """Render a standardized status badge and return the created badge element."""
    active_ui = ui_module or ui
    label, color = action_status_presentation(status)
    return active_ui.badge(label).props(f'color="{color}" text-color="white"')


def progress_counts(actions: list[Action]) -> tuple[int, int, float]:
    """Calculate completed and total action counts and completion ratio."""
    total = len(actions)
    completed = sum(1 for action in actions if action.status == ActionStatus.COMPLETED)
    ratio = completed / total if total > 0 else 0.0
    return completed, total, ratio


def progress_summary(actions: list[Action], ui_module: object | None = None) -> None:
    """Render completion summary text and progress bar for an action list."""
    active_ui = ui_module or ui
    completed, total, ratio = progress_counts(actions)
    active_ui.label(f"{completed} of {total} actions complete").classes(
        "text-subtitle2 text-weight-medium"
    )
    active_ui.linear_progress(value=ratio).props("color=primary stripe rounded")


def confirm_redispatch(
    action: Action,
    on_confirm: Callable[[], None],
    ui_module: object | None = None,
) -> object:
    """Create a confirmation dialog for redispatching an already-processed action."""
    active_ui = ui_module or ui
    dialog = active_ui.dialog()
    with dialog, active_ui.card().classes("q-pa-md q-gutter-md"):
        active_ui.label("Confirm Re-dispatch").classes("text-h6")
        active_ui.label(
            f"This action has already been {str(action.status).replace('_', ' ')}. Re-dispatch?"
        ).classes("text-body2")

        with active_ui.row().classes("w-full justify-end q-gutter-sm"):

            def _cancel() -> None:
                dialog.close()

            def _confirm() -> None:
                dialog.close()
                on_confirm()

            active_ui.button("Cancel", on_click=_cancel).props("outline")
            active_ui.button(
                "Re-dispatch",
                icon="send",
                on_click=_confirm,
                color="warning",
            )

    return dialog


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
