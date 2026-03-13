# Phase 5: UI Enhancements & Workflow Polish

## Phase Overview

**Objective**: Refine the user experience with improved navigation flow, comprehensive error handling, mobile-responsive layouts for iPhone Safari, and workflow quality-of-life features. This phase transforms the functional MVP from Phase 4 into a polished, pleasant-to-use application that works seamlessly on both macOS desktop and iPhone Safari.

**Deliverables**:
- Navigation improvements with smooth screen transitions, back navigation, and loading indicators across all screens
- Comprehensive error handling with toast notifications, inline form validation, and descriptive API error surfacing
- Mobile-responsive layouts tested for iPhone Safari (375px viewport), with stacked panels on small screens
- Workflow quality-of-life features: colour-coded status indicators, phase grouping/filtering, confirmation dialogs for re-dispatch, and clear visual hierarchy

**Dependencies**:
- Phase 4 complete (all UI screens functional: initial screen, executor config, action type defaults, secrets, link project, load project, main screen with dispatch workflow)
- Phase 3 complete (all backend services operational)
- Phase 2 complete (data models, config manager, settings module)
- NiceGUI 2.x with Quasar components available
- Python 3.13+ virtual environment activated

## Phase Goals

- Navigation between all screens is smooth with no broken routes, consistent back navigation, and loading indicators for async operations
- All GitHub API and executor API errors are surfaced with clear, actionable messages via toast notifications
- UI is fully usable on iPhone Safari (tested at 375px viewport width) with stacked panels on narrow screens
- Action items display colour-coded status indicators and are visually grouped by phase with filtering capability
- Confirmation dialogs protect against accidental re-dispatch of already-dispatched actions
- All new code passes Black, isort, evals, and achieves ≥ 30% test coverage on `app/src/`

---

## Components

### Component 5.1 — Navigation Flow & State Management

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 4.1: `AppState`, page routing, `app/src/main.py`
- Component 4.2: Initial screen
- Components 4.3–4.6: All configuration and project screens
- Component 4.7: Main screen

**Features**:
- [AI Agent] Add consistent back navigation to all screens via a reusable header/nav bar component
- [AI Agent] Add loading indicators (spinners) for all async operations: GitHub scanning, executor dispatch, project save/load
- [AI Agent] Improve in-memory app state management with proper state transitions and guards
- [AI Agent] Add breadcrumb or contextual title on each screen so the user always knows where they are
- [AI Agent] Add smooth transitions between screens (NiceGUI page transition support)

**Description**:
This component improves the navigation experience across all screens. Currently each screen independently implements back buttons and navigation. This component extracts a reusable page layout wrapper that provides a consistent header with the app title, contextual breadcrumbs, and back navigation. Loading indicators are added for all async operations (GitHub scanning, executor dispatch, project save/load) so users always know when something is in progress. The `AppState` is hardened with proper state transition guards — preventing stale state from causing confusing UI behaviour (e.g., navigating to the main screen without a loaded project).

**Acceptance Criteria**:
- [ ] All screens share a consistent page layout with app title header and back navigation
- [ ] Each screen displays a contextual title or breadcrumb showing the current location (e.g., "Dispatch > Configure Executor")
- [ ] Back button on every non-initial screen navigates to the previous logical screen (not browser back)
- [ ] Loading spinner appears during GitHub repo scanning (Link Project screen)
- [ ] Loading spinner appears during executor dispatch (Main screen)
- [ ] Loading spinner appears during project save and project load operations
- [ ] Navigating to `/project/{id}` without a valid project redirects to `/` with a notification
- [ ] `AppState` prevents stale project references after navigating away from a project
- [ ] Page transitions do not produce visual flickering or layout jumps

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/components.py` (create/extend with reusable layout wrapper)
  - `app/src/ui/state.py` (harden state transitions)
  - `app/src/ui/initial_screen.py` (adopt layout wrapper)
  - `app/src/ui/executor_config.py` (adopt layout wrapper)
  - `app/src/ui/action_type_defaults.py` (adopt layout wrapper)
  - `app/src/ui/secrets_screen.py` (adopt layout wrapper)
  - `app/src/ui/link_project.py` (adopt layout wrapper, improve loading indicator)
  - `app/src/ui/load_project.py` (adopt layout wrapper)
  - `app/src/ui/main_screen.py` (adopt layout wrapper, improve dispatch loading indicator)
- **Key Functions/Classes**:
  - `page_layout(title: str, back_url: str | None = None)` — context manager or function that wraps page content in a consistent layout with header and back nav
  - `loading_overlay()` — reusable loading indicator component (spinner + optional message)
  - `AppState.clear_project() -> None` — resets project state when navigating away
  - `AppState.ensure_project(project_id: str) -> Project` — loads project or redirects if not found
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: NiceGUI 2.x, `AppState` (Component 4.1)

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/components.py`**: Create a `page_layout(title: str, back_url: str | None = None)` function that renders a consistent page wrapper. Implementation: (1) `ui.header()` with a `ui.row()` containing the app title "Dispatch" (clickable, navigates to `/`), a `ui.separator()`, and the `title` parameter as a breadcrumb label. If `back_url` is provided, render a `ui.button(icon='arrow_back')` that navigates to `back_url`. Style the header with `elevated` class and consistent padding. (2) Return control to the caller for the page body content (the calling function renders its content after calling `page_layout()`). Create a `loading_overlay(message: str = "Loading...")` context manager or function: when active, displays a full-width `ui.spinner('dots', size='xl')` with an optional message label. Use a `ui.dialog()` with `persistent=True` and no escape — the dialog is shown/hidden programmatically. Provide `show()` and `hide()` methods. Also create a `with_loading(async_fn, message)` helper that shows the overlay, awaits the function, and hides the overlay in a `finally` block.

