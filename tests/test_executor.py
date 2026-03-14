"""Unit tests for the executor protocol and Autopilot implementation."""

from __future__ import annotations

from unittest.mock import Mock, patch

import httpx

from app.src.config.settings import Settings
from app.src.models import ExecutorConfig
from app.src.services.executor import AutopilotExecutor, Executor


def _sample_config() -> ExecutorConfig:
    return ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="http://localhost:8000/agent/run",
        api_key_env_key="AUTOPILOT_API_KEY",
    )


def _executor_with_api_key(api_key: str = "test-key") -> AutopilotExecutor:
    settings = Mock(spec=Settings)
    settings.get_secret.return_value = api_key
    return AutopilotExecutor(settings)


def test_dispatch_posts_expected_headers_payload_and_timeout() -> None:
    executor = _executor_with_api_key()
    config = _sample_config()
    payload = {"role": "implement", "repository": "sjmeehan9/dispatch"}

    response = Mock()
    response.status_code = 200
    response.is_success = True
    response.text = "ok"
    response.json.return_value = {"status": "queued", "run_id": "run-123"}

    client = Mock()
    client.post.return_value = response
    client_context = Mock()
    client_context.__enter__ = Mock(return_value=client)
    client_context.__exit__ = Mock(return_value=False)

    with patch(
        "app.src.services.executor.httpx.Client",
        return_value=client_context,
    ) as client_factory:
        result = executor.dispatch(payload, config)

    client_factory.assert_called_once_with(timeout=30.0)
    client.post.assert_called_once_with(
        str(config.api_endpoint),
        json=payload,
        headers={
            "X-API-Key": "test-key",
            "Content-Type": "application/json",
        },
    )
    assert result.status_code == 200
    assert result.message == "queued"
    assert result.run_id == "run-123"


def test_dispatch_parses_success_response() -> None:
    executor = _executor_with_api_key()
    config = _sample_config()
    payload = {"role": "test"}

    response = Mock()
    response.status_code = 200
    response.is_success = True
    response.text = "ok"
    response.json.return_value = {
        "status": "accepted",
        "run_id": "run-abc",
        "extra": "value",
    }

    client = Mock()
    client.post.return_value = response
    client_context = Mock()
    client_context.__enter__ = Mock(return_value=client)
    client_context.__exit__ = Mock(return_value=False)

    with patch(
        "app.src.services.executor.httpx.Client",
        return_value=client_context,
    ):
        result = executor.dispatch(payload, config)

    assert result.status_code == 200
    assert result.message == "accepted"
    assert result.run_id == "run-abc"
    assert result.raw_response == {
        "status": "accepted",
        "run_id": "run-abc",
        "extra": "value",
    }


def test_dispatch_returns_error_response_for_unauthorized_status() -> None:
    executor = _executor_with_api_key()
    config = _sample_config()

    response = Mock()
    response.status_code = 401
    response.is_success = False
    response.text = "Unauthorized"
    response.json.return_value = {"message": "Unauthorized"}

    client = Mock()
    client.post.return_value = response
    client_context = Mock()
    client_context.__enter__ = Mock(return_value=client)
    client_context.__exit__ = Mock(return_value=False)

    with patch(
        "app.src.services.executor.httpx.Client",
        return_value=client_context,
    ):
        result = executor.dispatch({"role": "implement"}, config)

    assert result.status_code == 401
    assert result.message == "Unauthorized"
    assert result.run_id is None
    assert result.raw_response is None


def test_dispatch_returns_error_response_for_connection_failure() -> None:
    executor = _executor_with_api_key()
    config = _sample_config()

    client = Mock()
    client.post.side_effect = httpx.ConnectError("cannot connect")
    client_context = Mock()
    client_context.__enter__ = Mock(return_value=client)
    client_context.__exit__ = Mock(return_value=False)

    with patch(
        "app.src.services.executor.httpx.Client",
        return_value=client_context,
    ):
        result = executor.dispatch({"role": "implement"}, config)

    assert result.status_code == 0
    assert result.message == f"Connection failed: could not reach {config.api_endpoint}"
    assert result.run_id is None


def test_dispatch_returns_error_response_for_timeout() -> None:
    executor = _executor_with_api_key()
    config = _sample_config()

    client = Mock()
    client.post.side_effect = httpx.TimeoutException("timed out")
    client_context = Mock()
    client_context.__enter__ = Mock(return_value=client)
    client_context.__exit__ = Mock(return_value=False)

    with patch(
        "app.src.services.executor.httpx.Client",
        return_value=client_context,
    ):
        result = executor.dispatch({"role": "implement"}, config)

    assert result.status_code == 0
    assert result.message == "Request timed out after 30 seconds"
    assert result.run_id is None


def test_dispatch_returns_configuration_error_when_api_key_missing() -> None:
    settings = Mock(spec=Settings)
    settings.get_secret.return_value = None
    executor = AutopilotExecutor(settings)

    with patch("app.src.services.executor.httpx.Client") as client_factory:
        result = executor.dispatch({"role": "implement"}, _sample_config())

    assert result.status_code == 0
    assert result.message == (
        "API key not configured. Set AUTOPILOT_API_KEY in your environment."
    )
    assert result.run_id is None
    client_factory.assert_not_called()


def test_autopilot_executor_satisfies_executor_protocol() -> None:
    executor = _executor_with_api_key()
    assert isinstance(executor, Executor)
