"""Executor protocol and Autopilot-backed implementation."""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

import httpx

from app.src.config.settings import Settings
from app.src.models import ExecutorConfig, ExecutorResponse

_LOGGER = logging.getLogger(__name__)


class ExecutorError(Exception):
    """Base exception for executor dispatch failures."""


class ExecutorConnectionError(ExecutorError):
    """Raised when the executor endpoint cannot be reached."""

    def __init__(self, endpoint: str) -> None:
        """Initialise exception with the failed endpoint URL."""
        self.endpoint = endpoint
        super().__init__(f"Cannot reach executor at {endpoint}")


class ExecutorAuthError(ExecutorError):
    """Raised when executor authentication fails."""


class ExecutorDispatchError(ExecutorError):
    """Raised when the executor rejects or fails to process a dispatch."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialise exception with executor HTTP status and message."""
        self.status_code = status_code
        self.message = message
        super().__init__(f"Executor error ({status_code}): {message}")


@runtime_checkable
class Executor(Protocol):
    """Protocol that all executor implementations must satisfy."""

    def dispatch(
        self, payload: dict[str, Any], config: ExecutorConfig
    ) -> ExecutorResponse:
        """Dispatch a payload to an executor endpoint."""


class AutopilotExecutor:
    """Dispatch actions to the configured Autopilot executor endpoint."""

    _REQUEST_TIMEOUT_SECONDS = 30.0

    def __init__(self, settings: Settings) -> None:
        """Initialise the executor with runtime settings access."""
        self._settings = settings

    def dispatch(
        self, payload: dict[str, Any], config: ExecutorConfig
    ) -> ExecutorResponse:
        """Send the payload to Autopilot and normalize the response."""
        api_key = self._settings.get_secret(config.api_key_env_key)
        if not api_key:
            message = (
                "API key not configured. "
                f"Set {config.api_key_env_key} in your environment."
            )
            raise ExecutorDispatchError(status_code=0, message=message)

        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        endpoint = str(config.api_endpoint)
        _LOGGER.info("Dispatching to %s", endpoint)

        try:
            with httpx.Client(timeout=self._REQUEST_TIMEOUT_SECONDS) as client:
                response = client.post(endpoint, json=payload, headers=headers)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            _LOGGER.warning("Executor connection failure for %s: %s", endpoint, exc)
            raise ExecutorConnectionError(endpoint) from exc
        except httpx.TimeoutException as exc:
            _LOGGER.warning(
                "Executor request timed out after %s seconds for %s",
                int(self._REQUEST_TIMEOUT_SECONDS),
                endpoint,
            )
            raise ExecutorConnectionError(endpoint) from exc
        except httpx.HTTPError as exc:
            _LOGGER.warning("Executor HTTP error for %s: %s", endpoint, exc)
            raise ExecutorDispatchError(status_code=0, message=str(exc)) from exc

        _LOGGER.info("Executor response: %s", response.status_code)

        if response.is_success:
            response_json = self._safe_json_dict(response)
            message = self._extract_success_message(response_json, response.text)
            run_id = self._extract_run_id(response_json)
            return ExecutorResponse(
                status_code=response.status_code,
                message=message,
                run_id=run_id,
                raw_response=response_json,
            )

        if response.status_code in (401, 403):
            raise ExecutorAuthError(
                "Executor API key rejected. Check your API key in Manage Secrets."
            )

        raise ExecutorDispatchError(
            status_code=response.status_code,
            message=self._extract_error_message(response),
        )

    @staticmethod
    def _safe_json_dict(response: httpx.Response) -> dict[str, object] | None:
        """Parse a JSON response body when it is a JSON object payload."""
        try:
            parsed = response.json()
        except ValueError:
            return None
        if isinstance(parsed, dict):
            return parsed
        return None

    @staticmethod
    def _extract_success_message(
        response_json: dict[str, object] | None, fallback_text: str
    ) -> str:
        """Extract a user-facing message from a successful response."""
        if response_json is None:
            return fallback_text
        message = response_json.get("status") or response_json.get("message")
        return str(message) if message is not None else fallback_text

    @staticmethod
    def _extract_run_id(response_json: dict[str, object] | None) -> str | None:
        """Extract run identifier from the successful response body."""
        if response_json is None:
            return None
        run_id = response_json.get("run_id")
        return str(run_id) if run_id is not None else None

    @classmethod
    def _extract_error_message(cls, response: httpx.Response) -> str:
        """Extract meaningful error text from a failed response."""
        response_json = cls._safe_json_dict(response)
        if response_json is None:
            return response.text

        for field in ("message", "error", "detail", "status"):
            value = response_json.get(field)
            if value:
                return str(value)
        return response.text
