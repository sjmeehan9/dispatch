"""Unit tests for saved-project load screen rendering."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.src.services.project_service import ProjectSummary
from app.src.ui import load_project


class _FakeContext:
    """Minimal context manager for fake NiceGUI layout primitives."""

    def __enter__(self) -> _FakeContext:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def classes(self, _: str) -> _FakeContext:
        return self

    def props(self, _: str) -> _FakeContext:
        return self


class _FakeButton(_FakeContext):
    """Simple fake button supporting style chaining."""

    def __init__(self, label: str | None = None) -> None:
        self.label = label


class _FakeLabel(_FakeContext):
    """Simple fake label capturing rendered text."""

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeDialog(_FakeContext):
    """Fake dialog object with open/close handlers."""

    def __init__(self) -> None:
        self.is_open = False

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False


class _FakeNavigate:
    """Fake navigation API for rendering tests."""

    def to(self, _: str) -> None:
        return None


class _FakeUI:
    """Fake NiceGUI module used to run render functions in unit tests."""

    def __init__(self) -> None:
        self.navigate = _FakeNavigate()
        self.labels: list[str] = []
        self.buttons: list[str] = []

    def column(self) -> _FakeContext:
        return _FakeContext()

    def header(self) -> _FakeContext:
        return _FakeContext()

    def card(self) -> _FakeContext:
        return _FakeContext()

    def row(self) -> _FakeContext:
        return _FakeContext()

    def dialog(self) -> _FakeDialog:
        return _FakeDialog()

    def separator(self) -> _FakeContext:
        return _FakeContext()

    def label(self, text: str) -> _FakeLabel:
        self.labels.append(text)
        return _FakeLabel(text)

    def spinner(self, *_args: object, **_kwargs: object) -> _FakeContext:
        return _FakeContext()

    def notify(self, _: str, type: str = "info") -> None:
        _ = type

    def refreshable(self, func):
        def _refresh() -> None:
            func()

        setattr(func, "refresh", _refresh)
        return func

    def button(
        self,
        label: str | None = None,
        *,
        on_click: object | None = None,
        icon: str | None = None,
        color: str | None = None,
    ) -> _FakeButton:
        _ = on_click, color
        rendered_label = label if label is not None else icon or ""
        self.buttons.append(rendered_label)
        return _FakeButton(rendered_label)


class _FakeProjectService:
    """Test double for local project listing/loading operations."""

    def __init__(self, projects: list[ProjectSummary]) -> None:
        self._projects = projects

    def list_projects(self) -> list[ProjectSummary]:
        return list(self._projects)

    def load_project(self, project_id: str) -> object:
        return SimpleNamespace(project_id=project_id)

    def delete_project(self, project_id: str) -> None:
        _ = project_id


def _build_app_state(projects: list[ProjectSummary]) -> SimpleNamespace:
    service = _FakeProjectService(projects)
    return SimpleNamespace(
        settings=SimpleNamespace(get_secret=lambda _key: None),
        current_project=None,
        get_project_service=lambda _token: service,
    )


def test_render_load_project_with_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Load-project screen should render empty-state content without errors."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(load_project, "ui", fake_ui)

    load_project.render_load_project(_build_app_state([]))

    assert "Load Project" in fake_ui.labels
    assert "No saved projects. Link a new project to get started." in fake_ui.labels
    assert "Link New Project" in fake_ui.buttons


def test_render_load_project_with_multiple_projects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load-project screen should render every saved project summary."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(load_project, "ui", fake_ui)

    projects = [
        ProjectSummary(
            project_id="project-2",
            project_name="Owner/Repo Two",
            repository="owner/repo-two",
            updated_at="2026-03-14T02:00:00Z",
        ),
        ProjectSummary(
            project_id="project-1",
            project_name="Owner/Repo One",
            repository="owner/repo-one",
            updated_at="2026-03-14T01:00:00Z",
        ),
    ]

    load_project.render_load_project(_build_app_state(projects))

    assert "Owner/Repo Two" in fake_ui.buttons
    assert "Owner/Repo One" in fake_ui.buttons
    assert "owner/repo-two" in fake_ui.labels
    assert "owner/repo-one" in fake_ui.labels
    assert "Updated: 2026-03-14T02:00:00Z" in fake_ui.labels
    assert "Updated: 2026-03-14T01:00:00Z" in fake_ui.labels
