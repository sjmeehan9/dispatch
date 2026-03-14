"""Navigation and state regression tests for Phase 5.5 validation."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from app.src.services.project_service import ProjectNotFoundError
from app.src.ui import components
from app.src.ui.state import AppState


class _FakeContext:
    """Minimal context manager test double for NiceGUI elements."""

    def __enter__(self) -> _FakeContext:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        _ = exc_type, exc, tb

    def classes(self, _: str) -> _FakeContext:
        return self

    def props(self, _: str) -> _FakeContext:
        return self


class _FakeDialog(_FakeContext):
    """Dialog fake that records open/close state transitions."""

    def __init__(self) -> None:
        self.is_open = False

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False


class _FakeNavigate:
    """Navigation test double for route calls."""

    def __init__(self) -> None:
        self.destinations: list[str] = []

    def to(self, destination: str) -> None:
        self.destinations.append(destination)


class _FakeUI:
    """Small fake ui module for shared component smoke tests."""

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


@pytest.fixture(scope="module")
def main_module(tmp_path_factory: pytest.TempPathFactory) -> ModuleType:
    """Import app.src.main in an isolated environment for route validation."""
    os.environ["DISPATCH_DATA_DIR"] = str(tmp_path_factory.mktemp("dispatch-main-nav"))
    module_name = "app.src.main"
    if module_name in sys.modules:
        return sys.modules[module_name]
    return importlib.import_module(module_name)


def test_required_ui_routes_are_registered(main_module: ModuleType) -> None:
    """Main app should expose all user-facing navigation routes."""
    registered_paths = {route.path for route in main_module.app.routes}

    assert "/" in registered_paths
    assert "/config/executor" in registered_paths
    assert "/config/action-types" in registered_paths
    assert "/config/secrets" in registered_paths
    assert "/project/link" in registered_paths
    assert "/project/load" in registered_paths
    assert "/project/{project_id}" in registered_paths


def test_page_layout_renders_title_and_back_button() -> None:
    """Shared page layout should render app title and provided page title."""
    fake_ui = _FakeUI()

    components.page_layout("Load Project", back_url="/", ui_module=fake_ui)

    assert "Dispatch" in fake_ui.labels
    assert "Load Project" in fake_ui.labels


def test_loading_overlay_show_and_hide() -> None:
    """Loading overlay should be programmatically controllable."""
    fake_ui = _FakeUI()

    overlay = components.loading_overlay("Linking...", ui_module=fake_ui)

    assert overlay._dialog.is_open is False
    overlay.show()
    assert overlay._dialog.is_open is True
    overlay.hide()
    assert overlay._dialog.is_open is False


def test_app_state_ensure_project_behaviour(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """ensure_project should return loaded project and None for unknown IDs."""
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path))
    state = AppState()

    known_project = SimpleNamespace(project_id="known")
    monkeypatch.setattr(
        state,
        "get_project_service",
        lambda _token: SimpleNamespace(
            load_project=lambda project_id: (
                known_project
                if project_id == "known"
                else (_ for _ in ()).throw(ProjectNotFoundError("missing"))
            )
        ),
    )

    loaded = state.ensure_project("known")
    missing = state.ensure_project("missing")

    assert loaded is known_project
    assert missing is None
    assert state.current_project is None


def test_app_state_clear_project_resets_runtime_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """clear_project should reset all project-scoped runtime state."""
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path))
    state = AppState()
    state.current_project = SimpleNamespace(project_id="project-1")
    state.last_dispatched_action = SimpleNamespace(action_id="a-1")
    state.dispatching_action_id = "a-2"
    state.completing_action_id = "a-3"
    state.selected_phase_filter_phase_id = 5

    state.clear_project()

    assert state.current_project is None
    assert state.last_dispatched_action is None
    assert state.dispatching_action_id is None
    assert state.completing_action_id is None
    assert state.selected_phase_filter_phase_id is None
