# Solution Design: Dispatch

## Executive Summary

Dispatch is a local-first Python web application built with NiceGUI that orchestrates AI agent execution against phased software project deliverables. It reads `phase-progress.json` from a linked GitHub repository, generates sequenced Execute Action items, and dispatches them to a configurable external executor API (defaulting to Autopilot). The app runs as a local server on macOS, accessible cross-device via any browser (including iPhone on the same network), with project data stored in an OneDrive-synced directory.

## Architecture Overview

### High-Level Architecture

- **UI Layer (NiceGUI)**: Single Python process serving a responsive web UI via Quasar/Vue. Split-panel layout for action management and response viewing. Accessible from any browser on the local network.
- **API Layer (FastAPI — built into NiceGUI)**: Custom FastAPI routes for webhook reception. NiceGUI is built on FastAPI, so webhook endpoints coexist in the same process.
- **Service Layer (Python modules)**: Project management, action generation, payload resolution, executor dispatch, and webhook polling — all plain Python classes.
- **Data Layer (Local JSON files)**: Project configs, executor settings, and action state persisted as JSON files in an OneDrive-synced directory. Secrets stored in `.env/.env.local` (gitignored).

### Architecture Principles

- **Simplicity first**: Single Python process, no database, no build pipeline, no JavaScript — everything is Python and JSON files.
- **Modular executor design**: Executor implementations are pluggable via a common interface; adding a new executor requires only a new class conforming to the protocol.
- **Local-first with cross-device access**: All data lives on the local filesystem (OneDrive-synced); the web UI is accessible from any device on the same network.
- **Separation of concerns**: UI, services, and data access are cleanly separated into distinct modules.

## Technology Stack

### Application Framework

- **Framework**: NiceGUI 2.x — *Rationale: Pure-Python web UI framework built on FastAPI/Quasar/Vue. Zero JavaScript required. Responsive layouts work on iPhone and desktop browsers. Built-in FastAPI integration allows custom API endpoints (webhooks) in the same process. Auto-reload during development. Lightweight and simple for a single-user local app.*
- **Language**: Python 3.13+
- **Underlying Server**: Uvicorn (bundled with NiceGUI)
- **UI Components**: Quasar (Material Design) via NiceGUI's Python API

### Backend Libraries

- **HTTP Client**: `httpx` — *Rationale: Modern async-capable HTTP client for GitHub API calls and executor API dispatch. Superior to requests for async support.*
- **GitHub API**: `httpx` direct calls to GitHub REST API — *Rationale: Only need a few endpoints (repo contents, file reads). A full GitHub SDK is unnecessary overhead.*
- **Payload Templating**: Python `string.Template` or simple `str.replace` — *Rationale: User requested simple string interpolation. No templating library needed.*
- **LLM Integration (optional)**: `openai` Python SDK — *Rationale: Official SDK for optional payload generation assistance.*

### Configuration & Storage

- **Data Format**: JSON files for all persisted state (projects, executor configs, action items)
- **Secrets Storage**: `.env/.env.local` file loaded via `python-dotenv` — *Rationale: Standard Python approach; gitignored for security.*
- **Data Directory**: `~/.dispatch/` symlinked or located within OneDrive for cross-device sync. Configurable via environment variable `DISPATCH_DATA_DIR`.

### DevOps

- **CI/CD**: GitHub Actions (lint, test, evals per copilot.instructions.md)
- **Formatting**: Black + isort
- **Testing**: pytest (30% coverage target per project standards)
- **Package Management**: pip with `pyproject.toml` (editable install)

## System Components

### Component: NiceGUI UI Layer

- **Purpose**: Renders all application screens and handles user interactions
- **Technology**: NiceGUI 2.x (Python → Quasar/Vue)
- **Responsibilities**:
  - Initial screen with Load Project, Link New Project, Configure Executor options
  - Executor and action type configuration screens
  - Secrets management screen
  - Main project screen with split-panel layout (action list left, responses right)
  - Action payload editing dialogs
  - Debug action insertion UI
