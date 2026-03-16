# Phase 8: Remote Access Security & Mobile Stability

## Phase Overview

**Objective**: Harden Dispatch for remote iPhone access over public tunnels by adding optional UI authentication, improving mobile reconnect behavior, and documenting the remote verification workflow.

**Deliverables**:
- Optional access-token auth gate for UI pages
- Login screen and page-level auth checks
- Webhook callback compatibility preserved while polling endpoint is token-protected
- Reconnect timeout tuned for unstable mobile networks
- Remote access documentation and verification checklist updates
- Phase tracking and implementation context updates

**Dependencies**:
- Phase 7 complete (UI modernisation, cross-device verification baseline, webhook compatibility)
- Existing NiceGUI app routing in `app/src/main.py`
- Existing settings/config and tests

---

## Component 8.1 - Remote Access Authentication, Resilience, and Documentation

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

### Features

- [AI Agent] Add optional `DISPATCH_ACCESS_TOKEN` support in settings
- [AI Agent] Add optional `DISPATCH_RELOAD` support for stable long-running sessions
- [AI Agent] Add login screen at `/login` and page-level auth gate for UI routes
- [AI Agent] Keep webhook callback endpoints unauthenticated for executor compatibility
- [AI Agent] Protect webhook poll endpoint with `Authorization: Bearer <token>` when auth is enabled
- [AI Agent] Increase NiceGUI reconnect timeout from 3s to 10s
- [AI Agent] Update env template, README, and cross-device verification for remote non-LAN flow
- [AI Agent] Add tests for new settings behavior and protected polling endpoint

### Files to Modify/Create

- `app/src/config/settings.py`
- `app/src/main.py`
- `app/src/ui/login_screen.py` (new)
- `.env/.env.example`
- `README.md`
- `docs/cross-device-verification.md`
- `tests/test_settings.py`
- `tests/test_main.py`

### Acceptance Criteria

- [ ] If `DISPATCH_ACCESS_TOKEN` is unset/blank, behavior remains unchanged (open LAN mode)
- [ ] If `DISPATCH_ACCESS_TOKEN` is set, UI routes require login and authenticate correctly
- [ ] `/login` renders and handles invalid token attempts with user feedback
- [ ] `POST /` and `POST /webhook/callback` remain available without auth
- [ ] `GET /webhook/poll/{run_id}` returns `401` without bearer token when auth is enabled
- [ ] `GET /webhook/poll/{run_id}` works with correct bearer token when auth is enabled
- [ ] Reconnect timeout is 10 seconds
- [ ] `DISPATCH_RELOAD` controls NiceGUI reload behavior
- [ ] README includes remote access security guidance
- [ ] Cross-device checklist includes remote non-LAN verification section
- [ ] Unit/integration tests pass without regressions
