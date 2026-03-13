# Phase Plan: Dispatch

## Overview

Dispatch is built incrementally across 7 phases — from project bootstrap through to a fully tested, documented application. The first phase establishes the repository, tooling, and conventions. Phases 2–4 deliver a working MVP: a locally runnable NiceGUI application that can configure an executor, link a GitHub project, generate Execute Action items from `phase-progress.json`, dispatch them, and display results. Phases 5–7 add UI polish, optional LLM payload generation, end-to-end testing, and documentation.

## Summary

- **Number of Phases**: 7
- **Number of Components**: 40

---

## Phase 1: Project Bootstrap & Environment Setup

### Phase Overview

**Overview**: Establish the repository structure, development environment, CI/CD pipeline, and quality tooling. Define the end-to-end testing scenarios that will be validated at the end of each subsequent phase. All foundational conventions are locked in before any application code is written.

**Objective**: A clean, installable Python package with CI/CD running, quality tooling configured, and E2E testing scenarios documented.

**Dependencies**: GitHub repository must exist. Python 3.13+ and virtual environment available on the developer's machine.

### Phase Key Deliverables

- **Repository structure**: Complete folder layout per solution design, with `pyproject.toml` for editable install
- **CI/CD pipeline**: GitHub Actions workflow running Black, isort, pytest, and evals
- **E2E testing scenarios**: Documented scenarios that will drive validation throughout the project
- **Quality tooling**: `scripts/evals.py`, Black/isort config, pytest conftest skeleton

### Phase Components

- **Component 1.1**: Human — create GitHub repository, Python 3.13+ virtual environment, and initial `.env/.env.local` from template
- **Component 1.2**: Repository structure and `pyproject.toml` with editable install, `.gitignore`, `.env/.env.example` template, and complete folder layout per solution design
- **Component 1.3**: CI/CD pipeline — GitHub Actions workflow (Black, isort, pytest, evals), `scripts/evals.py` quality gate script, and `conftest.py` skeleton
- **Component 1.4**: End-to-end testing scenario definitions documented in `docs/`, plus `README.md` skeleton and phase validation

### Phase Acceptance Criteria

- [ ] `pip install -e .` succeeds in the virtual environment
- [ ] `pytest` runs (even with zero tests) and exits cleanly
- [ ] `black --check app/src/` and `isort --check-only app/src/` pass
- [ ] `python scripts/evals.py` passes
- [ ] GitHub Actions CI pipeline runs successfully on push
- [ ] `.env/.env.example` includes all required environment variable placeholders
- [ ] E2E testing scenarios are documented with clear pass/fail criteria

---

## Phase 2: Data Models, Configuration & Secrets Management

### Phase Overview

**Overview**: Build the complete data foundation — all Pydantic and dataclass models, application settings, configuration management, and secrets handling. This phase creates the layer that every subsequent service and UI component depends on.

**Objective**: All data models defined and tested. Configuration and secrets can be read, written, and persisted to the local filesystem. The `~/.dispatch/` data directory is created and managed.

**Dependencies**: Phase 1 complete (repository structure, package installable).

### Phase Key Deliverables

- **Data models**: Project, Phase, Component, Action, ExecutorConfig, ExecutorResponse, PayloadTemplate models in `app/src/models/`
- **Settings module**: `app/src/config/settings.py` with environment loading and data directory management
- **Config & Secrets manager**: Service to read/write executor config, action type defaults, and secrets
- **Default configuration**: YAML defaults for Autopilot executor and all five action type templates

### Phase Components

- **Component 2.1**: Core data models — Project, Phase, Component, Action dataclasses and ExecutorConfig, ExecutorResponse, ActionTypeDefaults Pydantic models in `app/src/models/`
- **Component 2.2**: Application settings module — `DISPATCH_DATA_DIR` env var support, `.env/.env.local` loading via python-dotenv, data directory structure creation (`~/.dispatch/projects/`, `~/.dispatch/config/`)
- **Component 2.3**: Config & Secrets manager service — read/write secrets to `.env/.env.local`, read/write executor config and action type defaults as JSON, enforce gitignore for `.env/`
- **Component 2.4**: Default executor configuration — `app/config/defaults.yaml` with Autopilot defaults and all five action type payload templates (implement, test, review, document, debug)
- **Component 2.5**: Unit tests for models, settings, and config manager; verify data directory operations; E2E scenario validation; update implementation context