- **Interfaces**:
  - **Inputs**: User interactions (clicks, form inputs)
  - **Outputs**: Rendered UI, calls to service layer
- **Dependencies**: All service components
- **Scaling Strategy**: Single-user; no scaling needed

### Component: Project Service

- **Purpose**: Manages project lifecycle — linking, loading, saving, and GitHub repo scanning
- **Technology**: Python module with httpx for GitHub API
- **Responsibilities**:
  - Authenticate with GitHub using project-scoped OAuth token
  - Scan target repo for `docs/phase-progress.json` — block if not found
  - Scan target repo for agent files in `.claude/agents/` and `.github/agents/`
  - Parse and validate `phase-progress.json` structure
  - Persist project configuration (repo, token reference, loaded data) to local JSON
  - Load previously saved projects from data directory
- **Interfaces**:
  - **Inputs**: GitHub repo (owner/repo), OAuth token, data directory path
  - **Outputs**: Parsed phase data, agent file paths, project config
- **Dependencies**: GitHub REST API, local filesystem
- **Scaling Strategy**: N/A — single user

### Component: Action Generator

- **Purpose**: Derives Execute Action items from parsed `phase-progress.json` data
- **Technology**: Pure Python
- **Responsibilities**:
  - For each Phase: generate one Implement action per Component (ordered by componentId)
  - After all Component Implements: generate one Test, one Review, one Document action per Phase
  - Support manual insertion of Debug actions at any position within a Phase
  - Assign payload templates from action type defaults
  - Resolve payload variables via simple string interpolation
- **Interfaces**:
  - **Inputs**: Parsed phase-progress data, action type default templates, project context
  - **Outputs**: Ordered list of Execute Action items with resolved payloads
- **Dependencies**: Executor config (for payload templates)
- **Scaling Strategy**: N/A

### Component: Payload Resolver

- **Purpose**: Resolves variable placeholders in payload templates to concrete values
- **Technology**: Pure Python string interpolation
- **Responsibilities**:
  - Parse payload template strings for `{{variable}}` placeholders
  - Resolve variables against a known context map (phase-progress fields, agent paths, repo info)
  - Return fully resolved payload ready for dispatch
  - Support per-action payload editing (override resolved values)
- **Interfaces**:
  - **Inputs**: Payload template string, variable context map
  - **Outputs**: Resolved payload (dict/JSON)
- **Dependencies**: None
- **Scaling Strategy**: N/A

### Component: Executor Module (Modular)

- **Purpose**: Dispatches Execute Action item payloads to the configured external executor API
- **Technology**: Python Protocol class + concrete implementations
- **Responsibilities**:
  - Define a common `Executor` protocol: `dispatch(payload) -> ExecutorResponse`
  - Autopilot executor implementation (default): POST to Autopilot REST API with API key auth
  - Store and load executor configuration (endpoint URL, API key, webhook URL)
  - Return structured response (status code, message, run_id)
- **Interfaces**:
  - **Inputs**: Resolved payload dict, executor configuration
  - **Outputs**: `ExecutorResponse` (status_code, message, run_id)
- **Dependencies**: httpx for HTTP calls, executor config from data directory
- **Scaling Strategy**: N/A — adding executors means adding new classes

### Component: Webhook Poller

- **Purpose**: Receives webhook callbacks from the executor and makes results available to the UI via polling
- **Technology**: FastAPI route (built into NiceGUI) + in-memory store
- **Responsibilities**:
  - Expose a `POST /webhook/callback` endpoint that the executor (Autopilot) calls back to
  - Store received webhook data in memory keyed by `run_id`
  - Expose a `GET /webhook/poll/{run_id}` internal endpoint for the UI to poll
  - UI refresh button triggers a poll check and updates the display
- **Interfaces**:
  - **Inputs**: Webhook POST from executor (JSON payload)
  - **Outputs**: Webhook data served to UI on poll
- **Dependencies**: NiceGUI/FastAPI app instance
- **Scaling Strategy**: N/A — single user, in-memory is sufficient

### Component: Config & Secrets Manager

