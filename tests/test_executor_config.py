"""Unit tests for executor configuration screen rendering and save flow."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.src.models import ExecutorConfig
from app.src.ui import executor_config


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
    """Fake input control with value and validation support."""

    def __init__(
        self,
        label: str,
        value: str,
        validation: dict[str, object] | None = None,
    ) -> None:
        self.label = label
        self.value = value
        self.validation = validation or {}

    def validate(self) -> bool:
        validators = self.validation.values()
        return all(bool(validator(str(self.value))) for validator in validators)


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
    """Fake NiceGUI module for executor config unit tests."""

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

    def label(self, text: str) -> _FakeContext:
        self.labels.append(text)
        return _FakeContext()

    def input(
        self,
        label: str,
        value: str = "",
        validation: dict[str, object] | None = None,
    ) -> _FakeInput:
        control = _FakeInput(label=label, value=value, validation=validation)
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

    def separator(self) -> _FakeContext:
        return _FakeContext()

    def notify(self, message: str, type: str | None = None) -> None:
        self.notifications.append((message, type))


def _build_app_state(
    tmp_path: Path,
) -> tuple[SimpleNamespace, list[ExecutorConfig], dict[str, int]]:
    """Build a fake app_state with save capture and reload counter."""
    saves: list[ExecutorConfig] = []
    reload_calls = {"count": 0}

    def _save(config: ExecutorConfig) -> None:
        saves.append(config)

    def _reload() -> None:
        reload_calls["count"] += 1

    existing = ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="https://executor.example.com/run",
        api_key_env_key="AUTOPILOT_API_KEY",
        webhook_url="https://callback.example.com/hook",
    )

    app_state = SimpleNamespace(
        settings=SimpleNamespace(config_dir=tmp_path),
        config_manager=SimpleNamespace(
            get_executor_config=lambda: existing,
            save_executor_config=_save,
        ),
        reload_config=_reload,
    )
    return app_state, saves, reload_calls


def test_render_executor_config_prepopulates_existing_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Screen should load saved executor values when config file already exists."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(executor_config, "ui", fake_ui)
    monkeypatch.setattr(
        executor_config,
        "notify_error",
        lambda message: fake_ui.notify(message, "negative"),
    )
    monkeypatch.setattr(
        executor_config,
        "notify_success",
        lambda message: fake_ui.notify(message, "positive"),
    )

    app_state, _, _ = _build_app_state(tmp_path)
    (tmp_path / "executor.json").write_text("{}", encoding="utf-8")

    executor_config.render_executor_config(app_state)

    assert "Executor Configuration" in fake_ui.labels
    assert fake_ui.inputs["Executor Name"].value == "Autopilot"
    assert (
        fake_ui.inputs["API Endpoint URL"].value == "https://executor.example.com/run"
    )
    assert fake_ui.inputs["API Key Environment Variable"].value == "AUTOPILOT_API_KEY"
    assert (
        fake_ui.inputs["Webhook URL (optional)"].value
        == "https://callback.example.com/hook"
    )


def test_render_executor_config_saves_valid_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Save should persist validated config and show success notification."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(executor_config, "ui", fake_ui)
    monkeypatch.setattr(
        executor_config,
        "notify_error",
        lambda message: fake_ui.notify(message, "negative"),
    )
    monkeypatch.setattr(
        executor_config,
        "notify_success",
        lambda message: fake_ui.notify(message, "positive"),
    )
    app_state, saves, reload_calls = _build_app_state(tmp_path)

    executor_config.render_executor_config(app_state)
    fake_ui.inputs["Executor Name"].value = "My Executor"
    fake_ui.inputs["API Endpoint URL"].value = "https://api.example.com/dispatch"
    fake_ui.inputs["API Key Environment Variable"].value = "EXTERNAL_API_KEY"
    fake_ui.inputs["Webhook URL (optional)"].value = "https://callback.example.com/run"

    fake_ui.buttons["Save"].click()

    assert len(saves) == 1
    assert saves[0].executor_id == "my-executor"
    assert saves[0].executor_name == "My Executor"
    assert saves[0].api_key_env_key == "EXTERNAL_API_KEY"
    assert reload_calls["count"] == 1
    assert fake_ui.notifications[-1] == ("Executor configuration saved", "positive")


def test_render_executor_config_rejects_invalid_endpoint_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Save should block when required URL fields are invalid."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(executor_config, "ui", fake_ui)
    monkeypatch.setattr(
        executor_config,
        "notify_error",
        lambda message: fake_ui.notify(message, "negative"),
    )
    monkeypatch.setattr(
        executor_config,
        "notify_success",
        lambda message: fake_ui.notify(message, "positive"),
    )
    app_state, saves, reload_calls = _build_app_state(tmp_path)

    executor_config.render_executor_config(app_state)
    fake_ui.inputs["API Endpoint URL"].value = "executor.internal"

    fake_ui.buttons["Save"].click()

    assert saves == []
    assert reload_calls["count"] == 0
    message, notice_type = fake_ui.notifications[-1]
    assert notice_type == "negative"
    assert "API Endpoint URL is required" in message


def test_render_executor_config_back_button_navigates_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Shared header back icon should navigate to the initial screen route."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(executor_config, "ui", fake_ui)
    monkeypatch.setattr(
        executor_config,
        "notify_error",
        lambda message: fake_ui.notify(message, "negative"),
    )
    monkeypatch.setattr(
        executor_config,
        "notify_success",
        lambda message: fake_ui.notify(message, "positive"),
    )
    app_state, _, _ = _build_app_state(tmp_path)

    executor_config.render_executor_config(app_state)

    fake_ui.buttons["arrow_back"].click()
    assert fake_ui.navigate.destinations[-1] == "/"