### Phase Acceptance Criteria

- [ ] All data models instantiate correctly with valid data and reject invalid data
- [ ] `Settings` loads `DISPATCH_DATA_DIR` from environment with fallback to `~/.dispatch/`
- [ ] Config manager reads/writes executor config JSON to the data directory
- [ ] Config manager reads/writes action type default templates to the data directory
- [ ] Secrets manager writes to `.env/.env.local` and reads them back without exposing values in logs
- [ ] Default Autopilot executor config loads correctly when no user config exists
- [ ] Data directory `~/.dispatch/projects/` and `~/.dispatch/config/` are created on first run
- [ ] Unit tests pass with ≥ 30% coverage on new code

---

## Phase 3: Core Backend Services

### Phase Overview

**Overview**: Implement all backend service logic — GitHub API integration, project management (link/save/load), action generation from `phase-progress.json`, payload variable resolution, executor dispatch (with modular protocol), and webhook handling. After this phase, the complete business logic is testable independently from the UI.

**Objective**: All services operational and independently testable. A project can be linked via GitHub API, actions generated, payloads resolved, dispatched to an executor, and webhook responses stored — all via service-layer calls.

**Dependencies**: Phase 2 complete (data models, config manager, settings).

### Phase Key Deliverables

- **GitHub API client**: httpx-based client for repo contents and file reading
- **Project service**: Link new project (scan repo), save/load projects, list saved projects
- **Action generator**: Derive ordered Execute Action items from phase-progress data
- **Payload resolver**: `{{variable}}` interpolation against project context
- **Executor module**: Protocol definition plus Autopilot implementation
- **Webhook service**: In-memory store for callback data, keyed by `run_id`

### Phase Components

- **Component 3.1**: GitHub API client — httpx-based module for authenticated requests, `GET /repos/{owner}/{repo}/contents/{path}` for file existence/contents, directory listing, base64 content decoding
- **Component 3.2**: Project service — linking and scanning — validate repo format, scan for `docs/phase-progress.json`, parse and validate its structure, scan `.claude/agents/` and `.github/agents/` for agent files, generate project config with UUID
- **Component 3.3**: Project service — CRUD and persistence — save project to `~/.dispatch/projects/{project-id}.json`, load project from JSON, list all saved projects, delete project
- **Component 3.4**: Action generator service — generate actions from phase-progress data (Implement per Component, then Test, Review, Document per Phase), support Debug action insertion at any position, assign UUIDs to actions
- **Component 3.5**: Payload resolver service — parse `{{variable}}` placeholders, build context map from project data (repository, branch, phase_id, phase_name, component_id, component_name, component_breakdown_doc, agent_paths, webhook_url, pr_number), resolve all variables in payload templates
- **Component 3.6**: Executor protocol and Autopilot implementation — define `Executor` Protocol with `dispatch(payload) -> ExecutorResponse`, implement `AutopilotExecutor` (POST to API with `X-API-Key` header), parse response for status_code, message, run_id
- **Component 3.7**: Webhook service — in-memory store keyed by `run_id`, store webhook callback data, retrieve by `run_id`, clear stale entries
- **Component 3.8**: Unit tests for all services (mocked httpx for GitHub and executor), tests for action generator ordering, payload resolver variable coverage, E2E scenario validation, update implementation context

### Phase Acceptance Criteria

- [ ] GitHub client authenticates and retrieves file contents from a target repo
- [ ] Project service scans a repo, finds `docs/phase-progress.json`, and parses it correctly
- [ ] Project service blocks with a descriptive error if `docs/phase-progress.json` is not found
- [ ] Agent files are discovered from `.claude/agents/` and `.github/agents/` directories
- [ ] Projects can be saved, loaded, listed, and deleted from the data directory
- [ ] Action generator produces correct ordering: Implement per component → Test → Review → Document per phase
- [ ] Debug actions can be inserted at any position within a phase's action list
- [ ] Payload resolver correctly replaces all `{{variable}}` placeholders with concrete values
- [ ] Executor dispatches a payload via HTTP POST and returns a structured response
- [ ] Webhook service stores and retrieves data by `run_id`
- [ ] Unit tests pass with ≥ 30% coverage on new code

---

## Phase 4: MVP UI & End-to-End Integration

