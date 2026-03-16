"""Integration tests for app startup wiring and route registration."""

from __future__ import annotations

import importlib
import os
import sys
from types import ModuleType

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def startup_module(tmp_path_factory: pytest.TempPathFactory) -> ModuleType:
    """Import the main app module with an isolated data directory.

    Avoids importlib.reload to prevent duplicate middleware registration
    and storage secret errors in NiceGUI.
    """
    os.environ["DISPATCH_DATA_DIR"] = str(
        tmp_path_factory.mktemp("dispatch-startup-tests")
    )
    os.environ["DISPATCH_ACCESS_TOKEN"] = ""
    module_name = "app.src.main"
    if module_name in sys.modules:
        return sys.modules[module_name]
    return importlib.import_module(module_name)


def test_main_module_imports_and_initialises_app_state(
    startup_module: ModuleType,
) -> None:
    """Main module import should create app and shared state without errors."""
    assert startup_module.app is not None
    assert startup_module.app_state is not None
    assert startup_module.app_state.settings is not None


def test_required_ui_routes_are_registered(startup_module: ModuleType) -> None:
    """All required UI routes should be present in the FastAPI router."""
    paths = {route.path for route in startup_module.app.routes}

    assert "/" in paths
    assert "/config/executor" in paths
    assert "/config/action-types" in paths
    assert "/config/secrets" in paths
    assert "/project/link" in paths
    assert "/project/load" in paths
    assert "/project/{project_id}" in paths


def test_webhook_routes_are_registered(startup_module: ModuleType) -> None:
    """Webhook callback and polling endpoints should be registered."""
    paths = {route.path for route in startup_module.app.routes}
    assert "/webhook/callback" in paths
    assert "/webhook/poll/{run_id}" in paths


def test_webhook_endpoints_round_trip_payload(startup_module: ModuleType) -> None:
    """Webhook callback payloads should be stored and retrievable by run ID."""
    payload = {
        "run_id": "startup-run-1",
        "status": "success",
        "result": {"message": "ok"},
    }

    with TestClient(startup_module.app) as client:
        callback_response = client.post("/webhook/callback", json=payload)
        poll_response = client.get("/webhook/poll/startup-run-1")

    assert callback_response.status_code == 200
    assert callback_response.json() == {"received": True}
    assert poll_response.status_code == 200
    assert poll_response.json() == payload


def test_webhook_poll_returns_pending_for_unknown_run(
    startup_module: ModuleType,
) -> None:
    """Polling for an unknown run should return pending with a 404 status."""
    with TestClient(startup_module.app) as client:
        response = client.get("/webhook/poll/startup-unknown")

    assert response.status_code == 404
    assert response.json() == {"run_id": "startup-unknown", "status": "pending"}
