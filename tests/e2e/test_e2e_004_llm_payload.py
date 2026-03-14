"""E2E-004: Validate LLM payload generation success and fallback behaviour."""

from __future__ import annotations

import pytest

from app.src.exceptions import LLMTimeoutError
from app.src.services.llm_payload_generator import LLMPayloadGenerator
from app.src.services.llm_service import LLMService
from app.src.services.payload_resolver import PayloadResolver


def test_e2e_004_llm_payload_success_and_fallback(
    monkeypatch, sample_project, sample_executor_config
) -> None:
    """Validate LLM-assisted generation and fallback to deterministic interpolation."""

    implement_action = next(
        action
        for action in sample_project.actions
        if getattr(action.action_type, "value", str(action.action_type)) == "implement"
    )

    llm_enabled_config = sample_executor_config.model_copy(update={"use_llm": True})
    llm_service = LLMService(api_key="test-openai-key", model="gpt-4o")

    monkeypatch.setattr(
        llm_service,
        "generate",
        lambda system_prompt, user_prompt: (
            '{"agent_instructions": "Implement component with strict acceptance criteria and tests."}'
        ),
    )

    generator = LLMPayloadGenerator(
        llm_service=llm_service, payload_resolver=PayloadResolver()
    )
    llm_result = generator.generate_payload(
        action=implement_action,
        project=sample_project,
        executor_config=llm_enabled_config,
    )

    assert llm_result.llm_used is True
    assert "strict acceptance criteria" in str(llm_result.payload["agent_instructions"])
    assert llm_result.payload["repository"] == "owner/repo"
    assert llm_result.payload["branch"] == "main"
    assert llm_result.payload["model"] == "gpt-4o"
    assert (
        llm_result.payload["callback_url"] == "http://localhost:8000/webhook/callback"
    )

    def _raise_timeout(system_prompt: str, user_prompt: str) -> str:
        del system_prompt, user_prompt
        raise LLMTimeoutError("timed out")

    monkeypatch.setattr(llm_service, "generate", _raise_timeout)
    fallback_result = generator.generate_payload(
        action=implement_action,
        project=sample_project,
        executor_config=llm_enabled_config,
    )

    assert fallback_result.llm_used is False
    assert fallback_result.fallback_reason == "timed out"
    assert "{{" not in str(fallback_result.payload["agent_instructions"])

    llm_disabled_config = sample_executor_config.model_copy(update={"use_llm": False})
    disabled_result = generator.generate_payload(
        action=implement_action,
        project=sample_project,
        executor_config=llm_disabled_config,
    )
    assert disabled_result.llm_used is False
    assert (
        disabled_result.fallback_reason == "LLM generation disabled in executor config"
    )

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    no_key_service = LLMService(api_key=None)
    assert no_key_service.is_available() is False
    no_key_generator = LLMPayloadGenerator(
        llm_service=no_key_service,
        payload_resolver=PayloadResolver(),
    )
    no_key_result = no_key_generator.generate_payload(
        action=implement_action,
        project=sample_project,
        executor_config=llm_enabled_config,
    )
    assert no_key_result.llm_used is False
    assert no_key_result.fallback_reason == "OpenAI API key not configured"


@pytest.mark.parametrize("use_llm", [True, False])
def test_e2e_004_payload_generation_always_returns_dispatch_ready_payload(
    monkeypatch,
    sample_project,
    sample_executor_config,
    use_llm: bool,
) -> None:
    """Payload generation should always return a usable payload regardless of LLM mode."""

    implement_action = next(
        action
        for action in sample_project.actions
        if getattr(action.action_type, "value", str(action.action_type)) == "implement"
    )
    config = sample_executor_config.model_copy(update={"use_llm": use_llm})

    llm_service = LLMService(api_key="test-openai-key", model="gpt-4o")
    monkeypatch.setattr(
        llm_service,
        "generate",
        lambda *_args: '{"agent_instructions": "Generated instructions."}',
    )
    generator = LLMPayloadGenerator(
        llm_service=llm_service, payload_resolver=PayloadResolver()
    )

    result = generator.generate_payload(implement_action, sample_project, config)

    assert "repository" in result.payload
    assert "branch" in result.payload
    assert "agent_instructions" in result.payload