- **File 2: `app/src/ui/state.py`** (extend): Add `clear_project()` method that sets `self.current_project = None` and `self.last_dispatched_action = None`. Add `ensure_project(project_id: str) -> Project` that checks if `current_project` matches the requested `project_id`; if not, attempts to load via the project service; if loading fails, navigates to `/` and raises a redirect exception (or returns `None` to signal the caller to abort rendering). Add a `navigation_stack: list[str]` for tracking navigation history if needed for back-button logic, though for simplicity the explicit `back_url` parameter per screen is preferred.

- **Files 3–9: All UI screen files**: Update each screen's render function to call `page_layout(title, back_url)` at the top of the function before rendering screen-specific content. Remove individually implemented back buttons and replace with the shared layout. Wrap async operations (`_scan_and_link`, dispatch calls, save/load calls) with the `with_loading()` helper. Specific mappings: `initial_screen.py` → `page_layout("Home", back_url=None)` (no back on home); `executor_config.py` → `page_layout("Configure Executor", back_url="/")` ; `action_type_defaults.py` → `page_layout("Action Type Defaults", back_url="/")` ; `secrets_screen.py` → `page_layout("Manage Secrets", back_url="/")` ; `link_project.py` → `page_layout("Link New Project", back_url="/")` ; `load_project.py` → `page_layout("Load Project", back_url="/")` ; `main_screen.py` → `page_layout(f"Project: {project_name}", back_url="/")`.

**Test Requirements**:
- [ ] Unit tests: `page_layout()` renders without errors with various title/back_url combinations
- [ ] Unit tests: `loading_overlay()` can be shown and hidden without errors
- [ ] Unit tests: `AppState.ensure_project()` returns project when loaded, returns `None` for unknown ID
- [ ] Unit tests: `AppState.clear_project()` resets state correctly
- [ ] Manual verification: All screens display consistent header with breadcrumb
- [ ] Manual verification: Back navigation works correctly on every screen
- [ ] Manual verification: Loading spinners appear during async operations

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-5-component-5-1-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-5.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality (Phase 4 screens still render and navigate correctly)
- [ ] Core application is still working post component implementation

**Notes**:
NiceGUI's `ui.header()` renders a Quasar QHeader component that sticks to the top of the viewport — ideal for a persistent nav bar. The `page_layout()` function is not a Python context manager in the `with` sense (NiceGUI's declarative model doesn't work that way) — it's a regular function that adds header elements to the current page context, and the caller adds body content after it returns. For loading indicators, prefer a modal dialog overlay rather than inline spinners to prevent the user from interacting with the UI during async operations. NiceGUI's `ui.dialog()` with `value=True` shows the dialog and `value=False` hides it.

---

### Component 5.2 — Error Handling & User Feedback

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 5.1: Reusable `page_layout` and `loading_overlay` components
- Component 4.1: `AppState` with service instances
- Component 3.1: `GitHubClient` for GitHub API error types
- Component 3.6: `AutopilotExecutor` for executor error types

**Features**:
- [AI Agent] Implement toast notifications for all success events (save, dispatch, mark complete, link project)
- [AI Agent] Implement toast notifications for all error events with actionable context
- [AI Agent] Improve inline form validation on all config screens with descriptive error messages
- [AI Agent] Surface GitHub API errors with clear user-facing messages (auth failed, repo not found, file missing, rate limited)
- [AI Agent] Surface executor dispatch errors with status code, message, and retry guidance
- [AI Agent] Add a global error handler for unexpected exceptions that shows a notification without crashing the app

**Description**:
This component adds comprehensive error handling and user feedback across the entire application. Currently, errors may be silently swallowed or displayed inconsistently. This component standardises all success and error feedback through NiceGUI's toast notification system (`ui.notify()`), improves inline form validation with descriptive messages, maps GitHub API and executor API errors to clear user-facing messages, and adds a global exception handler to prevent the app from crashing on unexpected errors.

