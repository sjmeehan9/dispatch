"""Webhook receipt and retrieval service module."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

_LOGGER = logging.getLogger(__name__)


class WebhookService:
    """Store webhook callback payloads in memory by run identifier."""

    def __init__(self) -> None:
        """Initialise in-memory webhook storage with thread safety."""
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def store(self, run_id: str, data: dict[str, Any]) -> None:
        """Store webhook callback payload data for a run.

        Args:
            run_id: Executor run identifier.
            data: Raw webhook payload associated with the run.
        """
        with self._lock:
            self._store[run_id] = (time.time(), data)
        _LOGGER.info("Webhook data received for run_id %s", run_id)

    def retrieve(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve webhook callback payload data for a run.

        Args:
            run_id: Executor run identifier.

        Returns:
            Stored webhook payload if present, otherwise ``None``.
        """
        with self._lock:
            record = self._store.get(run_id)
            if record is None:
                return None
            return record[1]

    def has_result(self, run_id: str) -> bool:
        """Check whether webhook payload data exists for a run."""
        with self._lock:
            return run_id in self._store

    def clear(self, run_id: str) -> None:
        """Remove webhook payload data for a run if it exists."""
        with self._lock:
            self._store.pop(run_id, None)

    def clear_stale(self, max_age_seconds: int = 3600) -> int:
        """Clear stale webhook entries older than ``max_age_seconds``.

        Args:
            max_age_seconds: Maximum age in seconds before an entry is stale.

        Returns:
            Count of removed stale entries.
        """
        now = time.time()
        with self._lock:
            stale_run_ids = [
                run_id
                for run_id, (timestamp, _data) in self._store.items()
                if now - timestamp > max_age_seconds
            ]
            for run_id in stale_run_ids:
                self._store.pop(run_id, None)
            cleared_count = len(stale_run_ids)

        _LOGGER.info("Cleared %d stale webhook entries", cleared_count)
        return cleared_count
