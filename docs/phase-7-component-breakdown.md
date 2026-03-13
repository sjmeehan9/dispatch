# Phase 7: End-to-End Testing, Documentation & Release

## Phase Overview

**Objective**: Execute all defined end-to-end testing scenarios against the real application (with live and mocked executors), verify cross-device accessibility, finalize all documentation, and prepare the application for open-source release. This is the capstone phase — no new features are added; the focus is entirely on validation, documentation, and release readiness.

**Deliverables**:
- Automated E2E test suite executing all five defined scenarios (E2E-001 through E2E-005) with mocked external services, plus human-gated live executor tests using the `--autopilot-confirm` pytest flag
- Cross-device verification confirming the application works on macOS desktop browsers (Chrome/Safari) and iPhone Safari via local network access, with OneDrive data directory sync validated
- Complete documentation: README.md with setup guide, usage walkthrough, and configuration reference; updated agent runbook for AI-driven application running and E2E test execution; architecture decision records
- Release-ready repository: CI pipeline green, no secrets in repo, `.gitignore` verified, `pip install -e .` clean install, evals passing, ≥ 30% test coverage

**Dependencies**:
- Phase 5 complete (polished UI with navigation, error handling, responsive layouts, workflow quality-of-life)
- Phase 6 complete (LLM-assisted payload generation with fallback to standard interpolation)
- Phase 4 complete (all UI screens functional, dispatch workflow working)
- Phase 3 complete (all backend services operational)
- Phase 2 complete (data models, config, settings)
- Phase 1 complete (repository structure, CI/CD, E2E scenario definitions)
- Python 3.13+ virtual environment activated
- Autopilot executor service available for human-gated live tests (optional — tests auto-skip if unavailable)
- ngrok tunnel running for webhook callback tests (optional — tests auto-skip if unavailable)

## Phase Goals

- All five E2E testing scenarios (E2E-001 through E2E-005) are automated with mocked external services and pass reliably
- Human-gated live Autopilot executor test passes when the executor is available, and auto-skips cleanly in CI
- Application is verified working on macOS desktop browser and iPhone Safari via local network
- OneDrive data directory sync confirmed across devices
- README.md provides a complete guide for any developer to clone, install, configure, and use the application
- Agent runbook enables AI agents to run the application and execute E2E tests autonomously
- Repository is clean: no secrets, comprehensive `.gitignore`, CI green, evals pass, ≥ 30% test coverage
- All new code passes Black, isort, evals, and achieves ≥ 30% test coverage on `app/src/`

---

## Components

### Component 7.1 — End-to-End Test Suite

**Priority**: Must-have

**Estimated Effort**: 3 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.4: E2E testing scenario definitions (E2E-001 through E2E-005 documented in `docs/`)
- Component 4.10: Integration testing patterns from Phase 4
- Component 6.4: Phase 6 test patterns (mocked LLM tests)
- All Phase 3 services: GitHub client, project service, action generator, payload resolver, executor, webhook service
- All Phase 4 UI screens: initial, executor config, action type defaults, secrets, link project, load project, main screen
- Component 5.1: Navigation and state management
- Component 6.2: LLM payload generator (for E2E-004)
- conftest.py: pytest configuration with `--autopilot-confirm` flag pattern from `copilot.instructions.md`

**Features**:
- [AI Agent] Create `tests/e2e/test_e2e_001_configure_dispatch.py` — automated E2E test for the full configure-and-dispatch workflow with mocked GitHub API and executor API
- [AI Agent] Create `tests/e2e/test_e2e_002_load_run_phase.py` — automated E2E test for loading a saved project and dispatching all actions for a full phase
- [AI Agent] Create `tests/e2e/test_e2e_003_debug_action.py` — automated E2E test for inserting a debug action, editing its payload, dispatching, and marking complete
- [AI Agent] Create `tests/e2e/test_e2e_004_llm_payload.py` — automated E2E test for LLM-assisted payload generation with mocked OpenAI SDK, including fallback to standard interpolation
- [AI Agent] Create `tests/e2e/test_e2e_005_live_executor.py` — human-gated live Autopilot executor test using the `--autopilot-confirm` pytest flag pattern; auto-skips when flag is not passed
- [AI Agent] Extend `conftest.py` with `--autopilot-confirm` CLI flag, `pytest_collection_modifyitems` hook for auto-skip, and `confirm_autopilot_gateway` session-scoped fixture
- [AI Agent] Create shared E2E test fixtures for project data, executor config, and action generation in `tests/e2e/conftest.py`

**Description**:
This component creates the comprehensive E2E test suite that validates all five defined testing scenarios. Tests E2E-001 through E2E-004 use mocked external services (GitHub API, executor API, OpenAI API) to run reliably in CI without live dependencies. Test E2E-005 is human-gated: it requires a live Autopilot executor and optional ngrok tunnel, triggered by the `--autopilot-confirm` pytest flag. The flag pattern follows the project standard from `copilot.instructions.md` — register the flag via `pytest_addoption`, auto-skip tests marked `requires_autopilot` unless the flag is passed, and prompt the developer once per session to confirm the executor is running.

