"""Shared fixtures for Phase 7 end-to-end tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pytest

from app.src.config.settings import Settings
from app.src.models import (
    ActionTypeDefaults,
    ExecutorConfig,
    ExecutorResponse,
    PhaseData,
    Project,
)
from app.src.services.action_generator import ActionGenerator


@pytest.fixture
def isolated_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Settings:
    """Create isolated settings with temporary data/env paths for E2E tests."""

    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path / "dispatch-data"))
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")
    monkeypatch.setenv("TOKEN", "test-github-token")
    monkeypatch.setenv("AUTOPILOT_API_KEY", "test-autopilot-api-key")
    monkeypatch.setenv(
        "AUTOPILOT_API_ENDPOINT", "https://autopilot.example.com/agent/run"
    )
    monkeypatch.setattr(
        Settings,
        "_resolve_env_file_path",
        staticmethod(lambda: tmp_path / ".env/.env.local"),
    )
    return Settings()


@pytest.fixture
def sample_phase_progress() -> dict[str, Any]:
    """Return representative phase-progress data with two phases/components."""

    def _component(component_id: str, component_name: str) -> dict[str, str]:
        return {
            "componentId": component_id,
            "componentName": component_name,
            "owner": "AI Agent",
            "priority": "Must-have",
            "estimatedEffort": "2 hours",
            "status": "not-started",
        }

    return {
        "lastUpdated": "2026-03-15",
        "phases": [
            {
                "phaseId": 1,
                "phaseName": "Foundation",
                "status": "refined",
                "componentBreakdownDoc": "docs/phase-1-component-breakdown.md",
                "components": [
                    _component("1.1", "Bootstrap Project"),
                    _component("1.2", "Configure CI"),
                ],
            },
            {
                "phaseId": 2,
                "phaseName": "Service Layer",
                "status": "refined",
                "componentBreakdownDoc": "docs/phase-2-component-breakdown.md",
                "components": [
                    _component("2.1", "Models"),
                    _component("2.2", "Config Manager"),
                ],
            },
        ],
    }


@pytest.fixture
def sample_executor_config() -> ExecutorConfig:
    """Return Autopilot-like executor configuration for E2E tests."""

    return ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="https://autopilot.example.com/agent/run",
        api_key_env_key="AUTOPILOT_API_KEY",
        webhook_url="http://localhost:8000/webhook/callback",
        use_llm=False,
    )


@pytest.fixture
def sample_action_type_defaults() -> ActionTypeDefaults:
    """Return deterministic action template defaults covering all action types."""

    return ActionTypeDefaults(
        implement={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Implement {{component_name}} ({{component_id}}) for phase {{phase_id}}.",
            "role": "implement",
            "agent_paths": "{{agent_paths}}",
            "callback_url": "{{webhook_url}}",
            "model": "gpt-4o",
            "timeout_minutes": 30,
        },
        test={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Test phase {{phase_id}} ({{phase_name}}).",
            "role": "implement",
            "callback_url": "{{webhook_url}}",
        },
        review={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Review phase {{phase_id}} ({{phase_name}}).",
            "role": "review",
            "pr_number": "{{pr_number}}",
            "callback_url": "{{webhook_url}}",
        },
        merge={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Merge the PR for {{component_name}} ({{component_id}}) of Phase {{phase_id}}.",
            "role": "merge",
            "pr_number": "{{pr_number}}",
            "callback_url": "{{webhook_url}}",
        },
        document={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Document phase {{phase_id}} ({{phase_name}}).",
            "role": "implement",
            "callback_url": "{{webhook_url}}",
        },
        debug={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "",
            "role": "implement",
            "callback_url": "{{webhook_url}}",
        },
    )


@pytest.fixture
def sample_project(
    sample_phase_progress: dict[str, Any],
    sample_action_type_defaults: ActionTypeDefaults,
) -> Project:
    """Return a fully-populated project with generated actions."""

    phases = [
        PhaseData.model_validate(phase) for phase in sample_phase_progress["phases"]
    ]
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    actions = ActionGenerator.generate_actions(phases, sample_action_type_defaults)

    return Project(
        project_id="project-e2e-1",
        project_name="owner/repo",
        repository="owner/repo",
        github_token_env_key="GITHUB_TOKEN",
        phase_progress=sample_phase_progress,
        phases=phases,
        agent_files=[".claude/agents/implement.md", ".github/agents/review.md"],
        actions=actions,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_github_responses(sample_phase_progress: dict[str, Any]) -> dict[str, Any]:
    """Return URL-indexed mock GitHub responses for repository scanning."""

    return {
        "/repos/owner/repo/contents/docs/phase-progress.json": {
            "content": sample_phase_progress,
        },
        "/repos/owner/repo/contents/.claude/agents/": [
            {"type": "file", "path": ".claude/agents/implement.md"},
        ],
        "/repos/owner/repo/contents/.github/agents/": [
            {"type": "file", "path": ".github/agents/review.md"},
        ],
    }


@pytest.fixture
def mock_executor_response() -> Callable[..., ExecutorResponse]:
    """Return a factory that produces deterministic executor responses."""

    def _make(
        *,
        status_code: int = 200,
        message: str = "queued",
        run_id: str = "run-e2e-1",
    ) -> ExecutorResponse:
        return ExecutorResponse(
            status_code=status_code,
            message=message,
            run_id=run_id,
            raw_response={"status": message, "run_id": run_id},
        )

    return _make


@pytest.fixture
def mock_webhook_data() -> dict[str, dict[str, Any]]:
    """Return sample webhook payloads keyed by run identifier."""

    return {
        "run-e2e-1": {
            "run_id": "run-e2e-1",
            "status": "completed",
            "result": {"summary": "ok"},
        }
    }
