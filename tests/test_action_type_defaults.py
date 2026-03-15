"""Unit tests for action type defaults screen rendering and save flow."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.src.models import ActionTypeDefaults
from app.src.ui import action_type_defaults


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


class _FakeControl(_FakeContext):
    """Fake input-like control with mutable value."""

    def __init__(self, label: str, value: object) -> None:
        self.label = label
        self.value = value


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
    """Fake NiceGUI module for action defaults unit tests."""

    def __init__(self) -> None:
        self.labels: list[str] = []
        self.inputs: dict[str, _FakeControl] = {}
        self.textareas: dict[str, _FakeControl] = {}
        self.numbers: dict[str, _FakeControl] = {}
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

    def icon(self, _: str) -> _FakeContext:
        return _FakeContext()

    def expansion(self, text: str, value: bool = False) -> _FakeContext:
        self.labels.append(text)
        _ = value
        return _FakeContext()

    def tabs(self) -> _FakeContext:
        return _FakeContext()

    def tab(self, text: str) -> str:
        self.labels.append(text)
        return text

    def tab_panels(self, _: object, value: object | None = None) -> _FakeContext:
        _ = value
        return _FakeContext()

    def tab_panel(self, _: object) -> _FakeContext:
        return _FakeContext()

    def label(self, text: str) -> _FakeContext:
        self.labels.append(text)
        return _FakeContext()

    def input(self, label: str, value: str = "") -> _FakeControl:
        control = _FakeControl(label=label, value=value)
        self.inputs[label] = control
        return control

    def textarea(self, label: str, value: str = "") -> _FakeControl:
        control = _FakeControl(label=label, value=value)
        self.textareas[label] = control
        return control

    def number(self, label: str, value: float = 0.0) -> _FakeControl:
        control = _FakeControl(label=label, value=value)
        self.numbers[label] = control
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


def _sample_defaults() -> ActionTypeDefaults:
    return ActionTypeDefaults(
        implement={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Implement component {{component_id}}",
            "model": "claude-opus-4.6",
            "role": "implement",
            "agent_paths": "{{agent_paths}}",
            "callback_url": "{{webhook_url}}",
            "timeout_minutes": 30,
        },
        test={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Test phase {{phase_id}}",
            "model": "claude-opus-4.6",
            "role": "implement",
            "agent_paths": "{{agent_paths}}",
            "callback_url": "{{webhook_url}}",
            "timeout_minutes": 30,
        },
        review={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Review phase {{phase_id}}",
            "model": "claude-opus-4.6",
            "role": "review",
            "pr_number": "{{pr_number}}",
            "agent_paths": "{{agent_paths}}",
            "callback_url": "{{webhook_url}}",
            "timeout_minutes": 15,
        },
        merge={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Merge PR for component {{component_id}}",
            "model": "claude-opus-4.6",
            "role": "merge",
            "pr_number": "{{pr_number}}",
            "agent_paths": "{{agent_paths}}",
            "callback_url": "{{webhook_url}}",
            "timeout_minutes": 10,
        },
        document={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Document phase {{phase_id}}",
            "model": "claude-opus-4.6",
            "role": "implement",
            "agent_paths": "{{agent_paths}}",
            "callback_url": "{{webhook_url}}",
            "timeout_minutes": 20,
        },
        debug={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "",
            "model": "claude-opus-4.6",
            "role": "implement",
            "agent_paths": "{{agent_paths}}",
            "callback_url": "{{webhook_url}}",
            "timeout_minutes": 30,
        },
    )


def _build_app_state() -> (
    tuple[SimpleNamespace, list[ActionTypeDefaults], dict[str, int]]
):
    saves: list[ActionTypeDefaults] = []
    reload_calls = {"count": 0}

    def _save(defaults: ActionTypeDefaults) -> None:
        saves.append(defaults)

    def _reload() -> None:
        reload_calls["count"] += 1

    app_state = SimpleNamespace(
        config_manager=SimpleNamespace(
            get_action_type_defaults=_sample_defaults,
            save_action_type_defaults=_save,
        ),
        reload_config=_reload,
    )
    return app_state, saves, reload_calls


def test_render_action_type_defaults_prepopulates_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Screen should render expected labels and load existing template values."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(action_type_defaults, "ui", fake_ui)
    monkeypatch.setattr(
        action_type_defaults,
        "notify_error",
        lambda message: fake_ui.notify(message, "negative"),
    )
    monkeypatch.setattr(
        action_type_defaults,
        "notify_success",
        lambda message: fake_ui.notify(message, "positive"),
    )
    app_state, _, _ = _build_app_state()

    action_type_defaults.render_action_type_defaults(app_state)

    assert "Action Type Defaults" in fake_ui.labels
    assert "Available Variables" in fake_ui.labels
    assert fake_ui.inputs["Implement: Repository"].value == "{{repository}}"
    assert (
        fake_ui.textareas["Implement: Agent Instructions"].value
        == "Implement component {{component_id}}"
    )
    assert fake_ui.numbers["Review: Timeout Minutes"].value == 15.0
    assert fake_ui.inputs["Review: PR Number"].value == "{{pr_number}}"


def test_render_action_type_defaults_saves_updated_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Save should persist updated defaults and show a success notification."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(action_type_defaults, "ui", fake_ui)
    monkeypatch.setattr(
        action_type_defaults,
        "notify_error",
        lambda message: fake_ui.notify(message, "negative"),
    )
    monkeypatch.setattr(
        action_type_defaults,
        "notify_success",
        lambda message: fake_ui.notify(message, "positive"),
    )
    app_state, saves, reload_calls = _build_app_state()

    action_type_defaults.render_action_type_defaults(app_state)
    fake_ui.inputs["Implement: Repository"].value = "owner/new-repo"
    fake_ui.numbers["Implement: Timeout Minutes"].value = 45

    fake_ui.buttons["Save"].click()

    assert len(saves) == 1
    assert saves[0].implement["repository"] == "owner/new-repo"
    assert saves[0].implement["timeout_minutes"] == 45
    assert reload_calls["count"] == 1
    assert fake_ui.notifications[-1] == ("Action type defaults saved", "positive")
