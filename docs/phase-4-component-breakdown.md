# Phase 4: MVP UI & End-to-End Integration

## Phase Overview

**Objective**: Build the complete NiceGUI web application — all screens, navigation, and the main dispatch workflow. This phase integrates all backend services into the UI to deliver a fully working MVP. After this phase, the application can be launched locally and used end-to-end: configure an executor, link a GitHub project, view generated actions, dispatch them, see responses, and mark them complete.

**Deliverables**:
- NiceGUI application entry point (`app/src/main.py`) with Uvicorn startup, page routing, and FastAPI webhook endpoints
- Initial screen (`app/src/ui/initial_screen.py`) with Load Project, Link New Project, Configure Executor buttons and config gatekeeping
- Executor configuration screen (`app/src/ui/executor_config.py`) with form for executor settings, save/load, and validation
- Action type defaults screen (`app/src/ui/action_type_defaults.py`) with payload template editors for all five action types
- Secrets management screen (`app/src/ui/secrets_screen.py`) for entering/updating GitHub token, Autopilot API key, LLM key
- Link New Project screen (`app/src/ui/link_project.py`) with repo/token form, GitHub scanning, and error display
- Load Project screen (`app/src/ui/load_project.py`) with saved project listing and selection
- Main screen (`app/src/ui/main_screen.py`) with split-panel layout, action list, dispatch, response display, webhook polling, and mark-complete
- Debug action insertion and payload editing dialogs
- Integration tests verifying the full workflow (mocked APIs)

**Dependencies**:
- Phase 3 complete (all backend services in `app/src/services/` operational and tested)
- Phase 2 complete (data models in `app/src/models/`, config manager, settings module)
- NiceGUI 2.x declared in `pyproject.toml`
- Python 3.13+ virtual environment activated
- `.env/.env.local` exists with `DISPATCH_DATA_DIR` set

## Phase Goals

- `python -m app.src.main` launches the NiceGUI app on `localhost:8080` and serves the initial screen
- Executor configuration can be saved, loaded, and validated through the UI
- Action type default payload templates can be configured for all five types (implement, test, review, document, debug)
- Secrets (GitHub token, Autopilot API key, LLM key) can be entered and persisted via the UI
- Config gatekeeping prevents project operations until executor and action type defaults are configured
- A new project can be linked: enter repo/token → scan succeeds → actions generated → main screen displays
- Saved projects can be listed, loaded, and navigated to the main screen
- Main screen displays all Execute Action items in correct order with phase grouping
- Clicking an action dispatches the resolved payload and displays the API response
- Webhook responses display when a webhook URL is configured and data is received
- Actions can be marked as completed
- Debug actions can be inserted at any position in a phase
- Individual action payloads can be viewed and edited before dispatch
- Project state can be saved from the main screen
- Webhook endpoints (`POST /webhook/callback`, `GET /webhook/poll/{run_id}`) are registered and functional
- All new code passes Black, isort, evals, and achieves ≥ 30% test coverage

---

## Components

### Component 4.1 — NiceGUI App Entry Point & Routing

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 2.2: `Settings` module for data directory and environment loading
- Component 3.7: `WebhookService` for storing incoming webhook data
- Phase 1: `pyproject.toml` exists with NiceGUI declared as a dependency

**Features**:
- [AI Agent] Create `app/src/main.py` with NiceGUI app initialisation and Uvicorn startup
- [AI Agent] Define page route decorators for all application screens (initial, executor config, action type defaults, secrets, link project, load project, main)
- [AI Agent] Register FastAPI webhook endpoints (`POST /webhook/callback`, `GET /webhook/poll/{run_id}`) on the NiceGUI app
- [AI Agent] Create shared application state module (`app/src/ui/state.py`) for cross-screen state management
- [AI Agent] Create `app/src/ui/__init__.py` with module exports

**Description**:
This component creates the NiceGUI application entry point and routing infrastructure. The `main.py` file initialises the NiceGUI app with Uvicorn, defines page routes for all screens, and registers the FastAPI webhook endpoints that coexist in the same process. A shared application state module holds the in-memory state (current project, config status, service instances) that is shared across screens. This is the skeleton onto which all subsequent UI components are attached.

**Acceptance Criteria**:
- [ ] `python -m app.src.main` starts the NiceGUI app on `localhost:8080`
- [ ] The app serves a page at `/` (initial screen route)
- [ ] Routes are defined for: `/`, `/config/executor`, `/config/action-types`, `/config/secrets`, `/project/link`, `/project/load`, `/project/{project_id}`
- [ ] `POST /webhook/callback` accepts JSON payloads and stores them via `WebhookService`
- [ ] `GET /webhook/poll/{run_id}` returns stored webhook data or 404 if not yet received
- [ ] `AppState` class in `app/src/ui/state.py` eagerly initialises `Settings`, `ConfigManager`, `ActionGenerator`, `PayloadResolver`, `AutopilotExecutor`, and `WebhookService`; lazily creates `GitHubClient` and `ProjectService` on demand via factory methods (these require a GitHub token not available at startup)
- [ ] `AppState` provides `is_executor_configured` and `is_action_types_configured` properties for gatekeeping
- [ ] `from app.src.main import app` imports successfully
- [ ] NiceGUI auto-reload works during development

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/main.py`
  - `app/src/ui/__init__.py`
  - `app/src/ui/state.py`
- **Key Functions/Classes**:
  - `app/src/main.py`: NiceGUI `app` instance, page route functions, webhook endpoint functions
  - `AppState.__init__()` — eagerly initialises token-independent services (`Settings`, `ConfigManager`, `ActionGenerator`, `PayloadResolver`, `AutopilotExecutor`, `WebhookService`); does **not** create `GitHubClient` or `ProjectService` (these require a user-provided GitHub token)
  - `AppState.is_executor_configured: bool` — checks if executor config JSON exists and is valid
  - `AppState.is_action_types_configured: bool` — checks if action type defaults JSON exists and is valid
  - `AppState.current_project: Project | None` — the loaded/linked project
  - Webhook endpoint handlers: `webhook_callback(request)`, `webhook_poll(run_id)`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: NiceGUI 2.x, FastAPI (built into NiceGUI), all Phase 2 and Phase 3 service modules

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/state.py`**: Create an `AppState` class that serves as the central state container for the running application. `__init__()` eagerly instantiates token-independent services: `Settings`, `ConfigManager`, `WebhookService`, `ActionGenerator`, `PayloadResolver`, and `AutopilotExecutor`. Store `current_project: Project | None = None` for the active project. `GitHubClient` and `ProjectService` are **not** created at startup — they require a user-provided GitHub token that is only available when linking or loading a project. Instead, provide factory methods: `get_github_client(token: str) -> GitHubClient` creates and returns a new client with the given token; `get_project_service(token: str) -> ProjectService` creates a `GitHubClient` with the token and returns a `ProjectService` wired to it. These factory methods are called by the Link Project (Component 4.5) and Load Project (Component 4.6) screens when the token is available. Add a `is_executor_configured` property that calls `self.config_manager.get_executor_config()` and returns `True` if a valid config exists, `False` otherwise (catch exceptions). Add `is_action_types_configured` similarly by checking `self.config_manager.get_action_type_defaults()`. Add `is_fully_configured` as a combined property returning `is_executor_configured and is_action_types_configured`. Add `reload_config()` method that re-reads config from disk (called after config changes). The `AppState` instance is created once at app startup and shared across pages via NiceGUI's `app.storage` or as a module-level singleton.

