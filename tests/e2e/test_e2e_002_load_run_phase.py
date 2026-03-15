"""E2E-002: Load a saved project and execute all actions for one phase."""

from __future__ import annotations

from app.src.models import ActionStatus
from app.src.services.project_service import ProjectService


class _NoopGitHubClient:
    """Placeholder GitHub client for persistence-only test paths."""

    def get_file_contents(self, owner: str, repo: str, path: str) -> str:
        raise AssertionError("GitHub file lookup should not be called in load/run E2E")

    def list_directory(self, owner: str, repo: str, path: str) -> list[object]:
        raise AssertionError(
            "GitHub directory lookup should not be called in load/run E2E"
        )


def _action_type_value(action_type: object) -> str:
    """Normalise action type values to strings for assertions."""

    return getattr(action_type, "value", str(action_type))


def test_e2e_002_load_project_and_run_phase_actions(
    isolated_settings,
    sample_project,
    mock_executor_response,
) -> None:
    """Validate project load and complete execution lifecycle for phase 1 actions."""

    project_service = ProjectService(isolated_settings, _NoopGitHubClient())
    project_service.save_project(sample_project)
    loaded_project = project_service.load_project(sample_project.project_id)

    assert loaded_project.project_id == sample_project.project_id
    assert len(loaded_project.actions) == len(sample_project.actions)

    phase_one_actions = [
        action for action in loaded_project.actions if action.phase_id == 1
    ]
    phase_two_actions = [
        action for action in loaded_project.actions if action.phase_id == 2
    ]

    assert [_action_type_value(action.action_type) for action in phase_one_actions] == [
        "implement",
        "review",
        "merge",
        "implement",
        "review",
        "merge",
        "test",
        "document",
    ]

    for index, action in enumerate(phase_one_actions, start=1):
        response = mock_executor_response(
            run_id=f"phase-1-run-{index}",
            message=f"queued-{index}",
        )
        action.executor_response = response.model_dump(mode="json")
        action.status = ActionStatus.DISPATCHED
        action.status = ActionStatus.COMPLETED

    assert all(
        _action_type_value(action.status) == "completed" for action in phase_one_actions
    )
    assert all(
        _action_type_value(action.status) == "not_started"
        for action in phase_two_actions
    )
