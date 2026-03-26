"""Unit tests for payload resolver service."""

from __future__ import annotations

import json

import pytest

from app.src.models import ExecutorConfig, Project
from app.src.services.payload_resolver import PayloadResolver


def _sample_project() -> Project:
    return Project.model_validate(
        {
            "project_id": "project-1",
            "project_name": "Dispatch",
            "repository": "owner/repo",
            "github_token_env_key": "GITHUB_TOKEN",
            "phase_progress": {"phases": []},
            "phases": [
                {
                    "phaseId": 3,
                    "phaseName": "Core Backend Services",
                    "status": "refined",
                    "componentBreakdownDoc": "docs/phase-3-component-breakdown.md",
                    "components": [
                        {
                            "componentId": "3.5",
                            "componentName": "Payload Resolver Service",
                            "owner": "AI Agent",
                            "priority": "Must-have",
                            "estimatedEffort": "2 hours",
                            "status": "not-started",
                        }
                    ],
                }
            ],
            "agent_files": [
                ".claude/agents/implement.md",
                ".github/agents/review.md",
            ],
            "actions": [],
            "created_at": "2026-03-14T00:00:00Z",
            "updated_at": "2026-03-14T00:00:00Z",
        }
    )


def _sample_executor_config() -> ExecutorConfig:
    return ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="https://autopilot.example.com/api/dispatch",
        api_key_env_key="AUTOPILOT_API_KEY",
        webhook_url="https://dispatch.example.com/webhook",
    )


def test_build_context_returns_expected_values() -> None:
    context = PayloadResolver.build_context(
        project=_sample_project(),
        phase_id=3,
        component_id="3.5",
        executor_config=_sample_executor_config(),
    )

    assert context == {
        "repository": "owner/repo",
        "branch": "main",
        "phase_id": "3",
        "phase_name": "Core Backend Services",
        "component_id": "3.5",
        "component_name": "Payload Resolver Service",
        "component_breakdown_doc": "docs/phase-3-component-breakdown.md",
        "agent_paths": json.dumps(
            [".claude/agents/implement.md", ".github/agents/review.md"]
        ),
        "webhook_url": "https://dispatch.example.com/webhook",
        "pr_number": "",
    }


def test_build_context_normalises_root_webhook_url_to_callback_path() -> None:
    executor_config = ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="https://autopilot.example.com/api/dispatch",
        api_key_env_key="AUTOPILOT_API_KEY",
        webhook_url="https://dispatch.example.com",
    )

    context = PayloadResolver.build_context(
        project=_sample_project(),
        phase_id=3,
        component_id="3.5",
        executor_config=executor_config,
    )

    assert context["webhook_url"] == "https://dispatch.example.com/webhook/callback"


def test_build_context_with_no_component_sets_component_fields_empty() -> None:
    context = PayloadResolver.build_context(
        project=_sample_project(),
        phase_id=3,
        component_id=None,
        executor_config=_sample_executor_config(),
    )

    assert context["component_id"] == ""
    assert context["component_name"] == ""


def test_build_context_raises_for_missing_phase_or_component() -> None:
    project = _sample_project()
    executor_config = _sample_executor_config()

    with pytest.raises(ValueError, match="Phase 99"):
        PayloadResolver.build_context(project, 99, None, executor_config)

    with pytest.raises(ValueError, match="Component '3.999'"):
        PayloadResolver.build_context(project, 3, "3.999", executor_config)


def test_resolve_payload_replaces_placeholders_recursively() -> None:
    payload = {
        "repository": "{{repository}}",
        "instructions": "Use {{branch}} for {{repository}}",
        "config": {"phase": "{{phase_name}}", "component_id": "{{component_id}}"},
        "agents": ["{{agent_paths}}", "literal"],
    }
    context = PayloadResolver.build_context(
        project=_sample_project(),
        phase_id=3,
        component_id="3.5",
        executor_config=_sample_executor_config(),
    )

    resolved = PayloadResolver.resolve_payload(payload, context)

    assert resolved.payload["repository"] == "owner/repo"
    assert resolved.payload["instructions"] == "Use main for owner/repo"
    assert resolved.payload["config"] == {
        "phase": "Core Backend Services",
        "component_id": "3.5",
    }
    assert resolved.payload["agents"] == [
        [".claude/agents/implement.md", ".github/agents/review.md"],
        "literal",
    ]
    assert resolved.unresolved_variables == []


def test_resolve_payload_preserves_non_string_values_and_tracks_unresolved() -> None:
    payload = {
        "timeout": 120,
        "stream": False,
        "metadata": {"pr": "{{pr_number}}", "unknown": "{{missing_var}}"},
        "items": [1, True, None, "{{missing_var}}", "{{pr_number}}"],
    }
    context = {"pr_number": "42"}

    resolved = PayloadResolver.resolve_payload(payload, context)

    assert resolved.payload["timeout"] == 120
    assert resolved.payload["stream"] is False
    assert resolved.payload["items"][:3] == [1, True, None]
    assert resolved.payload["metadata"]["pr"] == "42"
    assert resolved.payload["items"][-1] == "42"
    assert resolved.payload["metadata"]["unknown"] == "{{missing_var}}"
    assert resolved.payload["items"][-2] == "{{missing_var}}"
    assert resolved.unresolved_variables == ["missing_var"]


def test_resolve_payload_tracks_unresolved_when_context_is_empty() -> None:
    payload = {"pr_number": "{{pr_number}}"}

    resolved = PayloadResolver.resolve_payload(payload, {})

    assert resolved.payload["pr_number"] == "{{pr_number}}"
    assert resolved.unresolved_variables == ["pr_number"]


def test_resolve_payload_deserialises_json_array_for_full_placeholder() -> None:
    """A placeholder that is the entire value and resolves to a JSON array
    should produce a native list, not a JSON string."""

    agent_list = [".claude/agents/implement.md", ".github/agents/review.md"]
    payload = {"agent_paths": "{{agent_paths}}"}
    context = {"agent_paths": json.dumps(agent_list)}

    resolved = PayloadResolver.resolve_payload(payload, context)

    assert resolved.payload["agent_paths"] == agent_list
    assert isinstance(resolved.payload["agent_paths"], list)
    assert resolved.unresolved_variables == []


def test_resolve_payload_keeps_json_string_when_embedded_in_text() -> None:
    """A placeholder embedded in surrounding text should remain a string,
    even if the context value is a JSON array."""

    agent_list = [".claude/agents/implement.md"]
    payload = {"note": "Agents: {{agent_paths}} end"}
    context = {"agent_paths": json.dumps(agent_list)}

    resolved = PayloadResolver.resolve_payload(payload, context)

    assert resolved.payload["note"] == f"Agents: {json.dumps(agent_list)} end"
    assert isinstance(resolved.payload["note"], str)