- **File 2: `app/src/main.py`**: Import NiceGUI (`from nicegui import app, ui`). Import FastAPI types for webhook endpoints. Create a module-level `AppState` instance (initialised at import time). Define page routes using `@ui.page('/')` for the initial screen, `@ui.page('/config/executor')` for executor config, `@ui.page('/config/action-types')` for action type defaults, `@ui.page('/config/secrets')` for secrets management, `@ui.page('/project/link')` for linking, `@ui.page('/project/load')` for loading, and `@ui.page('/project/{project_id}')` for the main project screen. Each page function will call the corresponding screen module's render function (implemented in later components), but for this component, render a placeholder `ui.label()` with the route name so routing can be verified. Register FastAPI endpoints on the underlying FastAPI app via `app.add_api_route()` or `@app.post()`: (1) `POST /webhook/callback` — parse the JSON body, extract `run_id`, call `app_state.webhook_service.store(run_id, data)`, return `{"received": True}` with status 200. (2) `GET /webhook/poll/{run_id}` — call `app_state.webhook_service.retrieve(run_id)`, return the data with 200 if found, or `{"run_id": run_id, "status": "pending"}` with 404 if not. At the bottom, add `ui.run(port=8080, reload=True, title="Dispatch")` guarded by `if __name__ == "__main__"` or using NiceGUI's standard entry pattern.

- **File 3: `app/src/ui/__init__.py`**: Create with initial exports for `AppState` from `state`.

**Test Requirements**:
- [ ] Unit tests: `AppState` initialises without errors when `Settings` can load
- [ ] Unit tests: `is_executor_configured` returns `False` when no config file exists
- [ ] Unit tests: `is_action_types_configured` returns `False` when no defaults file exists
- [ ] Unit tests: Webhook callback endpoint stores data correctly (test via httpx TestClient against the FastAPI app)
- [ ] Unit tests: Webhook poll returns data for known `run_id` and 404 for unknown

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-4-component-4-1-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-4.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
NiceGUI runs on top of FastAPI and Uvicorn. The `app` object from NiceGUI exposes the underlying FastAPI app for adding custom routes. For webhook endpoints, use FastAPI's standard route registration rather than NiceGUI page decorators — these are API endpoints, not UI pages. The `AppState` singleton pattern is appropriate here because NiceGUI runs as a single process with a single user — no concurrency concerns for state management. Use `nicegui.app.storage.general` or a module-level variable for the singleton. During development, `reload=True` enables auto-reload on file changes.

---

### Component 4.2 — Initial Screen

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 4.1: `AppState`, page routing, and NiceGUI app must exist
- Component 2.3: `ConfigManager` for config status checks

**Features**:
- [AI Agent] Create `app/src/ui/initial_screen.py` with the initial screen layout
- [AI Agent] Implement "Load Project" button (navigates to `/project/load`)
- [AI Agent] Implement "Link New Project" button (navigates to `/project/link`)
- [AI Agent] Implement "Configure Executor" button (navigates to `/config/executor`)
- [AI Agent] Implement "Action Type Defaults" button (navigates to `/config/action-types`)
- [AI Agent] Implement "Manage Secrets" button (navigates to `/config/secrets`)
- [AI Agent] Implement config gatekeeping — disable Load Project and Link New Project buttons until executor and action type defaults are configured

**Description**:
This component builds the first screen users see when the app launches. It presents the core navigation options: Load Project, Link New Project, and Configure Executor, plus buttons for Action Type Defaults and Secrets management. The key business logic here is config gatekeeping: project operations (Load and Link) are disabled until the executor and action type defaults are configured. This forces users through the configuration flow before working with projects. The screen displays clear status indicators showing which configurations are complete.

**Acceptance Criteria**:
- [ ] Initial screen renders at `/` with app title "Dispatch" and navigation buttons
- [ ] "Configure Executor" button navigates to `/config/executor`
- [ ] "Action Type Defaults" button navigates to `/config/action-types`
- [ ] "Manage Secrets" button navigates to `/config/secrets`
- [ ] "Load Project" and "Link New Project" buttons are visible but disabled when executor or action type defaults are not configured
- [ ] "Load Project" and "Link New Project" buttons become enabled when both configurations are complete
- [ ] Config status indicators show which configurations are complete (e.g., green check / red X)
- [ ] Screen layout is clean and centred, suitable for both desktop and mobile viewports
- [ ] `from app.src.ui.initial_screen import render_initial_screen` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/initial_screen.py`
  - `app/src/main.py` (update `/` route to call `render_initial_screen`)
- **Key Functions/Classes**:
  - `render_initial_screen(app_state: AppState) -> None` — renders the initial screen within the current NiceGUI page context
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: NiceGUI 2.x, `AppState` (Component 4.1)

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/initial_screen.py`**: Create a `render_initial_screen(app_state)` function. Use NiceGUI layout components: `ui.column()` for vertical layout, centred with `.classes('items-center mx-auto')`. Add a title using `ui.label("Dispatch").classes('text-h3 q-mb-lg')`. Create a configuration status section showing: "Executor Config: ✓ Configured / ✗ Not configured" and "Action Type Defaults: ✓ Configured / ✗ Not configured" — use `app_state.is_executor_configured` and `app_state.is_action_types_configured`. Use `ui.icon()` or coloured `ui.label()` for status indicators with Quasar classes for colour (`text-positive` / `text-negative`). Create the navigation buttons in a card or column: (1) `ui.button("Configure Executor", on_click=lambda: ui.navigate.to('/config/executor'))`. (2) `ui.button("Action Type Defaults", on_click=lambda: ui.navigate.to('/config/action-types'))`. (3) `ui.button("Manage Secrets", on_click=lambda: ui.navigate.to('/config/secrets'))`. (4) `ui.button("Link New Project", on_click=lambda: ui.navigate.to('/project/link'))` — set `.props('disable')` if not `app_state.is_fully_configured`. (5) `ui.button("Load Project", on_click=lambda: ui.navigate.to('/project/load'))` — same disable logic. Add a `ui.separator()` between config and project buttons for visual grouping. Apply consistent button styling (full width within the card, Material Design colours).

- **File 2: `app/src/main.py`** (update): Replace the placeholder in the `/` page route with a call to `render_initial_screen(app_state)`.

**Test Requirements**:
- [ ] Unit tests: `render_initial_screen()` executes without errors (NiceGUI test client)
- [ ] Manual verification: Buttons navigate to correct routes
- [ ] Manual verification: Project buttons are disabled when config is incomplete, enabled when complete

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-4-component-4-2-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-4.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
NiceGUI uses a declarative approach where calling `ui.button()` etc. inside a page function adds elements to the current page. Navigation between pages uses `ui.navigate.to(url)`. For config gatekeeping, the check happens at render time — when the user returns to the initial screen after configuring, the page re-renders and the buttons become enabled. Consider using NiceGUI's `ui.refreshable` decorator if dynamic updates are needed without full page reload.

---

### Component 4.3 — Executor Configuration Screen

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 4.1: `AppState`, page routing, NiceGUI app
- Component 2.3: `ConfigManager` for reading/writing executor config
- Component 2.1: `ExecutorConfig` model

