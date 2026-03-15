"""Unit tests for OpenAI-backed LLM service."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.src.exceptions import (
    LLMAuthError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
)
from app.src.services import llm_service as llm_module
from app.src.services.llm_service import LLMService


def _build_mock_openai_client(create_callable: Mock) -> SimpleNamespace:
    """Create a minimal mock OpenAI client shape used by LLMService.

    Args:
        create_callable: Mocked completion method.

    Returns:
        Minimal nested namespace compatible with OpenAI client access path.
    """

    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create_callable))
    )


def test_is_available_false_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service should report unavailable when no key is provided."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    service = LLMService(api_key=None)

    assert service.is_available() is False


def test_is_available_true_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service should report available when key is present."""
    create_mock = Mock()
    openai_factory = Mock(return_value=_build_mock_openai_client(create_mock))
    monkeypatch.setattr(llm_module, "OpenAI", openai_factory)

    service = LLMService(api_key="test-openai-key")

    assert service.is_available() is True
    openai_factory.assert_called_once_with(api_key="test-openai-key", timeout=10.0)


def test_generate_returns_completion_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generate should return assistant text from first completion choice."""
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content='{"agent_instructions":"Do work."}')
            )
        ]
    )
    create_mock = Mock(return_value=response)
    openai_factory = Mock(return_value=_build_mock_openai_client(create_mock))
    monkeypatch.setattr(llm_module, "OpenAI", openai_factory)

    service = LLMService(api_key="test-openai-key", model="gpt-4o-mini", timeout=3.5)

    result = service.generate("system prompt", "user prompt")

    assert result == '{"agent_instructions":"Do work."}'
    create_mock.assert_called_once_with(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"},
        ],
        timeout=3.5,
    )


def test_generate_raises_service_error_without_key() -> None:
    """Generate should fail fast when OpenAI key is not configured."""
    service = LLMService(api_key="")

    with pytest.raises(LLMServiceError, match="OpenAI API key not configured"):
        service.generate("system", "user")


def test_generate_raises_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auth errors from provider should map to LLMAuthError."""

    class FakeAuthenticationError(Exception):
        """Fake auth failure class."""

    monkeypatch.setattr(
        llm_module.openai, "AuthenticationError", FakeAuthenticationError
    )
    create_mock = Mock(side_effect=FakeAuthenticationError("401 unauthorized"))
    monkeypatch.setattr(
        llm_module,
        "OpenAI",
        Mock(return_value=_build_mock_openai_client(create_mock)),
    )

    service = LLMService(api_key="test-openai-key")

    with pytest.raises(LLMAuthError, match="401 unauthorized"):
        service.generate("system", "user")


def test_generate_raises_rate_limit_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rate limit provider failures should map to LLMRateLimitError."""

    class FakeRateLimitError(Exception):
        """Fake rate-limit class."""

    monkeypatch.setattr(llm_module.openai, "RateLimitError", FakeRateLimitError)
    create_mock = Mock(side_effect=FakeRateLimitError("429 rate limit"))
    monkeypatch.setattr(
        llm_module,
        "OpenAI",
        Mock(return_value=_build_mock_openai_client(create_mock)),
    )

    service = LLMService(api_key="test-openai-key")

    with pytest.raises(LLMRateLimitError, match="429 rate limit"):
        service.generate("system", "user")


def test_generate_raises_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeout provider failures should map to LLMTimeoutError."""

    class FakeTimeoutError(Exception):
        """Fake timeout class."""

    monkeypatch.setattr(llm_module.openai, "APITimeoutError", FakeTimeoutError)
    create_mock = Mock(side_effect=FakeTimeoutError("request timed out"))
    monkeypatch.setattr(
        llm_module,
        "OpenAI",
        Mock(return_value=_build_mock_openai_client(create_mock)),
    )

    service = LLMService(api_key="test-openai-key")

    with pytest.raises(LLMTimeoutError, match="request timed out"):
        service.generate("system", "user")


def test_generate_raises_service_error_for_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generic API provider failures should map to LLMServiceError."""

    class FakeAPIError(Exception):
        """Fake generic API error class."""

    monkeypatch.setattr(llm_module.openai, "APIError", FakeAPIError)
    create_mock = Mock(side_effect=FakeAPIError("provider failed"))
    monkeypatch.setattr(
        llm_module,
        "OpenAI",
        Mock(return_value=_build_mock_openai_client(create_mock)),
    )

    service = LLMService(api_key="test-openai-key")

    with pytest.raises(LLMServiceError, match="provider failed"):
        service.generate("system", "user")


def test_generate_warning_logs_do_not_include_api_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Warning logs should never contain the configured API key value."""

    class FakeAPIError(Exception):
        """Fake generic API error class."""

    monkeypatch.setattr(llm_module.openai, "APIError", FakeAPIError)
    create_mock = Mock(side_effect=FakeAPIError("sensitive-provider-message"))
    monkeypatch.setattr(
        llm_module,
        "OpenAI",
        Mock(return_value=_build_mock_openai_client(create_mock)),
    )

    api_key = "sk-test-secret-value"
    service = LLMService(api_key=api_key)

    with caplog.at_level("WARNING"):
        with pytest.raises(LLMServiceError):
            service.generate("system", "user")

    log_text = "\n".join(caplog.messages)
    assert api_key not in log_text
