# Dispatch

Dispatch is a local-first Python web application that orchestrates AI agent execution against phased software project deliverables. It reads a project's phase plan (`phase-progress.json`) from a linked GitHub repository, generates sequenced action items for each component, and dispatches them to a configurable executor API — with a clean UI for managing projects, configuring executors, and monitoring agent run results. Built with NiceGUI, it runs as a local server on macOS and is accessible cross-device from any browser on the local network, including iPhone Safari.

## Features

- **GitHub project linking** — scan a repository for `phase-progress.json` and agent files, parse phase/component structure automatically
- **Action generation** — derive ordered action items (Implement, Test, Review, Merge, Document) from phase-progress data with per-component grouping
- **Modular executor dispatch** — send action payloads to any executor API conforming to the dispatch protocol; Autopilot is the default
- **Autopilot integration** — dispatches to the Autopilot orchestration service, which runs GitHub Copilot agents via GitHub Actions workflows
- **Webhook monitoring** — receive executor result callbacks at `/webhook/callback`, display response data in the UI with a refresh button
- **LLM-assisted payload generation** — optional OpenAI integration enriches `agent_instructions` with component-aware context; falls back gracefully to standard interpolation
- **Debug action insertion** — insert debug actions at any position within a phase for ad-hoc agent runs
- **PR number propagation** — when an implement action completes and returns a PR number, it automatically populates review and merge actions for the same component
- **Cross-device access** — Uvicorn binds to `0.0.0.0:8080`, accessible from any device on the local network
- **Local-first design** — all data stored as JSON files in a configurable directory; point to OneDrive for cross-device sync
- **Card-based UI** — colour-coded action cards grouped by component, circular progress indicators, status-coloured response panels

## Prerequisites

- **Python 3.13+** with `pip`
- **macOS** (primary development host)
- **GitHub personal access token** with `repo` scope for the target repository
- **Autopilot executor** (optional) — the Autopilot service for dispatching agent runs
- **ngrok** (optional) — for exposing a public webhook callback URL to the executor
- **OpenAI API key** (optional) — for LLM-assisted payload generation
- **OneDrive** (optional) — for cross-device data sync

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/sjmeehan9/dispatch.git
cd dispatch

# 2. Create and activate a virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 4. Configure environment variables
cp .env/.env.example .env/.env.local
# Edit .env/.env.local — fill in GITHUB_TOKEN and optionally AUTOPILOT_API_KEY, OPENAI_API_KEY

# 5. Launch the application
python -m app.src.main
```

Open your browser to `http://localhost:8080`.

## Remote Access (iPhone from Any Network)

Dispatch can be accessed from any network using a tunnel service. Because the app binds to `0.0.0.0:8080`, a tunnel that forwards to `localhost:8080` exposes the full UI.

### Using ngrok

```bash
ngrok http 8080
```

Use the ngrok HTTPS URL in Safari on iPhone. You can use the same URL base for executor callbacks by setting `AUTOPILOT_WEBHOOK_URL`.

### Security for Public Tunnels

When exposing Dispatch over a public tunnel, set an access token:

```bash
# .env/.env.local
DISPATCH_ACCESS_TOKEN=your-secret-token-here
```

When set, UI routes require authentication through `/login`.

Webhook callback endpoints remain open so external executors can deliver results:
- `POST /`
- `POST /webhook/callback`

Webhook polling is token-protected when remote auth is enabled and expects:

```text
Authorization: Bearer <DISPATCH_ACCESS_TOKEN>
```

### Connection Resilience

The app uses a 10-second reconnection timeout to better tolerate transient mobile network drops.

You can also disable auto-reload for more stable long-lived sessions:

```bash
# .env/.env.local
DISPATCH_RELOAD=false
```

## Configuration

### Executor Config

Configure the executor endpoint, API key, and webhook URL through the **Configure Executor** screen in the UI, or by editing the defaults in `app/config/defaults.yaml`.