### Phase Overview

**Overview**: Build the complete NiceGUI web application — all screens, navigation, and the main dispatch workflow. This phase integrates all backend services into the UI to deliver a fully working MVP. After this phase, the application can be launched locally and used end-to-end: configure an executor, link a GitHub project, view generated actions, dispatch them, see responses, and mark them complete.

**Objective**: A locally runnable NiceGUI application with all screens functional: initial screen, executor configuration, action type defaults, secrets management, link/load project, and the main split-panel dispatch screen.

**Dependencies**: Phase 3 complete (all backend services operational).

### Phase Key Deliverables

- **NiceGUI application**: Entry point with Uvicorn, page routing, webhook FastAPI endpoint
- **Initial screen**: Load Project, Link New Project, Configure Executor with config gatekeeping
- **Configuration screens**: Executor config, action type defaults, secrets management
- **Project screens**: Link new project (with GitHub scanning), load saved project
- **Main screen**: Split-panel layout with action list, dispatch, response display, webhook results, refresh, and mark complete

### Phase Components

- **Component 4.1**: NiceGUI app entry point and routing — `app/src/main.py` with Uvicorn startup, page route definitions for all screens, webhook FastAPI endpoint registration (`POST /webhook/callback`, `GET /webhook/poll/{run_id}`)
- **Component 4.2**: Initial screen — `app/src/ui/initial_screen.py` with Load Project, Link New Project, Configure Executor buttons; config gatekeeping (disable project buttons until executor and action type defaults are configured)
- **Component 4.3**: Executor configuration screen — `app/src/ui/executor_config.py` with form fields for executor name, API endpoint URL, API key env var, webhook URL; save to executor config JSON; load existing config; input validation
- **Component 4.4**: Action type defaults and secrets screens — action type defaults editor with payload template fields for all five types and variable placeholder hints; secrets screen for entering/updating GitHub token, Autopilot API key, LLM key; save secrets to `.env/.env.local`
- **Component 4.5**: Link New Project screen — `app/src/ui/link_project.py` with form for GitHub repo (owner/repo) and GitHub token; trigger repo scan with progress indication; display results (phase-progress found, agent files found); error display if `phase-progress.json` not found; navigate to main screen on success
- **Component 4.6**: Load Project screen — list saved projects from data directory; click to load and navigate to main screen; handle empty state (no saved projects)
- **Component 4.7**: Main screen layout and action list — `app/src/ui/main_screen.py` with project header (name + Save button), split-panel layout (left/right), left panel with scrollable list of Execute Action items showing phase, component (for Implement), type, and status; click action to dispatch payload to executor
- **Component 4.8**: Main screen response display and controls — right panel top section for API response code and message, right panel bottom section for webhook response code and payload message (visible only when webhook URL configured), refresh button to poll for webhook data, mark complete button on each action item
- **Component 4.9**: Debug action insertion and payload editing — insert Debug action at any position in a phase's action list via UI control, payload editing dialog to view/edit resolved payload before dispatch, save edited payload back to action
- **Component 4.10**: Integration testing and phase validation — full workflow integration test (mocked APIs), verify app launches and all screens render, E2E scenario validation, update implementation context and agent runbook

### Phase Acceptance Criteria

- [ ] `python -m app.src.main` launches the NiceGUI app and serves the initial screen
- [ ] Executor configuration can be saved and persisted via the UI
- [ ] Action type default payload templates can be configured for all five types
- [ ] Secrets can be entered and saved to `.env/.env.local` via the UI
- [ ] Project buttons are disabled until executor and action type defaults are configured
- [ ] A new project can be linked: enter repo/token → scan succeeds → actions generated → main screen displays
- [ ] Saved projects appear in the Load Project list and can be loaded
- [ ] Main screen shows all Execute Action items in correct order per phase
- [ ] Clicking an action dispatches the resolved payload and displays the API response
- [ ] Webhook responses display in the lower right panel when webhook URL is configured
- [ ] Refresh button polls for and displays new webhook data
- [ ] Actions can be marked as completed
- [ ] Debug actions can be inserted at any position in a phase
- [ ] Individual action payloads can be edited before dispatch
- [ ] Project can be saved from the main screen

---

## Phase 5: UI Enhancements & Workflow Polish

### Phase Overview

