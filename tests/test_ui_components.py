"""Unit tests for shared UI components introduced in Phase 5."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.src.models import Action, ActionStatus, ActionType
from app.src.services import (
    ExecutorAuthError,
    ExecutorConnectionError,
    ExecutorDispatchError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from app.src.ui import components


class _FakeContext:
    """Minimal context manager for fake NiceGUI elements."""

    def __enter__(self) -> _FakeContext:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def classes(self, _: str) -> _FakeContext:
        return self

    def props(self, _: str) -> _FakeContext:
        return self


class _FakeDialog(_FakeContext):
    """Dialog test double that tracks open/close calls."""

    def __init__(self) -> None:
        self.is_open = False

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False


class _FakeNavigate:
    """Fake navigation API."""

    def __init__(self) -> None:
        self.destinations: list[str] = []

    def to(self, destination: str) -> None:
        self.destinations.append(destination)


class _FakeUI:
    """Small fake NiceGUI module for component helper tests."""

    def __init__(self) -> None:
        self.navigate = _FakeNavigate()
        self.labels: list[str] = []
        self.notifications: list[tuple[str, str, bool, int]] = []
        self.badges: list[str] = []
        self.progress_values: list[float] = []

    def header(self) -> _FakeContext:
        return _FakeContext()

    def row(self) -> _FakeContext:
        return _FakeContext()

    def button(
        self,
        label: str | None = None,
        on_click: object | None = None,
        icon: str | None = None,
    ) -> _FakeContext:
        _ = on_click, icon
        if label is not None:
            self.labels.append(label)
        return _FakeContext()

    def separator(self) -> _FakeContext:
        return _FakeContext()

    def label(self, text: str) -> _FakeContext:
        self.labels.append(text)
        return _FakeContext()

    def dialog(self) -> _FakeDialog:
        return _FakeDialog()

    def card(self) -> _FakeContext:
        return _FakeContext()

    def spinner(self, *_args: object, **_kwargs: object) -> _FakeContext:
        return _FakeContext()

    def notify(
        self,
        message: str,
        type: str = "info",
        close_button: bool = False,
        timeout: int = 0,
    ) -> None:
        self.notifications.append((message, type, close_button, timeout))

    def badge(self, text: str) -> _FakeContext:
        self.badges.append(text)
        return _FakeContext()

    def linear_progress(self, value: float) -> _FakeContext:
        self.progress_values.append(value)
        return _FakeContext()


def test_page_layout_renders_without_error() -> None:
    """page_layout should build header elements with provided context title."""
    fake_ui = _FakeUI()

    components.page_layout("Configure Executor", back_url="/", ui_module=fake_ui)

    assert "Dispatch" in fake_ui.labels
    assert "Configure Executor" in fake_ui.labels


def test_loading_overlay_show_hide_toggles_dialog_state() -> None:
    """loading_overlay should expose show/hide controls through dialog state."""
    fake_ui = _FakeUI()

    overlay = components.loading_overlay("Working...", ui_module=fake_ui)
    dialog = overlay._dialog

    assert dialog.is_open is False
    overlay.show()
    assert dialog.is_open is True
    overlay.hide()
    assert dialog.is_open is False


def test_with_loading_runs_operation_and_hides_overlay() -> None:
    """with_loading should show overlay, execute operation, then hide it."""
    calls: list[str] = []

    async def _operation() -> str:
        calls.append("run")
        return "ok"

    overlay = SimpleNamespace(
        show=lambda: calls.append("show"),
        hide=lambda: calls.append("hide"),
    )

    result = asyncio.run(components.with_loading(_operation, overlay))

    assert result == "ok"
    assert calls == ["show", "run", "hide"]


def test_notification_helpers_emit_expected_notify_calls(
    monkeypatch,
) -> None:
    """Notification helpers should route through ui.notify with standard options."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(components, "ui", fake_ui)

    components.notify_success("saved")
    components.notify_error("failed")
    components.notify_warning("careful")

    assert fake_ui.notifications == [
        ("saved", "positive", True, 5000),
        ("failed", "negative", True, 8000),
        ("careful", "warning", True, 5000),
    ]


