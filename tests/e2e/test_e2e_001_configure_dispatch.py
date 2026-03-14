"""E2E-001: Configure Dispatch and run one full mocked dispatch cycle."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from app.src.models import ActionStatus, ActionTypeDefaults, ExecutorConfig
from app.src.services.action_generator import ActionGenerator
from app.src.services.config_manager import ConfigManager
from app.src.services.executor import AutopilotExecutor
from app.src.services.github_client import GitHubFileEntry
from app.src.services.payload_resolver import PayloadResolver
from app.src.services.project_service import ProjectService
from app.src.services.webhook_service import WebhookService


class _MockGitHubClient:
    """Mock GitHub client returning deterministic phase and agent data."""

    def __init__(self, phase_progress: dict[str, object]) -> None:
        self._phase_progress = phase_progress

    def get_file_contents(self, owner: str, repo: str, path: str) -> str:
        assert (owner, repo, path) == ("owner", "repo", "docs/phase-progress.json")
        return json.dumps(self._phase_progress)

    def list_directory(self, owner: str, repo: str, path: str) -> list[GitHubFileEntry]:
        assert (owner, repo) == ("owner", "repo")
        if path == ".claude/agents/":
            return [
                GitHubFileEntry(
                    name="implement.md",
                    path=".claude/agents/implement.md",
                    type="file",
                    size=100,
                )
            ]
        if path == ".github/agents/":
            return [
                GitHubFileEntry(
                    name="review.md",
                    path=".github/agents/review.md",
                    type="file",
                    size=120,
                )
            ]
        raise AssertionError(f"Unexpected directory path: {path}")


def _action_type_value(action_type: object) -> str:
    """Normalise action type values to strings for assertions."""

    return getattr(action_type, "value", str(action_type))


def test_e2e_001_configure_and_dispatch_workflow(
    isolated_settings,
    sample_phase_progress,
    sample_executor_config: ExecutorConfig,
    sample_action_type_defaults: ActionTypeDefaults,
    mock_webhook_data,
) -> None:
    """Validate configure -> link -> generate -> resolve -> dispatch -> webhook flow."""

    config_manager = ConfigManager(isolated_settings)
    config_manager.save_executor_config(sample_executor_config)
    config_manager.save_action_type_defaults(sample_action_type_defaults)
    assert config_manager.has_config() is True

    loaded_executor = config_manager.get_executor_config()
    loaded_defaults = config_manager.get_action_type_defaults()

    project_service = ProjectService(
        settings=isolated_settings,
        github_client=_MockGitHubClient(sample_phase_progress),
    )
    project = project_service.link_project("owner/repo", "GITHUB_TOKEN")
    project_service.save_project(project)
    assert (
        project_service.load_project(project.project_id).project_id
        == project.project_id
    )

    actions = ActionGenerator.generate_actions(project.phases, loaded_defaults)
    assert len(actions) == 10
    assert [_action_type_value(action.action_type) for action in actions[:6]] == [
        "implement",
        "implement",
        "test",
        "review",
        "document",
        "implement",
    ]

    first_action = actions[0]
    resolver = PayloadResolver()
    context = resolver.build_context(
        project=project,
        phase_id=first_action.phase_id,
        component_id=first_action.component_id,
        executor_config=loaded_executor,
    )
    resolved = resolver.resolve_payload(first_action.payload, context)
    assert resolved.unresolved_variables == []
    assert "{{" not in json.dumps(resolved.payload)

    response = MagicMock()
    response.status_code = 200
    response.is_success = True
    response.text = "queued"
    response.json.return_value = {"status": "queued", "run_id": "run-e2e-1"}

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = response

    with patch("app.src.services.executor.httpx.Client", return_value=mock_client):
        executor = AutopilotExecutor(isolated_settings)
        dispatch_response = executor.dispatch(resolved.payload, loaded_executor)

    assert dispatch_response.status_code == 200
    assert dispatch_response.run_id == "run-e2e-1"
    assert dispatch_response.message == "queued"

    webhook_service = WebhookService()
    webhook_service.store("run-e2e-1", mock_webhook_data["run-e2e-1"])
    webhook_result = webhook_service.retrieve("run-e2e-1")
    assert webhook_result is not None
    assert webhook_result["run_id"] == "run-e2e-1"

    first_action.payload = resolved.payload
    first_action.executor_response = dispatch_response.model_dump(mode="json")
    first_action.webhook_response = webhook_result
    first_action.status = ActionStatus.COMPLETED
    assert _action_type_value(first_action.status) == "completed"