**Overview**: Refine the user experience with improved navigation flow, error handling, mobile-responsive layouts for iPhone Safari, and workflow quality-of-life features. This phase transforms the functional MVP into a polished, pleasant-to-use application.

**Objective**: Smooth navigation, clear error feedback, responsive layouts for both macOS desktop and iPhone Safari, and visual status indicators that make the workflow intuitive.

**Dependencies**: Phase 4 complete (all UI screens functional).

### Phase Key Deliverables

- **Navigation polish**: Smooth screen transitions, back navigation, loading indicators
- **Error handling**: Toast notifications, inline validation, descriptive API error surfacing
- **Mobile responsiveness**: iPhone Safari compatible layouts, stacked panels on small screens
- **Workflow refinements**: Status indicator colours, phase grouping, confirmation dialogs

### Phase Components

- **Component 5.1**: Navigation flow and state management — smooth transitions between screens, back navigation, in-memory app state management (current project, config status), loading indicators for async operations (GitHub scanning, executor dispatch)
- **Component 5.2**: Error handling and user feedback — toast notifications for success/error events, inline error messages for form validation, GitHub API error surfacing (auth failed, repo not found, file missing), executor dispatch error display with actionable context
- **Component 5.3**: Mobile responsiveness — test and adjust layouts for iPhone Safari, split panel stacks vertically on small screens, touch-friendly button sizes and spacing, responsive typography and Quasar breakpoints
- **Component 5.4**: Workflow quality-of-life — phase grouping/filtering in the action list, colour-coded status indicators (not-started, dispatched, completed), confirmation for re-dispatch of already-dispatched actions, clear visual hierarchy for action phases
- **Component 5.5**: Testing and phase validation — UI interaction tests, responsive layout verification on multiple viewport sizes, E2E scenario validation, update implementation context

### Phase Acceptance Criteria

- [ ] Navigation between all screens is smooth with no broken routes
- [ ] Loading indicators display during GitHub scanning and executor dispatch
- [ ] Errors from GitHub API and executor API are surfaced with clear, actionable messages
- [ ] Toast notifications confirm successful operations (save, dispatch, mark complete)
- [ ] UI is fully usable on iPhone Safari (tested at 375px viewport width)
- [ ] Split panel stacks vertically on screens narrower than 768px
- [ ] Action items display colour-coded status indicators
- [ ] Phase grouping visually organises actions in the left panel

---

## Phase 6: LLM-Assisted Payload Generation

### Phase Overview

**Overview**: Integrate optional OpenAI LLM support to intelligently populate Execute Action item payloads from project context. When enabled, the LLM interprets phase data, component details, and agent files to generate context-aware payload field values — replacing simple string interpolation with richer, more accurate instructions. Falls back gracefully to standard interpolation if the LLM call fails or is not configured.

**Objective**: Users can optionally enable LLM-assisted payload generation per executor config. The LLM generates payload content from project context, with full manual override capability.

**Dependencies**: Phase 4 complete (working MVP with payload editing). OpenAI API key available in secrets.

### Phase Key Deliverables

- **LLM service**: OpenAI SDK integration with prompt construction and response parsing
- **Payload generation logic**: Context-aware prompt building from phase data, component details, and agent files
- **UI integration**: Toggle for LLM generation, loading indicator, review-before-dispatch flow
- **Fallback handling**: Graceful degradation to standard string interpolation on failure

### Phase Components

- **Component 6.1**: OpenAI SDK integration — `app/src/services/llm_service.py` with client initialisation from secrets, prompt template for payload generation, error handling with fallback to standard interpolation, timeout handling
- **Component 6.2**: LLM payload generation logic — context prompt construction from phase data, component details, agent file contents, and executor requirements; call OpenAI API to generate payload field values; parse and validate LLM response; merge generated values into payload template
- **Component 6.3**: UI integration — toggle in executor config for "Use LLM for payload generation", loading indicator during LLM call (< 5 seconds target), show generated payload for review before dispatch, manual edit capability after LLM generation
- **Component 6.4**: Testing and phase validation — unit tests for LLM service (mocked OpenAI SDK), integration test for LLM generation → payload resolution flow, fallback test for LLM failure → standard interpolation, E2E scenario validation, update implementation context

### Phase Acceptance Criteria

