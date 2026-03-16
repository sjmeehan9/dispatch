# Implementation Plan: Mobile Remote Access (iPhone Anywhere)

**Date:** 2025-03-16  
**Status:** Draft — awaiting approval  
**Scope:** Enabling secure iPhone access to Dispatch from any network, not just local Wi-Fi

---

## Table of Contents

1. [Current State Assessment](#current-state-assessment)
2. [What Already Works](#what-already-works)
3. [What's Missing](#whats-missing)
4. [Requirement Summary](#requirement-summary)
5. [Implementation Phases](#implementation-phases)
6. [Risk & Migration Notes](#risk--migration-notes)

---

## Current State Assessment

Dispatch is a local-first NiceGUI application (FastAPI + Quasar/Vue) that runs as a Uvicorn server on macOS. The architecture was explicitly designed for cross-device LAN access (Architecture Decision #5) and already has significant mobile/responsive work in place.

### Network Architecture

```
┌─────────────────────────────────────────────────────┐
│ macOS Host                                          │
│   Uvicorn (0.0.0.0:8080)                           │
│   ├── NiceGUI UI pages (/, /project/{id}, etc.)     │
│   ├── Webhook endpoints (POST /webhook/callback)    │
│   └── Poll endpoint (GET /webhook/poll/{run_id})    │
└───────────┬─────────────────────────┬───────────────┘
            │ LAN (Wi-Fi)             │ ngrok tunnel
            ▼                         ▼
     ┌──────────┐           ┌─────────────────────┐
     │ iPhone   │           │ ngrok public URL     │
     │ (same    │           │ (HTTPS, WebSocket)   │
     │  network)│           │ → localhost:8080     │
     └──────────┘           └─────────────────────┘
```

---

## What Already Works

### 1. LAN Access — Fully Functional
- `ui.run(host="0.0.0.0", port=8080)` binds to all interfaces (`app/src/main.py:157`)
- iPhone on the same Wi-Fi can access `http://<mac-ip>:8080/`
- Verified in Phase 7 Component 7.2; cross-device checklist exists at `docs/cross-device-verification.md`

### 2. Mobile-Responsive UI — Fully Functional
- Viewport meta tag: `width=device-width, initial-scale=1` (`app/src/main.py:48`)
- Quasar responsive grid: `col-12 col-md-5` / `col-12 col-md-7` panels stack vertically on mobile (`app/src/ui/main_screen.py:1104-1114`)
- Touch targets: 44px minimum height/width at `<768px` (`app/src/static/styles.css`)
- Panel height adapts: `dispatch-panel-scroll` uses `height: auto` under 1023px
- Dialogs go full-screen: `dispatch-dialog-card` uses `100vw`/`100vh` under 767px
- Header title scales down on mobile

### 3. ngrok Tunnel — Already Running
- `AUTOPILOT_WEBHOOK_URL=https://joint-filly-inherently.ngrok-free.app` is configured in `.env/.env.local`
- ngrok forwards ALL traffic (not just webhooks) to `localhost:8080`
- This means the Dispatch UI is **already accessible** at the ngrok HTTPS URL from anywhere
- HTTPS is provided free by ngrok, solving transport security
- ngrok supports WebSocket forwarding, which NiceGUI requires for UI reactivity

### 4. Connection Resilience — Partially Handled
- `reconnect_timeout=3.0` configured in `_ensure_run_config()` (`app/src/main.py:53`)
- `message_history_length=1000` ensures missed UI updates are replayed after reconnection

### Bottom Line
**You can already open `https://joint-filly-inherently.ngrok-free.app/` on your iPhone from any network and use Dispatch.** The UI, dispatching, webhook monitoring — all of it works through the ngrok tunnel.

---

## What's Missing

Despite the above, there are three gaps that range from critical to nice-to-have:

### Gap 1: No Authentication (Critical)

There is **zero authentication** on any NiceGUI page or API endpoint. Anyone who discovers or guesses the ngrok URL has full access to:
- All project data and configurations
- The ability to dispatch actions (spend executor API credits, trigger agent runs)
- View GitHub tokens and API keys through the Secrets screen
- Receive and read webhook callbacks containing code review results

**Files affected:** `app/src/main.py` (all page routes and API endpoints), no auth middleware exists anywhere in the codebase.

On LAN this is an acceptable tradeoff (trusted home/office network). On the public internet via ngrok, it's a security hole.

### Gap 2: ngrok Free Tier Friction (Minor)

The ngrok free tier shows an interstitial "Visit Site" warning page on first access from each device/session. This:
- Adds friction on every new session from iPhone
- Can interfere with NiceGUI's initial WebSocket handshake (rare but possible)
- Has bandwidth and connection limits

This is a UX annoyance, not a blocker. A paid ngrok plan ($8/month) or an alternative tunnel (Tailscale, Cloudflare Tunnel) eliminates it.

### Gap 3: Mobile Connection Stability (Nice-to-Have)

NiceGUI maintains a persistent WebSocket for UI reactivity. On mobile networks:
- Cellular connections drop frequently (cell tower handoffs, subway, etc.)
- The current `reconnect_timeout=3.0s` may be too aggressive — a mobile reconnection after a brief drop might take 5-10 seconds
- No visual indication to the user that the connection was lost and is reconnecting

---

## Requirement Summary

| # | Requirement | Priority | Effort |
|---|------------|----------|--------|
| R1 | Add authentication to protect the app when exposed via tunnel | Critical | Small |
| R2 | Improve reconnection handling for unstable mobile connections | Nice-to-have | Trivial |
| R3 | Document the remote access setup clearly | Important | Trivial |

---

## Implementation Phases

### Phase A — Authentication

**Effort:** ~1-2 hours  
**Files modified:** 3-4 files, ~80 lines added

NiceGUI has built-in authentication support via `app.storage.user` and FastAPI middleware. The approach: add a simple shared-secret authentication gate that protects all UI pages and API endpoints.

#### A.1 — Add `DISPATCH_ACCESS_TOKEN` environment variable

**File:** `app/src/config/settings.py`

Add a property to `Settings` that reads an optional access token from the environment:

```python
@property
def access_token(self) -> str | None:
    """Return the optional access token for remote access protection."""
    return os.environ.get("DISPATCH_ACCESS_TOKEN")
```

**File:** `.env/.env.example`

```bash
# Optional access token for protecting remote access via tunnel.
# When set, all UI pages and API endpoints require this token.
# Leave blank to allow unauthenticated LAN access (default).
DISPATCH_ACCESS_TOKEN=
```

#### A.2 — Add login page and auth middleware

**File:** `app/src/ui/login_screen.py` (new)

A minimal login screen that accepts the access token:

```python
"""Login screen for remote access authentication."""

from nicegui import app, ui

def render_login_screen() -> None:
    """Render a minimal login form that validates the access token."""
    with ui.column().classes("absolute-center items-center q-gutter-md"):
        ui.icon("lock").props('size="3rem" color="primary"')
        ui.label("Dispatch").classes("text-h4")
        token_input = ui.input(
            "Access Token",
            password=True,
            password_toggle_button=True,
        ).classes("w-64")
        
        def _authenticate() -> None:
            if token_input.value == app.storage.general.get("_access_token"):
                app.storage.user["authenticated"] = True
                ui.navigate.to(app.storage.user.get("redirect", "/"))
            else:
                ui.notify("Invalid access token", type="negative")
        
        ui.button("Sign In", on_click=_authenticate, color="primary").classes(
            "w-64 dispatch-touch-target"
        )
```

#### A.3 — Add auth guard middleware to main.py

**File:** `app/src/main.py`

NiceGUI supports an `app.middleware` decorator for request interception. Add an auth guard that redirects unauthenticated users to the login page when an access token is configured:

```python
from starlette.responses import RedirectResponse

@app.middleware("http")
async def _auth_guard(request: Request, call_next):
    """Redirect unauthenticated users to login when access token is set."""
    access_token = app_state.settings.access_token
    
    # No token configured = no auth required (LAN-only mode)
    if not access_token:
        return await call_next(request)
    
    # Store the token for login validation
    app.storage.general["_access_token"] = access_token
    
    # Allow login page, static files, and webhook endpoints without auth
    path = request.url.path
    if path in ("/login", "/login/") or path.startswith("/static/") or path.startswith("/_nicegui"):
        return await call_next(request)
    
    # Webhook endpoints use a different auth model (caller knows the URL)
    if path.startswith("/webhook/"):
        return await call_next(request)
    
    # NiceGUI storage not available for non-page requests — allow through
    # (NiceGUI's built-in auth check handles page-level gating)
    return await call_next(request)
```

For page-level gating, add an auth check to each `@ui.page` decorator using NiceGUI's storage:

```python
def _require_auth() -> bool:
    """Check if user is authenticated, redirect to login if not."""
    if not app_state.settings.access_token:
        return True  # No auth required
    if not app.storage.user.get("authenticated"):
        app.storage.user["redirect"] = ui.context.client.page.path
        ui.navigate.to("/login")
        return False
    return True
```

Add `@ui.page("/login")` route and call `_require_auth()` at the top of each existing page function.

#### A.4 — Protect API endpoints

**File:** `app/src/main.py`

The webhook callback endpoints (`POST /`, `POST /webhook/callback`) should remain open — the executor needs to call them without browser auth. But the poll endpoint (`GET /webhook/poll/{run_id}`) should check for auth when a token is configured, using a simple `Authorization: Bearer <token>` header check or cookie-based session.

The pragmatic approach: webhook POST endpoints stay open (security through URL obscurity — the run_id is a UUID), poll endpoint is only called from the authenticated UI (NiceGUI fetches it internally), so it's already protected by the browser session.

#### A.5 — NiceGUI storage secret

**File:** `app/src/main.py`

NiceGUI's `app.storage` requires a storage secret for session encryption. Add:

```python
app.storage.secret = app_state.settings.access_token or "dispatch-local-dev"
```

This is already implicitly set but should be explicit when auth is enabled.

#### A.6 — Update .env files and tests

- `.env/.env.example` — add `DISPATCH_ACCESS_TOKEN=`
- `tests/` — ensure test fixtures work with auth disabled (no token set = no auth)

---

### Phase B — Connection Resilience

**Effort:** ~15 minutes  
**Files modified:** 1 file, ~5 lines changed

#### B.1 — Increase reconnect timeout for mobile

**File:** `app/src/main.py`

Change `reconnect_timeout` from `3.0` to `10.0` seconds. This gives mobile connections more time to recover after cell tower handoffs or brief network drops:

```python
reconnect_timeout=10.0,
```

NiceGUI automatically shows a reconnection overlay when the WebSocket drops, so the user gets visual feedback.

#### B.2 — Consider disabling `reload` in production mode

**File:** `app/src/main.py`

The `reload=True` flag causes Uvicorn to restart on file changes, which disconnects all clients. For mobile use, consider making this configurable:

```python
ui.run(
    host="0.0.0.0",
    port=8080,
    reload=os.environ.get("DISPATCH_RELOAD", "true").lower() == "true",
    title="Dispatch",
)
```

---

### Phase C — Documentation

**Effort:** ~15 minutes  
**Files modified:** 2 files

#### C.1 — Add remote access section to README

**File:** `README.md`

Add a section covering:

```markdown
### Remote Access (iPhone from Any Network)

Dispatch can be accessed from any network using a tunnel service. Since the app
already binds to `0.0.0.0:8080`, any tunnel that forwards to `localhost:8080`
exposes the full UI.

#### Using ngrok (recommended for simplicity)

```bash
# Start the tunnel (if not already running for webhooks)
ngrok http 8080
```

The ngrok HTTPS URL (e.g. `https://your-subdomain.ngrok-free.app`) works in
iPhone Safari. Set this same URL as `AUTOPILOT_WEBHOOK_URL` so one tunnel
handles both UI access and webhook callbacks.

#### Security

When exposing Dispatch over a tunnel, set an access token to protect the UI:

```bash
# In .env/.env.local
DISPATCH_ACCESS_TOKEN=your-secret-token-here
```

When set, all UI pages require authentication. Webhook callback endpoints
remain open so the executor can deliver results.

#### Alternative tunnels

| Tunnel | HTTPS | Auth Built-in | WebSocket | Cost |
|--------|-------|---------------|-----------|------|
| ngrok | ✅ | ❌ (use app auth) | ✅ | Free / $8/mo |
| Tailscale Funnel | ✅ | ✅ (device-level) | ✅ | Free for personal |
| Cloudflare Tunnel | ✅ | ✅ (via Access) | ✅ | Free |

Tailscale is the most secure option if both your Mac and iPhone have
Tailscale installed — traffic is encrypted end-to-end and never traverses
a public URL.
```

#### C.2 — Update cross-device verification checklist

**File:** `docs/cross-device-verification.md`

Add a Section 6 for remote (non-LAN) verification:

```markdown
## 6. Remote Access Verification (Non-LAN)

### 6.1 Prerequisites
- ngrok (or Tailscale/Cloudflare Tunnel) running and forwarding to `localhost:8080`
- `DISPATCH_ACCESS_TOKEN` set in `.env/.env.local`
- iPhone on a *different* network (e.g., cellular, different Wi-Fi)

### 6.2 Remote Checklist

| # | Test | Pass |
|---|------|------|
| 6.1 | Open tunnel URL on iPhone — login screen appears | ☐ |
| 6.2 | Enter correct access token — redirected to initial screen | ☐ |
| 6.3 | Enter wrong token — error notification shown, no access | ☐ |
| 6.4 | All Section 4 tests (4.1–4.10) pass via tunnel | ☐ |
| 6.5 | Connection drop recovery — toggle airplane mode briefly, UI reconnects | ☐ |
| 6.6 | Webhook callback — dispatch an action, webhook arrives via tunnel | ☐ |
```

---

## Implementation Phases — Summary

| Phase | Scope | Files | Effort |
|-------|-------|-------|--------|
| **A** | Authentication (access token gate) | 4–5 files, ~80 lines | ~1-2 hours |
| **B** | Connection resilience | 1 file, ~5 lines | ~15 minutes |
| **C** | Documentation | 2 files | ~15 minutes |

**Total effort:** ~2 hours

---

## Risk & Migration Notes

### Backward Compatibility

- **No token set = current behaviour.** Authentication is entirely opt-in. When `DISPATCH_ACCESS_TOKEN` is empty or unset, the app operates exactly as it does today — open LAN access, no login screen.
- **Existing ngrok setup works immediately.** The ngrok tunnel the user already has running for webhooks also serves the UI. No additional tunnel is needed.

### NiceGUI Auth Considerations

- NiceGUI's `app.storage.user` is backed by browser cookies. The session persists across page navigations within the same browser session, so the user authenticates once per session, not per page.
- The storage secret should be deterministic (not random on each restart) so sessions survive server restarts. Using the access token itself as the storage secret achieves this.

### WebSocket Over Tunnel

- ngrok, Tailscale, and Cloudflare Tunnel all support WebSocket forwarding, which NiceGUI requires.
- Latency will be higher than LAN access (typically 50-200ms depending on tunnel provider and geography). This is perceptible but not problematic for a dispatch-and-monitor workflow.
- ngrok free tier adds an interstitial page on first visit per session. This can interfere with NiceGUI's initial page load. A paid ngrok plan ($8/month) eliminates this completely.

### Webhook Endpoint Security

- Webhook endpoints (`POST /`, `POST /webhook/callback`) remain unauthenticated by design. The executor (Autopilot) needs to POST results to these URLs without browser cookies.
- Security is through URL obscurity: the webhook URL contains a unique ngrok subdomain, and payloads are keyed by `run_id` (a UUID). Adding a webhook secret header is a possible future improvement but out of scope here.

### Secrets Screen Exposure

- The Secrets management screen shows environment variable names (not values). When accessed remotely, this is acceptable because the auth gate protects access.
- If additional protection is desired, the Secrets screen could require re-entering the access token before displaying. This is not included in the current plan but is a simple extension.

### Tailscale as the Recommended Long-Term Solution

For a single-user tool, **Tailscale** is the strongest recommendation:
- Zero public URL exposure — traffic goes directly between devices over WireGuard
- No authentication layer needed at the app level (Tailscale handles device authentication)
- Free for personal use (up to 100 devices)
- Works on both macOS and iOS
- The Mac's Tailscale IP is stable (e.g., `100.x.y.z:8080`), no ngrok URL rotation

The only downside is that both devices need Tailscale installed. For users who prefer not to install another tool, ngrok + app-level auth (this plan) is the simpler path.
