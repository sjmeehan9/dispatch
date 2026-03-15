"""Integration tests for end-to-end Dispatch workflow with mocked external APIs."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from app.src.config.settings import Settings
from app.src.models import ActionStatus, ActionTypeDefaults, ExecutorConfig
from app.src.services.project_service import ProjectService
from app.src.ui.state import AppState


class _FakeGitHubClient:
    """Fake GitHub client that returns deterministic repository scan data."""

    def get_file_contents(self, owner: str, repo: str, path: str) -> str:
        """Return a static phase-progress payload for link scans."""
        assert owner == "owner"
        assert repo == "repo"
        assert path == "docs/phase-progress.json"
        return json.dumps(
            {
                "lastUpdated": "2026-03-14",
                "phases": [
                    {
                        "phaseId": 1,
                        "phaseName": "MVP UI",
                        "status": "refined",
                        "componentBreakdownDoc": "docs/phase-4-component-breakdown.md",
                        "components": [
                            {
                                "componentId": "4.7",
                                "componentName": "Main Screen Layout",
                                "owner": "AI Agent",
                                "priority": "Must-have",
                                "estimatedEffort": "3 hours",
                                "status": "not-started",
                            },
                            {
                                "componentId": "4.8",
                                "componentName": "Response Display",
                                "owner": "AI Agent",
                                "priority": "Must-have",
                                "estimatedEffort": "2 hours",
                                "status": "not-started",
                            },
                        ],
                    }
                ],
            }
        )

    def list_directory(self, owner: str, repo: str, path: str) -> list[object]:
        """Return deterministic agent file listings for known agent directories."""
        assert owner == "owner"
        assert repo == "repo"
        if path == ".claude/agents/":
            return [
                Mock(type="file", path=".claude/agents/implement.md"),
                Mock(type="dir", path=".claude/agents/archive"),
            ]
        if path == ".github/agents/":
            return [Mock(type="file", path=".github/agents/review.md")]
        raise AssertionError(f"Unexpected directory request: {path}")


def _prepare_isolated_app_state(monkeypatch, tmp_path: Path) -> AppState:
    """Create an AppState instance bound to isolated temp settings paths."""
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path / "dispatch-data"))
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")
    monkeypatch.setenv("AUTOPILOT_API_KEY", "test-autopilot-key")
    monkeypatch.setattr(
        Settings,
        "_resolve_env_file_path",
        staticmethod(lambda: tmp_path / ".env/.env.local"),
    )
    return AppState()


def _sample_executor_config() -> ExecutorConfig:
    """Build a concrete executor config for workflow integration tests."""
    return ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="https://autopilot.example.com/agent/run",
        api_key_env_key="AUTOPILOT_API_KEY",
        webhook_url="https://dispatch.example.com/webhook/callback",
    )


def _sample_action_defaults() -> ActionTypeDefaults:
    """Build deterministic action type templates with placeholders."""
    return ActionTypeDefaults(
        implement={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Implement {{component_name}} ({{component_id}})",
            "role": "implement",
            "agent_paths": "{{agent_paths}}",
            "callback_url": "{{webhook_url}}",
            "timeout_minutes": 30,
        },
        test={
            "repository": "{{repository}}",
            "agent_instructions": "Test phase {{phase_id}}",
            "role": "implement",
        },
        review={
            "repository": "{{repository}}",
            "agent_instructions": "Review phase {{phase_id}}",
            "role": "review",
            "pr_number": "{{pr_number}}",
        },
        merge={
            "repository": "{{repository}}",
            "agent_instructions": "Merge PR for component {{component_id}}",
            "role": "merge",
            "pr_number": "{{pr_number}}",
        },
        document={
            "repository": "{{repository}}",
            "agent_instructions": "Document phase {{phase_id}}",
            "role": "implement",
        },
        debug={
            "repository": "{{repository}}",
            "agent_instructions": "",
            "role": "implement",
        },
    )


def test_full_dispatch_workflow_with_mocked_external_dependencies(
    monkeypatch, tmp_path: Path
) -> None:
    """Validate config, linking, generation, dispatch, webhook, and persistence flow."""
    app_state = _prepare_isolated_app_state(monkeypatch, tmp_path)

    executor_config = _sample_executor_config()
    action_defaults = _sample_action_defaults()
    app_state.config_manager.save_executor_config(executor_config)
    app_state.config_manager.save_action_type_defaults(action_defaults)
    app_state.reload_config()

    assert app_state.is_fully_configured is True

    project_service = ProjectService(app_state.settings, _FakeGitHubClient())
    project = project_service.link_project("owner/repo", "GITHUB_TOKEN")

    generated_actions = app_state.action_generator.generate_actions(
        project.phases, action_defaults
    )
    assert len(generated_actions) == 8
    assert [action.action_type for action in generated_actions] == [
        "implement",
        "review",
        "merge",
        "implement",
        "review",
        "merge",
        "test",
        "document",
    ]

    implement_action = generated_actions[0]
    context = app_state.payload_resolver.build_context(
        project=project,
        phase_id=implement_action.phase_id,
        component_id=implement_action.component_id,
        executor_config=executor_config,
    )
    resolved = app_state.payload_resolver.resolve_payload(
        implement_action.payload, context
    )
    assert resolved.unresolved_variables == []
    assert "{{" not in json.dumps(resolved.payload)
    assert resolved.payload["repository"] == "owner/repo"
    assert resolved.payload["branch"] == "main"

    response = Mock()
    response.status_code = 200
    response.is_success = True
    response.text = "ok"
    response.json.return_value = {
        "status": "queued",
        "run_id": "workflow-run-1",
    }
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = response

    with patch("app.src.services.executor.httpx.Client", return_value=mock_client):
        dispatch_response = app_state.autopilot_executor.dispatch(
            payload=resolved.payload,
            config=executor_config,
        )

    assert dispatch_response.status_code == 200
    assert dispatch_response.run_id == "workflow-run-1"
    assert dispatch_response.message == "queued"

    app_state.webhook_service.store(
        "workflow-run-1",
        {
            "run_id": "workflow-run-1",
            "status": "success",
            "result": {"summary": "Completed"},
        },
    )
    webhook_payload = app_state.webhook_service.retrieve("workflow-run-1")
    assert webhook_payload is not None
    assert webhook_payload["status"] == "success"

    project.actions = generated_actions
    project.actions[0].payload = resolved.payload
    project.actions[0].executor_response = dispatch_response.model_dump(mode="json")
    project.actions[0].webhook_response = webhook_payload
    project.actions[0].status = ActionStatus.COMPLETED

    project_service.save_project(project)
    loaded_project = project_service.load_project(project.project_id)

    assert loaded_project.project_id == project.project_id
    assert loaded_project.actions[0].status == "completed"
    assert loaded_project.actions[0].executor_response is not None
    assert loaded_project.actions[0].webhook_response is not None
    assert loaded_project.actions[0].webhook_response["run_id"] == "workflow-run-1"
