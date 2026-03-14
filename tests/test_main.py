"""Tests for NiceGUI entrypoint routing and webhook endpoints."""

from __future__ import annotations

import importlib
import os
import sys
from types import ModuleType

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def main_module(tmp_path_factory: pytest.TempPathFactory) -> ModuleType:
    """Load app.src.main once with an isolated data directory."""
    os.environ["DISPATCH_DATA_DIR"] = str(tmp_path_factory.mktemp("dispatch-main"))
    module_name = "app.src.main"
    if module_name in sys.modules:
        return sys.modules[module_name]
    return importlib.import_module(module_name)


def test_root_route_returns_success(main_module: ModuleType) -> None:
    """Root UI route should be registered."""
    with TestClient(main_module.app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Dispatch" in response.text
    assert "Configure Executor" in response.text
    assert "Link New Project" in response.text
    assert "Load Project" in response.text


def test_all_required_routes_return_success(main_module: ModuleType) -> None:
    """All Component 4.1 screen routes should be defined."""
    with TestClient(main_module.app) as client:
        for route in (
            "/config/executor",
            "/config/action-types",
            "/config/secrets",
            "/project/link",
            "/project/load",
            "/project/example-id",
        ):
            response = client.get(route)
            assert response.status_code == 200


def test_executor_config_route_renders_form(main_module: ModuleType) -> None:
    """Executor config route should render expected form labels."""
    with TestClient(main_module.app) as client:
        response = client.get("/config/executor")

    assert response.status_code == 200
    assert "Executor Configuration" in response.text
    assert "Executor Name" in response.text
    assert "API Endpoint URL" in response.text
    assert "API Key Environment Variable" in response.text
    assert "Webhook URL (optional)" in response.text


def test_action_type_defaults_route_renders_form(main_module: ModuleType) -> None:
    """Action type defaults route should render expected labels."""
    with TestClient(main_module.app) as client:
        response = client.get("/config/action-types")

    assert response.status_code == 200
    assert "Action Type Defaults" in response.text
    assert "Available Variables" in response.text
    assert "Implement Template" in response.text


def test_secrets_route_renders_form(main_module: ModuleType) -> None:
    """Secrets route should render expected labels."""
    with TestClient(main_module.app) as client:
        response = client.get("/config/secrets")

    assert response.status_code == 200
    assert "Secrets Management" in response.text
    assert "GitHub Token" in response.text
    assert "Autopilot API Key" in response.text


def test_link_project_route_renders_form(main_module: ModuleType) -> None:
    """Link project route should render expected form labels."""
    with TestClient(main_module.app) as client:
        response = client.get("/project/link")

    assert response.status_code == 200
    assert "Link New Project" in response.text
    assert "GitHub Repository" in response.text
    assert "Scan &amp; Link" in response.text


def test_load_project_route_renders_screen(main_module: ModuleType) -> None:
    """Load project route should render expected screen content."""
    with TestClient(main_module.app) as client:
        response = client.get("/project/load")

    assert response.status_code == 200
    assert "Load Project" in response.text
    assert "Dispatch" in response.text


def test_webhook_callback_stores_payload(main_module: ModuleType) -> None:
    """Webhook callback should persist payload data to WebhookService."""
    payload = {"run_id": "run-123", "status": "completed"}

    with TestClient(main_module.app) as client:
        response = client.post("/webhook/callback", json=payload)

    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert main_module.app_state.webhook_service.retrieve("run-123") == payload


def test_webhook_poll_returns_stored_payload(main_module: ModuleType) -> None:
    """Polling endpoint should return webhook payload when present."""
    payload = {"run_id": "run-456", "status": "ok"}
    main_module.app_state.webhook_service.store("run-456", payload)

    with TestClient(main_module.app) as client:
        response = client.get("/webhook/poll/run-456")

    assert response.status_code == 200
    assert response.json() == payload


def test_webhook_poll_returns_pending_for_unknown_run(main_module: ModuleType) -> None:
    """Polling endpoint should return pending payload with 404 for unknown run."""
    with TestClient(main_module.app) as client:
        response = client.get("/webhook/poll/unknown-run-id")

    assert response.status_code == 404
    assert response.json() == {"run_id": "unknown-run-id", "status": "pending"}
