"""Unit and integration tests for LLM payload generation logic."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.src.exceptions import LLMServiceError, LLMTimeoutError
from app.src.models import Action, ExecutorConfig, Project
from app.src.models.project import ActionStatus, ActionType
from app.src.services.llm_payload_generator import LLMPayloadGenerator
from app.src.services.llm_service import LLMService
from app.src.services.payload_resolver import PayloadResolver


class _StubLLMService:
    """Small configurable LLM service stub used by generator tests."""

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
        """Return whether the fake service is available."""

        return self._available

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return configured response or raise configured error."""

        self.calls.append((system_prompt, user_prompt))
        if self._error is not None:
            raise self._error
        if self._response is None:
            raise AssertionError("Test setup error: response must be provided")
        return self._response


def _sample_project(*, component_notes: str = "") -> Project:
    component = {
        "componentId": "6.2",
        "componentName": "LLM Payload Generation Logic",
        "owner": "AI Agent",
        "priority": "Must-have",
        "estimatedEffort": "3 hours",
        "status": "not-started",
    }
    if component_notes:
        component["details"] = component_notes

    return Project.model_validate(
        {
            "project_id": "project-6",
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
                        "description": "Phase-level context.",
                        "components": [component],
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
                            "componentId": "6.2",
                            "componentName": "LLM Payload Generation Logic",
                            "owner": "AI Agent",
                            "priority": "Must-have",
                            "estimatedEffort": "3 hours",
                            "status": "not-started",
                        },
                        {
                            "componentId": "6.3",
                            "componentName": "UI Integration",
                            "owner": "AI Agent",
                            "priority": "Must-have",
                            "estimatedEffort": "2 hours",
                            "status": "not-started",
                        },
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


def _sample_action() -> Action:
    return Action(
        action_id="action-6-2",
        phase_id=6,
        component_id="6.2",
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


def _sample_executor_config(*, use_llm: bool) -> ExecutorConfig:
    return ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="https://autopilot.example.com/agent/run",
        api_key_env_key="AUTOPILOT_API_KEY",
        webhook_url="https://dispatch.example.com/webhook/callback",
        use_llm=use_llm,
    )


def test_generate_payload_falls_back_when_llm_unavailable() -> None:
    """Return deterministic interpolation when LLM service is unavailable."""

    generator = LLMPayloadGenerator(_StubLLMService(available=False), PayloadResolver())

    result = generator.generate_payload(
        action=_sample_action(),
        project=_sample_project(),
        executor_config=_sample_executor_config(use_llm=True),
    )

    assert result.llm_used is False
    assert result.fallback_reason == "OpenAI API key not configured"
    assert result.payload["repository"] == "owner/dispatch"
    assert "LLM Payload Generation Logic" in str(result.payload["agent_instructions"])


def test_generate_payload_falls_back_when_llm_disabled_in_executor_config() -> None:
    """Return deterministic interpolation when executor LLM toggle is disabled."""

    generator = LLMPayloadGenerator(
        _StubLLMService(available=True, response='{"agent_instructions": "unused"}'),
        PayloadResolver(),
    )

    result = generator.generate_payload(
        action=_sample_action(),
        project=_sample_project(),
        executor_config=_sample_executor_config(use_llm=False),
    )

    assert result.llm_used is False
    assert result.fallback_reason == "LLM generation disabled in executor config"


def test_generate_payload_calls_llm_and_merges_instructions() -> None:
    """Use LLM output for agent_instructions while preserving structural fields."""

    generator = LLMPayloadGenerator(
        _StubLLMService(
            available=True,
            response='{"agent_instructions": "Use docs/phase-6-component-breakdown.md and implement thoroughly."}',
        ),
        PayloadResolver(),
    )

    result = generator.generate_payload(
        action=_sample_action(),
        project=_sample_project(),
        executor_config=_sample_executor_config(use_llm=True),
    )

    assert result.llm_used is True
    assert result.fallback_reason is None
    assert result.payload["repository"] == "owner/dispatch"
    assert result.payload["branch"] == "main"
    assert result.payload["timeout_minutes"] == 30
    assert result.payload["agent_instructions"].startswith(
        "Use docs/phase-6-component-breakdown.md"
    )


def test_generate_payload_falls_back_on_timeout() -> None:
    """Fall back to deterministic interpolation when LLM request times out."""

    generator = LLMPayloadGenerator(
        _StubLLMService(available=True, error=LLMTimeoutError("timed out")),
        PayloadResolver(),
    )

    result = generator.generate_payload(
        action=_sample_action(),
        project=_sample_project(),
        executor_config=_sample_executor_config(use_llm=True),
    )

    assert result.llm_used is False
    assert result.fallback_reason == "timed out"
    assert "Implement LLM Payload Generation Logic" in str(
        result.payload["agent_instructions"]
    )


def test_generate_payload_falls_back_on_service_error() -> None:
    """Fall back to deterministic interpolation on generic LLM service errors."""

    generator = LLMPayloadGenerator(
        _StubLLMService(
            available=True,
            error=LLMServiceError("provider temporarily unavailable"),
        ),
        PayloadResolver(),
    )

    result = generator.generate_payload(
        action=_sample_action(),
        project=_sample_project(),
        executor_config=_sample_executor_config(use_llm=True),
    )

    assert result.llm_used is False
    assert result.fallback_reason == "provider temporarily unavailable"


def test_assemble_context_for_implement_includes_phase_component_and_agents() -> None:
    """Implement-action context should include phase, component, and agent paths."""

    generator = LLMPayloadGenerator(
        _StubLLMService(available=False),
        PayloadResolver(),
    )

    context = generator._assemble_context(_sample_action(), _sample_project())

    assert "Phase Name: LLM-Assisted Payload Generation" in context
    assert "Component Name: LLM Payload Generation Logic" in context
    assert ".claude/agents/implement.agent.md" in context
    assert ".github/agents/review.agent.md" in context


def test_assemble_context_truncates_component_breakdown_text() -> None:
    """Long component breakdown text should be truncated to context character limit."""

    long_text = "x" * 4500
    generator = LLMPayloadGenerator(
        _StubLLMService(available=False),
        PayloadResolver(),
        context_char_limit=4000,
    )

    context = generator._assemble_context(
        _sample_action(),
        _sample_project(component_notes=long_text),
    )

    assert "Component Breakdown Context:" in context
    breakdown_text = context.split("Component Breakdown Context:\n", maxsplit=1)[1]
    breakdown_text = breakdown_text.split("\nAgent Files:", maxsplit=1)[0]
    assert len(breakdown_text) == 4000
    assert "x" * 3900 in breakdown_text


def test_build_system_prompt_mentions_agent_instructions() -> None:
    """System prompt should instruct JSON output containing agent_instructions key."""

    prompt = LLMPayloadGenerator._build_system_prompt()

    assert "agent_instructions" in prompt
    assert "valid JSON object" in prompt


def test_build_user_prompt_includes_action_type_template_and_context() -> None:
    """User prompt should include action type, template text, and assembled context."""

    generator = LLMPayloadGenerator(_StubLLMService(available=False), PayloadResolver())

    prompt = generator._build_user_prompt(
        action=_sample_action(),
        context="Phase context",
        template={"agent_instructions": "Template {{component_name}}"},
    )

    assert "Action type: implement" in prompt
    assert "Template {{component_name}}" in prompt
    assert "Phase context" in prompt


def test_parse_response_accepts_valid_json() -> None:
    """Parser should return dictionary for clean JSON response."""

    parsed = LLMPayloadGenerator._parse_response(
        '{"agent_instructions": "Do the thing."}'
    )

    assert parsed == {"agent_instructions": "Do the thing."}


def test_parse_response_accepts_json_inside_code_fences() -> None:
    """Parser should strip markdown code fences before JSON decode."""

    parsed = LLMPayloadGenerator._parse_response(
        '```json\n{"agent_instructions": "Do the thing."}\n```'
    )

    assert parsed == {"agent_instructions": "Do the thing."}


def test_parse_response_raises_for_invalid_json() -> None:
    """Parser should fail for non-JSON response text."""

    with pytest.raises(ValueError, match="not valid JSON"):
        LLMPayloadGenerator._parse_response("not-json")


def test_parse_response_raises_when_key_missing() -> None:
    """Parser should fail when agent_instructions key is absent."""

    with pytest.raises(ValueError, match="agent_instructions"):
        LLMPayloadGenerator._parse_response('{"other": "value"}')


def test_merge_payload_preserves_structural_fields_and_overrides_instructions() -> None:
    """Merge should keep resolved fields and replace agent_instructions only."""

    merged = LLMPayloadGenerator._merge_payload(
        template={"agent_instructions": "template"},
        llm_fields={"agent_instructions": "Generated instruction"},
        resolved_fields={
            "repository": "owner/repo",
            "branch": "main",
            "model": "gpt-4o",
            "agent_instructions": "template instruction",
        },
    )

    assert merged["repository"] == "owner/repo"
    assert merged["branch"] == "main"
    assert merged["model"] == "gpt-4o"
    assert merged["agent_instructions"] == "Generated instruction"


def test_integration_success_flow_merges_llm_and_resolved_fields() -> None:
    """Integration-style flow should produce llm_used=True with merged payload."""

    generator = LLMPayloadGenerator(
        _StubLLMService(
            available=True,
            response='{"agent_instructions": "Implement component 6.2 with robust validation."}',
        ),
        PayloadResolver(),
    )

    result = generator.generate_payload(
        action=_sample_action(),
        project=_sample_project(),
        executor_config=_sample_executor_config(use_llm=True),
    )

    assert result.llm_used is True
    assert result.fallback_reason is None
    assert result.payload["repository"] == "owner/dispatch"
    assert result.payload["agent_instructions"] == (
        "Implement component 6.2 with robust validation."
    )


def test_integration_parse_failure_falls_back_to_standard_payload() -> None:
    """Invalid LLM response should fall back to standard interpolation result."""

    generator = LLMPayloadGenerator(
        _StubLLMService(available=True, response="I cannot return JSON"),
        PayloadResolver(),
    )

    result = generator.generate_payload(
        action=_sample_action(),
        project=_sample_project(),
        executor_config=_sample_executor_config(use_llm=True),
    )

    assert result.llm_used is False
    assert result.fallback_reason is not None
    assert "Implement LLM Payload Generation Logic" in str(
        result.payload["agent_instructions"]
    )
