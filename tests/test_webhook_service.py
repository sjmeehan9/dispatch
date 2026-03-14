"""Unit tests for webhook service."""

from __future__ import annotations

from unittest.mock import patch

from app.src.services.webhook_service import WebhookService


def test_store_and_retrieve_round_trip() -> None:
    service = WebhookService()
    payload = {"status": "completed", "message": "done"}

    service.store("run-123", payload)

    assert service.retrieve("run-123") == payload


def test_retrieve_returns_none_for_unknown_run_id() -> None:
    service = WebhookService()

    assert service.retrieve("missing-run") is None


def test_has_result_reflects_store_state() -> None:
    service = WebhookService()

    assert service.has_result("run-123") is False
    service.store("run-123", {"ok": True})
    assert service.has_result("run-123") is True


def test_clear_removes_entry() -> None:
    service = WebhookService()
    service.store("run-123", {"ok": True})

    service.clear("run-123")

    assert service.has_result("run-123") is False
    assert service.retrieve("run-123") is None


def test_clear_stale_removes_old_entries_and_keeps_recent() -> None:
    service = WebhookService()
    with patch("app.src.services.webhook_service.time.time", return_value=1000.0):
        service.store("old-run", {"status": "old"})
    with patch("app.src.services.webhook_service.time.time", return_value=1900.0):
        service.store("fresh-run", {"status": "fresh"})
    with patch("app.src.services.webhook_service.time.time", return_value=2000.0):
        cleared_count = service.clear_stale(max_age_seconds=500)

    assert cleared_count == 1
    assert service.retrieve("old-run") is None
    assert service.retrieve("fresh-run") == {"status": "fresh"}
