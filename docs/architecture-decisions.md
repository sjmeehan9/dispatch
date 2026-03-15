# Architecture Decisions

This document records the key technical decisions made during the design and implementation of Dispatch. Each entry follows a lightweight ADR (Architecture Decision Record) format: Context, Decision, and Rationale.

---

## 1. NiceGUI over Electron, Tauri, or PWA

**Context**: Dispatch needs a responsive web UI accessible from both macOS desktop browsers and iPhone Safari. The developer works in Python and wants to avoid a JavaScript build pipeline. Framework options included Electron (desktop app), Tauri (Rust desktop shell), PWA (Progressive Web App), and NiceGUI (pure-Python web UI).

**Decision**: Use NiceGUI 2.x as the UI framework.

**Rationale**: NiceGUI is a pure-Python web UI framework built on FastAPI, Quasar (Material Design), and Vue. It eliminates the need for a JavaScript build pipeline, Node.js tooling, or separate frontend code. Quasar's responsive components work on both desktop and mobile browsers without additional effort. The built-in FastAPI integration allows custom API endpoints (webhook callbacks) to coexist in the same process. Auto-reload during development accelerates iteration. For a single-user local tool, NiceGUI's simplicity and zero-configuration deployment are ideal.

---

## 2. JSON Files over SQLite

**Context**: Dispatch needs to persist project configurations, executor settings, and action item state. Storage options included SQLite (embedded relational database), JSON files, or a full database like PostgreSQL.

**Decision**: Use local JSON files for all persisted state.

**Rationale**: For a single-user local application, JSON files are the simplest option with zero external dependencies. Files are human-readable and debuggable with any text editor. Crucially, individual JSON files are OneDrive-syncable — each project is stored as a separate file, avoiding conflicts from concurrent writes. SQLite would add a binary database dependency and complicate cross-device sync through OneDrive (binary files don't merge well). The data volumes are small (kilobytes per project), so file I/O performance is not a concern.

---

## 3. Polling over WebSocket for Webhook Results

**Context**: After dispatching an action to the executor, Dispatch needs to display the executor's result when it arrives via webhook callback. Options included maintaining a persistent WebSocket connection from the UI, server-sent events (SSE), or a simpler POST-and-poll architecture.

**Decision**: Use POST-based webhook reception with in-memory storage and a UI refresh button for polling.

**Rationale**: The webhook callback is an async event from an external service — the executor POSTs the result to Dispatch's `/webhook/callback` endpoint. Dispatch stores the payload keyed by `run_id` in an in-memory dict. The user clicks "Refresh" to poll for results. This avoids the complexity of persistent WebSocket connections (connection lifecycle management, reconnection logic, per-client state). The latency tradeoff (manual refresh vs. instant push) is acceptable for a single-user tool where dispatches take minutes or hours to complete.

---

## 4. Simple `{{variable}}` Interpolation over Jinja2

**Context**: Action payloads use templates with placeholder variables (e.g., `{{repository}}`, `{{component_id}}`) that are resolved before dispatch. Template engine options included Jinja2, Python string.Template, or simple string replacement.

**Decision**: Use simple `{{variable}}` string replacement via Python's `str.replace()`.

**Rationale**: The variable set is small and well-defined (approximately 10 variables from phase-progress data, agent paths, and webhook URL). Simple string replacement is predictable, has no external dependencies, and is trivially debuggable. Jinja2 would add a dependency and template compilation overhead for zero practical benefit given the straightforward substitution needs. The replacement logic is a single pass through the known variable list — no conditionals, loops, or filters are needed.

---

## 5. Local-First Design with OneDrive Sync over Cloud Hosting

**Context**: Dispatch must be accessible from both a macOS desktop and an iPhone. Deployment options included cloud hosting (AWS, Vercel), a native mobile app, or a local-first architecture with file sync for cross-device access.

**Decision**: Run Dispatch as a local server on macOS, accessible from other devices on the same network via `http://<mac-ip>:8080`. Store project data in an OneDrive-synced directory for cross-device data portability.

**Rationale**: Cloud hosting would introduce infrastructure cost, deployment complexity, and authentication requirements — all unnecessary for a single-user tool. A local-first architecture gives the user full control over their data and secrets. The Uvicorn server binds to `0.0.0.0`, making it accessible from any device on the local network (including iPhone Safari). OneDrive sync handles cross-device data portability transparently — Dispatch writes atomic JSON files, and OneDrive syncs them to the cloud and other devices. Zero infrastructure cost, zero multi-tenancy complexity.

---

## 6. Modular Executor Protocol over Hardcoded Autopilot

**Context**: Dispatch's primary executor is Autopilot (a GitHub Copilot agent orchestration service), but the design should support alternative executors without architectural changes.

**Decision**: Define a Python `Protocol` class (`ExecutorProtocol`) that all executor implementations must conform to. The Autopilot executor is the default implementation. Executor configuration (endpoint, API key, webhook URL) is decoupled from the executor implementation.

**Rationale**: The Protocol pattern allows swapping or adding executors without modifying the dispatch service or UI. A new executor requires only a new class that implements `dispatch(payload) -> ExecutorResponse`. The executor configuration screen in the UI is already generic — it stores endpoint, auth, and webhook URL regardless of which executor is behind it. This future-proofs the design for alternative AI agent services without over-engineering the current implementation.

---

## 7. Optional LLM Payload Generation with Graceful Fallback

**Context**: Action payloads can be generated using simple variable interpolation (sufficient for most cases) or enhanced with an LLM that interprets component context to write richer `agent_instructions`. The LLM feature is optional — not all users will have an OpenAI API key.

**Decision**: LLM payload generation is opt-in via a toggle in the executor configuration. When enabled and available (valid API key, successful API call), the LLM generates the `agent_instructions` field. All other payload fields (repository, branch, model, callback_url) are always filled via standard interpolation. When the LLM is unavailable, disabled, or fails, the system falls back to standard interpolation silently.

**Rationale**: The LLM enhances but does not gatekeep the workflow. A user without an OpenAI API key can still use Dispatch fully — the standard interpolation templates produce functional payloads. The graceful fallback ensures that LLM API timeouts, rate limits, or key expiry never block the dispatch workflow. The user always reviews the payload before dispatch, so LLM-generated content is validated by a human in the loop.
