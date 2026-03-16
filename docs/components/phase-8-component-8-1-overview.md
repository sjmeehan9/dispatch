# Phase 8 Component 8.1 Overview

## Component

- **ID**: 8.1
- **Name**: Remote Access Authentication, Resilience, and Documentation
- **Status**: Completed
- **Date**: 2026-03-16

## Summary

Component 8.1 implemented secure remote access controls for Dispatch while preserving the existing local-first workflow. The feature is opt-in through environment configuration and does not change behavior when disabled.

## Delivered Capabilities

- Added optional access token support in settings via `DISPATCH_ACCESS_TOKEN`.
- Added optional reload control via `DISPATCH_RELOAD`.
- Added new login screen (`/login`) for token-based authentication.
- Added page-level auth guard for all UI routes.
- Kept webhook callbacks (`POST /`, `POST /webhook/callback`) open for executor interoperability.
- Added bearer-token protection for webhook polling (`GET /webhook/poll/{run_id}`) when auth is enabled.
- Increased NiceGUI reconnect timeout to 10 seconds to improve behavior on unstable mobile networks.
- Updated documentation for ngrok/tunnel-based remote access and non-LAN verification.

## Technical Notes

- Session auth uses NiceGUI `app.storage.user["authenticated"]`.
- Storage secret is set explicitly from access token (or local fallback) for deterministic session behavior.
- Auth behavior is backward compatible: no token means no login gate.
- Poll endpoint auth is enforced in middleware using `Authorization: Bearer <token>`.

## Validation Coverage

- Added tests for settings access-token parsing and reload flag parsing.
- Added test ensuring poll endpoint returns `401` without bearer token when auth is enabled.
- Existing route and webhook tests remain valid in default no-token mode.

## Files

- app/src/config/settings.py
- app/src/main.py
- app/src/ui/login_screen.py
- tests/test_settings.py
- tests/test_main.py
- .env/.env.example
- README.md
- docs/cross-device-verification.md
