"""Unit tests for main screen grouping and dispatch workflow."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.src.models import (
    Action,
    ActionStatus,
    ActionType,
    ComponentData,
    ExecutorConfig,
    PhaseData,
    Project,
    ResolvedPayload,
)
from app.src.ui import main_screen


class _FakeRun:
    """Fake NiceGUI run helper that executes io-bound calls inline."""

    @staticmethod
    async def io_bound(func: object, *args: object) -> object:
        if not callable(func):
            raise AssertionError("io_bound expects a callable")
        return func(*args)


class _FakeUI:
    """Fake NiceGUI ui helper for notification assertions."""

    def __init__(self) -> None:
        self.notifications: list[tuple[str, str]] = []

    def notify(self, message: str, type: str = "info") -> None:
        self.notifications.append((message, type))


class _FakeProjectService:
    """Simple project service test double for save assertions."""

    def __init__(self) -> None:
        self.saved_projects: list[Project] = []

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
                        estimatedEffort="1 hour",
                        status="not-started",
                    )
                ],
            ),
            PhaseData(
                phaseId=2,
                phaseName="Phase 2",
                status="refined",
                componentBreakdownDoc="docs/phase-2-component-breakdown.md",
                components=[
                    ComponentData(
                        componentId="2.1",
                        componentName="Component 2.1",
                        owner="AI Agent",
                        priority="Must-have",
                        estimatedEffort="1 hour",
                        status="not-started",
                    )
                ],
            ),
        ],
        agent_files=[".claude/agents/implement.md"],
        actions=[
            Action(
                action_id="a1",
                phase_id=1,
                component_id="1.1",
                action_type=ActionType.IMPLEMENT,
                payload={"repository": "{{repository}}"},
                status=ActionStatus.NOT_STARTED,
                executor_response=None,
                webhook_response=None,
            ),
            Action(
                action_id="a2",
                phase_id=1,
                component_id=None,
                action_type=ActionType.TEST,
                payload={"phase": "{{phase_name}}"},
                status=ActionStatus.NOT_STARTED,
                executor_response=None,
                webhook_response=None,
            ),
            Action(
                action_id="a3",
                phase_id=2,
                component_id="2.1",
                action_type=ActionType.IMPLEMENT,
                payload={"repository": "{{repository}}"},
                status=ActionStatus.NOT_STARTED,
                executor_response=None,
                webhook_response=None,
            ),
        ],
        created_at="2026-03-14T00:00:00Z",
        updated_at="2026-03-14T00:00:00Z",
    )


def test_group_actions_by_phase_preserves_order_and_phase_names() -> None:
    """Actions should be grouped by phase with stable in-phase ordering."""
    project = _sample_project()

    grouped = main_screen._group_actions_by_phase(project)

    assert [(phase_id, phase_name) for phase_id, phase_name, _ in grouped] == [
        (1, "Phase 1"),
        (2, "Phase 2"),
    ]
    assert [action.action_id for action in grouped[0][2]] == ["a1", "a2"]
    assert [action.action_id for action in grouped[1][2]] == ["a3"]


def test_dispatch_action_resolves_payload_dispatches_and_updates_status(
    monkeypatch,
) -> None:
    """Dispatch should resolve payload, call executor, persist, and mark dispatched."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(main_screen, "ui", fake_ui)
    monkeypatch.setattr(main_screen, "run", _FakeRun())

    project = _sample_project()
    action = project.actions[0]
    project_service = _FakeProjectService()

    executor_config = ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="https://executor.example.com/run",
        api_key_env_key="AUTOPILOT_API_KEY",
        webhook_url="https://callback.example.com/hook",
    )

    executor_calls: list[tuple[dict[str, object], ExecutorConfig]] = []

    def _dispatch(
        payload: dict[str, object], config: ExecutorConfig
    ) -> SimpleNamespace:
        executor_calls.append((payload, config))
        return SimpleNamespace(
            status_code=200,
            message="queued",
            run_id="run-1",
            model_dump=lambda: {
                "status_code": 200,
                "message": "queued",
                "run_id": "run-1",
            },
        )

    app_state = SimpleNamespace(
        current_project=project,
        config_manager=SimpleNamespace(get_executor_config=lambda: executor_config),
        payload_resolver=SimpleNamespace(
            build_context=lambda **_: {
                "repository": "owner/repo",
                "phase_name": "Phase 1",
            },
            resolve_payload=lambda payload, context: ResolvedPayload(
                payload={
                    "repository": payload["repository"].replace(
                        "{{repository}}", context["repository"]
                    )
                },
                unresolved_variables=[],
            ),
        ),
        autopilot_executor=SimpleNamespace(dispatch=_dispatch),
    )

    response = asyncio.run(
        main_screen._dispatch_action(app_state, project_service, action)
    )

    assert response is not None
    assert response.status_code == 200
    assert executor_calls[0][0] == {"repository": "owner/repo"}
    assert action.payload == {"repository": "owner/repo"}
    assert action.status == ActionStatus.DISPATCHED
    assert action.executor_response == {
        "status_code": 200,
        "message": "queued",
        "run_id": "run-1",
    }
    assert project_service.saved_projects == [project]
    assert ("Action dispatched", "positive") in fake_ui.notifications


def test_dispatch_action_keeps_status_when_executor_returns_failure(
    monkeypatch,
) -> None:
    """Failed dispatch responses should not mark an action as dispatched."""
    fake_ui = _FakeUI()
    monkeypatch.setattr(main_screen, "ui", fake_ui)
    monkeypatch.setattr(main_screen, "run", _FakeRun())

    project = _sample_project()
    action = project.actions[0]
    project_service = _FakeProjectService()

    executor_config = ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="https://executor.example.com/run",
        api_key_env_key="AUTOPILOT_API_KEY",
        webhook_url="https://callback.example.com/hook",
    )

    def _dispatch(
        payload: dict[str, object], config: ExecutorConfig
    ) -> SimpleNamespace:
        _ = payload, config
        return SimpleNamespace(
            status_code=0,
            message="Connection failed",
            run_id=None,
            model_dump=lambda: {
                "status_code": 0,
                "message": "Connection failed",
                "run_id": None,
            },
        )

    app_state = SimpleNamespace(
        current_project=project,
        config_manager=SimpleNamespace(get_executor_config=lambda: executor_config),
        payload_resolver=SimpleNamespace(
            build_context=lambda **_: {
                "repository": "owner/repo",
                "phase_name": "Phase 1",
            },
            resolve_payload=lambda payload, context: ResolvedPayload(
                payload={
                    "repository": payload["repository"].replace(
                        "{{repository}}", context["repository"]
                    )
                },
                unresolved_variables=[],
            ),
        ),
        autopilot_executor=SimpleNamespace(dispatch=_dispatch),
    )

    response = asyncio.run(
        main_screen._dispatch_action(app_state, project_service, action)
    )

    assert response is not None
    assert response.status_code == 0
    assert action.status == ActionStatus.NOT_STARTED
    assert action.executor_response == {
        "status_code": 0,
        "message": "Connection failed",
        "run_id": None,
    }
    assert project_service.saved_projects == [project]
    assert ("Dispatch failed: Connection failed", "negative") in fake_ui.notifications
