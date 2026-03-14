"""Integration tests for end-to-end LLM payload generation flow."""

from __future__ import annotations

import pytest

from app.src.exceptions import LLMServiceError
from app.src.models import Action, ExecutorConfig, Project
from app.src.models.project import ActionStatus, ActionType
from app.src.services.llm_payload_generator import LLMPayloadGenerator
from app.src.services.payload_resolver import PayloadResolver


class _IntegrationLLMService:
    """Configurable LLM service double for integration-flow tests."""

    def __init__(
        self,
        *,
        available: bool,
        response: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self._available = available
        self._response = response
        self._error = error
        self.calls: list[tuple[str, str]] = []

    def is_available(self) -> bool:
        """Return configured availability state."""

        return self._available

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return configured response or raise configured error."""

        self.calls.append((system_prompt, user_prompt))
        if self._error is not None:
            raise self._error
        if self._response is None:
            raise AssertionError("Integration test setup requires an LLM response")
        return self._response


def _integration_project() -> Project:
    return Project.model_validate(
        {
            "project_id": "project-phase-6",
            "project_name": "dispatch",
            "repository": "owner/dispatch",
            "github_token_env_key": "GITHUB_TOKEN",
            "phase_progress": {
                "phases": [
                    {
                        "phaseId": 6,
                        "phaseName": "LLM-Assisted Payload Generation",
                        "status": "refined",
                        "componentBreakdownDoc": "docs/phase-6-component-breakdown.md",
                        "description": "Validate LLM-assisted payload generation.",
                        "components": [
                            {
                                "componentId": "6.4",
                                "componentName": "Testing & Phase Validation",
                                "owner": "AI Agent",
                                "priority": "Must-have",
                                "estimatedEffort": "2 hours",
                                "status": "not-started",
                                "details": "Cover success and fallback flows for payload generation.",
                            }
                        ],
                    }
                ]
            },
            "phases": [
                {
                    "phaseId": 6,
                    "phaseName": "LLM-Assisted Payload Generation",
                    "status": "refined",
                    "componentBreakdownDoc": "docs/phase-6-component-breakdown.md",
                    "components": [
                        {
                            "componentId": "6.4",
                            "componentName": "Testing & Phase Validation",
                            "owner": "AI Agent",
                            "priority": "Must-have",
                            "estimatedEffort": "2 hours",
                            "status": "not-started",
                        }
                    ],
                }
            ],
            "agent_files": [
                ".claude/agents/implement.agent.md",
                ".github/agents/review.agent.md",
            ],
            "actions": [],
            "created_at": "2026-03-15T00:00:00Z",
            "updated_at": "2026-03-15T00:00:00Z",
        }
    )


def _integration_action() -> Action:
    return Action(
        action_id="action-6-4",
        phase_id=6,
        component_id="6.4",
        action_type=ActionType.IMPLEMENT,
        payload={
            "repository": "{{repository}}",
            "branch": "{{branch}}",
            "agent_instructions": "Implement {{component_name}} for phase {{phase_id}}.",
            "callback_url": "{{webhook_url}}",
            "model": "gpt-4o",
            "role": "implement",
            "timeout_minutes": 30,
        },
        status=ActionStatus.NOT_STARTED,
    )


def _integration_executor_config(*, use_llm: bool) -> ExecutorConfig:
    return ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="https://autopilot.example.com/agent/run",
        api_key_env_key="AUTOPILOT_API_KEY",
        webhook_url="https://dispatch.example.com/webhook/callback",
        use_llm=use_llm,
    )


def test_llm_generation_integration_success_flow() -> None:
    """LLM success should return merged payload with llm_used=True."""

    llm_service = _IntegrationLLMService(
        available=True,
        response='{"agent_instructions": "Implement component 6.4 and run full validation checks."}',
    )
    generator = LLMPayloadGenerator(llm_service, PayloadResolver())

    result = generator.generate_payload(
        action=_integration_action(),
        project=_integration_project(),
        executor_config=_integration_executor_config(use_llm=True),
    )

    assert result.llm_used is True
    assert result.fallback_reason is None
    assert result.payload["repository"] == "owner/dispatch"
    assert result.payload["branch"] == "main"
    assert result.payload["timeout_minutes"] == 30
    assert result.payload["agent_instructions"] == (
        "Implement component 6.4 and run full validation checks."
    )
    assert len(llm_service.calls) == 1
    system_prompt, user_prompt = llm_service.calls[0]
    assert "agent_instructions" in system_prompt
    assert "Action type: implement" in user_prompt
    assert "Component Name: Testing & Phase Validation" in user_prompt


def test_llm_generation_integration_fallback_flow() -> None:
    """LLM error should trigger deterministic interpolation fallback."""

    llm_service = _IntegrationLLMService(
        available=True,
        error=LLMServiceError("provider unavailable"),
    )
    generator = LLMPayloadGenerator(llm_service, PayloadResolver())

    result = generator.generate_payload(
        action=_integration_action(),
        project=_integration_project(),
        executor_config=_integration_executor_config(use_llm=True),
    )

    assert result.llm_used is False
    assert result.fallback_reason == "provider unavailable"
    assert result.payload["repository"] == "owner/dispatch"
    assert result.payload["branch"] == "main"
    assert result.payload["agent_instructions"] == (
        "Implement Testing & Phase Validation for phase 6."
    )
    assert len(llm_service.calls) == 1
