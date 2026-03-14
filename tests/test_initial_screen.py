"""Unit tests for initial screen rendering and config gatekeeping."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.src.ui import initial_screen


class _FakeContext:
    """Minimal context manager used by fake NiceGUI layout calls."""

    def __enter__(self) -> _FakeContext:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def classes(self, _: str) -> _FakeContext:
        return self

    def props(self, _: str) -> _FakeContext:
        return self


class _FakeButton(_FakeContext):
    """Fake button capturing disable props."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.disabled = False

    def props(self, value: str) -> _FakeButton:
        if "disable" in value:
            self.disabled = True
        return self


class _FakeNavigate:
    """Fake navigation API."""

    def to(self, _: str) -> None:
        return None


class _FakeUI:
    """Fake NiceGUI module collecting rendered buttons."""

    def __init__(self) -> None:
        self.buttons: list[_FakeButton] = []
        self.navigate = _FakeNavigate()

    def column(self) -> _FakeContext:
        return _FakeContext()

    def header(self) -> _FakeContext:
        return _FakeContext()

    def card(self) -> _FakeContext:
        return _FakeContext()

    def row(self) -> _FakeContext:
        return _FakeContext()

    def label(self, _: str) -> _FakeContext:
        return _FakeContext()

    def icon(self, _: str) -> _FakeContext:
        return _FakeContext()

    def separator(self) -> _FakeContext:
        return _FakeContext()

    def button(
        self,
        label: str | None = None,
        on_click: object | None = None,
        icon: str | None = None,
    ) -> _FakeButton:
        rendered_label = label if label is not None else icon or ""
        _ = on_click
        button = _FakeButton(rendered_label)
        self.buttons.append(button)
        return button


def _render_with_state(
    monkeypatch: pytest.MonkeyPatch, is_fully_configured: bool
) -> _FakeUI:
    """Render with fake UI and return captured state."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(initial_screen, "ui", fake_ui)

    app_state = SimpleNamespace(
        is_executor_configured=is_fully_configured,
        is_action_types_configured=is_fully_configured,
        is_fully_configured=is_fully_configured,
    )
    initial_screen.render_initial_screen(app_state)
    return fake_ui


def test_project_buttons_disabled_when_config_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load/link project buttons should be disabled until setup is complete."""
    fake_ui = _render_with_state(monkeypatch, is_fully_configured=False)

    button_state = {button.label: button.disabled for button in fake_ui.buttons}
    assert button_state["Link New Project"] is True
    assert button_state["Load Project"] is True


def test_project_buttons_enabled_when_fully_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load/link project buttons should be enabled when config is complete."""
    fake_ui = _render_with_state(monkeypatch, is_fully_configured=True)

    button_state = {button.label: button.disabled for button in fake_ui.buttons}
    assert button_state["Link New Project"] is False
    assert button_state["Load Project"] is False