**Acceptance Criteria**:
- [ ] E2E-001 test passes: configure executor → link project (mocked GitHub) → generate actions → dispatch (mocked executor) → verify response display → poll webhook (mocked) → mark action complete
- [ ] E2E-002 test passes: save project → load project → verify actions present → dispatch all Implement actions for Phase 1 → dispatch Test → dispatch Review → dispatch Document → all actions marked complete
- [ ] E2E-003 test passes: load project → insert Debug action at specific position → edit debug payload → dispatch → verify response → mark complete
- [ ] E2E-004 test passes: enable LLM toggle → generate payload via LLM (mocked OpenAI) → verify AI-generated instructions in payload → test fallback when LLM fails → verify standard interpolation used
- [ ] E2E-005 test with `--autopilot-confirm` flag: dispatch a real payload to live Autopilot → receive real response → poll for webhook data (if ngrok available) → mark complete
- [ ] E2E-005 test auto-skips cleanly when `--autopilot-confirm` is not passed
- [ ] `conftest.py` registers `--autopilot-confirm` flag and the `pytest_collection_modifyitems` hook auto-skips `requires_autopilot`-marked tests
- [ ] `confirm_autopilot_gateway` fixture prompts the developer once per session, returns connection parameters or skips if declined
- [ ] All E2E tests pass: `pytest tests/e2e/ -q`
- [ ] All existing unit and integration tests from Phases 2–6 still pass (no regression)

**Technical Details**:
- **Files to Create/Modify**:
  - `tests/e2e/__init__.py` (create)
  - `tests/e2e/conftest.py` (create — shared E2E fixtures)
  - `tests/e2e/test_e2e_001_configure_dispatch.py` (create)
  - `tests/e2e/test_e2e_002_load_run_phase.py` (create)
  - `tests/e2e/test_e2e_003_debug_action.py` (create)
  - `tests/e2e/test_e2e_004_llm_payload.py` (create)
  - `tests/e2e/test_e2e_005_live_executor.py` (create)
  - `conftest.py` (extend — add `--autopilot-confirm` flag and hooks)
- **Key Functions/Classes**:
  - `pytest_addoption(parser)`: Register `--autopilot-confirm` flag
  - `pytest_collection_modifyitems(config, items)`: Auto-skip tests marked `requires_autopilot` when flag is absent
  - `confirm_autopilot_gateway` fixture: Session-scoped, prompts developer, returns executor URL and API key or skips
  - `mock_github_client` fixture: Returns a pre-configured mock GitHub client with sample repo data
  - `mock_executor` fixture: Returns a mock executor that returns successful dispatch responses
  - `sample_project` fixture: Returns a fully configured `Project` with phase-progress data and generated actions
  - `sample_executor_config` fixture: Returns an `ExecutorConfig` with Autopilot defaults
- **Human/AI Agent**: AI Agent writes all automated tests; Human runs E2E-005 with live executor
- **Dependencies**: pytest, pytest-cov, httpx (for mocked responses), unittest.mock, all `app/src/` modules

**Detailed Implementation Requirements**:

- **File 1: `conftest.py`** (extend root conftest): Add `pytest_addoption` hook to register `--autopilot-confirm` as a CLI flag with help text "Run live Autopilot executor tests (requires running Autopilot service)". Add `pytest_collection_modifyitems` hook: iterate `items`, find tests with the `requires_autopilot` marker, and if `config.getoption("--autopilot-confirm")` is falsy, append a skip marker with reason "Need --autopilot-confirm to run live executor tests". Add a `confirm_autopilot_gateway` session-scoped fixture: check `request.config.getoption("--autopilot-confirm")`, if not set return `pytest.skip()`. Prompt the developer via `input()`: "Is the Autopilot executor running at {url}? [y/N]: ". If declined, skip. Load the Autopilot API endpoint and API key from environment variables (`AUTOPILOT_API_ENDPOINT`, `AUTOPILOT_API_KEY`). Return a dict with `api_endpoint` and `api_key`. Wrap in a try/except for `EOFError` (CI environments) — skip if prompt fails.

- **File 2: `tests/e2e/conftest.py`**: Create shared E2E fixtures. (1) `sample_phase_progress` fixture: return a dict matching the `phase-progress.json` schema with 2 phases, each with 2 components — sufficient for E2E testing. (2) `sample_executor_config` fixture: return an `ExecutorConfig` instance with Autopilot defaults, webhook URL set to `http://localhost:8000/webhook/callback`, `use_llm=False`. (3) `sample_project` fixture: return a `Project` instance created from `sample_phase_progress` with a test repository name and generated actions. (4) `mock_github_responses` fixture: return a dict mapping GitHub API URLs to mock response data (repo contents, phase-progress.json content, agent file listings). (5) `mock_executor_response` fixture: return a callable that produces mock `ExecutorResponse` objects with configurable status codes and run IDs. (6) `mock_webhook_data` fixture: return sample webhook callback data keyed by run_id.

