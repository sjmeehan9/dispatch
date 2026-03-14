# Phase 3 Component 3.7 Overview: Webhook Service

## Summary
Component 3.7 introduces a dedicated `WebhookService` for storing executor callback data in memory by `run_id`. This service supports Phase 4 webhook API wiring and UI polling by providing safe, deterministic retrieval and cleanup operations.

## Implemented Scope
- Added `WebhookService` in `app/src/services/webhook_service.py`.
- Added service export in `app/src/services/__init__.py`.
- Added unit test suite in `tests/test_webhook_service.py`.

## Service API
- `store(run_id: str, data: dict[str, Any]) -> None`
  - Stores callback payload with an insertion timestamp.
- `retrieve(run_id: str) -> dict[str, Any] | None`
  - Returns callback payload if present; otherwise `None`.
- `has_result(run_id: str) -> bool`
  - Returns whether callback payload exists for the run.
- `clear(run_id: str) -> None`
  - Removes an entry if present (idempotent).
- `clear_stale(max_age_seconds: int = 3600) -> int`
  - Evicts entries older than the threshold and returns eviction count.

## Design Decisions
- **Thread safety**: A shared `threading.Lock` guards all reads and writes to protect cross-thread access between webhook callbacks and UI polling.
- **Storage model**: Internal map shape is `dict[str, tuple[float, dict[str, Any]]]` so stale cleanup can compute age without additional metadata structures.
- **Logging**: INFO logs are emitted for receipt and cleanup events while avoiding sensitive payload logging.

## Validation
- Added test coverage for:
  - store/retrieve round-trip,
  - missing run retrieval,
  - `has_result` transitions,
  - `clear` removal behavior,
  - `clear_stale` age-based eviction with mocked time.

## Notes for Integration
- The service is intentionally in-memory and process-local; persistence is not included in this component.
- `clear_stale()` is explicit and can be called by webhook endpoint handlers or polling flows when needed.
