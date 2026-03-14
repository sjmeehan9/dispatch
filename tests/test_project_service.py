"""Unit tests for project linking and scanning service."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.src.config.settings import Settings
from app.src.services.github_client import (
    GitHubAuthError,
    GitHubFileEntry,
    GitHubNotFoundError,
)
from app.src.services.project_service import ProjectLinkError, ProjectService


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