**Acceptance Criteria**:
- [ ] Success toast appears after: saving executor config, saving action type defaults, saving secrets, saving project, dispatching an action, marking an action complete, linking a project
- [ ] Error toast appears for: GitHub API auth failure ("Authentication failed. Verify your GitHub token in Manage Secrets."), repo not found ("Repository {repo} not found. Check the owner/repo format."), phase-progress.json missing ("phase-progress.json not found at docs/phase-progress.json in {repo}."), rate limiting ("GitHub API rate limit exceeded. Wait and retry.")
- [ ] Error toast appears for executor errors: connection refused ("Cannot reach executor at {url}. Is the executor running?"), 401 ("Executor API key rejected. Check your API key in Manage Secrets."), 4xx/5xx with message from the response body
- [ ] Inline validation on executor config screen: required fields show "This field is required" on blur if empty; URL fields show "Must start with http:// or https://" for invalid URLs
- [ ] Inline validation on Link Project screen: repo format shows "Must be in owner/repo format" for invalid input
- [ ] Global error handler catches unhandled exceptions and shows "An unexpected error occurred. Check the console for details." without crashing the UI
- [ ] Error messages never expose secrets, tokens, or full stack traces to the UI — only in console logs
- [ ] All toasts are dismissible and auto-hide after 5 seconds (error toasts after 8 seconds)

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/components.py` (extend with notification helpers and error mapping)
  - `app/src/ui/executor_config.py` (improve inline validation)
  - `app/src/ui/action_type_defaults.py` (improve inline validation)
  - `app/src/ui/secrets_screen.py` (improve validation)
  - `app/src/ui/link_project.py` (improve error handling and feedback)
  - `app/src/ui/main_screen.py` (improve dispatch error handling)
  - `app/src/main.py` (add global exception handler)
  - `app/src/services/github_client.py` (ensure errors raise typed exceptions)
  - `app/src/services/executor.py` (ensure errors raise typed exceptions)
- **Key Functions/Classes**:
  - `notify_success(message: str) -> None` — wrapper for `ui.notify(message, type="positive", close_button=True, timeout=5000)`
  - `notify_error(message: str) -> None` — wrapper for `ui.notify(message, type="negative", close_button=True, timeout=8000)`
  - `notify_warning(message: str) -> None` — wrapper for `ui.notify(message, type="warning", close_button=True, timeout=5000)`
  - `map_github_error(exc: Exception) -> str` — maps GitHub API exceptions to user-facing messages
  - `map_executor_error(exc: Exception) -> str` — maps executor dispatch exceptions to user-facing messages
  - Custom exception classes: `GitHubAuthError`, `GitHubNotFoundError`, `GitHubRateLimitError`, `ExecutorConnectionError`, `ExecutorAuthError`, `ExecutorDispatchError`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: NiceGUI 2.x, `logging` module, service exception hierarchies

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/components.py`** (extend): Add notification helper functions: `notify_success(message)` calls `ui.notify(message, type="positive", close_button=True, timeout=5000)`; `notify_error(message)` calls `ui.notify(message, type="negative", close_button=True, timeout=8000)`; `notify_warning(message)` calls `ui.notify(message, type="warning", close_button=True, timeout=5000)`. Add error mapping functions: `map_github_error(exc)` matches exception type to message — `GitHubAuthError` → "Authentication failed. Verify your GitHub token in Manage Secrets.", `GitHubNotFoundError` → "Repository not found. Check the owner/repo format.", `GitHubRateLimitError` → "GitHub API rate limit exceeded. Wait a few minutes and retry.", generic `Exception` → "GitHub API error: {str(exc)}". Similarly `map_executor_error(exc)` maps: `ExecutorConnectionError` → "Cannot reach executor at {url}. Is the executor running?", `ExecutorAuthError` → "Executor API key rejected. Check your API key in Manage Secrets.", `ExecutorDispatchError` → "Executor error ({status_code}): {message}", generic → "Dispatch error: {str(exc)}". Ensure no secrets appear in mapped error messages — use the endpoint URL (safe) but never the API key value.

- **File 2: `app/src/services/github_client.py`** (extend): Ensure the GitHub client raises typed exceptions: `GitHubAuthError` on 401 responses, `GitHubNotFoundError` on 404 responses, `GitHubRateLimitError` on 403 with rate limit header, and generic `GitHubApiError` for other failures. These should be defined in `app/src/models/` or a shared `app/src/exceptions.py` module.

- **File 3: `app/src/services/executor.py`** (extend): Ensure the executor raises typed exceptions: `ExecutorConnectionError` on `httpx.ConnectError` or `httpx.ConnectTimeout`, `ExecutorAuthError` on 401/403 responses, `ExecutorDispatchError` on 4xx/5xx with the status code and message from the response body.

- **File 4: `app/src/ui/executor_config.py`** (extend): Replace simple validation with NiceGUI's inline validation. Use `validation` parameter on `ui.input()`: `validation={'Required': lambda v: bool(v.strip())}` for required fields; `validation={'Invalid URL': lambda v: v.startswith(('http://', 'https://')) if v.strip() else True}` for URL fields (allow empty for optional fields). Replace manual error handling in save with `notify_success()` / `notify_error()` calls.

- **File 5: `app/src/ui/link_project.py`** (extend): Add validation on repository input: `validation={'Invalid format': lambda v: bool(re.match(r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$', v)) if v.strip() else True}`. Wrap the `_scan_and_link()` function in a try/except that catches GitHub exceptions and calls `notify_error(map_github_error(exc))`. Replace generic error displays with toast notifications.

- **File 6: `app/src/ui/main_screen.py`** (extend): Wrap the `_dispatch_action()` function in a try/except that catches executor exceptions and calls `notify_error(map_executor_error(exc))`. Add `notify_success(f"Dispatched: {action_label}")` on successful dispatch. Add `notify_success("Marked complete")` on mark complete. Add `notify_success("Project saved")` on save.

- **File 7: `app/src/main.py`** (extend): Add a global exception handler using NiceGUI's `app.on_exception()` or a middleware approach. Log the full traceback to console at ERROR level. Show `notify_error("An unexpected error occurred. Check the console for details.")` to the user. Never expose the stack trace or internal details in the UI notification.

