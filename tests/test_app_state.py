"""Unit tests for shared application state."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.src.services import ProjectService
from app.src.services.config_manager import ConfigManager
from app.src.ui.state import AppState


def test_app_state_initialises_without_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AppState should eagerly initialise token-independent services."""
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path))

    state = AppState()

    assert isinstance(state.config_manager, ConfigManager)
    assert state.current_project is None
    assert state.webhook_service is not None
    assert state.action_generator is not None
    assert state.payload_resolver is not None
    assert state.autopilot_executor is not None


def test_is_executor_configured_false_when_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Executor configuration flag should be false when file is absent."""
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path))
    state = AppState()

    assert state.is_executor_configured is False


def test_is_action_types_configured_false_when_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Action defaults flag should be false when file is absent."""
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path))
    state = AppState()

    assert state.is_action_types_configured is False


def test_project_service_factory_creates_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Project service factory should return a wired service instance."""
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path))
    state = AppState()

    service = state.get_project_service("token-value")

    assert isinstance(service, ProjectService)
