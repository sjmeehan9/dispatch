"""E2E-005: Human-confirmed live Autopilot executor integration test."""

from __future__ import annotations

import os
import time

import httpx
import pytest

from app.src.config.settings import Settings
from app.src.models import ExecutorConfig
from app.src.services.executor import AutopilotExecutor


@pytest.mark.requires_autopilot
def test_e2e_005_live_autopilot_executor_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    confirm_autopilot_gateway: dict[str, str],
) -> None:
    """Dispatch a real payload to live Autopilot and optionally poll webhook status."""

    monkeypatch.setenv("AUTOPILOT_API_KEY", confirm_autopilot_gateway["api_key"])
    monkeypatch.setenv(
        "AUTOPILOT_API_ENDPOINT", confirm_autopilot_gateway["api_endpoint"]
    )
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path / "dispatch-data-live"))
    monkeypatch.setattr(
        Settings,
        "_resolve_env_file_path",
        staticmethod(lambda: tmp_path / ".env/.env.local"),
    )

    settings = Settings()
    executor = AutopilotExecutor(settings)
    config = ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint=confirm_autopilot_gateway["api_endpoint"],
        api_key_env_key="AUTOPILOT_API_KEY",
        webhook_url=None,
        use_llm=False,
    )

    payload = {
        "repository": "owner/repo",
        "branch": "main",
        "agent_instructions": "Run a minimal verification task and report status.",
        "role": "implement",
        "model": "gpt-4o",
        "timeout_minutes": 10,
    }

    response = executor.dispatch(payload=payload, config=config)
    assert response.status_code == 200
    assert response.run_id is not None and response.run_id.strip()

    webhook_poll_base = os.environ.get("DISPATCH_WEBHOOK_POLL_BASE_URL", "").strip()
    if not webhook_poll_base:
        return

    deadline = time.monotonic() + 120
    webhook_data: dict[str, object] | None = None

    with httpx.Client(timeout=10.0) as client:
        while time.monotonic() < deadline:
            poll_response = client.get(
                f"{webhook_poll_base.rstrip('/')}/{response.run_id}"
            )
            if poll_response.status_code == 200:
                data = poll_response.json()
                if (
                    isinstance(data, dict)
                    and str(data.get("run_id", "")) == response.run_id
                ):
                    webhook_data = data
                    break
            time.sleep(5)

    assert webhook_data is not None, "Webhook data not received within 120 seconds"
