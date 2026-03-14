# Phase 7 Component 7.1 Overview

## Summary

Component 7.1 delivers the complete end-to-end test suite for Dispatch focused on the full service workflow from configuration to dispatch and result handling. The suite validates all planned E2E scenarios while keeping CI stability through deterministic mocks and explicit gating for live external executor tests.

## Scope Delivered

- Added tests/e2e package with reusable fixtures and five scenario tests.
- Added root-level pytest support for live executor confirmation and automatic skipping when not explicitly enabled.
- Covered mocked full-chain workflows for configuration, linking, action generation, payload resolution, dispatch simulation, webhook handling, and completion state transitions.
- Added an opt-in live Autopilot dispatch test with bounded polling behavior.

## Scenario Coverage

- E2E-001: Configure Dispatch and perform a full mocked dispatch roundtrip.
- E2E-002: Load a persisted project and run all phase actions through completion.
- E2E-003: Insert a Debug action, edit payload, dispatch, and mark complete.
- E2E-004: Validate LLM-assisted payload generation success and fallback modes.
- E2E-005: Human-confirmed live Autopilot dispatch path with optional webhook polling.

## Technical Notes

- Shared fixtures in tests/e2e/conftest.py provide isolated settings and deterministic project data.
- Live test execution requires --autopilot-confirm and environment-provided executor secrets.
- Existing TOKEN/GITHUB_TOKEN alias behavior remains compatible with repository secret naming constraints.

## Verification Strategy

- Primary verification runs mocked E2E scenarios using pytest selection that excludes requires_autopilot.
- Secondary verification confirms requires_autopilot tests auto-skip cleanly when confirmation flag is absent.
- Live verification is intentionally manual and gated to avoid unsafe automated external calls.

## Risks and Mitigations

- Risk: Flaky external dependency behavior in CI.
  Mitigation: Live tests are marker-gated and skipped by default.
- Risk: Environment mismatch for webhook polling endpoints.
  Mitigation: Polling endpoint is optional and configured through environment variable.