- [ ] LLM toggle is available in executor config and persisted
- [ ] When enabled, LLM generates payload content from project context within 5 seconds
- [ ] Generated payloads are displayed for review before dispatch
- [ ] Users can manually edit LLM-generated payloads
- [ ] If OpenAI API call fails, system falls back to standard `{{variable}}` interpolation with a warning
- [ ] If no OpenAI API key is configured, LLM toggle is disabled with explanatory text
- [ ] Unit tests pass with mocked OpenAI SDK

---

## Phase 7: End-to-End Testing, Documentation & Release

### Phase Overview

**Overview**: Execute all defined end-to-end testing scenarios against the real application (with live and mocked executors), verify cross-device accessibility, finalize all documentation, and prepare the application for open-source release.

**Objective**: All E2E testing scenarios pass, documentation is complete (README, runbook, architecture), cross-device access verified on macOS and iPhone, and the repository is ready for public use.

**Dependencies**: Phase 5 complete (polished UI). Phase 6 complete if LLM feature is included.

### Phase Key Deliverables

- **E2E test suite**: Automated tests for all defined scenarios, plus human-gated live executor tests
- **Cross-device verification**: Confirmed working on macOS desktop and iPhone Safari
- **Documentation**: Complete README, agent runbook, setup guide, architecture notes
- **Release readiness**: CI green, no secrets in repo, gitignore verified, evals passing

### Phase Components

- **Component 7.1**: End-to-end test suite — automated E2E tests for: configure executor → link project → generate actions → dispatch → webhook; load project → dispatch from saved state; debug action insertion → dispatch; human-gated tests for live Autopilot executor (using `--autopilot-confirm` pytest flag)
- **Component 7.2**: Cross-device verification (Human + AI) — test on macOS desktop browser (Chrome/Safari), test on iPhone Safari via local network, verify OneDrive data directory sync between devices, document and fix any device-specific issues
- **Component 7.3**: Documentation — complete `README.md` with setup instructions, usage guide, configuration reference; agent runbook for AI agent-driven application running and E2E test execution; update autopilot integration notes; architecture decision records for key decisions
- **Component 7.4**: Final quality checks and release preparation — run full test suite (pytest, coverage report, evals), verify CI pipeline green, security audit (no secrets in repo, `.gitignore` comprehensive), verify `pip install -e .` clean install works, final implementation context and phase summary update

### Phase Acceptance Criteria

- [ ] All automated E2E tests pass
- [ ] Human-gated Autopilot executor test passes when live executor is available
- [ ] Application is fully usable on macOS desktop browser
- [ ] Application is fully usable on iPhone Safari via same local network
- [ ] OneDrive data directory sync works across devices
- [ ] README contains complete setup, usage, and configuration instructions
- [ ] Agent runbook enables AI agents to run the app and execute E2E tests
- [ ] `pytest -q --cov=app/src --cov-report=term-missing` achieves ≥ 30% coverage
- [ ] `python scripts/evals.py` passes with no violations
- [ ] CI pipeline is green with all checks passing
- [ ] No secrets, tokens, or API keys exist anywhere in the repository
- [ ] `.gitignore` covers `.env/`, `~/.dispatch/`, `.venv/`, `__pycache__/`

---

## Cross-Cutting Concerns

### Testing Strategy

- **E2E Testing Scenarios**:
  1. **Configure & dispatch**: Configure executor (Autopilot endpoint, API key, webhook URL) → configure action type defaults → link a new GitHub project → app scans repo and finds `docs/phase-progress.json` → generates action items → click an Implement action → payload dispatched → response displays → click Refresh → webhook data displays → mark action complete
  2. **Load & run full phase**: Load a previously saved project → left panel shows all actions → click through all Implement actions for Phase 1 → click Test → click Review → click Document → all responses visible → all actions marked complete
  3. **Debug action workflow**: Load project → insert Debug action at a specific position in Phase 1 → edit the debug payload's agent instructions → dispatch → review response → mark complete
  4. **LLM payload generation**: Enable LLM toggle in executor config → click an action → LLM generates payload → review generated payload → edit if needed → dispatch → verify response
  5. **Cross-device access**: Launch app on macOS → access from iPhone Safari on same network → verify all screens render and interactions work → verify data persists across devices via OneDrive
