"""Error handling and notification tests for Phase 5.5 validation."""

from __future__ import annotations

from app.src.services import (
    ExecutorAuthError,
    ExecutorConnectionError,
    ExecutorDispatchError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from app.src.ui import components


class _FakeNotifyUI:
    """Tiny fake UI that records notification calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bool, int]] = []

    def notify(
        self,
        message: str,
        type: str = "info",
        close_button: bool = False,
        timeout: int = 0,
    ) -> None:
        self.calls.append((message, type, close_button, timeout))


def test_map_github_error_messages() -> None:
    """GitHub exceptions should map to consistent user-facing text."""
    assert components.map_github_error(GitHubAuthError("bad token")) == (
        "Authentication failed. Verify your GitHub token in Manage Secrets."
    )
    assert components.map_github_error(GitHubNotFoundError("missing")) == (
        "Repository not found. Check the owner/repo format."
    )
    assert components.map_github_error(GitHubRateLimitError("quota")) == (
        "GitHub API rate limit exceeded. Wait a few minutes and retry."
    )
    assert components.map_github_error(Exception("boom")) == "GitHub API error: boom"


def test_map_executor_error_messages() -> None:
    """Executor exceptions should map to actionable user-facing text."""
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
            ExecutorDispatchError(status_code=502, message="gateway failure")
        )
        == "Executor error (502): gateway failure"
    )
    assert components.map_executor_error(Exception("socket closed")) == (
        "Dispatch error: socket closed"
    )


def test_error_messages_redact_secret_values() -> None:
    """Mapped error messages should not expose token-like values from URLs."""
    connection_error = ExecutorConnectionError(
        "https://user:super-secret@example.com/run?token=ghp_123456&safe=true"
    )
    dispatch_error = ExecutorDispatchError(
        status_code=400,
        message=(
            "Remote call failed at "
            "https://api.example.com/dispatch?access_token=ghp_abcdef&x=1"
        ),
    )

    connection_message = components.map_executor_error(connection_error)
    dispatch_message = components.map_executor_error(dispatch_error)

    assert "super-secret" not in connection_message
    assert "ghp_123456" not in connection_message
    assert "ghp_abcdef" not in dispatch_message
    assert "***" in connection_message
    assert "%2A%2A%2A" in dispatch_message


def test_notification_helpers_smoke(monkeypatch) -> None:
    """Notification helper wrappers should call ui.notify with expected defaults."""
    fake_ui = _FakeNotifyUI()
    monkeypatch.setattr(components, "ui", fake_ui)

    components.notify_success("saved")
    components.notify_error("failed")
    components.notify_warning("careful")

    assert fake_ui.calls == [
        ("saved", "positive", True, 5000),
        ("failed", "negative", True, 8000),
        ("careful", "warning", True, 5000),
    ]
