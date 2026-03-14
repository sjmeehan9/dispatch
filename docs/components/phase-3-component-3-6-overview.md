# Phase 3 Component 3.6 Overview — Executor Protocol & Autopilot Implementation

## Summary
Component 3.6 introduces the executor abstraction and the default Autopilot-backed implementation used to dispatch resolved action payloads. The service now exposes a protocol-driven contract and returns normalized `ExecutorResponse` objects for both success and failure paths without surfacing transport exceptions to callers.

## Implemented Scope
- Added `app/src/services/executor.py`:
  - `Executor` protocol (`runtime_checkable`) with:
    - `dispatch(payload: dict[str, Any], config: ExecutorConfig) -> ExecutorResponse`
  - `AutopilotExecutor` class with:
    - `__init__(settings: Settings)`
    - `dispatch(payload, config) -> ExecutorResponse`
    - internal parsing helpers for success/error message extraction and run-id extraction.
- Updated `app/src/services/__init__.py` exports to include:
  - `Executor`
  - `AutopilotExecutor`

## Key Behavior
- Resolves the executor API key at dispatch time from `Settings.get_secret(config.api_key_env_key)`.
- Returns configuration failure response when key is missing:
  - `status_code=0`
  - message: `API key not configured. Set <ENV_KEY> in your environment.`
- Sends HTTP POST to `config.api_endpoint` with:
  - JSON payload body,
  - headers `X-API-Key` and `Content-Type: application/json`,
  - timeout of 30 seconds.
- Normalizes outcomes into `ExecutorResponse`:
  - **2xx**: includes status code, parsed status/message, optional `run_id`, and parsed JSON object in `raw_response`.
  - **Non-2xx**: includes status code, parsed error message, `run_id=None`, `raw_response=None`.
  - **Network/transport failures** (`ConnectError`, `TimeoutException`, `HTTPError`): `status_code=0` and descriptive message.
- Emits INFO/WARNING logs for dispatch lifecycle and errors while avoiding payload/secret logging.

## Tests Added
- New file: `tests/test_executor.py`
- Coverage includes:
  - request construction (endpoint, headers, JSON payload, timeout),
  - successful 200 parsing with `run_id`,
  - unauthorized 401 mapping,
  - connection failure handling,
  - timeout handling,
  - missing API key handling,
  - structural protocol conformance (`isinstance(..., Executor)`).

## Notes
- The implementation intentionally returns `ExecutorResponse` for all failure modes so UI and orchestration layers can handle a single response type without exception branching.
