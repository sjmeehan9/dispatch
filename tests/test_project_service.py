"""Unit tests for project linking and scanning service."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.src.config.settings import Settings
from app.src.models import Project
from app.src.services.github_client import (
    GitHubAuthError,
    GitHubFileEntry,
    GitHubNotFoundError,
)
from app.src.services.project_service import (
    ProjectLinkError,
    ProjectNotFoundError,
    ProjectService,
)


class _FakeGitHubClient:
    """Test double for GitHub client interactions."""

    def __init__(
        self,
        *,
        phase_progress_payload: dict[str, object] | None = None,
        phase_progress_exception: Exception | None = None,
        claude_entries: list[GitHubFileEntry] | None = None,
        github_entries: list[GitHubFileEntry] | None = None,
    ) -> None:
        self._phase_progress_payload = phase_progress_payload
        self._phase_progress_exception = phase_progress_exception
        self._claude_entries = claude_entries or []
        self._github_entries = github_entries or []

    def get_file_contents(self, owner: str, repo: str, path: str) -> str:
        assert owner == "owner"
        assert repo == "repo"
        assert path == "docs/phase-progress.json"
        if self._phase_progress_exception is not None:
            raise self._phase_progress_exception
        return json.dumps(self._phase_progress_payload)

    def list_directory(self, owner: str, repo: str, path: str) -> list[GitHubFileEntry]:
        assert owner == "owner"
        assert repo == "repo"
        if path == ".claude/agents/":
            return self._claude_entries
        if path == ".github/agents/":
            return self._github_entries
        raise AssertionError(f"Unexpected path requested: {path}")


def _build_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Settings:
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path / "dispatch-data"))
    monkeypatch.setattr(
        Settings,
        "_resolve_env_file_path",
        staticmethod(lambda: tmp_path / ".env/.env.local"),
    )
    monkeypatch.setenv("GITHUB_TOKEN", "token-from-env")
    return Settings()


def _sample_phase_progress_payload() -> dict[str, object]:
    return {
        "lastUpdated": "2026-03-14",
        "phases": [
            {
                "phaseId": 1,
                "phaseName": "Phase 1",
                "status": "refined",
                "componentBreakdownDoc": "docs/phase-1-component-breakdown.md",
                "components": [
                    {
                        "componentId": "1.1",
                        "componentName": "Component 1.1",
                        "owner": "AI Agent",
                        "priority": "Must-have",
                        "estimatedEffort": "2 hours",
                        "status": "not-started",
                    }
                ],
            }
        ],
    }


def _sample_project(
    project_id: str, updated_at: str = "2026-03-14T00:00:00Z"
) -> Project:
    return Project(
        project_id=project_id,
        project_name=f"Project {project_id}",
        repository="owner/repo",
        github_token_env_key="GITHUB_TOKEN",
        phase_progress=_sample_phase_progress_payload(),
        phases=[],
        agent_files=[],
        actions=[],
        created_at="2026-03-14T00:00:00Z",
        updated_at=updated_at,
    )


def test_link_project_returns_valid_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    github_client = _FakeGitHubClient(
        phase_progress_payload=_sample_phase_progress_payload(),
        claude_entries=[
            GitHubFileEntry(
                name="implement.md",
                path=".claude/agents/implement.md",
                type="file",
                size=10,
            )
        ],
        github_entries=[
            GitHubFileEntry(
                name="review.md",
                path=".github/agents/review.md",
                type="file",
                size=12,
            )
        ],
    )
    service = ProjectService(settings=settings, github_client=github_client)

    project = service.link_project("owner/repo", "GITHUB_TOKEN")

    assert project.project_name == "owner/repo"
    assert project.repository == "owner/repo"
    assert project.github_token_env_key == "GITHUB_TOKEN"
    assert len(project.phases) == 1
    assert project.phases[0].phase_id == 1
    assert project.phases[0].components[0].component_id == "1.1"
    assert project.agent_files == [
        ".claude/agents/implement.md",
        ".github/agents/review.md",
    ]
    assert project.actions == []
    assert project.created_at.endswith("Z")
    assert project.updated_at.endswith("Z")


def test_link_project_raises_for_invalid_repository(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(
        settings=settings,
        github_client=_FakeGitHubClient(
            phase_progress_payload=_sample_phase_progress_payload()
        ),
    )

    with pytest.raises(ProjectLinkError, match="owner/repo"):
        service.link_project("no-slash", "GITHUB_TOKEN")


def test_link_project_raises_when_phase_progress_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(
        settings=settings,
        github_client=_FakeGitHubClient(
            phase_progress_exception=GitHubNotFoundError("missing")
        ),
    )

    with pytest.raises(ProjectLinkError, match="phase-progress.json not found"):
        service.link_project("owner/repo", "GITHUB_TOKEN")


def test_link_project_raises_on_auth_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(
        settings=settings,
        github_client=_FakeGitHubClient(
            phase_progress_exception=GitHubAuthError("denied")
        ),
    )

    with pytest.raises(ProjectLinkError, match="Authentication failed"):
        service.link_project("owner/repo", "GITHUB_TOKEN")


def test_parse_phase_progress_maps_camel_case_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(
        settings=settings,
        github_client=_FakeGitHubClient(
            phase_progress_payload=_sample_phase_progress_payload()
        ),
    )

    parsed = service._parse_phase_progress(_sample_phase_progress_payload())

    assert parsed[0].phase_name == "Phase 1"
    assert parsed[0].component_breakdown_doc == "docs/phase-1-component-breakdown.md"
    assert parsed[0].components[0].component_name == "Component 1.1"
    assert parsed[0].components[0].estimated_effort == "2 hours"


def test_discover_agent_files_finds_both_standard_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    github_client = _FakeGitHubClient(
        phase_progress_payload=_sample_phase_progress_payload(),
        claude_entries=[
            GitHubFileEntry(
                name="implement.md",
                path=".claude/agents/implement.md",
                type="file",
                size=1,
            ),
            GitHubFileEntry(
                name="nested",
                path=".claude/agents/nested",
                type="dir",
                size=0,
            ),
        ],
        github_entries=[
            GitHubFileEntry(
                name="review.md",
                path=".github/agents/review.md",
                type="file",
                size=2,
            )
        ],
    )
    service = ProjectService(settings=settings, github_client=github_client)

    discovered = service._discover_agent_files("owner", "repo")

    assert discovered == [".claude/agents/implement.md", ".github/agents/review.md"]


def test_discover_agent_files_returns_empty_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(
        settings=settings,
        github_client=_FakeGitHubClient(
            phase_progress_payload=_sample_phase_progress_payload(),
            claude_entries=[],
            github_entries=[],
        ),
    )

    assert service._discover_agent_files("owner", "repo") == []


def test_save_project_creates_valid_json_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(settings=settings, github_client=_FakeGitHubClient())
    project = _sample_project("project-1")
    original_updated_at = project.updated_at

    service.save_project(project)

    project_path = settings.projects_dir / "project-1.json"
    assert project_path.exists()
    payload = json.loads(project_path.read_text(encoding="utf-8"))
    assert payload["project_id"] == "project-1"
    assert payload["project_name"] == "Project project-1"
    assert project.updated_at.endswith("Z")
    assert project.updated_at != original_updated_at


def test_save_and_load_project_round_trip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(settings=settings, github_client=_FakeGitHubClient())
    project = _sample_project("project-2")

    service.save_project(project)
    loaded = service.load_project("project-2")

    assert loaded.model_dump(mode="json") == project.model_dump(mode="json")


def test_load_project_raises_for_missing_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(settings=settings, github_client=_FakeGitHubClient())

    with pytest.raises(ProjectNotFoundError, match="missing"):
        service.load_project("missing")


def test_list_projects_returns_sorted_summaries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    (settings.projects_dir / "older.json").write_text(
        json.dumps(
            {
                "project_id": "older",
                "project_name": "Older",
                "repository": "owner/repo",
                "updated_at": "2026-03-14T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (settings.projects_dir / "newer.json").write_text(
        json.dumps(
            {
                "project_id": "newer",
                "project_name": "Newer",
                "repository": "owner/repo",
                "updated_at": "2026-03-14T02:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    service = ProjectService(settings=settings, github_client=_FakeGitHubClient())

    summaries = service.list_projects()

    assert [summary.project_id for summary in summaries] == ["newer", "older"]


def test_list_projects_returns_empty_when_none_exist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(settings=settings, github_client=_FakeGitHubClient())

    assert service.list_projects() == []


def test_list_projects_skips_malformed_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    (settings.projects_dir / "broken.json").write_text("{not-json", encoding="utf-8")
    service = ProjectService(settings=settings, github_client=_FakeGitHubClient())

    summaries = service.list_projects()

    assert summaries == []
    assert "Skipping malformed project file" in caplog.text


def test_delete_project_removes_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(settings=settings, github_client=_FakeGitHubClient())
    project = _sample_project("project-delete")
    service.save_project(project)

    service.delete_project("project-delete")

    assert not (settings.projects_dir / "project-delete.json").exists()
    with pytest.raises(ProjectNotFoundError):
        service.delete_project("project-delete")


def test_delete_project_raises_for_missing_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(settings=settings, github_client=_FakeGitHubClient())

    with pytest.raises(ProjectNotFoundError, match="missing"):
        service.delete_project("missing")


def test_save_project_uses_atomic_replace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    service = ProjectService(settings=settings, github_client=_FakeGitHubClient())
    project = _sample_project("project-atomic")
    replace_calls: list[tuple[str, str, bool]] = []
    real_replace = os.replace

    def _capture_replace(
        src: os.PathLike[str] | str, dst: os.PathLike[str] | str
    ) -> None:
        src_path = Path(src)
        dst_path = Path(dst)
        replace_calls.append((str(src_path), str(dst_path), src_path.exists()))
        real_replace(src_path, dst_path)

    monkeypatch.setattr("app.src.services.project_service.os.replace", _capture_replace)

    service.save_project(project)

    assert len(replace_calls) == 1
    src, dst, src_existed = replace_calls[0]
    assert src.endswith(".json.tmp")
    assert dst.endswith(".json")
    assert src_existed