- **Unit Testing**: pytest with fixtures, targeting ≥ 30% coverage. Focus on services (action generator, payload resolver, executor, project service)
- **Integration Testing**: Mocked httpx for GitHub API and executor API calls. Full-chain tests from project linking through action generation to dispatch
- **Performance Testing**: Verify UI interactions < 100ms, executor dispatch < 1 second, LLM generation < 5 seconds
- **Security Testing**: Verify secrets never appear in logs, JSON files, or git history. Validate `.gitignore` coverage

### Documentation Requirements

- **Developer Context Documentation**: Phase Component Overview (`implementation-context-phase-X.md`), Component Overview (`phase-X-component-X-Y-overview.md`)
- **Agent Runbook**: Runbook for AI agent application running, execution of end-to-end testing scenarios
- **Code Documentation**: Google-style docstrings on all public functions, inline comments where logic is non-obvious
- **API Documentation**: Internal webhook API documented in solution design (no external OpenAPI needed — local-only app)
- **Architecture Decision Records**: Key decisions documented (NiceGUI choice, JSON over SQLite, polling over WebSocket, simple interpolation over Jinja2)
- **User Documentation**: README with setup guide, usage walkthrough, configuration reference
- **Deployment Documentation**: Local setup instructions, OneDrive sync configuration, ngrok setup for webhooks

### Quality Gates

- **Code Review**: All PRs require AI agent or self-review before merge
- **Automated Tests**: Must pass before merge (`pytest -q --cov=app/src`)
- **Code Coverage**: Minimum 30% coverage on `app/src/`
- **Performance**: UI < 100ms, dispatch < 1s, LLM < 5s (per brief NFRs)
- **Security Scan**: No secrets in repo; Gitleaks and CodeQL configured
- **Evals**: `python scripts/evals.py` must pass (docstrings present, no TODO/FIXME)

### DevOps & Deployment

- **CI/CD Pipeline**: GitHub Actions — Black, isort, pytest, evals on push/PR
- **Environment Promotion**: Local development only — no staging/production environments
- **Rollback Strategy**: Git revert on `main` branch
- **Monitoring**: Python `logging` module with structured JSON output to console
- **Alerting**: N/A — local-only application

## Dependencies & External Factors

### External Dependencies

- **GitHub REST API**: Required for project linking (repo scanning for `phase-progress.json` and agent files). If GitHub is down, linking fails but existing projects work. Rate limit: 5,000 req/hr authenticated
- **Autopilot Executor API**: Required for dispatching Execute Action items. If unavailable, dispatches fail but app remains functional for configuration and payload editing
- **ngrok**: Required for receiving webhook callbacks from external executors. If unavailable, webhooks won't arrive but polling fallback and manual refresh still work
- **OpenAI API** (optional): Required only for LLM-assisted payload generation. If unavailable, standard string interpolation is used
- **OneDrive**: Required for cross-device data sync. If unavailable, app works on a single device; data portability is affected

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy | Owner |
|------|--------|------------|---------------------|-------|
| NiceGUI limitations for complex UI patterns | Medium | Low | UI is simple (split panels, forms, lists); well within NiceGUI capabilities. Fallback: raw FastAPI + Jinja2 | AI Agent |
| iPhone Safari rendering issues with Quasar components | Medium | Medium | Test on Safari iOS early (Phase 5). Quasar is mobile-first; use responsive breakpoints | AI Agent |
| OneDrive sync conflicts with JSON files | Medium | Low | Atomic file writes, single-device-at-a-time usage (documented). No concurrent access expected | Human |
| Webhook not received (ngrok down, network issues) | Medium | Medium | Refresh button shows clear "no data" state. User can poll executor status API directly. Non-blocking UI | AI Agent |
| GitHub API rate limiting during heavy scanning | Low | Low | Cache scanned data locally in project config. Only re-scan on explicit user action | AI Agent |
| LLM generates inaccurate payload content | Medium | Medium | LLM is optional; generated payloads always shown for review before dispatch; manual editing always available | AI Agent |
| Executor API payload structure changes | Medium | Low | Modular executor config; templates are user-editable; payload structure is not hardcoded | Human |

## Change Management

### Scope Change Process

1. Identify change request
2. Document in amendment log

### Amendment Log

| Date | Phase/Component | Change | Reason | Impact |
|------|-----------------|--------|--------|--------|
| — | — | — | — | — |

## Approval

- [ ] Approved on: ___