**Test Requirements**:
- [ ] Unit tests: `notify_success()`, `notify_error()`, `notify_warning()` call `ui.notify()` with correct parameters
- [ ] Unit tests: `map_github_error()` returns correct message for each exception type
- [ ] Unit tests: `map_executor_error()` returns correct message for each exception type
- [ ] Unit tests: GitHub client raises `GitHubAuthError` on 401 (mocked httpx response)
- [ ] Unit tests: Executor raises `ExecutorConnectionError` on connection failure (mocked)
- [ ] Manual verification: Toast notifications appear for all success and error scenarios
- [ ] Manual verification: Error messages are helpful and do not expose secrets

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-5-component-5-2-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-5.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
NiceGUI's `ui.notify()` uses Quasar's QNotify plugin under the hood. The `type` parameter accepts `"positive"`, `"negative"`, `"warning"`, and `"info"` for colour-coded toasts. The `close_button=True` adds a dismiss button. The `timeout` is in milliseconds. For inline validation, NiceGUI's `ui.input(validation=...)` parameter accepts a dict mapping error messages to validation lambdas — the error message appears below the input when the lambda returns `False`. The validation runs on every keystroke by default; use `validation` with `on_change` or `lazy_validation=True` parameter (if available) for blur-only validation. Custom exception classes should be lightweight — inherit from a base `DispatchError(Exception)` for consistent handling.

---

### Component 5.3 — Mobile Responsiveness

**Priority**: Must-have

**Estimated Effort**: 3 hours

**Owner**: AI Agent

**Dependencies**:
- Component 5.1: Reusable page layout wrapper
- Component 5.2: Error handling and notifications
- Components 4.2–4.9: All UI screens for responsive adjustment