| Setting | Description | Default |
|---------|-------------|---------|
| API Endpoint | Executor API URL for dispatch requests | `http://localhost:8000/agent/run` |
| API Key Env Var | Environment variable name holding the API key | `AUTOPILOT_API_KEY` |
| Webhook URL | Public URL for receiving async result callbacks | *(empty — optional)* |

When a webhook URL is configured, Dispatch receives executor result callbacks at `/webhook/callback`. If a root URL is provided (e.g., an ngrok URL without a path), Dispatch normalises it to append `/webhook/callback`.

### Action Type Defaults

Each action type (Implement, Test, Review, Merge, Document, Debug) has a configurable payload template. Templates use `{{variable}}` placeholders that are resolved at dispatch time:

| Variable | Description |
|----------|-------------|
| `{{repository}}` | Target repository in `owner/repo` format |
| `{{branch}}` | Target branch (typically `main`) |
| `{{phase_id}}` | Phase number |
| `{{phase_name}}` | Phase display name |
| `{{component_id}}` | Component identifier (Implement, Review, Merge actions) |
| `{{component_name}}` | Component display name (Implement, Review, Merge actions) |
| `{{component_breakdown_doc}}` | Path to the component breakdown document |
| `{{agent_paths}}` | Discovered agent file paths as a JSON array |
| `{{webhook_url}}` | Configured callback URL |
| `{{pr_number}}` | Pull request number (Review, Merge actions) |

Configure defaults through the **Action Type Defaults** screen in the UI.

### Secrets Management

Manage secrets through the **Manage Secrets** screen in the UI or by editing `.env/.env.local` directly. Never commit `.env/.env.local` to version control.

In GitHub Actions, store secrets in repository or `copilot` environment secrets. Use `TOKEN` for the GitHub token and map it to `GITHUB_TOKEN` at runtime.

### Data Directory

Project data is stored in the directory specified by `DISPATCH_DATA_DIR` (default: `~/.dispatch/`). To enable cross-device sync, point this to an OneDrive-synced folder:

```bash
DISPATCH_DATA_DIR=~/OneDrive/dispatch-data
```

## Usage

### First-Time Setup

1. **Configure Executor** — set the executor API endpoint, API key environment variable, and optional webhook URL
2. **Configure Action Type Defaults** — review and customise payload templates for each action type
3. **Manage Secrets** — enter your GitHub token and optionally your Autopilot API key and OpenAI API key

### Link a New Project

1. Navigate to **Link New Project**
2. Enter the target GitHub repository in `owner/repo` format
3. Dispatch scans the repository for `docs/phase-progress.json` (required) and agent files in `.claude/agents/` and `.github/agents/`
4. Action items are generated automatically — grouped by component with Implement → Review → Merge triplets, followed by phase-level Test and Document actions

### Dispatch Actions

1. From the main project screen, click any action card to dispatch its payload to the configured executor
2. The right panel displays the executor's response (status code and message)
3. If a webhook URL is configured, click **Refresh** to poll for the executor's result callback
4. The webhook response panel shows the full result payload with status-coloured headers

### Insert Debug Actions

Click the debug insertion button to add a Debug action at any position within a phase. Edit the debug action's payload (particularly `agent_instructions`) before dispatch.

### LLM Payload Generation

When enabled in the executor config and an OpenAI API key is configured:
1. The LLM generates enriched `agent_instructions` based on component context
2. Structural fields (repository, branch, model, callback_url) are always filled via standard interpolation
3. If the LLM is unavailable or fails, the system falls back silently to standard interpolation

### Save and Load Projects

- **Save Project** — persists the current project state (actions, progress) to the data directory
- **Load Project** — restores a previously saved project from the initial screen

## Development

### Running Tests

```bash
source .venv/bin/activate

# Full test suite with coverage
pytest -q --cov=app/src --cov-report=term-missing

# E2E tests (mocked services)
pytest tests/e2e/ -q -k "not requires_autopilot"

# E2E tests with live Autopilot (interactive)
pytest tests/e2e/ -q --autopilot-confirm
```

### Code Formatting

```bash
black --check app/src/ tests/
isort --check-only app/src/ tests/
```

### Quality Evals