- **File 3: `tests/e2e/test_e2e_001_configure_dispatch.py`**: Test the full configure-and-dispatch workflow at the service layer. (1) Create an `ExecutorConfig` and save it via the config manager. (2) Create action type defaults and save them. (3) Mock the GitHub client to return a sample `phase-progress.json` and agent files when scanning a test repo. (4) Call the project service to link the project — verify it parses the phase-progress data, finds agent files, and persists the project. (5) Call the action generator to produce actions — verify correct ordering (Implement per component, then Test, Review, Document per phase). (6) Resolve a payload for the first Implement action — verify all `{{variable}}` placeholders are replaced. (7) Mock the executor to return a successful dispatch response. Dispatch the resolved payload — verify the response contains a `run_id` and status "dispatched". (8) Store mock webhook data for the `run_id`. Poll the webhook service — verify data is retrieved. (9) Mark the action as complete — verify status change. Assert no exceptions raised throughout the flow.

- **File 4: `tests/e2e/test_e2e_002_load_run_phase.py`**: Test loading a saved project and running a full phase. (1) Using fixtures, create and save a project with generated actions to the data directory. (2) Load the project from the data directory via the project service. Verify all phase-progress data and actions are intact. (3) Iterate through all actions for Phase 1: dispatch each Implement action (mocked executor), verify responses, then dispatch Test, Review, Document. (4) Mark each action complete after dispatch. (5) Verify all Phase 1 actions have status "completed". (6) Verify Phase 2 actions remain "not-started".

- **File 5: `tests/e2e/test_e2e_003_debug_action.py`**: Test debug action insertion and dispatch. (1) Load a project with generated actions. (2) Insert a Debug action at position 2 in Phase 1's action list (between the first and second Implement actions). (3) Verify the Debug action appears at the correct position with correct type. (4) Edit the Debug action's payload — set custom `agent_instructions`. (5) Dispatch the Debug action (mocked executor) — verify response. (6) Mark the Debug action complete. (7) Verify surrounding actions are unaffected.

- **File 6: `tests/e2e/test_e2e_004_llm_payload.py`**: Test LLM-assisted payload generation end-to-end. (1) Configure executor with `use_llm=True`. (2) Mock the `LLMService.generate()` to return a valid JSON response with `agent_instructions`. (3) Call `LLMPayloadGenerator.generate_payload()` for an Implement action. Verify `result.llm_used is True` and `agent_instructions` contains the LLM-generated text. (4) Verify structural fields (`repository`, `branch`, `model`, `callback_url`) are from standard interpolation. (5) Test fallback: mock `LLMService.generate()` to raise `LLMTimeoutError`. Call `generate_payload()`. Verify `result.llm_used is False`, `fallback_reason` is set, and payload matches standard interpolation. (6) Test fallback when `use_llm=False`: verify standard interpolation used. (7) Test fallback when no API key: set `LLMService` with no key, verify `is_available()` is `False` and standard interpolation used.

- **File 7: `tests/e2e/test_e2e_005_live_executor.py`**: Human-gated live Autopilot executor test. Mark test class with `@pytest.mark.requires_autopilot`. (1) Use `confirm_autopilot_gateway` fixture to get live executor connection parameters. (2) Create a minimal payload with the test repo, branch `main`, simple `agent_instructions`, and the live API key. (3) Dispatch to the real Autopilot endpoint via `AutopilotExecutor`. (4) Assert response status code is 200 and `run_id` is present. (5) If webhook URL is configured, wait up to 120 seconds for webhook callback (poll every 5 seconds). Verify webhook data is received with matching `run_id`. (6) Clean up: no persistent side effects (the agent run on the target repo is the expected side effect). Use `threading.Event` for cross-thread webhook coordination if polling via background thread. Always disconnect/clean up in a `finally` block.

**Test Requirements**:
- [ ] All E2E tests pass with mocked services: `pytest tests/e2e/ -q -k "not requires_autopilot"`
- [ ] E2E-005 auto-skips when `--autopilot-confirm` is not passed
- [ ] E2E-005 passes when run with `--autopilot-confirm` and live Autopilot is available
- [ ] All existing unit and integration tests from Phases 2–6 still pass

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-7-component-7-1-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-7.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality (Phases 1–6 tests still pass)
- [ ] Core application is still working post component implementation

**Notes**:
The E2E tests operate at the service layer, not the UI layer — NiceGUI does not easily support automated UI testing (no Selenium/Playwright support due to WebSocket architecture). Service-layer E2E tests verify the complete business logic chain. UI rendering and interaction verification are covered by the manual cross-device testing in Component 7.2. For E2E-005, the `--autopilot-confirm` flag pattern mirrors the human-gated test strategy defined in `copilot.instructions.md`. The `threading.Event` pattern for webhook coordination ensures the test doesn't hang if the webhook never arrives — the 120-second timeout prevents indefinite waits.

---

### Component 7.2 — Cross-Device Verification

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: Human + AI Agent

**Dependencies**:
- Component 5.3: Mobile responsiveness (iPhone Safari layouts, stacked panels)
- Component 5.1: Navigation flow (smooth transitions, loading indicators)
- Component 4.1: NiceGUI app entry point (Uvicorn server, network binding)
- Component 2.2: Application settings (`DISPATCH_DATA_DIR` for OneDrive directory)
- All Phase 4 and 5 UI components functional