- **Purpose**: Manages application configuration, executor settings, and secret values
- **Technology**: Python module with python-dotenv and JSON files
- **Responsibilities**:
  - Load secrets from `.env/.env.local` (GitHub token, API keys, LLM key)
  - Save user-entered secrets to `.env/.env.local` via the UI
  - Load/save executor configuration (endpoint, API key, webhook URL) as JSON
  - Load/save action type default payload templates as JSON
  - Ensure `.env` directory and files are gitignored
- **Interfaces**:
  - **Inputs**: User-entered secrets and config values
  - **Outputs**: Config values, secrets (in memory only — never logged)
- **Dependencies**: Local filesystem, python-dotenv
- **Scaling Strategy**: N/A

## Data Model

### Project Configuration (JSON file: `~/.dispatch/projects/{project-id}.json`)

```json
{
  "project_id": "uuid-string",
  "project_name": "owner/repo-name",
  "repository": "owner/repo-name",
  "github_token_env_key": "GITHUB_TOKEN_project_id",
  "phase_progress": { "...parsed phase-progress.json contents..." },
  "agent_files": [
    ".claude/agents/implement.agent.md",
    ".github/agents/reviewer.agent.md"
  ],
  "actions": [
    {
      "action_id": "uuid-string",
      "phase_id": 1,
      "component_id": "1.1",
      "action_type": "implement",
      "payload": { "...resolved payload..." },
      "status": "not-started",
      "executor_response": null,
      "webhook_response": null
    }
  ],
  "created_at": "2026-03-14T10:00:00Z",
  "updated_at": "2026-03-14T10:00:00Z"
}
```

- **Purpose**: Stores all state for a linked project including loaded phase data, generated actions, and execution results.
- **Key Relationships**: References executor config by ID. Actions reference phases/components from phase-progress data.
- **Indexes**: N/A — file-based storage, accessed by project_id filename.

### Executor Configuration (JSON file: `~/.dispatch/config/executor.json`)

```json
{
  "executor_id": "autopilot",
  "executor_name": "Autopilot",
  "api_endpoint": "http://localhost:8000/agent/run",
  "api_key_env_key": "AUTOPILOT_API_KEY",
  "webhook_url": "https://joint-filly-inherently.ngrok-free.app",
  "action_type_defaults": {
    "implement": {
      "repository": "{{repository}}",
      "branch": "{{branch}}",
      "agent_instructions": "Implement {{component_name}} ({{component_id}}) of Phase {{phase_id}}. Follow the component breakdown in {{component_breakdown_doc}}.",
      "model": "claude-opus-4.6",
      "role": "implement",
      "agent_paths": "{{agent_paths}}",
      "callback_url": "{{webhook_url}}",
      "timeout_minutes": 30
    },
    "test": {
      "repository": "{{repository}}",
      "branch": "{{branch}}",
      "agent_instructions": "Test Phase {{phase_id}} ({{phase_name}}). Validate all components are working correctly.",
      "model": "claude-opus-4.6",
      "role": "implement",
      "agent_paths": "{{agent_paths}}",
      "callback_url": "{{webhook_url}}",
      "timeout_minutes": 30
    },
    "review": {
      "repository": "{{repository}}",
      "branch": "{{branch}}",
      "agent_instructions": "Review Phase {{phase_id}} ({{phase_name}}). Check code quality, standards compliance, and correctness.",
      "model": "claude-opus-4.6",
      "role": "review",
      "pr_number": "{{pr_number}}",
      "agent_paths": "{{agent_paths}}",
      "callback_url": "{{webhook_url}}",
      "timeout_minutes": 15
    },
    "document": {
      "repository": "{{repository}}",
      "branch": "{{branch}}",
      "agent_instructions": "Create documentation for Phase {{phase_id}} ({{phase_name}}). Generate the phase summary.",
      "model": "claude-opus-4.6",
      "role": "implement",
      "agent_paths": "{{agent_paths}}",
      "callback_url": "{{webhook_url}}",
      "timeout_minutes": 20
    },
    "debug": {
      "repository": "{{repository}}",
      "branch": "{{branch}}",
      "agent_instructions": "",
      "model": "claude-opus-4.6",
      "role": "implement",
      "agent_paths": "{{agent_paths}}",
      "callback_url": "{{webhook_url}}",
      "timeout_minutes": 30
    }
  }
}
```

