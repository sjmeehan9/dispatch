"""Unit tests for shared application state."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.src.services import ProjectService
from app.src.services.config_manager import ConfigManager
from app.src.services.project_service import ProjectNotFoundError
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


def test_clear_project_resets_project_scoped_runtime_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """clear_project should drop in-memory project and action runtime state."""
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path))
    state = AppState()
    state.current_project = SimpleNamespace(project_id="project-1")
    state.last_dispatched_action = SimpleNamespace(action_id="action-1")
    state.dispatching_action_id = "action-2"
    state.completing_action_id = "action-3"

    state.clear_project()

    assert state.current_project is None
    assert state.last_dispatched_action is None
    assert state.dispatching_action_id is None
    assert state.completing_action_id is None


def test_ensure_project_returns_loaded_project_when_service_finds_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """ensure_project should load and retain a project when available."""
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path))
    state = AppState()
    project = SimpleNamespace(project_id="project-1")

    monkeypatch.setattr(
        state,
        "get_project_service",
        lambda _token: SimpleNamespace(load_project=lambda _id: project),
    )

    loaded = state.ensure_project("project-1")

    assert loaded is project
    assert state.current_project is project


def test_ensure_project_returns_none_when_project_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """ensure_project should clear stale state and return None for unknown IDs."""
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path))
    state = AppState()
    state.current_project = SimpleNamespace(project_id="stale")

    def _raise_not_found(_id: str) -> None:
        raise ProjectNotFoundError("not found")

    monkeypatch.setattr(
        state,
        "get_project_service",
        lambda _token: SimpleNamespace(load_project=_raise_not_found),
    )

    loaded = state.ensure_project("missing")

    assert loaded is None
    assert state.current_project is None