**Features**:
- [AI Agent] Create `app/src/ui/executor_config.py` with the executor config form
- [AI Agent] Implement form fields: executor name, API endpoint URL, API key env var name, webhook URL (optional)
- [AI Agent] Implement form validation (required fields, URL format)
- [AI Agent] Implement save to executor config JSON via `ConfigManager`
- [AI Agent] Implement load existing config into form on screen entry
- [AI Agent] Implement navigation back to initial screen

**Description**:
This component builds the executor configuration screen where users define how Dispatch communicates with the external executor API. The form captures the executor name, API endpoint URL, the environment variable name holding the API key, and an optional webhook URL. On save, the config is persisted via `ConfigManager`. If a config already exists, it is loaded into the form on entry. This screen is critical path — it must be completed before project operations are enabled.

**Acceptance Criteria**:
- [ ] Executor config screen renders at `/config/executor` with a form
- [ ] Form fields: Executor Name (text), API Endpoint URL (text, required), API Key Env Var (text, required), Webhook URL (text, optional)
- [ ] Form pre-populates with existing config if one is saved
- [ ] Save button validates required fields and URL format before saving
- [ ] Save button persists the config via `ConfigManager.save_executor_config()`
- [ ] Success notification displays after save
- [ ] Validation error messages display inline for invalid inputs
- [ ] "Back" button navigates to `/` (initial screen)
- [ ] After saving, navigating to `/` shows executor config as "Configured"
- [ ] `from app.src.ui.executor_config import render_executor_config` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/executor_config.py`
  - `app/src/main.py` (update `/config/executor` route)
- **Key Functions/Classes**:
  - `render_executor_config(app_state: AppState) -> None`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: NiceGUI 2.x, `ConfigManager` (Component 2.3), `ExecutorConfig` model (Component 2.1)

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/executor_config.py`**: Create `render_executor_config(app_state)`. Load existing config via `app_state.config_manager.get_executor_config()` — if it exists, pre-populate form field values; if not, use empty strings (and "autopilot" as default executor name). Build the form using NiceGUI components inside a `ui.card()` with a column layout: (1) `ui.label("Executor Configuration").classes('text-h5 q-mb-md')`. (2) `executor_name = ui.input("Executor Name", value=existing.executor_name or "autopilot")` with validation for non-empty. (3) `api_endpoint = ui.input("API Endpoint URL", value=existing.api_endpoint or "")` with validation for non-empty and basic URL format (starts with `http://` or `https://`). (4) `api_key_env_var = ui.input("API Key Environment Variable", value=existing.api_key_env_key or "AUTOPILOT_API_KEY")` with validation for non-empty. Add a helper label: "Name of the env var in .env.local that holds the API key". (5) `webhook_url = ui.input("Webhook URL (optional)", value=existing.webhook_url or "")`. Add a helper label: "The URL the executor will call back to with results". (6) A Save button that: validates all required fields, constructs an `ExecutorConfig` model, calls `app_state.config_manager.save_executor_config(config)`, shows a `ui.notify("Executor configuration saved", type="positive")`, and refreshes app state. (7) A "Back to Home" button that navigates to `/`. Handle validation errors by displaying `ui.notify()` with type `"negative"` and the specific error.

- **File 2: `app/src/main.py`** (update): Replace the placeholder in `/config/executor` route with `render_executor_config(app_state)`.

**Test Requirements**:
- [ ] Unit tests: `render_executor_config()` executes without errors
- [ ] Unit tests: Saving a valid config via `ConfigManager` (test the service layer, mocked)
- [ ] Manual verification: Form pre-populates with saved config
- [ ] Manual verification: Validation blocks save with missing required fields

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-4-component-4-3-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-4.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
NiceGUI's `ui.input()` supports `validation` parameter for inline validation. Use `validation={'Required': lambda v: len(v) > 0}` for required fields. For URL validation, a simple prefix check (`http://` or `https://`) is sufficient — no need for a full URL parsing library. The `api_key_env_key` field stores the *name* of the environment variable (e.g., `AUTOPILOT_API_KEY`), not the key itself — this aligns with the security pattern from Phase 2 where the actual secret is in `.env/.env.local` and models reference it by env var name.

---

### Component 4.4 — Action Type Defaults & Secrets Screens

**Priority**: Must-have

**Estimated Effort**: 3 hours

**Owner**: AI Agent

**Dependencies**:
- Component 4.1: `AppState`, page routing, NiceGUI app
- Component 2.3: `ConfigManager` for reading/writing action type defaults and secrets
- Component 2.1: `ActionTypeDefaults` model
- Component 2.4: Default executor configuration (for initial template values)

**Features**:
- [AI Agent] Create `app/src/ui/action_type_defaults.py` with the action type defaults editor
- [AI Agent] Implement payload template editors for all five action types (implement, test, review, document, debug) with a field per payload key
- [AI Agent] Implement variable placeholder hints showing available `{{variables}}`
- [AI Agent] Implement save/load for action type defaults via `ConfigManager`
- [AI Agent] Create `app/src/ui/secrets_screen.py` with the secrets management screen
- [AI Agent] Implement secret input fields for GitHub Token, Autopilot API Key, and LLM API Key (optional)
- [AI Agent] Implement save secrets to `.env/.env.local` via `ConfigManager`

**Description**:
This component builds two configuration screens. The Action Type Defaults screen lets users configure the default payload template for each of the five Execute Action item types. Each type has multiple payload fields (repository, branch, agent_instructions, model, role, agent_paths, callback_url, timeout_minutes), and the user can use `{{variable}}` placeholders that will be resolved at dispatch time. The Secrets screen provides a simple form to enter and save sensitive values (GitHub token, API keys) to the local `.env/.env.local` file via the config manager. Both screens are part of the configuration flow that must be completed before project operations.

**Acceptance Criteria**:
- [ ] Action type defaults screen renders at `/config/action-types`
- [ ] Screen displays a tabbed or accordion interface with one section per action type (implement, test, review, document, debug)
- [ ] Each section has input fields for all payload template keys (repository, branch, agent_instructions, model, role, agent_paths, callback_url, timeout_minutes)
- [ ] A hints panel shows available `{{variable}}` placeholders and their descriptions
- [ ] Existing defaults are loaded and pre-populated on screen entry
- [ ] Save button persists all five type templates via `ConfigManager.save_action_type_defaults()`
- [ ] Secrets screen renders at `/config/secrets`
- [ ] Secrets screen has input fields for: `GITHUB_TOKEN`, `AUTOPILOT_API_KEY`, `OPENAI_API_KEY` (optional)
- [ ] Secret input fields use password-type masking
- [ ] Save button persists secrets to `.env/.env.local` via `ConfigManager.save_secret()`
- [ ] Success notifications display after save on both screens
- [ ] Both screens have "Back to Home" navigation

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/action_type_defaults.py`
  - `app/src/ui/secrets_screen.py`
  - `app/src/main.py` (update `/config/action-types` and `/config/secrets` routes)
- **Key Functions/Classes**:
  - `render_action_type_defaults(app_state: AppState) -> None`
  - `render_secrets_screen(app_state: AppState) -> None`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: NiceGUI 2.x, `ConfigManager` (Component 2.3), `ActionTypeDefaults` model (Component 2.1)

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/action_type_defaults.py`**: Create `render_action_type_defaults(app_state)`. Load existing defaults via `app_state.config_manager.get_action_type_defaults()` — if they exist, pre-populate; if not, load from `app/config/defaults.yaml` (the default Autopilot templates from Phase 2). Build the UI: (1) Title label "Action Type Defaults". (2) A variable reference panel (collapsible `ui.expansion`) listing all available variables: `{{repository}}`, `{{branch}}`, `{{phase_id}}`, `{{phase_name}}`, `{{component_id}}`, `{{component_name}}`, `{{component_breakdown_doc}}`, `{{agent_paths}}`, `{{webhook_url}}`, `{{pr_number}}` — with a one-line description per variable. (3) Use `ui.tabs()` with five tabs — one per action type. (4) For each tab, create a `ui.tab_panel()` containing input fields for each payload key. Use `ui.input()` for short fields (repository, branch, model, role, agent_paths, callback_url) and `ui.textarea()` for `agent_instructions` (which will contain longer prompt text). Use `ui.number()` for `timeout_minutes`. Pre-populate from loaded defaults — each action type's template is a `dict[str, Any]`, so iterate the keys and create appropriate input fields. (5) A global Save button at the bottom that collects all field values from all five tabs, constructs an `ActionTypeDefaults` model, and saves via `config_manager.save_action_type_defaults()`. Show success notification.

