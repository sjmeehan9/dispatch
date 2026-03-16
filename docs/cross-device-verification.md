# Cross-Device Verification Checklist

This document provides step-by-step instructions for verifying the Dispatch application across macOS desktop browsers and iPhone Safari, including OneDrive data directory sync.

---

## 1. Prerequisites

- macOS with Python 3.13+ and the virtual environment activated
- Google Chrome (latest) and Safari (latest) installed on macOS
- iPhone (iOS 17+) on the **same Wi-Fi network** as the Mac
- OneDrive installed and syncing on macOS (optional — for data portability testing)
- Application dependencies installed: `pip install -e .`
- Environment configured: `.env/.env.local` populated (at minimum `GITHUB_TOKEN`)

---

## 2. Local Network Setup

### 2.1 Find Your Mac's Local IP

```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

Look for the IP on your Wi-Fi interface (typically `en0`), e.g. `192.168.1.42`.

### 2.2 Verify Server Binds to All Interfaces

The app must bind to `0.0.0.0` (not `127.0.0.1`) for LAN access. This is configured in `app/src/main.py`:

```python
ui.run(host="0.0.0.0", port=8080, reload=True, title="Dispatch")
```

### 2.3 Start the Application

```bash
source .venv/bin/activate
set -o allexport; source .env/.env.local; set +o allexport
python -m app.src.main
```

### 2.4 Test Access

- **Mac browser:** Open `http://localhost:8080/`
- **iPhone Safari:** Open `http://<mac-ip>:8080/` (e.g. `http://192.168.1.42:8080/`)

> **Note:** The app is served over HTTP, not HTTPS. Some browser features (e.g. clipboard API) may be restricted on non-localhost origins. This is expected for local development.

---

## 3. macOS Desktop Checklist

Run through the following for **both Chrome and Safari**:

| # | Test | Chrome | Safari |
|---|------|--------|--------|
| 3.1 | **Initial screen** (`/`) renders — title, "Configure Executor" and "Load Project" buttons visible | ☐ | ☐ |
| 3.2 | **Executor config** (`/config/executor`) — form loads, can enter endpoint URL, API key, webhook URL; save succeeds with toast notification | ☐ | ☐ |
| 3.3 | **Action type defaults** (`/config/action-types`) — default payload templates display, can edit and save | ☐ | ☐ |
| 3.4 | **Secrets screen** (`/config/secrets`) — can view/set GitHub token and API keys; save succeeds | ☐ | ☐ |
| 3.5 | **Link project** (`/project/link`) — enter a GitHub repo name, scan succeeds (requires valid `GITHUB_TOKEN`), phase-progress data parsed, project created and redirects to main screen | ☐ | ☐ |
| 3.6 | **Main screen** (`/project/{id}`) — actions list displays with correct ordering (Implement per component, then Test/Review/Document per phase) | ☐ | ☐ |
| 3.7 | **Dispatch action** — select an action, view resolved payload, click Dispatch; response panel shows run_id and status | ☐ | ☐ |
| 3.8 | **Webhook polling** — after dispatch, poll button retrieves webhook data (or shows "pending") | ☐ | ☐ |
| 3.9 | **Mark action complete** — action status changes to "completed" | ☐ | ☐ |
| 3.10 | **Insert debug action** — insert a Debug action at a chosen position; verify it appears correctly | ☐ | ☐ |
| 3.11 | **Edit payload** — edit action payload fields; changes persist | ☐ | ☐ |
| 3.12 | **Save project** — save project to disk; verify file written to data directory | ☐ | ☐ |
| 3.13 | **Load project** (`/project/load`) — load a previously saved project; all data intact | ☐ | ☐ |
| 3.14 | **LLM toggle** (if `OPENAI_API_KEY` configured) — enable LLM payload generation; verify AI-generated instructions appear in payload | ☐ | ☐ |
| 3.15 | **Navigation** — all screen transitions smooth, loading indicators display during async operations, back/forward browser navigation works | ☐ | ☐ |
| 3.16 | **Error handling** — triggering an error (e.g. invalid repo name) shows a user-friendly toast notification, no crash | ☐ | ☐ |

---

## 4. iPhone Safari Checklist

Access the app at `http://<mac-ip>:8080/` on iPhone Safari. Run through the same functional checks as Section 3, plus the following responsive/mobile-specific checks:

| # | Test | Pass |
|---|------|------|
| 4.1 | All screens from Section 3 (3.1–3.16) function correctly on iPhone | ☐ |
| 4.2 | **Stacked layout** — split panels (e.g. action list + detail panel on main screen) stack vertically on narrow viewport | ☐ |
| 4.3 | **Touch targets** — buttons and interactive elements are at least 44×44px; easy to tap without mis-hits | ☐ |
| 4.4 | **Text readability** — all text is legible without pinch-to-zoom; font sizes appropriate for mobile | ☐ |
| 4.5 | **Form usability** — text inputs, selects, and textareas work with the mobile keyboard; no input zoom issues | ☐ |
| 4.6 | **Loading indicators** — spinners/progress indicators visible during async operations | ☐ |
| 4.7 | **Toast notifications** — success/error toasts display correctly and are dismissible | ☐ |
| 4.8 | **Scrolling** — long action lists and payload content scroll smoothly; no stuck scroll areas | ☐ |
| 4.9 | **Viewport** — page respects `viewport` meta tag; no horizontal overflow or awkward zoom | ☐ |
| 4.10 | **Safe area** — content does not overlap iPhone notch or home indicator areas | ☐ |

---

## 5. OneDrive Data Directory Sync

### 5.1 Configure OneDrive Data Directory

Set `DISPATCH_DATA_DIR` to an OneDrive-synced folder in `.env/.env.local`:

```bash
DISPATCH_DATA_DIR=~/Library/CloudStorage/OneDrive-Personal/dispatch-data
```

> Adjust the path to match your OneDrive mount point. Common paths:
> - `~/Library/CloudStorage/OneDrive-Personal/dispatch-data`
> - `~/OneDrive/dispatch-data`

Restart the application after changing this value.

### 5.2 Sync Verification Checklist

| # | Test | Pass |
|---|------|------|
| 5.1 | Application starts with OneDrive data directory — no errors, directories created | ☐ |
| 5.2 | **Save project** — link or create a project; save it. Verify the JSON file appears at `$DISPATCH_DATA_DIR/projects/` | ☐ |
| 5.3 | **OneDrive sync** — the project file syncs to OneDrive cloud (check OneDrive sync status icon on the file) | ☐ |
| 5.4 | **Cross-device access** — on another device (or the same Mac after clearing local cache), verify the project file is present in the OneDrive-synced directory | ☐ |
| 5.5 | **Load synced project** — load the synced project file from the OneDrive directory; all data intact (phases, actions, statuses) | ☐ |
| 5.6 | **Concurrent access** — save a project on Device A, wait for sync, load on Device B — no data corruption | ☐ |

---

## 6. Remote Access Verification (Non-LAN)

### 6.1 Prerequisites

- ngrok (or another tunnel) is running and forwarding to `localhost:8080`
- `DISPATCH_ACCESS_TOKEN` is set in `.env/.env.local`
- iPhone is on a different network (cellular or different Wi-Fi)

### 6.2 Remote Checklist

| # | Test | Pass |
|---|------|------|
| 6.1 | Open tunnel URL on iPhone; login screen appears | ☐ |
| 6.2 | Enter correct access token; redirected to initial screen | ☐ |
| 6.3 | Enter wrong token; error notification shown and no access granted | ☐ |
| 6.4 | Section 4 tests (4.1-4.10) pass through tunnel URL | ☐ |
| 6.5 | Connection recovery: toggle airplane mode briefly; UI reconnects | ☐ |
| 6.6 | Dispatch action and verify webhook callback arrives through tunnel | ☐ |

## 7. Known Limitations

| Limitation | Detail |
|------------|--------|
| **HTTP only** | The app runs over HTTP on the local network. Some browser APIs (clipboard, notifications) may be restricted on non-localhost HTTP origins. HTTPS requires additional certificate setup not covered here. |
| **No real-time sync** | OneDrive sync is file-based and asynchronous. Changes may take 30–60 seconds to propagate. The app does not detect external file changes — you must reload/re-load the project manually. |
| **iPhone input zoom** | Safari on iOS may zoom into input fields with font size < 16px. NiceGUI's Quasar components use 16px by default, but custom-styled inputs should be verified. |
| **WebSocket reconnect** | If the iPhone locks or the network connection drops, NiceGUI's WebSocket may disconnect. The app should reconnect automatically within 10 seconds (configured `reconnect_timeout`), but a page refresh may be needed in some cases. |
| **No offline support** | The app requires an active network connection to the Mac. There is no service worker or offline mode. |

---

## 8. Test Results Summary

Record your test results here after completing verification:

| Device / Browser | Date | Tester | Result | Notes |
|------------------|------|--------|--------|-------|
| macOS Chrome | | | | |
| macOS Safari | | | | |
| iPhone Safari | | | | |
| OneDrive Sync | | | | |