**Features**:
- [Human] Test application on macOS desktop browser (Chrome and Safari) — verify all screens render correctly, navigation works, dispatch workflow functions
- [Human] Test application on iPhone Safari via local network — navigate to `http://<mac-ip>:8080/` and verify all screens render, interactions work, touch targets are appropriately sized
- [Human] Verify OneDrive data directory sync — create/save a project on one device, verify the project data appears on the other device's filesystem via OneDrive sync
- [AI Agent] Create a cross-device verification checklist document (`docs/cross-device-verification.md`) with detailed test steps for each device/browser combination
- [AI Agent] Document the local network access setup: how to find the Mac's IP, how to ensure the Uvicorn server binds to `0.0.0.0`, how to access from iPhone on the same network
- [AI Agent] Document and fix any device-specific issues found during testing — create issue tickets or fix directly if the issue is CSS/layout related

**Description**:
This component validates that the application works correctly across the primary target devices: macOS desktop (Chrome and Safari) and iPhone Safari. The Human performs the actual device testing while the AI Agent prepares the verification checklist and documents the network access setup. Cross-device data portability is validated by configuring `DISPATCH_DATA_DIR` to point to an OneDrive-synced directory and verifying that project data saved on one device appears on the other. Any device-specific layout or interaction issues found are documented and fixed.

**Acceptance Criteria**:
- [ ] Application renders correctly on macOS Chrome (latest) — all screens, navigation, dispatch workflow verified
- [ ] Application renders correctly on macOS Safari (latest) — all screens, navigation, dispatch workflow verified
- [ ] Application renders correctly on iPhone Safari (iOS 17+) — all screens, stacked panel layout on narrow viewport, touch-friendly interactions
- [ ] Local network access works: iPhone can reach the app at `http://<mac-ip>:8080/`
- [ ] OneDrive data directory sync verified: project saved on macOS appears in OneDrive directory and is accessible from another device's filesystem
- [ ] Cross-device verification checklist document created at `docs/cross-device-verification.md`
- [ ] Local network access setup documented in README or verification checklist
- [ ] Any device-specific issues found are documented and fixed (or documented as known limitations)

**Technical Details**:
- **Files to Create/Modify**:
  - `docs/cross-device-verification.md` (create)
  - `app/src/main.py` (verify Uvicorn binds to `0.0.0.0` for network access)
  - CSS/layout files (if device-specific fixes needed)
- **Key Functions/Classes**: N/A — this is primarily a testing and documentation component
- **Human/AI Agent**: Human performs device testing; AI Agent creates documentation and fixes
- **Dependencies**: macOS desktop with Chrome and Safari, iPhone on same local network, OneDrive configured

**Detailed Implementation Requirements**:

- **File 1: `docs/cross-device-verification.md`**: Create a structured verification checklist with sections: (1) **Prerequisites** — macOS with Python 3.13+, iPhone on same Wi-Fi network, OneDrive configured with `DISPATCH_DATA_DIR` pointing to an OneDrive folder. (2) **Local Network Setup** — how to find Mac IP (`ifconfig | grep "inet " | grep -v 127.0.0.1`), verify Uvicorn binds to `0.0.0.0:8080` (check `app/src/main.py`), test access from iPhone at `http://<mac-ip>:8080/`. (3) **macOS Desktop Checklist** — for both Chrome and Safari: initial screen renders, executor config works, link project scans repo, main screen shows actions, dispatch works, webhook data displays, debug action insertion, payload editing, save/load project, LLM toggle (if configured). (4) **iPhone Safari Checklist** — same functional checks plus: split panels stack vertically, touch targets >= 44px, text is readable without zoom, forms are usable on mobile keyboard, loading indicators visible, toast notifications display correctly. (5) **OneDrive Sync Checklist** — configure `DISPATCH_DATA_DIR=~/OneDrive/dispatch-data`, save a project, check the file appears in OneDrive, check the file syncs to another device, load the project from the synced file. (6) **Known Limitations** — document any known device-specific issues or workarounds.

- **File 2: `app/src/main.py`** (verify/fix): Ensure the NiceGUI/Uvicorn startup binds to `0.0.0.0` (not `127.0.0.1`) so the app is accessible from other devices on the local network. The `ui.run()` call should include `host="0.0.0.0"`. If it's already set correctly, no change needed — just verify.

