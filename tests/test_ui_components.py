"""Unit tests for shared UI components introduced in Phase 5."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

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