- **Purpose**: Stores the active executor configuration and payload templates for all five action types.
- **Key Relationships**: Referenced by project actions during payload resolution.

### Data Flow: Execute Action Item Dispatch

1. User clicks an Execute Action item in the left panel
2. UI calls Action Generator to retrieve the action's resolved payload
3. Payload Resolver applies `{{variable}}` interpolation against the context map:
   - `{{repository}}` → project's GitHub repo (e.g., `owner/repo-name`)
   - `{{branch}}` → `main` (or configured branch)
   - `{{phase_id}}` → phase number from phase-progress.json
   - `{{phase_name}}` → phase name from phase-progress.json
   - `{{component_id}}` → component ID (e.g., `1.1`) — Implement type only
   - `{{component_name}}` → component name — Implement type only
   - `{{component_breakdown_doc}}` → path to component breakdown doc
   - `{{agent_paths}}` → JSON array of discovered agent file paths
   - `{{webhook_url}}` → configured webhook URL from executor config
   - `{{pr_number}}` → manually entered PR number (Review type)
4. Executor Module sends the resolved payload to the configured API endpoint
5. API response (status code, message, run_id) is displayed in the right panel (top)
6. User clicks Refresh to poll for webhook callback data
7. Webhook data (status code, payload message) is displayed in the right panel (bottom)

## API Design

### Internal API: Webhook Reception

#### `POST /webhook/callback`

- **Purpose**: Receives callback payloads from the executor (e.g., Autopilot) after an agent run completes
- **Authentication**: None required (local-only; ngrok URL is the access control)
- **Request Body**:
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "result": "...",
  "completed_at": "2026-03-14T10:30:00Z"
}
```
- **Response**: `200 OK`
```json
{
  "received": true
}
```
- **Behaviour**: Stores the callback payload in memory keyed by `run_id`

#### `GET /webhook/poll/{run_id}`

- **Purpose**: Internal endpoint for the UI to check if webhook data has arrived for a given run
- **Authentication**: None (local only)
- **Response**: `200 OK`
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "result": "...",
  "completed_at": "2026-03-14T10:30:00Z"
}
```
- **Response if not yet received**: `404 Not Found`
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending"
}
```

### External API: Executor Dispatch (Autopilot — Default)

#### `POST {executor_api_endpoint}` (e.g., `http://localhost:8000/agent/run`)