**Features**:
- [AI Agent] Test and adjust all screen layouts for iPhone Safari (375px width)
- [AI Agent] Convert the main screen split panel to vertical stack on screens narrower than 768px
- [AI Agent] Ensure touch-friendly button sizes (minimum 44x44px touch target) and spacing on all screens
- [AI Agent] Apply responsive typography using Quasar's responsive breakpoint classes
- [AI Agent] Ensure the page layout header collapses gracefully on small screens
- [AI Agent] Verify all forms are usable on mobile (input fields don't overflow, labels wrap correctly)

**Description**:
This component makes the entire application usable on iPhone Safari. The main challenge is the split-panel layout on the main screen — this must stack vertically on narrow viewports (below 768px). All forms, buttons, and interactive elements must be touch-friendly with adequate sizing and spacing. The Quasar framework (underlying NiceGUI) provides responsive utility classes and breakpoints that can be leveraged for most adjustments. This component tests every screen at 375px width (iPhone SE / iPhone 13 mini) and 390px width (iPhone 14) and fixes any overflow, truncation, or usability issues.

**Acceptance Criteria**:
- [ ] Main screen split panel stacks vertically (action list on top, responses below) on viewports < 768px wide
- [ ] On mobile, the action list and response panel each occupy full width
- [ ] All buttons have a minimum touch target of 44x44px on mobile viewports
- [ ] All form input fields are full-width on mobile and do not horizontally overflow
- [ ] Form labels wrap correctly and do not truncate on narrow screens
- [ ] The page layout header (from Component 5.1) adapts to mobile — app title may abbreviate, breadcrumb wraps or collapses
- [ ] Toast notifications are fully visible and dismissible on mobile
- [ ] The action type defaults tabs (from Component 4.4) are scrollable/swipeable on mobile rather than overflowing
- [ ] The payload editing dialog (from Component 4.9) is full-screen on mobile with adequate textarea sizing
- [ ] The debug action insertion dialog (from Component 4.9) is usable on mobile with touch-friendly controls
- [ ] No horizontal scrolling on any screen at 375px viewport width
- [ ] Tested and verified on Safari (iPhone viewport simulation via Chrome DevTools or Safari Responsive Design Mode)

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/main_screen.py` (responsive split panel)
  - `app/src/ui/components.py` (responsive layout wrapper adjustments)
  - `app/src/ui/executor_config.py` (responsive form adjustments)
  - `app/src/ui/action_type_defaults.py` (responsive tabs)
  - `app/src/ui/secrets_screen.py` (responsive form adjustments)
  - `app/src/ui/link_project.py` (responsive form adjustments)
  - `app/src/ui/load_project.py` (responsive list adjustments)
  - `app/src/ui/initial_screen.py` (responsive button layout)
  - `app/src/static/styles.css` (custom responsive CSS if needed)
- **Key Functions/Classes**:
  - Quasar responsive classes applied via `.classes()` on NiceGUI elements
  - Custom CSS media queries in `app/src/static/styles.css` for fine-grained control
  - `ui.query('body').classes('mobile')` or viewport-aware class toggling
- **Human/AI Agent**: AI Agent implements all responsive adjustments
- **Dependencies**: NiceGUI 2.x, Quasar responsive utility classes

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/main_screen.py`** (extend): The main screen's `ui.splitter()` does not natively stack on mobile. Replace or augment it with a responsive approach: use Quasar's `q-responsive` or CSS media query to conditionally render the layout. Option A (preferred): Use `ui.element('div').classes('row q-col-gutter-md')` with two child `ui.element('div')` elements. Apply `.classes('col-12 col-md-5')` to the action list container and `.classes('col-12 col-md-7')` to the response panel container. This uses Quasar's 12-column grid: on screens ≥ 768px (md breakpoint), it renders side-by-side; below 768px, each takes full width and stacks vertically. Option B: Keep `ui.splitter()` for desktop and use `ui.query()` with a CSS media query to override the splitter layout on mobile. Option A is cleaner and recommended. Ensure the action list and response panel each have `ui.scroll_area()` with a max height on desktop (e.g., `calc(100vh - 120px)`) and natural flow on mobile.

- **File 2: `app/src/ui/components.py`** (extend): Update `page_layout()` to be responsive. On mobile, the header should show only the app title and back button (collapse breadcrumb into a smaller font or hide if space is tight). Apply `.classes('text-h6')` instead of `text-h4` on small screens for the title. Use Quasar's `$q.screen.lt.md` concept — in NiceGUI, this can be approximated by adding CSS classes: `.classes('lt-md:text-subtitle1 gt-sm:text-h5')` for responsive typography (Quasar visibility classes). Ensure the header doesn't cause horizontal scroll.

- **File 3: `app/src/ui/initial_screen.py`** (extend): Ensure buttons stack in full-width column on mobile. Apply `.classes('full-width')` to all buttons. The card container should use `.classes('col-12 col-md-6 col-lg-4')` so it's full-width on mobile, half-width on tablet, and third-width on desktop — centred with `q-mx-auto`.

- **File 4: `app/src/ui/executor_config.py`** (extend): Apply `.classes('full-width')` to all input fields. Ensure the form card uses `col-12 col-md-8 col-lg-6` for responsive width. Add `dense` prop to inputs on mobile for compact spacing if needed.

- **File 5: `app/src/ui/action_type_defaults.py`** (extend): The tabs (`ui.tabs()`) may overflow horizontally on mobile. Add `.props('scrollable')` to the tabs component so tabs can be horizontally scrolled. Alternatively use `.props('vertical')` on mobile and horizontal on desktop. Apply full-width classes to all input fields within tab panels.

- **File 6: `app/src/ui/main_screen.py` (dialogs)**: The payload editing dialog should be full-screen on mobile: add `.props('maximized')` or conditional `.props('full-width full-height')` when viewport < 768px. Use `ui.query()` to detect viewport or apply CSS media queries. Ensure the textarea fills available space. The debug insertion dialog should have adequately sized touch targets for the position selector.

- **File 7: `app/src/static/styles.css`** (create if needed): Add any custom media queries that cannot be achieved with Quasar utility classes alone. For example: `@media (max-width: 767px) { .q-splitter { flex-direction: column !important; } .q-splitter__separator { display: none; } }` as a fallback if the grid approach doesn't fully replace the splitter. Register this CSS file in `app/src/main.py` via `app.add_static_files('/static', 'app/src/static')` and include via `ui.add_head_html('<link rel="stylesheet" href="/static/styles.css">')`.

**Test Requirements**:
- [ ] Manual verification: All screens tested at 375px, 390px, and 768px viewport widths using browser DevTools responsive mode
- [ ] Manual verification: Main screen stacks vertically below 768px — action list on top, responses below
- [ ] Manual verification: No horizontal scrollbar on any screen at 375px
- [ ] Manual verification: All buttons have adequate touch targets (visually confirm ≥ 44px height)
- [ ] Manual verification: Action type defaults tabs are scrollable on mobile
- [ ] Manual verification: Payload editor dialog is full-screen on mobile
- [ ] Unit tests: Responsive classes are applied correctly via `.classes()` assertions (if testable via NiceGUI test utilities)

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-5-component-5-3-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-5.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation
- [ ] All screens verified at 375px and 768px viewport widths

**Notes**:
Quasar (the UI framework underlying NiceGUI) has excellent responsive support via its 12-column grid system (`col-12`, `col-md-6`, etc.) and visibility classes (`lt-md`, `gt-sm`). However, NiceGUI's Python API may not expose all Quasar props directly — use `.props()` and `.classes()` to pass Quasar classes and properties through. The main screen splitter replacement is the most significant change: moving from `ui.splitter()` to Quasar's column grid gives native responsive behaviour without JavaScript. For the static CSS file, NiceGUI supports serving static files and injecting custom HTML into the `<head>` — this is the escape hatch for any responsive rules that Quasar classes alone don't cover. Test using Chrome DevTools Device Toolbar (375px iPhone SE, 390px iPhone 14) and Safari's Responsive Design Mode.

---

### Component 5.4 — Workflow Quality-of-Life

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Components 5.1–5.3: Navigation, error handling, and responsive layout must be in place
- Component 4.7: Main screen action list
- Component 4.8: Main screen response display and mark complete
- Component 2.1: Action model with `ActionStatus` enum

**Features**:
- [AI Agent] Implement colour-coded status indicators on action items (not_started: grey, dispatched: blue/amber, completed: green)
- [AI Agent] Implement phase grouping with expand/collapse and action count badges per phase
- [AI Agent] Implement phase filtering — allow the user to select a specific phase to view rather than all phases
- [AI Agent] Implement confirmation dialog when re-dispatching an already-dispatched or completed action
- [AI Agent] Implement clear visual hierarchy differentiating action types (Implement, Test, Review, Document, Debug) with distinct icons and colours
- [AI Agent] Add a progress summary bar showing overall completion (e.g., "12/24 actions complete")

**Description**:
This component adds workflow polish to the main screen that makes managing a large list of Execute Action items intuitive. Status indicators provide instant visual feedback on each action's state. Phase grouping with expand/collapse and filtering lets users focus on one phase at a time without scrolling through the entire list. Confirmation dialogs prevent accidental re-dispatch of already-processed actions. A progress summary gives a high-level view of overall phase completion. These features collectively transform the main screen from a functional list into an efficient workflow tool.

**Acceptance Criteria**:
- [ ] Action items display status badges with colour: `not_started` = grey, `dispatched` = amber/blue, `completed` = green
- [ ] Phase groups display an action count badge showing "completed / total" (e.g., "3/6")
- [ ] Phase groups can be expanded and collapsed individually
- [ ] A phase filter dropdown/selector at the top of the action list allows viewing a single phase or "All Phases"
- [ ] When a phase filter is selected, only that phase's actions are visible in the list
- [ ] Clicking an action that has status `dispatched` or `completed` triggers a confirmation dialog: "This action has already been {status}. Re-dispatch?"
- [ ] Confirmation dialog has "Re-dispatch" and "Cancel" buttons
- [ ] Each action type has a distinct icon: Implement = `build` (or `code`), Test = `science`, Review = `rate_review`, Document = `description`, Debug = `bug_report`
- [ ] Each action type has a subtle colour accent: Implement = blue, Test = purple, Review = orange, Document = teal, Debug = red
- [ ] A progress summary bar at the top of the action list shows "X of Y actions complete" with a linear progress indicator
- [ ] Progress summary updates dynamically when actions are marked complete

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/main_screen.py` (extend action list with all quality-of-life features)
  - `app/src/ui/components.py` (add reusable action status badge, progress bar, confirmation dialog)
- **Key Functions/Classes**:
  - `action_status_badge(status: ActionStatus) -> None` — renders a coloured badge for the given status
  - `action_type_icon(action_type: ActionType) -> tuple[str, str]` — returns (icon_name, colour_class) for the action type
  - `progress_summary(actions: list[Action]) -> None` — renders the progress bar and completion count
  - `confirm_redispatch(action: Action, on_confirm: Callable) -> None` — shows confirmation dialog for re-dispatch
  - `phase_filter(phases: list[PhaseData], on_select: Callable[[int | None], None]) -> None` — renders the phase filter selector
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: NiceGUI 2.x, Quasar components (`QBadge`, `QLinearProgress`, `QSelect`, `QDialog`)

**Detailed Implementation Requirements**:

- **File 1: `app/src/ui/components.py`** (extend): Add `action_status_badge(status)`: render a `ui.badge()` with text matching the status and colour mapping — `not_started` → `grey` label "Pending", `dispatched` → `amber` label "Dispatched", `completed` → `green` label "Complete". Use `.props(f'color="{colour}" text-color="white"')`. Add `action_type_icon(action_type)`: return a tuple of (Material icon name, Quasar colour class) — `implement` → (`"code"`, `"primary"`), `test` → (`"science"`, `"purple"`), `review` → (`"rate_review"`, `"orange"`), `document` → (`"description"`, `"teal"`), `debug` → (`"bug_report"`, `"red"`). Add `progress_summary(actions)`: count completed vs total, render `ui.label(f"{completed} of {total} actions complete")` and `ui.linear_progress(value=completed/total if total > 0 else 0, show_value=False).classes('q-mt-sm')` with appropriate colour. Add `confirm_redispatch(action, on_confirm)`: create a `ui.dialog()` with message `f"This action has already been {action.status.value}. Re-dispatch?"` and two buttons: "Re-dispatch" (calls `on_confirm()` and closes dialog) and "Cancel" (closes dialog). Return the dialog for the caller to `.open()`.

- **File 2: `app/src/ui/main_screen.py`** (extend): Update the action list rendering (`_render_action_list`): (1) At the top, add `progress_summary(app_state.current_project.actions)`. (2) Below the progress summary, add a `ui.select()` for phase filtering with options: `[{"label": "All Phases", "value": None}] + [{"label": f"Phase {p.phase_id}: {p.phase_name}", "value": p.phase_id} for p in project.phases]`. Bind the selected value to a reactive variable. (3) When rendering phase groups, filter by the selected phase (or show all if `None`). (4) In each phase expansion header, add a count badge: `ui.badge(f"{phase_completed}/{phase_total}")`. (5) Replace the simple icon and label on each action item with `action_type_icon()` for the icon and colour, and `action_status_badge()` for the status. (6) In the dispatch handler (`_dispatch_action`), check `action.status` before dispatching. If status is `dispatched` or `completed`, open `confirm_redispatch()` and only proceed on confirmation. If `not_started`, dispatch immediately. (7) After marking an action complete, call `progress_summary.refresh()` (or refresh the entire action list) to update the counts. Use `@ui.refreshable` decorators strategically to enable incremental updates without full-page re-renders.

**Test Requirements**:
- [ ] Unit tests: `action_status_badge()` renders correct colour for each status
- [ ] Unit tests: `action_type_icon()` returns correct icon and colour for each action type
- [ ] Unit tests: `progress_summary()` calculates correct completion ratio
- [ ] Unit tests: Phase filtering produces correct subset of actions
- [ ] Manual verification: Status badges update colour when action status changes
- [ ] Manual verification: Phase filter shows/hides correct phases
- [ ] Manual verification: Confirmation dialog appears when re-dispatching a completed action
- [ ] Manual verification: Progress bar updates after marking actions complete

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-5-component-5-4-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-5.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality
- [ ] Core application is still working post component implementation

**Notes**:
NiceGUI's `ui.badge()` renders Quasar's QBadge — support for colour, text-color, and floating positioning. Use `.props('floating')` to position count badges on phase expansion headers. `ui.linear_progress()` renders Quasar's QLinearProgress — accepts `value` (0 to 1), `color`, and `size` props. `ui.select()` renders Quasar's QSelect — supports `options` as a list of dicts with `label` and `value` keys. For the phase filter, use `on_change` to trigger a refresh of the action list. The confirmation dialog pattern is common in Quasar/NiceGUI — create the dialog, call `.open()` to show it, and handle the result via button callbacks.

---

### Component 5.5 — Testing & Phase Validation

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Components 5.1 through 5.4: All Phase 5 UI enhancements implemented
- Phase 4 tests still passing (no regression)

**Features**:
- [AI Agent] Create UI interaction tests for navigation flow, error handling, and responsive behaviour
- [AI Agent] Verify responsive layout at 375px, 768px, and 1440px viewport widths
- [AI Agent] Run full quality validation (Black, isort, pytest, evals)
- [AI Agent] Create/update Phase 5 implementation context documentation
- [AI Agent] Update the agent runbook with responsive testing instructions
- [AI Agent] Execute E2E scenario validation to confirm Phase 5 changes don't break workflows

**Description**:
This component completes Phase 5 by consolidating tests for all UI enhancements, running quality checks, and creating phase documentation. Tests verify that navigation flows work correctly, error messages display properly, responsive layouts adapt at each breakpoint, and workflow features (status badges, phase filtering, confirmation dialogs) function as expected. The E2E scenarios from Phase 4 are re-executed to confirm no regressions. Documentation captures all Phase 5 components and design decisions.

**Acceptance Criteria**:
- [ ] All Phase 4 tests continue to pass (no regression)
- [ ] Navigation tests: Verify all screen routes respond, back navigation works, loading indicators appear
- [ ] Error handling tests: Verify error mapping functions return correct messages for all exception types
- [ ] Responsive tests (manual): Document test results at 375px, 768px, and 1440px viewport widths
- [ ] Workflow feature tests: Verify phase filter, status badges, progress bar, and confirmation dialog logic
- [ ] All unit tests pass: `pytest -q --cov=app/src --cov-report=term-missing`
- [ ] Test coverage on `app/src/` is ≥ 30%
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes
- [ ] `python scripts/evals.py` passes (all public functions have docstrings, no TODO/FIXME)
- [ ] `docs/implementation-context-phase-5.md` exists with entries for all Phase 5 components
- [ ] Agent runbook updated with responsive testing instructions and breakpoint reference
- [ ] E2E scenarios E2E-001, E2E-002, and E2E-003 still pass after Phase 5 changes

**Technical Details**:
- **Files to Create/Modify**:
  - `tests/test_navigation.py`
  - `tests/test_error_handling.py`
  - `tests/test_workflow_features.py`
  - `docs/implementation-context-phase-5.md`
  - `docs/components/phase-5-component-5-5-overview.md`
  - `docs/autopilot-runbook.md` (or `docs/dispatch-runbook.md`) — update with responsive testing section
- **Key Functions/Classes**: Test functions for navigation, error mapping, workflow features
- **Human/AI Agent**: AI Agent writes all tests and documentation
- **Dependencies**: pytest, pytest-cov, all Phase 5 UI modules

**Detailed Implementation Requirements**:

- **File 1: `tests/test_navigation.py`**: Test the navigation flow: (1) Verify all page routes are registered in the NiceGUI app. (2) Test `page_layout()` renders header with correct title and back button. (3) Test `loading_overlay()` can be instantiated, shown, and hidden. (4) Test `AppState.ensure_project()` returns `None` for unknown project IDs and returns the project for loaded ones. (5) Test `AppState.clear_project()` resets state. Keep tests focused on the Python-level logic rather than browser rendering.

- **File 2: `tests/test_error_handling.py`**: Test error handling functions: (1) Test `map_github_error()` for each exception type (`GitHubAuthError`, `GitHubNotFoundError`, `GitHubRateLimitError`, generic). Verify returned messages match expected strings. (2) Test `map_executor_error()` for each exception type (`ExecutorConnectionError`, `ExecutorAuthError`, `ExecutorDispatchError`, generic). (3) Verify no secret values appear in any error message (pass a mock exception with a URL containing a token and verify the token is not in the output). (4) Test that `notify_success`, `notify_error`, `notify_warning` are callable (basic smoke tests — full notification rendering is manual).

- **File 3: `tests/test_workflow_features.py`**: Test workflow features: (1) Test `action_type_icon()` returns correct icon and colour for each type. (2) Test `action_status_badge()` logic (if testable without NiceGUI rendering — test the colour/label mapping). (3) Test `progress_summary()` calculation — given a list of actions with mixed statuses, verify correct completed/total count. (4) Test phase filtering logic — given actions for multiple phases, verify filtering by `phase_id` returns correct subset. (5) Test confirmation dialog trigger — verify that an action with `dispatched` status triggers the dialog (test the conditional logic, not the dialog rendering).

- **File 4: `docs/implementation-context-phase-5.md`**: Running log with entries for Components 5.1–5.5. Each entry includes: component ID and name, status (completed), key files created/modified, notable decisions (e.g., "replaced ui.splitter with Quasar column grid for responsive layout", "centralised notifications via helper functions", "custom exception hierarchy for typed error handling", "Quasar breakpoint classes for mobile responsiveness").

- **File 5: `docs/components/phase-5-component-5-5-overview.md`**: Summary of the testing and validation component.

- **File 6: Agent runbook update**: Add a "Responsive Testing" section: (1) How to test responsive layout using Chrome DevTools Device Toolbar. (2) Target viewports: 375px (iPhone SE), 390px (iPhone 14), 768px (iPad), 1440px (desktop). (3) Key checkpoints per viewport: header collapse, panel stacking, button sizing, form field width, tab scrollability. (4) Known limitations or device-specific notes.

**Test Requirements**:
- [ ] All new test files pass
- [ ] All Phase 4 tests still pass
- [ ] `pytest -q --cov=app/src --cov-report=term-missing` reports ≥ 30% coverage
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes
- [ ] `python scripts/evals.py` passes

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing with ≥ 30% coverage
- [ ] All quality checks pass (Black, isort, pytest, evals)
- [ ] Documentation created: Component Overview (`docs/components/phase-5-component-5-5-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-5.md`). Maximum 50 lines of markdown per component.
- [ ] Agent runbook updated with responsive testing section
- [ ] No regression in existing functionality (Phase 1, 2, 3, and 4 tests still pass)
- [ ] Core application is still working post component implementation

**Notes**:
NiceGUI does not natively provide a headless browser test client for UI rendering — Python-level tests focus on logic and data flow rather than rendered output. Responsive behaviour is best verified manually using browser DevTools. Document manual test results in the component overview. For the E2E scenario re-validation, re-run the integration tests from Phase 4 (`test_ui_integration.py`) and confirm they pass without modification — if Phase 5 changes broke any integration, fix the issue before completing this component.

---

## Phase Acceptance Criteria

- [ ] Navigation between all screens is smooth with consistent header, breadcrumbs, and back navigation
- [ ] Loading indicators display during GitHub scanning, executor dispatch, project save/load
- [ ] All GitHub API and executor API errors are surfaced with clear, actionable toast messages
- [ ] Toast notifications confirm successful operations (save, dispatch, mark complete)
- [ ] Inline form validation provides descriptive error messages on all config screens
- [ ] Global exception handler prevents app crashes from unexpected errors
- [ ] UI is fully usable on iPhone Safari (tested at 375px viewport width)
- [ ] Main screen split panel stacks vertically on screens narrower than 768px
- [ ] All buttons have touch-friendly sizing on mobile (≥ 44px touch target)
- [ ] No horizontal scrolling on any screen at 375px viewport width
- [ ] Action items display colour-coded status indicators (grey/amber/green)
- [ ] Phase groups have expand/collapse and action count badges
- [ ] Phase filter allows viewing a single phase or all phases
- [ ] Confirmation dialog appears when re-dispatching already-dispatched actions
- [ ] Progress summary bar shows overall action completion
- [ ] Each action type has a distinct icon and colour accent
- [ ] All tests pass with ≥ 30% coverage on `app/src/`
- [ ] `black --check app/src/` and `isort --check-only app/src/` pass
- [ ] `python scripts/evals.py` passes with no violations
- [ ] Phase 4 tests still pass (no regression)
- [ ] `docs/implementation-context-phase-5.md` documents all implemented components
- [ ] Agent runbook includes responsive testing instructions

---

## Cross-Cutting Concerns

### Testing Strategy
- **E2E Testing Scenarios**: After Phase 5, all Phase 4 E2E scenarios (E2E-001, E2E-002, E2E-003) must still pass. Phase 5 adds no new E2E scenarios but adds responsive testing checkpoints that are documented in the runbook.
- **Unit Testing**: pytest with fixtures. Focus on navigation logic (`ensure_project`, `clear_project`), error mapping functions, workflow feature logic (status badges, progress calculation, phase filtering), and custom exception classes. Target ≥ 30% coverage on `app/src/`.
- **Responsive Testing**: Manual testing at 375px, 390px, 768px, and 1440px viewport widths using browser DevTools. Document results per component.
- **Integration Testing**: Re-run Phase 4 integration tests to confirm no regressions from UI enhancements.

### Documentation Requirements
- **Developer Context Documentation**: `docs/implementation-context-phase-5.md`, `docs/components/phase-5-component-5-X-overview.md` per component
- **Agent Runbook**: Updated with responsive testing section (viewports, checkpoints, tools)
- **Code Documentation**: Google-style docstrings on all new public functions and classes
- **Architecture Decision Records**: Document in implementation context: Quasar grid replacing splitter for responsive layout, centralised notification helpers, custom exception hierarchy, CSS media query escape hatch for NiceGUI limitations
