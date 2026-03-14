"""Unit tests for secrets screen rendering and save flow."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.src.ui import secrets_screen


class _FakeContext:
    """Minimal context manager for fake NiceGUI layout containers."""

    def __enter__(self) -> _FakeContext:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def classes(self, _: str) -> _FakeContext:
        return self

    def props(self, _: str) -> _FakeContext:
        return self


class _FakeInput(_FakeContext):
    """Fake input control with value and placeholder support."""

    def __init__(self, label: str, placeholder: str = "") -> None:
        self.label = label
        self.placeholder = placeholder
        self.value = ""


class _FakeButton(_FakeContext):
    """Fake button exposing click behavior."""

    def __init__(self, label: str, on_click: object | None = None) -> None:
        self.label = label
        self._on_click = on_click

    def props(self, _: str) -> _FakeButton:
        return self

    def click(self) -> None:
        if callable(self._on_click):
            self._on_click()


class _FakeNavigate:
    """Fake navigate API collecting destination calls."""

    def __init__(self) -> None:
        self.destinations: list[str] = []

    def to(self, destination: str) -> None:
        self.destinations.append(destination)


class _FakeUI:
    """Fake NiceGUI module for secrets screen unit tests."""

    def __init__(self) -> None:
        self.labels: list[str] = []
        self.inputs: dict[str, _FakeInput] = {}
        self.buttons: dict[str, _FakeButton] = {}
        self.notifications: list[tuple[str, str | None]] = []
        self.navigate = _FakeNavigate()

    def column(self) -> _FakeContext:
        return _FakeContext()

    def header(self) -> _FakeContext:
        return _FakeContext()

    def card(self) -> _FakeContext:
        return _FakeContext()

    def row(self) -> _FakeContext:
        return _FakeContext()

    def separator(self) -> _FakeContext:
        return _FakeContext()

    def label(self, text: str) -> _FakeContext:
        self.labels.append(text)
        return _FakeContext()

    def input(
        self,
        label: str,
        password: bool = False,
        password_toggle_button: bool = False,
        placeholder: str = "",
    ) -> _FakeInput:
        _ = password
        _ = password_toggle_button
        control = _FakeInput(label=label, placeholder=placeholder)
        self.inputs[label] = control
        return control

    def button(
        self,
        label: str | None = None,
        on_click: object | None = None,
        color: str | None = None,
        icon: str | None = None,
    ) -> _FakeButton:
        _ = color
        rendered_label = label if label is not None else icon or ""
        button = _FakeButton(rendered_label, on_click=on_click)
        self.buttons[rendered_label] = button
        return button

    def notify(self, message: str, type: str | None = None) -> None:
        self.notifications.append((message, type))


def _build_app_state() -> tuple[SimpleNamespace, list[tuple[str, str]]]:
    saved_secrets: list[tuple[str, str]] = []

    def _set_secret(key: str, value: str) -> None:
        saved_secrets.append((key, value))

    app_state = SimpleNamespace(
        settings=SimpleNamespace(
            get_secret=lambda key: "existing-value" if key == "GITHUB_TOKEN" else None
        ),
        config_manager=SimpleNamespace(set_secret=_set_secret),
    )
    return app_state, saved_secrets


def test_render_secrets_screen_shows_masked_placeholders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inputs should show masked placeholder text when a secret is already configured."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(secrets_screen, "ui", fake_ui)
    app_state, _ = _build_app_state()

    secrets_screen.render_secrets_screen(app_state)

    assert "Secrets Management" in fake_ui.labels
    assert fake_ui.inputs["GitHub Token"].placeholder == "••••••• (set)"
    assert fake_ui.inputs["Autopilot API Key"].placeholder == ""


def test_render_secrets_screen_saves_only_non_empty_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Save should persist only populated secrets and show success notification."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(secrets_screen, "ui", fake_ui)
    app_state, saved_secrets = _build_app_state()

    secrets_screen.render_secrets_screen(app_state)
    fake_ui.inputs["GitHub Token"].value = "gh-token"
    fake_ui.inputs["OpenAI API Key (Optional)"].value = "openai-key"

    fake_ui.buttons["Save"].click()

    assert saved_secrets == [
        ("GITHUB_TOKEN", "gh-token"),
        ("OPENAI_API_KEY", "openai-key"),
    ]
    assert fake_ui.notifications[-1] == ("Secrets saved", "positive")