- **Purpose**: Dispatches an Execute Action item to the configured executor
- **Authentication**: `X-API-Key` header with executor API key
- **Request Body**: Per sample payload structure:
```json
{
  "repository": "owner/repo-name",
  "branch": "main",
  "agent_instructions": "Implement Component 1.1...",
  "model": "claude-opus-4.6",
  "role": "implement",
  "agent_paths": [".github/agents/implement.agent.md"],
  "callback_url": "https://your-ngrok-url.ngrok-free.app/webhook/callback",
  "timeout_minutes": 30
}
```
- **Response**: `200 OK`
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "dispatched",
  "created_at": "2026-03-14T10:00:00Z"
}
```
- **Error Responses**: `400 Bad Request`, `401 Unauthorized`, `500 Internal Server Error`

## Security Design

### Authentication & Authorization

- **Strategy**: No application-level auth — single-user local app. Access is controlled by network (localhost / local network only).
- **GitHub Token**: OAuth personal access token entered via UI, stored in `.env/.env.local`, loaded at runtime, never logged.
- **Executor API Key**: Entered via UI, stored in `.env/.env.local`, sent as `X-API-Key` header to executor only.
- **LLM API Key (optional)**: Entered via UI, stored in `.env/.env.local`, sent to OpenAI API only.

### Data Protection

- **Encryption at Rest**: Not required — local filesystem, user's device encryption applies.
- **Encryption in Transit**: HTTPS for all external API calls (GitHub, executor, OpenAI). Webhook callback URL uses ngrok HTTPS.
- **Secrets Management**: `.env/.env.local` file, gitignored via `.gitignore`. Secrets loaded into memory via `python-dotenv`, never written to project JSON or logs.
- **PII Handling**: No PII stored — only GitHub tokens and API keys.

### Security Controls

- **Input Validation**: Validate all user inputs (repo format, URL format, JSON structure) at the UI boundary before processing.
- **No Secret Logging**: Secrets are never logged, printed, or included in error messages. Only sent to their intended API endpoint.
- **Gitignore Enforcement**: `.env/` directory and `~/.dispatch/` data directory patterns are in `.gitignore`.

## Performance & Scalability

### Performance Targets

- **UI interactions**: Instant (< 100ms) — NiceGUI handles this natively via WebSocket.
- **Executor dispatch**: < 1 second from click to API call sent (per brief requirement).
- **Payload resolution**: Instant — simple string interpolation, no LLM call in the default path.
- **LLM-assisted generation (optional)**: < 5 seconds (per brief requirement), async call with loading indicator.
- **Webhook polling**: UI refresh button triggers immediate poll; no continuous background polling needed.

### Scaling Strategy

- **Not required**: Single user, single process. NiceGUI + Uvicorn handles one user efficiently.
- **Multiple projects**: Supported by file-based project storage — each project is an independent JSON file.

## Resilience & Reliability

### Availability Target

- **SLA**: None — local app, availability equals user's machine uptime.
- **Data Durability**: JSON files on local filesystem (OneDrive-synced for backup).

### Error Handling

- **Executor unreachable**: Display clear error in the right panel with status code and message. Do not block UI.
- **GitHub API failure**: Show error during project linking/scanning. Allow retry.
- **Webhook not received**: Refresh button shows "No webhook data received yet" message. User can re-dispatch or wait.
- **Invalid phase-progress.json**: Block project creation with descriptive validation error.

### Monitoring & Alerting

- **Logging**: Python `logging` module with structured JSON output to console. Log levels: INFO for dispatch events, WARNING for failed calls, ERROR for exceptions.
- **No external monitoring**: Local app — console logs are sufficient.

## Integration Points

### External System: GitHub REST API

- **Purpose**: Scan target repo for `docs/phase-progress.json` and agent files during project linking
- **Integration Type**: REST API via httpx
- **Authentication**: OAuth token in `Authorization: Bearer {token}` header
- **Endpoints Used**:
  - `GET /repos/{owner}/{repo}/contents/{path}` — check file existence and read contents
  - `GET /repos/{owner}/{repo}/contents/.claude/agents/` — list agent files
  - `GET /repos/{owner}/{repo}/contents/.github/agents/` — list agent files
- **Error Handling**: Retry once on 5xx; surface 404 (file not found) as user-facing error
- **Rate Limits**: 5,000 requests/hour for authenticated users — far exceeds usage
- **Dependencies**: If GitHub is down, project linking fails but existing projects still work

### External System: Autopilot Executor (Default)

- **Purpose**: Dispatch agent run requests for Execute Action items
- **Integration Type**: REST API via httpx
- **Authentication**: `X-API-Key` header
- **Endpoint**: `POST /agent/run` — as documented in autopilot runbook
- **Error Handling**: Display full error response in UI. No retry — user can re-click to retry.
- **Rate Limits**: None documented
- **Dependencies**: If Autopilot is down, dispatches fail but app remains fully functional for configuration and payload editing

### External System: Webhook Callback (via ngrok)

- **Purpose**: Receive agent run results from the executor
- **Integration Type**: Inbound webhook POST to local server
- **Authentication**: None (ngrok URL acts as access control)
- **Error Handling**: Store whatever is received; UI polls and displays
- **Dependencies**: Requires ngrok tunnel running for external executor to reach local server. If ngrok is down, webhooks won't arrive but app functions normally.

### External System: OpenAI API (Optional)

- **Purpose**: LLM-assisted payload generation for Execute Action items
- **Integration Type**: REST API via `openai` Python SDK
- **Authentication**: API key in SDK configuration
- **Error Handling**: If LLM call fails, fall back to standard string interpolation. Show error notification.
- **Rate Limits**: Per OpenAI account limits
- **Dependencies**: Optional — app fully functional without it

## Development & Deployment

### Project Structure

```
dispatch/
├── .env/
│   ├── .env.local          # Secrets (gitignored)
│   ├── .env.example         # Template for required env vars
│   └── .env.test            # Test credentials
├── .github/
│   └── instructions/
│       └── copilot.instructions.md
├── app/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py              # NiceGUI app entry point, page definitions
│   │   ├── ui/
│   │   │   ├── __init__.py
│   │   │   ├── initial_screen.py    # Load/Link/Configure options
│   │   │   ├── main_screen.py       # Split-panel project screen
│   │   │   ├── executor_config.py   # Executor configuration UI
│   │   │   ├── secrets_screen.py    # Secrets management UI
│   │   │   └── components.py        # Reusable UI components
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── project_service.py       # GitHub scanning, project CRUD
│   │   │   ├── action_generator.py      # Action item generation from phase data
│   │   │   ├── payload_resolver.py      # {{variable}} string interpolation
│   │   │   ├── executor.py             # Executor protocol + Autopilot implementation
│   │   │   ├── webhook_service.py      # Webhook receipt + polling
│   │   │   └── llm_service.py          # Optional OpenAI integration
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── project.py         # Project, Phase, Component, Action dataclasses
│   │   │   ├── executor.py        # ExecutorConfig, ExecutorResponse models
│   │   │   └── payload.py         # PayloadTemplate, ResolvedPayload models
│   │   └── config/
│   │       ├── __init__.py
│   │       └── settings.py        # App settings, env loading, data dir paths
│   ├── config/
│   │   └── defaults.yaml           # Default executor templates, app defaults
│   └── docs/
├── docs/
│   ├── brief.md
│   ├── requirements.md
│   ├── solution-design.md
│   ├── autopilot-runbook.md
│   └── sample-payload.json
├── tests/
│   ├── conftest.py
│   ├── test_action_generator.py
│   ├── test_payload_resolver.py
│   ├── test_project_service.py
│   └── test_executor.py
├── scripts/
│   └── evals.py
├── pyproject.toml
├── .gitignore
├── LICENSE
└── README.md
```

### Testing Scenarios

1. **Link project and dispatch action**: User opens app → configures executor (Autopilot endpoint, API key, webhook URL) → configures action type defaults → links a new GitHub project → app scans repo and finds `docs/phase-progress.json` → generates action items → user clicks an Implement action → payload is dispatched to executor → response code and message display in right panel → user clicks Refresh → webhook data displays in lower right panel → user marks action complete.

2. **Load existing project and run full phase**: User opens app → loads a previously saved project → left panel shows all actions → user clicks through Implement actions for Phase 1 components sequentially → clicks Test action → clicks Review action → clicks Document action → all responses visible → all actions marked complete.

3. **Insert debug action and dispatch**: User opens app → loads project → right-clicks or triggers "Add Debug" at a specific position in Phase 1 → debug action appears with default debug payload template → user edits the agent instructions in the payload → dispatches → reviews response → marks complete.

### Development Workflow

- **Version Control**: GitHub flow (main + feature branches)
- **Branching Strategy**: `main` (stable), `feature/*` branches
- **Code Review**: Required via PR (AI agent or self-review)
- **Testing Requirements**: pytest, 30% coverage target, evals pass

### CI/CD Pipeline

- **Build**: Black → isort → type check → pytest → evals.py
- **Test Stages**: Unit tests → integration tests (mocked HTTP)
- **Deployment**: N/A — local app, `pip install -e .` + `python -m app.src.main`
- **Rollback Strategy**: Git revert on main

### Environment Strategy

- **Development**: `source .venv/bin/activate && python -m app.src.main` — auto-reload via NiceGUI
- **Production**: Same as development — it's a local app. `pip install .` for clean install.
- **Data Directory**: `~/.dispatch/` by default, overridable via `DISPATCH_DATA_DIR` env var. User symlinks or places this within OneDrive for cross-device data sync.

## Risks & Technical Debt

### Technology Risks

- **NiceGUI maturity**: NiceGUI is actively maintained (2.x) with a growing community but is less established than React/Angular. Mitigation: the UI is simple enough that any framework limitations are unlikely to be hit. Fallback: replace with raw FastAPI + Jinja2 templates if needed.
- **iPhone browser compatibility**: NiceGUI renders Quasar/Vue components which are mobile-responsive. Mitigation: test on Safari iOS early in development. The split-panel may need to stack vertically on small screens.
- **OneDrive sync conflicts**: Concurrent access from two devices could corrupt JSON files. Mitigation: single-device-at-a-time usage (documented), atomic file writes.

## Cost Estimation

### Infrastructure Costs (Monthly)

- **Compute**: $0 (local machine)
- **Database**: $0 (JSON files)
- **Storage**: $0 (local filesystem)
- **Networking**: $0 (ngrok free tier for webhook)
- **Third-party APIs**: $0 base (OpenAI optional — pay-per-use if LLM generation used)
- **Total**: $0 per month at baseline

### Scaling Costs

- N/A — single user, local-only. No scaling costs.

## Assumptions & Decisions

### Key Assumptions

- The user runs the app on macOS and accesses from iPhone via the same local network (or ngrok if remote)
- `docs/phase-progress.json` is always at a fixed path in the target repository
- The Autopilot executor API conforms to the payload structure in `docs/sample-payload.json`
- ngrok (or similar tunnelling tool) is running when webhook callbacks are needed from external executors
- OneDrive sync is configured on the macOS machine for the data directory

### Design Decisions & Rationale

1. **NiceGUI over Electron/Reflex/Streamlit**: Pure Python, built on FastAPI, responsive, zero build pipeline. Ideal for a single-user local app with a split-panel layout.
   - *Alternatives considered*: Reflex (heavier, compiles to Next.js), Streamlit (limited layout control, stateful re-runs), Electron (requires JavaScript, heavier), FastAPI + raw HTML (more manual work)
   - *Tradeoffs*: Less ecosystem/community than React-based solutions, but the simplicity gain for a local single-user app far outweighs this

2. **JSON file storage over SQLite**: Simpler to implement, human-readable, OneDrive-syncable without database locking issues.
   - *Alternatives considered*: SQLite (better querying, but sync-unfriendly), TinyDB (marginal benefit over raw JSON)
   - *Tradeoffs*: No complex queries possible, but the data model is simple enough that this isn't needed

3. **Polling for webhook data over WebSocket push**: User clicks Refresh to check for webhook results. Simpler than maintaining a persistent WebSocket or SSE connection to the webhook receiver.
   - *Alternatives considered*: NiceGUI timer-based auto-refresh, Server-Sent Events
   - *Tradeoffs*: User must click Refresh, but this matches the brief's explicit mention of a refresh button and keeps the implementation simple

4. **Simple string interpolation over Jinja2/Moustache**: `{{variable}}` placeholders replaced via `str.replace()` or `string.Template`. No conditional logic or loops in templates.
   - *Alternatives considered*: Jinja2 (powerful but overkill), Python f-strings (not user-editable)
   - *Tradeoffs*: Cannot do conditional payload fields — but the brief calls for simple interpolation, and users can manually edit payloads for edge cases

5. **httpx over PyGithub for GitHub API**: Only a few endpoints needed (contents listing, file reading). A full SDK adds unnecessary dependency weight.
   - *Alternatives considered*: PyGithub (full-featured), `requests` (no async)
   - *Tradeoffs*: Must construct API calls manually, but there are only 2-3 endpoints to call

6. **`~/.dispatch/` data directory with OneDrive symlink**: Keeps app data separate from the repo. User symlinks or configures OneDrive to sync this path for cross-device access.
   - *Alternatives considered*: Store data inside the repo (would be committed), store in OneDrive directly (path varies)
   - *Tradeoffs*: Requires user to set up symlink or configure `DISPATCH_DATA_DIR` — documented in setup guide