- **File 2: `app/src/ui/secrets_screen.py`**: Create `render_secrets_screen(app_state)`. Build a form with: (1) Title "Secrets Management". (2) A brief explanation: "Secrets are stored locally in .env/.env.local and never committed to the repository." (3) `ui.input("GitHub Token", password=True, password_toggle_button=True)` — load existing value hint (show "••••••• (set)" if the env var exists, empty if not). (4) `ui.input("Autopilot API Key", password=True, password_toggle_button=True)` — same pattern. (5) `ui.input("OpenAI API Key (Optional)", password=True, password_toggle_button=True)` — same pattern. (6) Save button that calls `app_state.config_manager.save_secret(key_name, value)` for each non-empty field. Only save fields where the user has entered a new value (don't overwrite existing secrets with empty strings). Show success notification. (7) "Back to Home" navigation button.

- **File 3: `app/src/main.py`** (update): Replace placeholders in `/config/action-types` and `/config/secrets` routes with `render_action_type_defaults(app_state)` and `render_secrets_screen(app_state)`.

**Test Requirements**:
- [ ] Unit tests: `render_action_type_defaults()` executes without errors
- [ ] Unit tests: `render_secrets_screen()` executes without errors
- [ ] Unit tests: Saving action type defaults round-trips through `ConfigManager` (service-layer test)
- [ ] Manual verification: All five tabs render with correct fields
- [ ] Manual verification: Variable hints display correctly
- [ ] Manual verification: Secrets are saved and can be retrieved

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-4-component-4-4-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-4.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
For the action type defaults editor, the payload keys match the Autopilot sample payload structure: `repository`, `branch`, `agent_instructions`, `model`, `role`, `agent_paths`, `callback_url`, `timeout_minutes`. The Review type also includes `pr_number`. The Debug type has an empty `agent_instructions` by default (user fills in ad-hoc). For secrets, never display the actual secret value in the input field — instead show a placeholder like "••••••• (currently set)" if the env var exists. When saving, only write non-empty values to avoid accidentally blanking a secret. NiceGUI's `ui.input(password=True, password_toggle_button=True)` provides the masked input with a toggle to reveal.

---

### Component 4.5 — Link New Project Screen

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 4.1: `AppState`, page routing, NiceGUI app
- Component 3.2: `ProjectService.link_project()` for repo scanning and parsing
- Component 3.4: `ActionGenerator.generate_actions()` for action derivation
- Component 3.5: `PayloadResolver` for initial payload resolution
- Component 2.3: `ConfigManager` for loading action type defaults

**Features**:
- [AI Agent] Create `app/src/ui/link_project.py` with the Link New Project form
- [AI Agent] Implement form fields: GitHub repository (owner/repo format), GitHub token env var name
- [AI Agent] Implement scanning trigger with progress indication (spinner)
- [AI Agent] Implement results display: phases found, components found, agent files found
- [AI Agent] Implement error display for scan failures (repo not found, auth failed, phase-progress.json missing)
- [AI Agent] Implement action generation and initial payload resolution after successful scan
- [AI Agent] Implement navigation to main screen on success

**Description**:
This component builds the screen for linking a new GitHub project to Dispatch. The user enters a repository in `owner/repo` format and the name of the environment variable containing the GitHub token. On submit, the app uses the `ProjectService` to scan the remote repo for `docs/phase-progress.json` and agent files, then the `ActionGenerator` to derive Execute Action items, and the `PayloadResolver` to perform initial payload resolution. The results are displayed (number of phases, components, and agent files found), and the user is navigated to the main screen. Errors are displayed inline with clear, actionable messages.

**Acceptance Criteria**:
- [ ] Link project screen renders at `/project/link`
- [ ] Form fields: Repository (text, required, `owner/repo` format), GitHub Token Env Var (text, required, defaults to `GITHUB_TOKEN`)
- [ ] Submit button triggers the scanning workflow with a visible spinner/loading indicator
- [ ] On success: displays summary (e.g., "Found 3 phases, 8 components, 2 agent files")
- [ ] On success: generates actions and resolves initial payloads
- [ ] On success: saves the project and navigates to `/project/{project_id}` (main screen)
- [ ] On failure (phase-progress.json not found): displays error "phase-progress.json not found at docs/phase-progress.json in {repo}"
- [ ] On failure (auth error): displays error "Authentication failed. Check your GitHub token."
- [ ] On failure (invalid repo format): displays inline validation error
- [ ] "Back" button navigates to `/`
- [ ] `from app.src.ui.link_project import render_link_project` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/link_project.py`
  - `app/src/main.py` (update `/project/link` route)
- **Key Functions/Classes**:
  - `render_link_project(app_state: AppState) -> None`
  - Internal async `_scan_and_link(app_state, repository, token_env_key)` for the scanning workflow
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: `ProjectService` (Components 3.2, 3.3), `ActionGenerator` (Component 3.4), `PayloadResolver` (Component 3.5), `ConfigManager` (Component 2.3)

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/link_project.py`**: Create `render_link_project(app_state)`. Build the form: (1) Title "Link New Project". (2) `repo_input = ui.input("GitHub Repository", placeholder="owner/repo-name")` with validation for `owner/repo` format. (3) `token_var_input = ui.input("GitHub Token Env Var", value="GITHUB_TOKEN")` with a helper label "Name of the env var in .env.local holding the GitHub token". (4) A `ui.button("Scan & Link")` that triggers the scanning workflow. (5) A results area (initially hidden) to show scan results or errors. (6) A loading spinner displayed during scanning (use `ui.spinner()` inside a `ui.row()` that is shown/hidden). Define an `async` or threaded scan function `_scan_and_link()`: (a) Retrieve the token value via `app_state.settings.get_secret(token_env_key)` — if empty, show error "Token not found in environment. Add {token_env_key} to .env.local via Manage Secrets." (b) Create a `GitHubClient` with the token. (c) Create a `ProjectService` with settings and the client. (d) Call `project_service.link_project(repository, token_env_key)` — wrap in try/except `ProjectLinkError` to display errors. (e) On success, load action type defaults via `config_manager.get_action_type_defaults()`. (f) Generate actions via `action_generator.generate_actions(project.phases, action_type_defaults)`. (g) Resolve initial payloads for each action using `payload_resolver`. (h) Set `project.actions = generated_actions`. (i) Save the project via `project_service.save_project(project)`. (j) Set `app_state.current_project = project`. (k) Display success summary and navigate to `/project/{project.project_id}`. Use `ui.timer()` or `ui.run_javascript` or background tasks to avoid blocking the UI during the scan. NiceGUI supports running blocking code with `await run.io_bound()` or similar patterns.

- **File 2: `app/src/main.py`** (update): Replace placeholder in `/project/link` route with `render_link_project(app_state)`.

**Test Requirements**:
- [ ] Unit tests: Scanning workflow with mocked `ProjectService` and `ActionGenerator` completes successfully
- [ ] Unit tests: Error handling for `ProjectLinkError` produces correct error message
- [ ] Unit tests: Action generation produces expected count for sample phase-progress data
- [ ] Manual verification: Loading spinner appears during scan
- [ ] Manual verification: Success summary displays correct counts

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-4-component-4-5-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-4.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
The scanning operation involves network calls to the GitHub API, which may take a few seconds. Use NiceGUI's async patterns or `run.io_bound()` to run the blocking HTTP calls without freezing the UI. The `token_env_key` defaults to `GITHUB_TOKEN` — the user should have already set this value via the Secrets screen. If the token is not found, show a helpful error directing them to the Secrets screen. After successful linking, the project is saved immediately so it appears in the Load Project list even if the user navigates away before explicitly saving from the main screen.

---

### Component 4.6 — Load Project Screen

**Priority**: Must-have

**Estimated Effort**: 1 hour

**Owner**: AI Agent

**Dependencies**:
- Component 4.1: `AppState`, page routing, NiceGUI app
- Component 3.3: `ProjectService.list_projects()` and `ProjectService.load_project()` for project retrieval

**Features**:
- [AI Agent] Create `app/src/ui/load_project.py` with the Load Project list screen
- [AI Agent] Implement project listing from saved projects in the data directory
- [AI Agent] Implement click-to-load navigation to the main screen
- [AI Agent] Implement empty state handling (no saved projects)
- [AI Agent] Implement project deletion from the list

**Description**:
This component builds the screen for loading previously saved projects. It lists all projects found in the data directory (via `ProjectService.list_projects()`), displaying the project name, repository, and last updated date. Clicking a project loads it and navigates to the main screen. If no projects are saved, an empty state message directs the user to link a new project. A delete action allows removing unwanted projects.

**Acceptance Criteria**:
- [ ] Load project screen renders at `/project/load`
- [ ] Screen lists all saved projects with project name, repository, and last updated date
- [ ] Projects are sorted by most recently updated first
- [ ] Clicking a project loads it via `ProjectService.load_project()` and navigates to `/project/{project_id}`
- [ ] Empty state displays "No saved projects. Link a new project to get started." with a link to `/project/link`
- [ ] Delete button on each project removes it via `ProjectService.delete_project()` and refreshes the list
- [ ] Delete prompts for confirmation before removing
- [ ] "Back" button navigates to `/`
- [ ] `from app.src.ui.load_project import render_load_project` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/load_project.py`
  - `app/src/main.py` (update `/project/load` route)
- **Key Functions/Classes**:
  - `render_load_project(app_state: AppState) -> None`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: `ProjectService` (Component 3.3)

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/load_project.py`**: Create `render_load_project(app_state)`. Call `app_state.project_service.list_projects()` to get the project summaries. Build the UI: (1) Title "Load Project". (2) If the list is empty, display a `ui.label("No saved projects.")` and a `ui.button("Link New Project", on_click=lambda: ui.navigate.to('/project/link'))`. (3) If projects exist, create a `ui.list()` or column of `ui.card()` elements, one per project. Each card shows: project name (bold), repository, and `Updated: {updated_at}`. The card is clickable — on click, call `app_state.project_service.load_project(project_id)`, set `app_state.current_project`, and navigate to `/project/{project_id}`. Add a small delete icon button (`ui.button(icon='delete')`) on each card that triggers a `ui.dialog()` confirmation ("Delete project {name}?") — on confirm, call `app_state.project_service.delete_project(project_id)` and refresh the list. (4) "Back to Home" button navigates to `/`. Use `@ui.refreshable` on the project list portion so it can be refreshed after deletion without full page reload.

- **File 2: `app/src/main.py`** (update): Replace placeholder in `/project/load` route with `render_load_project(app_state)`.

**Test Requirements**:
- [ ] Unit tests: `render_load_project()` executes without errors with empty project list
- [ ] Unit tests: `render_load_project()` executes with multiple projects in the list
- [ ] Manual verification: Clicking a project navigates to the main screen
- [ ] Manual verification: Delete removes the project and refreshes the list

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-4-component-4-6-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-4.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
`list_projects()` returns `ProjectSummary` objects (lightweight, not full project data) for fast listing. The full `load_project()` is called only when the user clicks a specific project. The `@ui.refreshable` decorator is useful here — decorate the list rendering function so it can be re-invoked after a deletion. Sorting by `updated_at` descending means the most recently worked-on project appears first, which is the expected behaviour for a returning user.

---

### Component 4.7 — Main Screen Layout & Action List

**Priority**: Must-have

**Estimated Effort**: 3 hours

**Owner**: AI Agent

**Dependencies**:
- Component 4.1: `AppState`, page routing, NiceGUI app
- Component 4.5: Link project workflow (to have a loaded project with actions)
- Component 4.6: Load project workflow
- Component 3.4: `ActionGenerator` for action ordering
- Component 3.5: `PayloadResolver` for payload context
- Component 2.1: `Project`, `Action`, `ActionType`, `ActionStatus` models

**Features**:
- [AI Agent] Create `app/src/ui/main_screen.py` with the main project screen layout
- [AI Agent] Implement project header with project name, Save Project button, and Load Project button
- [AI Agent] Implement split-panel layout (left/right) using NiceGUI's Quasar splitter
- [AI Agent] Implement left panel with scrollable list of Execute Action items grouped by phase
- [AI Agent] Implement action item display showing phase, component (for Implement), type, and status
- [AI Agent] Implement click-to-dispatch on action items — dispatches payload to executor

**Description**:
This component builds the main application screen — the primary workspace for managing and dispatching Execute Action items. The layout follows the solution design: a header with the project name and control buttons, and a split-panel body. The left panel contains a scrollable list of all Execute Action items, grouped by phase. Each action shows its type, component reference (for Implement), and status. Clicking an action item dispatches its resolved payload to the configured executor. The right panel (built in Component 4.8) will display responses.

**Acceptance Criteria**:
- [ ] Main screen renders at `/project/{project_id}` with the loaded project
- [ ] Header displays the project name, a "Save" button, and a "Home" button
- [ ] Save button calls `ProjectService.save_project()` and shows a success notification
- [ ] Layout is split into left (40%) and right (60%) panels using Quasar splitter
- [ ] Left panel contains a scrollable list of all Execute Action items
- [ ] Actions are grouped by phase with a phase header (e.g., "Phase 1: Project Bootstrap")
- [ ] Within each phase, actions appear in correct order: Implement per component, then Test, Review, Document
- [ ] Each action item displays: action type icon/label, component name (for Implement), and status badge
- [ ] Status badges use colours: grey for not_started, blue for dispatched, green for completed
- [ ] Clicking an action item dispatches its payload to the executor via `AutopilotExecutor.dispatch()`
- [ ] During dispatch, a loading indicator appears on the clicked action
- [ ] If no project is loaded, redirect to `/`
- [ ] `from app.src.ui.main_screen import render_main_screen` imports successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/main_screen.py`
  - `app/src/main.py` (update `/project/{project_id}` route)
- **Key Functions/Classes**:
  - `render_main_screen(app_state: AppState, project_id: str) -> None`
  - `_render_action_list(app_state: AppState) -> None` — renders the left panel action list
  - `_dispatch_action(app_state: AppState, action: Action) -> ExecutorResponse` — dispatches a single action
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: NiceGUI 2.x, `ProjectService`, `PayloadResolver`, `AutopilotExecutor`, all models

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/main_screen.py`**: Create `render_main_screen(app_state, project_id)`. First, load the project: if `app_state.current_project` is `None` or has a different ID, load via `project_service.load_project(project_id)` and set it on `app_state`. If loading fails, navigate to `/` with an error notification. Build the layout: (1) **Header row**: `ui.row()` with project name label (`text-h4`), a `ui.button("Save", icon="save")` that calls `project_service.save_project(app_state.current_project)` and notifies, and a `ui.button("Home", icon="home")` that navigates to `/`. (2) **Split panel**: Use `ui.splitter(value=40)` to create the left/right split. Inside the `splitter.before` slot: render the action list. Inside the `splitter.after` slot: render a placeholder for now (Component 4.8 fills this in). For the action list: iterate `app_state.current_project.actions`, group by `phase_id`. For each phase, find the matching `PhaseData` to get `phase_name`. Render a `ui.expansion(f"Phase {phase_id}: {phase_name}", value=True)` as the group header. Inside each expansion, render a `ui.list()` of action items. Each action item is a `ui.item()` with: an icon based on `action_type` (e.g., build icon for implement, bug icon for debug, science icon for test, grading icon for review, description icon for document), the action label (e.g., "Implement: Component Name" or "Test Phase 1"), and a `ui.badge()` for status with colour mapping (`not_started` → `grey`, `dispatched` → `blue`, `completed` → `green`). Make each item clickable. On click, execute `_dispatch_action()`: (a) Load executor config from `config_manager`. (b) Build context via `payload_resolver.build_context(project, action.phase_id, action.component_id, executor_config)`. (c) Resolve payload via `payload_resolver.resolve_payload(action.payload, context)`. (d) Dispatch via `executor.dispatch(resolved_payload.payload, executor_config)`. (e) Store the response on `action.executor_response = response.model_dump()`. (f) Update action status to `dispatched`. (g) Refresh the right panel display (Component 4.8). Use `@ui.refreshable` on the action list so it re-renders after status changes.

- **File 2: `app/src/main.py`** (update): Replace placeholder in `/project/{project_id}` route with `render_main_screen(app_state, project_id)`.

**Test Requirements**:
- [ ] Unit tests: Action list renders correct number of items for sample project data
- [ ] Unit tests: Actions are grouped by phase correctly
- [ ] Unit tests: `_dispatch_action()` calls executor with resolved payload (mocked executor)
- [ ] Unit tests: Action status updates to `dispatched` after dispatch
- [ ] Manual verification: Split panel renders with correct proportions
- [ ] Manual verification: Clicking an action dispatches and updates status badge

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-4-component-4-7-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-4.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
NiceGUI's `ui.splitter()` uses Quasar's QSplitter component — it accepts a `value` parameter (0-100) for the initial split percentage. The left panel should be scrollable for projects with many actions — wrap the content in a `ui.scroll_area()`. Phase grouping uses `ui.expansion()` which is collapsible — expand all by default (`value=True`) so actions are immediately visible. The dispatch operation may take a second (network call to executor) — use NiceGUI's async machinery or `run.io_bound()` to avoid blocking the UI thread. After dispatch, the action's `executor_response` is stored on the action object in memory, and the project should be auto-saved to persist the response. Consider a debounced auto-save after each dispatch.

---

### Component 4.8 — Main Screen Response Display & Controls

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 4.7: Main screen layout with split-panel and dispatch functionality
- Component 3.6: `AutopilotExecutor` for response format
- Component 3.7: `WebhookService` for webhook data retrieval

**Features**:
- [AI Agent] Implement right panel top section: API response code and message display
- [AI Agent] Implement right panel bottom section: webhook response code and payload message
- [AI Agent] Implement refresh button to poll for webhook data
- [AI Agent] Implement "Mark Complete" button on each action item
- [AI Agent] Implement conditional webhook section visibility (only when webhook URL configured)
- [AI Agent] Implement response area update after each dispatch

**Description**:
This component completes the main screen's right panel with response display areas and control buttons. The top section shows the executor API response (status code and message) after an action is dispatched. The bottom section shows webhook callback data (status and payload message) when a webhook URL is configured and data has been received. A refresh button triggers a poll for new webhook data. Each action item gets a "Mark Complete" button that updates its status to completed. This component ties together the dispatch workflow with visible feedback.

**Acceptance Criteria**:
- [ ] Right panel top section displays "Response: {status_code}" and the response message after a dispatch
- [ ] Right panel top section shows "No action dispatched yet" when no dispatch has occurred
- [ ] Right panel bottom section displays webhook status and payload message when data is received
- [ ] Right panel bottom section is hidden if no webhook URL is configured in executor config
- [ ] Right panel bottom section shows "Waiting for webhook response..." when an action is dispatched but no webhook data yet
- [ ] Refresh button polls `WebhookService` for the dispatched action's `run_id` and updates the display
- [ ] "Mark Complete" button on each action updates status to `completed` and changes the badge colour to green
- [ ] Response display updates dynamically after each dispatch (no page reload needed)
- [ ] The response display shows data for the most recently dispatched action

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/main_screen.py` (extend from Component 4.7)
- **Key Functions/Classes**:
  - `_render_response_panel(app_state: AppState) -> None` — renders the right panel content
  - `_poll_webhook(app_state: AppState, run_id: str) -> dict | None` — polls for webhook data
  - `_mark_complete(app_state: AppState, action: Action) -> None` — marks an action as completed
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: `WebhookService` (Component 3.7), `ExecutorConfig` (Component 2.1)

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/main_screen.py`** (extend): Add a `_render_response_panel(app_state)` function decorated with `@ui.refreshable`. This function renders the right panel content inside the `splitter.after` slot. Track the "last dispatched action" on `app_state` (e.g., `app_state.last_dispatched_action: Action | None`). Build the right panel: (1) **API Response section**: `ui.card()` with title "Executor Response". If no action dispatched yet, show `ui.label("No action dispatched yet.").classes('text-grey')`. If dispatched, show: `ui.label(f"Status: {response.status_code}")` with colour coding (2xx green, 4xx/5xx red, 0 orange for connection errors), `ui.label(f"Message: {response.message}")`, and if `run_id` exists, `ui.label(f"Run ID: {response.run_id}")`. (2) **Webhook Response section** (conditional): Only render if `executor_config.webhook_url` is set. `ui.card()` with title "Webhook Response". If the action has `webhook_response`, display the status and payload message from the stored data. If not, show "Waiting for webhook response..." with a `ui.button("Refresh", icon="refresh")`. The refresh button calls `_poll_webhook(app_state, run_id)`: retrieve from `webhook_service.retrieve(run_id)`, if found, store on `action.webhook_response`, and call `_render_response_panel.refresh()` to update the display. (3) **Mark Complete section**: Conditionally display a `ui.button("Mark Complete", icon="check_circle", color="positive")` for the currently displayed action. On click, call `_mark_complete()`: set `action.status = ActionStatus.COMPLETED`, save the project, and refresh both the action list and response panel. Update `_dispatch_action()` from Component 4.7 to: set `app_state.last_dispatched_action = action`, and call `_render_response_panel.refresh()` after storing the executor response.

**Test Requirements**:
- [ ] Unit tests: Response panel shows correct data after dispatch (mocked action with response)
- [ ] Unit tests: Webhook section hidden when no webhook URL configured
- [ ] Unit tests: `_poll_webhook()` retrieves data from `WebhookService` correctly
- [ ] Unit tests: `_mark_complete()` updates action status and saves project
- [ ] Manual verification: Response updates after clicking an action
- [ ] Manual verification: Refresh button retrieves webhook data

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-4-component-4-8-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-4.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
The `@ui.refreshable` decorator is key here — it allows the response panel to be re-rendered without reloading the entire page. When the user dispatches a different action, calling `_render_response_panel.refresh()` updates just the right panel. The webhook poll is manual (user clicks Refresh) rather than automatic — this keeps the implementation simple and avoids background polling complexity. The `run_id` from the executor response is used as the key for webhook lookup. If the executor doesn't return a `run_id` (connection error etc.), the webhook section shows "No run ID — webhook polling unavailable".

---

### Component 4.9 — Debug Action Insertion & Payload Editing

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 4.7: Main screen with action list
- Component 3.4: `ActionGenerator.insert_debug_action()` for debug insertion logic
- Component 3.5: `PayloadResolver` for variable resolution display

**Features**:
- [AI Agent] Implement "Add Debug" control per phase in the action list
- [AI Agent] Implement debug action insertion at a user-selected position within a phase
- [AI Agent] Implement payload editing dialog — view and edit the resolved payload for any action
- [AI Agent] Implement save edited payload back to the action
- [AI Agent] Implement payload variable highlight (show unresolved variables in a different colour)

**Description**:
This component adds two key interactive features to the main screen: inserting Debug-type Execute Action items and editing individual action payloads. The Debug insertion UI provides a control per phase group that lets the user insert a Debug action at any position in that phase's action list. The payload editor opens a dialog showing the action's current payload as editable JSON, highlights any unresolved `{{variable}}` placeholders, and lets the user save changes back to the action.

**Acceptance Criteria**:
- [ ] Each phase group in the action list has an "Add Debug" button
- [ ] Clicking "Add Debug" opens a dialog to select the insertion position (0 to N, where N is the count of actions in the phase)
- [ ] After insertion, the action list refreshes with the new Debug action at the selected position
- [ ] Debug actions appear with a distinct icon and "Debug" label
- [ ] Each action item has an "Edit Payload" button/icon
- [ ] Clicking "Edit Payload" opens a dialog with the action's payload displayed as formatted JSON in an editable text area
- [ ] Unresolved `{{variable}}` placeholders are visually indicated (in the JSON text or as a warning label)
- [ ] Saving the edited payload updates the action's payload and closes the dialog
- [ ] Invalid JSON in the editor is caught with a validation error, preventing save
- [ ] Edited payloads persist when the project is saved
- [ ] `from app.src.ui.main_screen import render_main_screen` still imports (all in same file)

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/main_screen.py` (extend with debug and payload editing features)
- **Key Functions/Classes**:
  - `_insert_debug_action(app_state: AppState, phase_id: int, position: int) -> None`
  - `_show_payload_editor(app_state: AppState, action: Action) -> None`
  - `_save_edited_payload(action: Action, new_payload_json: str) -> bool`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: `ActionGenerator` (Component 3.4), JSON for payload serialisation

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/main_screen.py`** (extend): Add an "Add Debug" button within each phase expansion group (from Component 4.7), positioned after the last action in the phase. On click, open a `ui.dialog()` with a `ui.number("Insert at position", min=0, max=phase_action_count)` and a Confirm button. On confirm, call `ActionGenerator.insert_debug_action(app_state.current_project.actions, phase_id, position, action_type_defaults)`. Then re-resolve the new Debug action's payload via `PayloadResolver`. Refresh the action list via `_render_action_list.refresh()`. Add an "Edit Payload" icon button (`ui.button(icon='edit')`) on each action item row. On click, open `_show_payload_editor()`: create a `ui.dialog()` with `ui.textarea()` pre-populated with `json.dumps(action.payload, indent=2)`. Set the textarea to a large size (e.g., `.props('rows=20')` with a fixed width). Below the textarea, display any unresolved variables (scan the JSON string for `{{variable}}` patterns and list them with a warning icon). Add "Save" and "Cancel" buttons. The Save button calls `_save_edited_payload()`: try `json.loads(new_json)` — if invalid, show `ui.notify("Invalid JSON", type="negative")` and don't close. If valid, update `action.payload = parsed_json`, close the dialog, and refresh the action list. If the user cancels, close without saving.

**Test Requirements**:
- [ ] Unit tests: `insert_debug_action()` adds a Debug action at the correct position (re-uses service tests)
- [ ] Unit tests: `_save_edited_payload()` validates JSON and rejects invalid input
- [ ] Unit tests: `_save_edited_payload()` updates action payload on valid input
- [ ] Manual verification: Debug action appears at the selected position
- [ ] Manual verification: Payload editor displays and saves valid JSON
- [ ] Manual verification: Invalid JSON shows error notification

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-4-component-4-9-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-4.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
The payload editor uses a simple JSON textarea rather than a structured form — this is intentional because payload structures may vary by executor and action type, and a textarea allows full flexibility. The `json.loads()` validation ensures only valid JSON can be saved back. Unresolved variables are detected by scanning the JSON string for `\{\{(\w+)\}\}` patterns — the same regex used in `PayloadResolver`. The "Add Debug" position dialog uses `ui.number()` with min/max bounds to prevent out-of-range insertions. The Debug action inherits its initial payload from the Debug-type defaults in `ActionTypeDefaults`, with the `agent_instructions` field empty by default for the user to fill in.

---

### Component 4.10 — Integration Testing & Phase Validation

**Priority**: Must-have

**Estimated Effort**: 3 hours

**Owner**: AI Agent

**Dependencies**:
- Components 4.1 through 4.9: All UI components must be implemented
- Phase 3 tests still passing (no regression)

**Features**:
- [AI Agent] Create integration tests for the full workflow (mocked APIs)
- [AI Agent] Verify app launches and all screens render without errors
- [AI Agent] Validate E2E scenario preconditions at the UI level
- [AI Agent] Run full quality validation (Black, isort, pytest, evals)
- [AI Agent] Create/update phase implementation context documentation
- [AI Agent] Update the agent runbook with app launch and basic usage instructions

**Description**:
This component completes Phase 4 by consolidating integration tests, running all quality checks, and creating the phase documentation. Integration tests verify the full workflow with mocked external APIs: configure executor → link project → generate actions → dispatch → webhook. Tests verify that the app launches, all screens render, and key workflows complete. The implementation context document captures all Phase 4 components and notable decisions. The agent runbook is updated with instructions for launching and using the app.

**Acceptance Criteria**:
- [ ] Integration test: Full workflow with mocked APIs — configure executor config in memory → link project (mocked GitHub) → generate actions → dispatch action (mocked executor) → store webhook data → retrieve webhook data
- [ ] Integration test: App imports and initialises without errors
- [ ] Integration test: All page routes are registered and respond to requests
- [ ] All unit tests pass: `pytest -q --cov=app/src --cov-report=term-missing`
- [ ] Test coverage on `app/src/` is ≥ 30%
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes
- [ ] `python scripts/evals.py` passes (all public functions have docstrings, no TODO/FIXME)
- [ ] Phase 3 tests still pass (no regression)
- [ ] `docs/implementation-context-phase-4.md` exists with entries for all Phase 4 components
- [ ] Agent runbook updated with: how to launch the app, URL to access, first-time configuration flow
- [ ] E2E scenario readiness: E2E-001 through E2E-003 can now be executed via the UI (documented in runbook)

**Technical Details**:
- **Files to Create/Modify**:
  - `tests/test_ui_integration.py`
  - `tests/test_app_startup.py`
  - `docs/implementation-context-phase-4.md`
  - `docs/components/phase-4-component-4-10-overview.md`
  - `docs/autopilot-runbook.md` (update with Dispatch app instructions, or create a separate `docs/dispatch-runbook.md`)
- **Key Functions/Classes**: Integration test functions covering the full dispatch workflow
- **Human/AI Agent**: AI Agent writes all tests and documentation
- **Dependencies**: pytest, pytest-cov, httpx (for test client), all Phase 4 UI modules

**Detailed Implementation Requirements**:

- **File 1: `tests/test_app_startup.py`**: Test that the NiceGUI app initialises correctly: (1) Import `app` from `app.src.main` — verify no import errors. (2) Verify `AppState` initialises with `Settings` from a test environment (use temp data directory). (3) Verify all page routes are registered (check NiceGUI's route registry). (4) Verify webhook endpoints are registered (test via httpx TestClient against the FastAPI app — POST to `/webhook/callback` with sample data, GET from `/webhook/poll/{run_id}`).

- **File 2: `tests/test_ui_integration.py`**: Full workflow integration test with all external services mocked: (1) Create an `AppState` with a test `Settings` (temp data dir). (2) Save an executor config via `ConfigManager`. (3) Save action type defaults via `ConfigManager`. (4) Verify `app_state.is_fully_configured` returns `True`. (5) Mock `GitHubClient` to return sample phase-progress.json content and agent files. (6) Call `ProjectService.link_project()` with the mocked client — verify `Project` returned with correct phases and actions. (7) Call `ActionGenerator.generate_actions()` — verify correct count and ordering. (8) Resolve a payload via `PayloadResolver` — verify all variables replaced. (9) Mock the executor HTTP call — call `AutopilotExecutor.dispatch()` and verify response. (10) Store webhook data via `WebhookService` and verify retrieval. (11) Mark action as completed and verify status change. (12) Save and reload project — verify round-trip. This tests the full chain at the service layer, confirming all Phase 3 and Phase 4 code integrates correctly. Add a separate test for the UI rendering if NiceGUI provides a test client (otherwise, rendering tests are manual).

- **File 3: `docs/implementation-context-phase-4.md`**: Running log with entries for Components 4.1–4.10. Each entry includes: component ID and name, status (completed), key files created, notable decisions (e.g., "module-level AppState singleton for cross-page state", "ui.refreshable for dynamic panel updates", "manual webhook polling via refresh button", "JSON textarea for payload editing", "config gatekeeping on initial screen").

- **File 4: `docs/components/phase-4-component-4-10-overview.md`**: Summary of the testing and validation component.

- **File 5: Agent runbook update**: Add a "Dispatch Application" section with: (1) How to launch: `source .venv/bin/activate && python -m app.src.main`. (2) Access URL: `http://localhost:8080`. (3) First-time setup: Configure Executor → Action Type Defaults → Manage Secrets → Link New Project. (4) Testing: `pytest -q --cov=app/src --cov-report=term-missing`. (5) E2E scenarios now executable via the UI.

**Test Requirements**:
- [ ] All tests in test files pass
- [ ] `pytest -q --cov=app/src --cov-report=term-missing` reports ≥ 30% coverage
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes
- [ ] `python scripts/evals.py` passes
- [ ] Phase 2 and Phase 3 tests still pass

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing with ≥ 30% coverage
- [ ] All quality checks pass (Black, isort, pytest, evals)
- [ ] Documentation created: Component Overview (`docs/components/phase-4-component-4-10-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-4.md`). Maximum 50 lines of markdown per component.
- [ ] Agent runbook updated with Dispatch app launch and usage instructions
- [ ] No regression in existing functionality (Phase 1, 2, and 3 tests still pass)
- [ ] Core application is still working post component implementation

**Notes**:
NiceGUI may or may not provide a formal test client — if not, focus integration tests on the service layer and app initialisation, and rely on manual testing for UI interactions. The httpx `TestClient` can be used against the underlying FastAPI app for webhook endpoint tests. Keep integration tests focused on the critical path: config → link → generate → dispatch → webhook. Edge cases (invalid inputs, error states) are covered by the unit tests in individual components. The agent runbook should contain enough information for an AI agent to launch the app, run through the first-time setup, and execute the E2E scenarios autonomously.

---

## Phase Acceptance Criteria

- [ ] `python -m app.src.main` launches the NiceGUI app and serves the initial screen at `http://localhost:8080`
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
- [ ] Webhook endpoints (`POST /webhook/callback`, `GET /webhook/poll/{run_id}`) are functional
- [ ] All tests pass with ≥ 30% coverage on new code
- [ ] `black --check app/src/` and `isort --check-only app/src/` pass
- [ ] `python scripts/evals.py` passes with no violations
- [ ] Phase 2 and Phase 3 tests still pass (no regression)
- [ ] `docs/implementation-context-phase-4.md` documents all implemented components
- [ ] Agent runbook includes app launch and usage instructions

---

## Cross-Cutting Concerns

### Testing Strategy
- **E2E Testing Scenarios**: After Phase 4, the first three E2E scenarios are fully executable via the UI: E2E-001 (configure, link, generate, dispatch), E2E-002 (load project, dispatch from saved state), E2E-003 (debug action insertion, dispatch). Human-gated live executor tests remain for Phase 7.
- **Unit Testing**: pytest with mocked services. Target ≥ 30% coverage on `app/src/`. Focus on `AppState` initialisation, webhook endpoints, and integration flow.
- **Integration Testing**: Full workflow chain — configure → link (mocked GitHub) → generate actions → dispatch (mocked executor) → webhook store/retrieve → mark complete → save project. These tests validate that all Phase 2, 3, and 4 code integrates correctly.

### Documentation Requirements
- **Developer Context Documentation**: `docs/implementation-context-phase-4.md`, `docs/components/phase-4-component-4-X-overview.md` per component
- **Agent Runbook**: Updated with Dispatch app launch instructions, first-time setup flow, and E2E test execution steps
- **Code Documentation**: Google-style docstrings on all public functions and classes in `app/src/ui/` and `app/src/main.py`
- **API Documentation**: Webhook endpoints documented in implementation context
- **Architecture Decision Records**: Document decisions in implementation context: NiceGUI page routing pattern, AppState singleton for cross-page state, `@ui.refreshable` for dynamic updates, manual webhook polling, JSON textarea for payload editing, config gatekeeping pattern
