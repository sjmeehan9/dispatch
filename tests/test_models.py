"""Unit tests for core Dispatch data models."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.src.models import (
    Action,
    ActionType,
    ActionTypeDefaults,
    ExecutorConfig,
    PayloadTemplate,
    Project,
    ResolvedPayload,
)


def _sample_project_payload() -> dict[str, object]:
    return {
        "project_id": str(uuid.uuid4()),
        "project_name": "Dispatch",
        "repository": "sjmeehan9/dispatch",
        "github_token_env_key": "GITHUB_TOKEN",
        "phase_progress": {"phases": []},
        "phases": [
            {
                "phaseId": 2,
                "phaseName": "Data Models",
                "status": "refined",
                "componentBreakdownDoc": "docs/phase-2-component-breakdown.md",
                "components": [
                    {
                        "componentId": "2.1",
                        "componentName": "Core Data Models",
                        "owner": "AI Agent",
                        "priority": "Must-have",
                        "estimatedEffort": "2 hours",
                        "status": "not-started",
                    }
                ],
            }
        ],
        "agent_files": [".github/agents/Implementation.agent.md"],
        "created_at": "2026-03-14T00:00:00Z",
        "updated_at": "2026-03-14T00:00:00Z",
    }


def test_project_instantiation_and_round_trip_serialization() -> None:
    payload = _sample_project_payload()

    project = Project.model_validate(payload)
    dumped = project.model_dump()
    reloaded = Project.model_validate(dumped)

    assert project.repository == "sjmeehan9/dispatch"
    assert project.phases[0].phase_id == 2
    assert project.phases[0].components[0].component_id == "2.1"
    assert reloaded.model_dump() == dumped


def test_project_rejects_invalid_repository_format() -> None:
    payload = _sample_project_payload()
    payload["repository"] = "invalid-format"

    with pytest.raises(ValidationError):
        Project.model_validate(payload)


def test_action_defaults_use_not_started_and_none_responses() -> None:
    action = Action(
        action_id=str(uuid.uuid4()),
        phase_id=2,
        action_type=ActionType.IMPLEMENT,
        payload={"repository": "sjmeehan9/dispatch"},
    )

    assert action.status == "not_started"
    assert action.executor_response is None
    assert action.webhook_response is None


@pytest.mark.parametrize(
    "action_type",
    [
        ActionType.IMPLEMENT,
        ActionType.TEST,
        ActionType.REVIEW,
        ActionType.DOCUMENT,
        ActionType.DEBUG,
    ],
)
def test_action_supports_all_action_types(action_type: ActionType) -> None:
    action = Action(
        action_id=str(uuid.uuid4()),
        phase_id=2,
        action_type=action_type,
        payload={},
    )

    assert action.action_type == action_type.value


def test_executor_config_validates_endpoint_format() -> None:
    ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="http://localhost:8000/agent/run",
        api_key_env_key="AUTOPILOT_API_KEY",
    )

    with pytest.raises(ValidationError):
        ExecutorConfig(
            executor_id="autopilot",
            executor_name="Autopilot",
            api_endpoint="not-a-url",
            api_key_env_key="AUTOPILOT_API_KEY",
        )


def test_executor_config_use_llm_defaults_to_false_when_missing() -> None:
    """Executor config should remain backward-compatible when use_llm is absent."""
    config = ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="http://localhost:8000/agent/run",
        api_key_env_key="AUTOPILOT_API_KEY",
    )

    assert config.use_llm is False


def test_executor_config_serializes_use_llm_field() -> None:
    """Executor config should include use_llm when dumping persisted JSON payload."""
    config = ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="http://localhost:8000/agent/run",
        api_key_env_key="AUTOPILOT_API_KEY",
        use_llm=True,
    )

    assert config.model_dump()["use_llm"] is True


def test_action_type_defaults_includes_all_action_payload_templates() -> None:
    defaults = ActionTypeDefaults(
        implement={"role": "implement"},
        test={"role": "implement"},
        review={"role": "review"},
        document={"role": "implement"},
        debug={"role": "implement"},
    )

    dumped = defaults.model_dump()

    assert set(dumped) == {"implement", "test", "review", "document", "debug"}


def test_payload_template_extracts_variables_from_nested_values() -> None:
    template = PayloadTemplate(
        template_fields={
            "repository": "{{repository}}",
            "meta": {
                "branch": "{{branch}}",
                "notes": ["component={{component_id}}", "keep"],
            },
        }
    )

    assert template.get_variables() == {"repository", "branch", "component_id"}


def test_resolved_payload_defaults_unresolved_variables_to_empty_list() -> None:
    resolved = ResolvedPayload(payload={"repository": "sjmeehan9/dispatch"})

    assert resolved.unresolved_variables == []