**Test Requirements**:
- [ ] Manual testing: macOS Chrome — all screens and workflows verified against checklist
- [ ] Manual testing: macOS Safari — all screens and workflows verified against checklist
- [ ] Manual testing: iPhone Safari — all screens, responsive layout, and touch interactions verified
- [ ] Manual testing: OneDrive sync — project data portability confirmed

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] `docs/cross-device-verification.md` created with complete checklist
- [ ] macOS Chrome testing completed and documented
- [ ] macOS Safari testing completed and documented
- [ ] iPhone Safari testing completed and documented
- [ ] OneDrive sync testing completed and documented
- [ ] Any device-specific issues fixed or documented as known limitations
- [ ] Documentation created: Component Overview (`docs/components/phase-7-component-7-2-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-7.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
NiceGUI uses Quasar (Material Design) components which are mobile-first by design. Phase 5 (Component 5.3) already implemented responsive layouts, so minimal fixes are expected. The primary risk is iPhone Safari-specific CSS behaviour (safe area insets, viewport handling, input zoom). If the app is served over HTTP (not HTTPS) on the local network, some browser features may be restricted — document this. OneDrive sync relies on atomic file writes (individual JSON file per project) to avoid conflicts. The `DISPATCH_DATA_DIR` environment variable from Phase 2 (Component 2.2) already supports custom data directory paths, so pointing it to an OneDrive folder should work without code changes.

---

### Component 7.3 — Documentation

**Priority**: Must-have

**Estimated Effort**: 3 hours

**Owner**: AI Agent

**Dependencies**:
- All Phases 1–6 complete (full application implemented)
- Component 7.1: E2E test suite (for documenting test execution)
- Component 7.2: Cross-device verification (for documenting setup and known limitations)
- `docs/autopilot-runbook.md`: Existing Autopilot integration reference
- `docs/sample-payload.json`: Existing sample payload reference
- `copilot.instructions.md`: Project standards and conventions

**Features**:
- [AI Agent] Complete `README.md` with: project overview, features, prerequisites, installation and setup guide, configuration walkthrough (executor, action type defaults, secrets), usage guide (link project, dispatch actions, monitor results), development guide (running tests, CI/CD, code standards), architecture overview, and license
- [AI Agent] Update `docs/autopilot-runbook.md` with Dispatch-specific integration notes: how Dispatch configures and dispatches to Autopilot, webhook callback format, and troubleshooting common integration issues
- [AI Agent] Create/update agent runbook (`docs/agent-runbook.md`) for AI agent-driven application running: how to start the app, execute E2E tests, run quality checks, and common operations
- [AI Agent] Create architecture decision records (`docs/architecture-decisions.md`) documenting key technical decisions: NiceGUI over alternatives, JSON files over SQLite, polling over WebSocket for webhooks, simple interpolation over Jinja2, local-first design with OneDrive sync, modular executor protocol
- [AI Agent] Update `.env/.env.example` with all required and optional environment variable placeholders with descriptions

**Description**:
This component finalizes all project documentation to make the repository self-contained for developers, contributors, and AI agents. The README serves as the primary entry point and must guide a developer from clone to running the app. The agent runbook enables AI agents to operate the application autonomously. Architecture decision records capture the "why" behind key technical choices for future maintainability. The Autopilot runbook update bridges the existing executor documentation with Dispatch-specific usage.

**Acceptance Criteria**:
- [ ] `README.md` contains: project overview, features list, prerequisites (Python 3.13+, virtual environment), installation steps (`pip install -e .`), configuration guide (executor, action type defaults, secrets), usage walkthrough (link project, dispatch, monitor), development guide (tests, CI, standards), architecture overview, license section
- [ ] README installation steps work end-to-end: clone → install → configure → launch → use
- [ ] `docs/agent-runbook.md` enables an AI agent to: start the app (`python -m app.src.main`), run all tests (`pytest -q --cov=app/src`), run quality checks (`black --check`, `isort --check-only`, evals), execute E2E tests, and troubleshoot common issues
- [ ] `docs/architecture-decisions.md` documents at least 6 key decisions with context, decision, and rationale for each
- [ ] Autopilot integration notes added to existing runbook or as a new section
- [ ] `.env/.env.example` includes all environment variables with descriptions: `DISPATCH_DATA_DIR`, `GITHUB_TOKEN`, `AUTOPILOT_API_KEY`, `AUTOPILOT_API_ENDPOINT`, `OPENAI_API_KEY`, `OPENAI_MODEL`

**Technical Details**:
- **Files to Create/Modify**:
  - `README.md` (create or overwrite — replace skeleton from Phase 1)
  - `docs/agent-runbook.md` (create)
  - `docs/architecture-decisions.md` (create)
  - `docs/autopilot-runbook.md` (extend with Dispatch integration section)
  - `.env/.env.example` (update with all variables)
- **Key Functions/Classes**: N/A — pure documentation
- **Human/AI Agent**: AI Agent writes all documentation
- **Dependencies**: All implemented components, existing docs

**Detailed Implementation Requirements**:

- **File 1: `README.md`**: Replace the Phase 1 skeleton with a complete README. Structure: (1) **Dispatch** — one-paragraph project description. (2) **Features** — bullet list of key capabilities: GitHub project linking, phase-progress.json parsing, action generation, modular executor dispatch, Autopilot integration, webhook monitoring, LLM-assisted payload generation, cross-device access, local-first design. (3) **Prerequisites** — Python 3.13+, pip, virtual environment, GitHub personal access token, Autopilot executor (optional), ngrok (optional for webhooks), OpenAI API key (optional for LLM). (4) **Quick Start** — step-by-step: clone, create/activate venv, `pip install -e .`, copy `.env/.env.example` to `.env/.env.local`, fill in secrets, launch with `python -m app.src.main`, open browser to `http://localhost:8080`. (5) **Configuration** — subsections for Executor Config (endpoint, API key, webhook URL), Action Type Defaults (payload templates with variable reference), Secrets Management (GitHub token, API keys), Data Directory (default `~/.dispatch/`, configurable via `DISPATCH_DATA_DIR`). (6) **Usage** — walkthrough of: first-time setup, linking a new project, dispatching actions, monitoring results, inserting debug actions, LLM payload generation, loading saved projects, cross-device access. (7) **Development** — running tests (`pytest`), code formatting (`black`, `isort`), quality checks (`evals.py`), CI/CD pipeline. (8) **Architecture** — brief overview: NiceGUI + FastAPI, service layer, JSON file storage, modular executor protocol. Link to `docs/architecture-decisions.md` for details. (9) **Project Structure** — folder tree from solution design. (10) **License** — reference LICENSE file.

- **File 2: `docs/agent-runbook.md`**: Create a runbook for AI agents operating the application. Structure: (1) **Starting the Application** — `source .venv/bin/activate`, `set -o allexport; source .env/.env.local; set +o allexport`, `python -m app.src.main`. Verify with `curl http://localhost:8080`. (2) **Running Tests** — `pytest -q --cov=app/src --cov-report=term-missing` for all tests, `pytest tests/e2e/ -q -k "not requires_autopilot"` for E2E tests, `pytest --autopilot-confirm` for live executor tests. (3) **Quality Checks** — `black --check app/src/`, `isort --check-only app/src/`, `python scripts/evals.py`. (4) **Common Operations** — save/load project from data directory, view application logs, check webhook data, reset application state. (5) **Troubleshooting** — common errors and resolutions: port in use, missing environment variables, GitHub API auth failures, executor unreachable, OneDrive sync issues.

- **File 3: `docs/architecture-decisions.md`**: Document key architectural decisions using a lightweight ADR format (Context, Decision, Rationale). Decisions to document: (1) **NiceGUI over Electron/Tauri/PWA** — pure Python, built-in FastAPI, Quasar responsive components, zero JavaScript build pipeline. (2) **JSON files over SQLite** — simpler for single-user local app, human-readable, OneDrive-syncable, no database dependency. (3) **Polling over WebSocket for webhook results** — simpler architecture, webhook POST + in-memory store + UI refresh button, no persistent WebSocket connection management. (4) **Simple `{{variable}}` interpolation over Jinja2** — minimal dependency, sufficient for known variable set, predictable behaviour. (5) **Local-first with OneDrive sync over cloud hosting** — zero infrastructure cost, user controls data, file sync handles cross-device, single-user requirement. (6) **Modular executor protocol over hardcoded Autopilot** — Python Protocol class allows swapping executors without code changes, future-proof for new executor types. (7) **Optional LLM payload generation** — enhances but doesn't gatekeep workflow, graceful fallback, user always reviews before dispatch.

- **File 4: `docs/autopilot-runbook.md`** (extend): Add a new section "## Dispatch Integration" at the end of the existing file. Subsections: (1) **How Dispatch Uses Autopilot** — Dispatch sends POST requests to the Autopilot `/agent/run` endpoint with the payload structure matching `docs/sample-payload.json`. The `X-API-Key` header authenticates the request. (2) **Webhook Callback** — Autopilot sends a POST to the `callback_url` in the payload when the agent run completes. Dispatch's `/webhook/callback` endpoint receives and stores this data. (3) **Configuration in Dispatch** — set `AUTOPILOT_API_ENDPOINT` and `AUTOPILOT_API_KEY` in `.env/.env.local`, configure the endpoint and API key env var in the Dispatch executor config screen. (4) **Troubleshooting** — common issues: 401 Unauthorized (check API key), connection refused (check Autopilot is running), webhook not received (check ngrok tunnel, check callback_url).

- **File 5: `.env/.env.example`** (update): Ensure all environment variables are listed with descriptive comments. Variables: `DISPATCH_DATA_DIR` (default `~/.dispatch/`), `GITHUB_TOKEN` (GitHub personal access token), `AUTOPILOT_API_ENDPOINT` (Autopilot API URL, e.g., `http://localhost:8000/agent/run`), `AUTOPILOT_API_KEY` (Autopilot API key), `OPENAI_API_KEY` (optional, for LLM payload generation), `OPENAI_MODEL` (optional, default `gpt-4o`).

**Test Requirements**:
- [ ] Manual verification: README instructions work end-to-end (clone, install, configure, launch)
- [ ] Manual verification: Agent runbook commands execute successfully
- [ ] All documentation is free of TODO/FIXME placeholders

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] README.md is complete and accurate
- [ ] Agent runbook is complete and tested
- [ ] Architecture decisions document is complete
- [ ] Autopilot integration notes added
- [ ] `.env/.env.example` updated
- [ ] Documentation created: Component Overview (`docs/components/phase-7-component-7-3-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-7.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
The README must be approachable for developers who have not seen the project before — assume no context beyond "a Python project on GitHub". Use concrete code blocks for all commands. The agent runbook is specifically aimed at AI agents (like Copilot or Claude) that might be asked to operate or test the application — keep instructions precise and unambiguous with exact commands. Architecture decisions should be concise — one paragraph per section (Context, Decision, Rationale) is sufficient.

---

### Component 7.4 — Final Quality Checks & Release Preparation

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Components 7.1 through 7.3: All Phase 7 components implemented
- All Phases 1–6 complete
- CI/CD pipeline (Component 1.3) configured and functional

**Features**:
- [AI Agent] Run full test suite and generate coverage report — `pytest -q --cov=app/src --cov-report=term-missing`
- [AI Agent] Run all quality checks — `black --check app/src/`, `isort --check-only app/src/`, `python scripts/evals.py`
- [AI Agent] Security audit — verify no secrets, tokens, or API keys exist in any tracked file in the repository; verify `.gitignore` covers `.env/`, `~/.dispatch/`, `.venv/`, `__pycache__/`, `.DS_Store`
- [AI Agent] Verify clean install — `pip install -e .` in a fresh virtual environment succeeds without errors
- [AI Agent] Verify CI pipeline — push and confirm all GitHub Actions checks pass
- [AI Agent] Create/update final implementation context and phase summary documentation
- [AI Agent] Update `docs/phase-progress.json` — mark Phase 7 status as appropriate
- [AI Agent] Execute all E2E scenario validations one final time to confirm complete system integrity

**Description**:
This component is the final gate before release. It runs every quality check, security audit, and verification step to ensure the repository is clean and ready for public use. The full test suite is executed with coverage reporting to confirm ≥ 30% coverage. Security scanning ensures no secrets exist in tracked files. A clean install test verifies the package installs correctly from scratch. The CI pipeline is verified green. All documentation from previous components is verified complete. This component produces the final phase summary and implementation context updates.

**Acceptance Criteria**:
- [ ] `pytest -q --cov=app/src --cov-report=term-missing` passes with ≥ 30% coverage
- [ ] `black --check app/src/` passes with no reformatting needed
- [ ] `isort --check-only app/src/` passes with no reordering needed
- [ ] `python scripts/evals.py` passes with no violations (all docstrings present, no TODO/FIXME)
- [ ] Security audit: `grep -r "GITHUB_TOKEN\|API_KEY\|sk-" app/ tests/ --include="*.py"` returns no hardcoded secrets (only env var references)
- [ ] Security audit: `.gitignore` contains entries for `.env/`, `.venv/`, `__pycache__/`, `*.pyc`, `.DS_Store`, and `~/.dispatch/` (or the `DISPATCH_DATA_DIR` pattern)
- [ ] Clean install: `python -m venv /tmp/dispatch-test-venv && source /tmp/dispatch-test-venv/bin/activate && pip install -e . && python -c "import app.src"` succeeds
- [ ] CI pipeline: all GitHub Actions workflow checks pass on the latest push
- [ ] All E2E tests pass one final time: `pytest tests/e2e/ -q -k "not requires_autopilot"`
- [ ] All unit and integration tests pass: `pytest -q`
- [ ] `docs/implementation-context-phase-7.md` exists with entries for all Phase 7 components
- [ ] `docs/phase-summary.md` is updated with Phase 7 completion entry
- [ ] No TODO/FIXME comments remain in any file under `app/src/`

**Technical Details**:
- **Files to Create/Modify**:
  - `docs/implementation-context-phase-7.md` (create)
  - `docs/phase-summary.md` (update with Phase 7 entry)
  - `docs/components/phase-7-component-7-4-overview.md` (create)
  - `.gitignore` (verify/extend if needed)
- **Key Functions/Classes**: N/A — this is a validation and documentation component
- **Human/AI Agent**: AI Agent runs all checks and creates documentation
- **Dependencies**: All `app/src/` modules, pytest, Black, isort, evals script, CI pipeline

**Detailed Implementation Requirements**:

- **File 1: `docs/implementation-context-phase-7.md`**: Running log with entries for Components 7.1–7.4. Each entry includes: component ID and name, status (completed), key files created/modified, notable observations. For 7.1: list of E2E test files, key test scenarios covered, `--autopilot-confirm` flag pattern. For 7.2: cross-device verification results summary, any device-specific fixes applied, access setup notes. For 7.3: list of documentation files created/updated, key documentation decisions. For 7.4: final test results (pass count, coverage percentage), quality check results, security audit findings, CI status.

- **File 2: `docs/phase-summary.md`** (update): Add a Phase 7 entry to the phase summary document. Include: phase objective, key deliverables (E2E test suite, cross-device verification, documentation, release readiness), completion date, test coverage final number, total test count, any notable findings or issues encountered, and overall project completion status.

- **File 3: `docs/components/phase-7-component-7-4-overview.md`**: Summary of the final quality checks component — test execution results, coverage report summary, security audit results, clean install verification, CI pipeline status, and the final verification checklist results.

- **File 4: `.gitignore`** (verify/extend): Verify the following entries exist (add any that are missing): `.env/`, `.venv/`, `__pycache__/`, `*.pyc`, `.DS_Store`, `*.egg-info/`, `dist/`, `build/`, `.pytest_cache/`, `.coverage`, `htmlcov/`. Note: `~/.dispatch/` is the user's data directory outside the repo — it doesn't need a `.gitignore` entry, but document this in the README.

**Test Requirements**:
- [ ] All tests pass: `pytest -q --cov=app/src --cov-report=term-missing`
- [ ] All quality checks pass: Black, isort, evals
- [ ] Security audit passes: no secrets in tracked files
- [ ] Clean install succeeds in fresh virtual environment
- [ ] CI pipeline green

**Definition of Done**:
- [ ] All quality checks pass (Black, isort, pytest, evals)
- [ ] Test coverage ≥ 30% on `app/src/`
- [ ] Security audit: no secrets in repository  
- [ ] Clean install verified
- [ ] CI pipeline green
- [ ] `docs/implementation-context-phase-7.md` documents all Phase 7 components
- [ ] `docs/phase-summary.md` updated with Phase 7 completion
- [ ] Documentation created: Component Overview (`docs/components/phase-7-component-7-4-overview.md`). Maximum 100 lines of markdown.
- [ ] No regression in any existing functionality
- [ ] Core application is fully working
- [ ] Repository is ready for open-source release
- [ ] All E2E scenarios pass one final time

**Notes**:
The clean install test should be done in a completely fresh virtual environment to catch any missing dependencies in `pyproject.toml`. The security audit is a simple grep-based check — it's not a full SAST scan, but it catches obvious hardcoded secrets. The `.gitignore` verification is critical for open-source release — any sensitive file patterns must be covered. The phase summary update marks the end of the project's build phase. After this component, the repository should be in a state where someone can clone it, follow the README, and have a working application.

---

## Phase Acceptance Criteria

- [ ] All automated E2E tests pass: `pytest tests/e2e/ -q -k "not requires_autopilot"`
- [ ] Human-gated Autopilot executor test passes when live executor is available (via `--autopilot-confirm`)
- [ ] Application is fully usable on macOS desktop browser (Chrome and Safari verified)
- [ ] Application is fully usable on iPhone Safari via local network
- [ ] OneDrive data directory sync works across devices
- [ ] `README.md` contains complete setup, usage, and configuration instructions
- [ ] Agent runbook (`docs/agent-runbook.md`) enables AI agents to run the app and execute E2E tests
- [ ] Architecture decisions are documented in `docs/architecture-decisions.md`
- [ ] `pytest -q --cov=app/src --cov-report=term-missing` achieves ≥ 30% coverage
- [ ] `python scripts/evals.py` passes with no violations
- [ ] `black --check app/src/` and `isort --check-only app/src/` pass
- [ ] CI pipeline is green with all checks passing
- [ ] No secrets, tokens, or API keys exist anywhere in the repository
- [ ] `.gitignore` covers `.env/`, `.venv/`, `__pycache__/`, `.DS_Store`, and other generated files
- [ ] `pip install -e .` succeeds in a clean virtual environment
- [ ] No TODO/FIXME comments remain in delivered code
- [ ] `docs/implementation-context-phase-7.md` documents all implemented components
- [ ] `docs/phase-summary.md` updated with Phase 7 completion
- [ ] All previous phase tests continue to pass (no regression)

---

## Cross-Cutting Concerns

### Testing Strategy
- **E2E Testing Scenarios**: All five scenarios (E2E-001 through E2E-005) are fully tested in this phase. E2E-001 (configure & dispatch), E2E-002 (load & run full phase), E2E-003 (debug action workflow), and E2E-004 (LLM payload generation) run with mocked external services in CI. E2E-005 (live executor) is human-gated via `--autopilot-confirm`. Cross-device verification (E2E-005's cross-device aspect) is manual.
- **Unit Testing**: No new unit tests expected beyond what's needed for E2E infrastructure (conftest fixtures). Existing unit tests from Phases 2–6 are re-validated.
- **Integration Testing**: E2E tests serve as the final integration validation — they chain multiple services together in realistic workflows.
- **Performance Testing**: Verified as part of cross-device testing — UI responsiveness on both macOS and iPhone.
- **Security Testing**: Dedicated security audit in Component 7.4 — grep for secrets, verify `.gitignore`, verify no sensitive data in logs.

### Documentation Requirements
- **Developer Context Documentation**: `docs/implementation-context-phase-7.md` (running log), `docs/components/phase-7-component-7-X-overview.md` per component
- **Agent Runbook**: `docs/agent-runbook.md` — complete guide for AI agents to operate and test the application
- **Code Documentation**: All public functions should already have Google-style docstrings from previous phases — verified by evals
- **Architecture Decision Records**: `docs/architecture-decisions.md` documenting 7 key decisions
- **User Documentation**: `README.md` with complete setup, usage, and configuration guide
- **Cross-Device Documentation**: `docs/cross-device-verification.md` with testing checklist and setup instructions