def test_map_github_error_returns_expected_messages() -> None:
    """GitHub error mapping should provide actionable and safe user text."""
    assert components.map_github_error(GitHubAuthError("bad token")) == (
        "Authentication failed. Verify your GitHub token in Manage Secrets."
    )
    assert components.map_github_error(GitHubNotFoundError("missing repo")) == (
        "Repository not found. Check the owner/repo format."
    )
    assert components.map_github_error(GitHubRateLimitError("quota")) == (
        "GitHub API rate limit exceeded. Wait a few minutes and retry."
    )
    assert components.map_github_error(Exception("boom")) == "GitHub API error: boom"


def test_map_executor_error_returns_expected_messages() -> None:
    """Executor error mapping should provide actionable and safe user text."""
    assert components.map_executor_error(
        ExecutorConnectionError("https://executor.example.com/run")
    ) == (
        "Cannot reach executor at https://executor.example.com/run. Is the executor running?"
    )
    assert components.map_executor_error(ExecutorAuthError("unauthorized")) == (
        "Executor API key rejected. Check your API key in Manage Secrets."
    )
    assert (
        components.map_executor_error(
            ExecutorDispatchError(status_code=500, message="internal failure")
        )
        == "Executor error (500): internal failure"
    )
    assert components.map_executor_error(Exception("socket closed")) == (
        "Dispatch error: socket closed"
    )


def test_action_type_icon_returns_expected_icon_and_color() -> None:
    """Action type icon helper should map each action type to expected values."""
    assert components.action_type_icon(ActionType.IMPLEMENT) == ("code", "primary")
    assert components.action_type_icon(ActionType.TEST) == ("science", "purple")
    assert components.action_type_icon(ActionType.REVIEW) == ("rate_review", "orange")
    assert components.action_type_icon(ActionType.DOCUMENT) == ("description", "teal")
    assert components.action_type_icon(ActionType.DEBUG) == ("bug_report", "red")


def test_action_status_presentation_returns_expected_label_and_color() -> None:
    """Status presentation helper should map statuses to badge labels and colors."""
    assert components.action_status_presentation(ActionStatus.NOT_STARTED) == (
        "Pending",
        "grey",
    )
    assert components.action_status_presentation(ActionStatus.DISPATCHED) == (
        "Dispatched",
        "blue",
    )
    assert components.action_status_presentation(ActionStatus.COMPLETED) == (
        "Complete",
        "green",
    )


def test_action_status_badge_renders_expected_badge_text() -> None:
    """Status badge helper should render a badge with expected text."""
    fake_ui = _FakeUI()

    components.action_status_badge(ActionStatus.DISPATCHED, ui_module=fake_ui)

    assert fake_ui.badges == ["Dispatched"]


def test_progress_counts_calculates_completion_ratio() -> None:
    """Progress count helper should calculate completed/total and ratio correctly."""
    actions = [
        Action(
            action_id="a1",
            phase_id=1,
            action_type=ActionType.IMPLEMENT,
            payload={},
            status=ActionStatus.COMPLETED,
        ),
        Action(
            action_id="a2",
            phase_id=1,
            action_type=ActionType.TEST,
            payload={},
            status=ActionStatus.NOT_STARTED,
        ),
    ]

    completed, total, ratio = components.progress_counts(actions)

    assert completed == 1
    assert total == 2
    assert ratio == 0.5


def test_progress_summary_renders_label_and_progress_value() -> None:
    """Progress summary should render completion label and linear progress value."""
    fake_ui = _FakeUI()
    actions = [
        Action(
            action_id="a1",
            phase_id=1,
            action_type=ActionType.IMPLEMENT,
            payload={},
            status=ActionStatus.COMPLETED,
        ),
        Action(
            action_id="a2",
            phase_id=1,
            action_type=ActionType.TEST,
            payload={},
            status=ActionStatus.NOT_STARTED,
        ),
    ]

    components.progress_summary(actions, ui_module=fake_ui)

    assert "1 of 2 actions complete" in fake_ui.labels
    assert fake_ui.progress_values == [0.5]