```bash
python scripts/evals.py
```

Checks for missing docstrings and TODO/FIXME placeholders in production code.

### CI/CD

The GitHub Actions workflow runs on every push and pull request:
- Black and isort formatting checks
- Full pytest suite with coverage reporting
- Project evals (`scripts/evals.py`)

## Architecture

Dispatch is a single-process Python application built on NiceGUI (which wraps FastAPI, Quasar, and Vue):

- **UI Layer** — NiceGUI renders responsive screens; Quasar Material Design components handle desktop and mobile layouts
- **API Layer** — FastAPI routes (built into NiceGUI) handle webhook reception at `/webhook/callback`
- **Service Layer** — pure Python modules for project management, action generation, payload resolution, executor dispatch, and webhook storage
- **Data Layer** — JSON files in the local filesystem for project configs, executor settings, and action state

Key design choices are documented in [docs/architecture-decisions.md](docs/architecture-decisions.md).

### Project Structure

```
dispatch/
├── app/
│   ├── config/
│   │   └── defaults.yaml          # Default executor and action type templates
│   ├── docs/
│   │   ├── agent-runbook.md       # AI agent operational runbook
│   │   ├── executor-configuration-guide.md  # Executor setup guide
│   │   └── phase-progress-guide.md          # phase-progress.json reference
│   ├── src/
│   │   ├── main.py                # NiceGUI app entry point and webhook routes
│   │   ├── exceptions.py          # Custom exception hierarchy
│   │   ├── config/
│   │   │   ├── constants.py       # Application constants
│   │   │   └── settings.py        # Environment-aware settings (Pydantic)
│   │   ├── models/
│   │   │   ├── project.py         # Project, Phase, Action, ActionType models
│   │   │   ├── executor.py        # ExecutorConfig, ActionTypeDefaults models
│   │   │   └── payload.py         # Payload and LLM result models
│   │   ├── services/
│   │   │   ├── github_client.py   # GitHub REST API client (httpx)
│   │   │   ├── project_service.py # Project lifecycle management
│   │   │   ├── action_generator.py# Action derivation from phase-progress data
│   │   │   ├── payload_resolver.py# Template variable interpolation
│   │   │   ├── config_manager.py  # Executor and defaults persistence
│   │   │   ├── executor.py        # Executor protocol and Autopilot implementation
│   │   │   ├── webhook_service.py # In-memory webhook payload storage
│   │   │   ├── llm_service.py     # OpenAI LLM client wrapper
│   │   │   └── llm_payload_generator.py # LLM-assisted payload generation
│   │   ├── ui/
│   │   │   ├── initial_screen.py  # Landing page with navigation options
│   │   │   ├── executor_config.py # Executor configuration form
│   │   │   ├── action_type_defaults.py # Action type template editor
│   │   │   ├── secrets_screen.py  # Secrets management form
│   │   │   ├── link_project.py    # GitHub project linking flow
│   │   │   ├── load_project.py    # Saved project loading
│   │   │   ├── main_screen.py     # Main project view (actions + responses)
│   │   │   ├── components.py      # Shared UI components and helpers
│   │   │   └── state.py           # Application state container
│   │   └── static/
│   │       └── styles.css         # Custom CSS (card styles, animations)
├── tests/                         # pytest test suite
│   ├── e2e/                       # End-to-end service-layer tests
│   └── ...                        # Unit and integration tests
├── scripts/
│   └── evals.py                   # Quality evaluation script
├── .env/
│   ├── .env.example               # Environment variable template
│   └── .env.local                 # Local secrets (gitignored)
├── pyproject.toml                 # Package configuration
└── LICENSE                        # MIT License
```

## Documentation

### Application Guides (`app/docs/`)

- [Executor Configuration Guide](app/docs/executor-configuration-guide.md) — how to set up and configure an executor
- [Phase Progress JSON Guide](app/docs/phase-progress-guide.md) — required fields and structure of `phase-progress.json`
- [Agent Runbook](app/docs/agent-runbook.md) — for AI agents operating the application

## License

This project is licensed under the [MIT License](LICENSE).
