"""Optional OpenAI-backed LLM integration service module."""

from __future__ import annotations

import logging
import os

import openai
from openai import OpenAI

from app.src.exceptions import (
    LLMAuthError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
)

_LOGGER = logging.getLogger(__name__)


class LLMService:
    """Wrapper around the OpenAI SDK used for payload-generation prompts."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        """Initialise the OpenAI client from explicit args or environment.

        Args:
                api_key: Optional API key override. Falls back to OPENAI_API_KEY.
                model: Optional model override. Falls back to OPENAI_MODEL or gpt-4o.
                timeout: Request timeout in seconds.
        """

        resolved_api_key = (
            api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        )
        self._model = (
            model if model is not None else os.environ.get("OPENAI_MODEL", "gpt-4o")
        )
        self._timeout = timeout
        self._client = (
            OpenAI(api_key=resolved_api_key, timeout=timeout)
            if resolved_api_key
            else None
        )

    def is_available(self) -> bool:
        """Return whether the service is ready to call OpenAI."""

        return self._client is not None

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text using a chat completion request.

        Args:
                system_prompt: System prompt instructions for the model.
                user_prompt: User prompt content for generation.

        Returns:
                Assistant response text.

        Raises:
                LLMServiceError: If the API key is not configured or response is invalid.
                LLMAuthError: If authentication fails.
                LLMRateLimitError: If rate limited.
                LLMTimeoutError: If request times out.
        """

        if not self.is_available() or self._client is None:
            raise LLMServiceError("OpenAI API key not configured")

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                timeout=self._timeout,
            )
        except openai.AuthenticationError as exc:
            _LOGGER.warning("OpenAI authentication failed")
            raise LLMAuthError(str(exc)) from exc
        except openai.RateLimitError as exc:
            _LOGGER.warning("OpenAI rate limit exceeded")
            raise LLMRateLimitError(str(exc)) from exc
        except openai.APITimeoutError as exc:
            _LOGGER.warning(
                "OpenAI request timed out after %.1f seconds", self._timeout
            )
            raise LLMTimeoutError(str(exc)) from exc
        except openai.APIError as exc:
            _LOGGER.warning("OpenAI service error")
            raise LLMServiceError(str(exc)) from exc

        if not response.choices:
            raise LLMServiceError("OpenAI response did not include any choices")

        content = response.choices[0].message.content
        if content is None:
            raise LLMServiceError("OpenAI response did not include message content")
        return str(content)
