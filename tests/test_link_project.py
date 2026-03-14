"""Unit tests for link-project workflow and error normalization."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.src.models import (
    Action,
    ActionStatus,
    ActionType,
    ActionTypeDefaults,
    ComponentData,
    ExecutorConfig,
    PhaseData,
    Project,
    ResolvedPayload,
)
from app.src.services.project_service import ProjectLinkError
from app.src.ui import link_project


class _FakeRun:
    """Fake NiceGUI run helper that executes io-bound calls inline."""

    @staticmethod
    async def io_bound(func: object, *args: object) -> object:
        if not callable(func):
            raise AssertionError("io_bound expects a callable.")
        return func(*args)


class _FakeProjectService:
    """Test double for project linking and save operations."""

    def __init__(self, project: Project) -> None:
        self.project = project
        self.link_calls: list[tuple[str, str]] = []
        self.saved_projects: list[Project] = []

    def link_project(self, repository: str, token_env_key: str) -> Project:
        self.link_calls.append((repository, token_env_key))
        return self.project

    def save_project(self, project: Project) -> None:
        self.saved_projects.append(project)


def _sample_project() -> Project:
    return Project(
        project_id="project-1",
        project_name="owner/repo",
        repository="owner/repo",
        github_token_env_key="GITHUB_TOKEN",
        phase_progress={"phases": []},
        phases=[
            PhaseData(
                phaseId=1,
                phaseName="Phase 1",
                status="refined",
                componentBreakdownDoc="docs/phase-1-component-breakdown.md",
                components=[
                    ComponentData(
                        componentId="1.1",
                        componentName="Component 1.1",
                        owner="AI Agent",
                        priority="Must-have",
                        estimatedEffort="2 hours",
                        status="not-started",
                    )
                ],
            )
        ],
        agent_files=[".claude/agents/implement.md", ".github/agents/review.md"],
        actions=[],
        created_at="2026-03-14T00:00:00Z",
        updated_at="2026-03-14T00:00:00Z",
    )


def _sample_action_defaults() -> ActionTypeDefaults:
    payload = {
        "repository": "{{repository}}",
        "branch": "{{branch}}",
        "agent_instructions": "run",
        "model": "gpt-4.1",
        "role": "engineer",
        "agent_paths": "{{agent_paths}}",
        "callback_url": "{{webhook_url}}",
        "timeout_minutes": 60,
    }
    return ActionTypeDefaults(
        implement=payload,
        test=payload,
        review={**payload, "pr_number": "{{pr_number}}"},
        document=payload,
        debug=payload,
    )


def test_scan_and_link_success_generates_and_resolves_actions(monkeypatch) -> None:
    """Successful scan should save project and populate resolved action payloads."""
    monkeypatch.setattr(link_project, "run", _FakeRun())

    project = _sample_project()
    project_service = _FakeProjectService(project)
    generated_action = Action(
        action_id="action-1",
        phase_id=1,
        component_id="1.1",
        action_type=ActionType.IMPLEMENT,
        payload={"repository": "{{repository}}", "component": "{{component_name}}"},
        status=ActionStatus.NOT_STARTED,
        executor_response=None,
        webhook_response=None,
    )
    action_generator = SimpleNamespace(
        generate_actions=lambda _phases, _defaults: [generated_action]
    )
    payload_resolver = SimpleNamespace(
        build_context=lambda **_: {
            "repository": "owner/repo",
            "component_name": "Component 1.1",
        },
        resolve_payload=lambda payload, context: ResolvedPayload(
            payload={
                "repository": payload["repository"].replace(
                    "{{repository}}", context["repository"]
                ),
                "component": payload["component"].replace(
                    "{{component_name}}", context["component_name"]
                ),
            },
            unresolved_variables=[],
        ),
    )
    app_state = SimpleNamespace(
        settings=SimpleNamespace(
            get_secret=lambda key: "token" if key == "GITHUB_TOKEN" else None
        ),
        get_project_service=lambda token: project_service if token == "token" else None,
        config_manager=SimpleNamespace(
            get_action_type_defaults=_sample_action_defaults,
            get_executor_config=lambda: ExecutorConfig(
                executor_id="autopilot",
                executor_name="Autopilot",
                api_endpoint="https://executor.example.com/run",
                api_key_env_key="AUTOPILOT_API_KEY",
                webhook_url="https://callback.example.com/hook",
            ),
        ),
        action_generator=action_generator,
        payload_resolver=payload_resolver,
        current_project=None,
    )

    linked_project = asyncio.run(
        link_project._scan_and_link(app_state, "owner/repo", "GITHUB_TOKEN")
    )

    assert linked_project.project_id == "project-1"
    assert linked_project.actions[0].payload == {
        "repository": "owner/repo",
        "component": "Component 1.1",
    }
    assert project_service.link_calls == [("owner/repo", "GITHUB_TOKEN")]
    assert project_service.saved_projects == [linked_project]
    assert app_state.current_project == linked_project


def test_scan_and_link_raises_when_token_missing() -> None:
    """Missing token env value should raise a helpful link error."""
    app_state = SimpleNamespace(
        settings=SimpleNamespace(get_secret=lambda _key: None),
    )

    try:
        asyncio.run(
            link_project._scan_and_link(app_state, "owner/repo", "GITHUB_TOKEN")
        )
    except ProjectLinkError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected ProjectLinkError when token is missing.")

    assert "Token not found in environment." in message
    assert "TOKEN for GITHUB_TOKEN" in message


def test_normalise_link_error_maps_expected_user_messages() -> None:
    """Known link errors should be mapped to required user-facing text."""
    phase_error = link_project._normalise_link_error(
        "phase-progress.json not found at docs/phase-progress.json in owner/repo. This file is required.",
        "owner/repo",
    )
    auth_error = link_project._normalise_link_error(
        "Authentication failed for owner/repo. Check your GitHub token.",
        "owner/repo",
    )

    assert (
        phase_error
        == "phase-progress.json not found at docs/phase-progress.json in owner/repo"
    )
    assert auth_error == "Authentication failed. Check your GitHub token."
