# Phase 6: LLM-Assisted Payload Generation

## Phase Overview

**Objective**: Integrate optional OpenAI LLM support to intelligently populate Execute Action item payloads from project context. When enabled, the LLM interprets phase data, component details, and agent files to generate context-aware payload field values — replacing simple string interpolation with richer, more accurate instructions. Falls back gracefully to standard interpolation if the LLM call fails or is not configured.

**Deliverables**:
- LLM service module with OpenAI SDK integration, prompt construction, response parsing, error handling with graceful fallback to standard string interpolation
- Context-aware prompt building pipeline that assembles phase data, component details, agent file contents, and executor requirements into a structured prompt for payload generation
- UI integration: toggle for LLM generation in executor config, loading indicator during LLM calls, review-before-dispatch flow showing generated payload for manual editing
- Comprehensive tests with mocked OpenAI SDK covering success, failure, timeout, and fallback scenarios

**Dependencies**:
- Phase 4 complete (working MVP with payload editing, executor dispatch, and action generation)
- Phase 5 complete (navigation polish, error handling with toast notifications, loading indicators, responsive layouts)
- Phase 3 complete (payload resolver service with `{{variable}}` interpolation as fallback)
- Phase 2 complete (data models, config manager, secrets management for OpenAI API key)
- OpenAI Python SDK (`openai`) added to `pyproject.toml` dependencies
- Python 3.13+ virtual environment activated

## Phase Goals

- Users can optionally enable LLM-assisted payload generation per executor config, with the toggle disabled and explanatory text when no OpenAI API key is configured
- LLM generates context-aware payload content from phase data, component details, and agent file contents within 5 seconds
- Generated payloads are always displayed for review before dispatch, with full manual editing capability
- If the OpenAI API call fails or times out, the system falls back to standard `{{variable}}` string interpolation with a warning notification
- All new code passes Black, isort, evals, and achieves ≥ 30% test coverage on `app/src/`

---

## Components

### Component 6.1 — OpenAI SDK Integration

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 2.2: Application settings module — `DISPATCH_DATA_DIR`, `.env/.env.local` loading
- Component 2.3: Config & Secrets manager — read secrets from `.env/.env.local` (specifically `OPENAI_API_KEY` and `OPENAI_MODEL`)
- Component 2.1: Data models — `ExecutorConfig` model for LLM toggle state

**Features**:
- [AI Agent] Create `app/src/services/llm_service.py` with `LLMService` class wrapping the OpenAI Python SDK
- [AI Agent] Implement client initialisation from secrets (`OPENAI_API_KEY` environment variable via config manager)
- [AI Agent] Implement configurable model selection (default: `gpt-4o`, overridable via `OPENAI_MODEL` env var or executor config)
- [AI Agent] Implement timeout handling with a configurable timeout (default: 10 seconds) to meet the < 5 second target under normal conditions
- [AI Agent] Implement structured error handling: API errors, authentication errors, rate limit errors, timeout errors — all caught and converted to typed exceptions
- [AI Agent] Implement graceful availability check (`is_available() -> bool`) that returns `False` when no API key is configured
- [AI Agent] Add `openai` package to `pyproject.toml` dependencies

**Description**:
This component creates the foundational LLM service that wraps the OpenAI Python SDK. It handles client lifecycle, authentication, error handling, and timeout management. The service exposes a clean interface for the payload generation logic (Component 6.2) to call without worrying about SDK-specific details. The service is designed to fail gracefully — if no API key is configured, `is_available()` returns `False` and the UI can disable the LLM toggle. If an API call fails, a typed exception is raised that the caller (Component 6.2) converts to a fallback to standard interpolation.

**Acceptance Criteria**:
- [ ] `LLMService` initialises the OpenAI client from the `OPENAI_API_KEY` environment variable
- [ ] `LLMService.is_available()` returns `True` when API key is set, `False` when missing or empty
- [ ] `LLMService.generate(system_prompt: str, user_prompt: str) -> str` sends a chat completion request and returns the response content
- [ ] Model is configurable via `OPENAI_MODEL` env var with fallback to `gpt-4o`
- [ ] Timeout is enforced at 10 seconds — raises `LLMTimeoutError` if exceeded
- [ ] `LLMAuthError` is raised on 401/403 OpenAI API responses
- [ ] `LLMRateLimitError` is raised on 429 OpenAI API responses
- [ ] `LLMServiceError` is raised on all other OpenAI API errors with the original error message preserved
- [ ] `openai` package is added to `pyproject.toml` under `[project.dependencies]`
- [ ] All exception classes inherit from a base `LLMError` class for consistent handling

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/services/llm_service.py` (create)
  - `app/src/exceptions.py` (extend with LLM exception classes)
  - `pyproject.toml` (add `openai` dependency)
- **Key Functions/Classes**:
  - `LLMService` class with `__init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 10.0)`
  - `LLMService.is_available() -> bool` — checks if API key is set
  - `LLMService.generate(system_prompt: str, user_prompt: str) -> str` — sends chat completion, returns assistant response content
  - `LLMError(Exception)` — base exception for all LLM errors
  - `LLMTimeoutError(LLMError)` — raised on timeout
  - `LLMAuthError(LLMError)` — raised on auth failure
  - `LLMRateLimitError(LLMError)` — raised on rate limiting
  - `LLMServiceError(LLMError)` — raised on other API errors
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: `openai` Python SDK, `python-dotenv`, config manager (Component 2.3)

**Detailed Implementation Requirements**:

- **File 1: `app/src/services/llm_service.py`**: Create the `LLMService` class. In `__init__`, accept optional `api_key`, `model`, and `timeout` parameters. If `api_key` is not provided, attempt to read from the environment variable `OPENAI_API_KEY` via `os.environ.get("OPENAI_API_KEY")`. If `model` is not provided, read from `OPENAI_MODEL` env var or default to `"gpt-4o"`. Store `timeout` (default 10.0 seconds). Initialise the `openai.OpenAI` client with the `api_key` and `timeout` parameters only if the API key is available — do not initialise the client if no key is present (store `self._client = None`). Implement `is_available() -> bool`: return `self._client is not None`. Implement `generate(system_prompt: str, user_prompt: str) -> str`: guard with `if not self.is_available(): raise LLMServiceError("OpenAI API key not configured")`. Call `self._client.chat.completions.create(model=self._model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], timeout=self._timeout)`. Extract and return `response.choices[0].message.content`. Wrap the call in a try/except block: catch `openai.AuthenticationError` → raise `LLMAuthError`; catch `openai.RateLimitError` → raise `LLMRateLimitError`; catch `openai.APITimeoutError` → raise `LLMTimeoutError`; catch `openai.APIError` → raise `LLMServiceError` with the original message. Use `logging.getLogger(__name__)` to log errors at WARNING level (never log the API key).

- **File 2: `app/src/exceptions.py`** (extend): Add the LLM exception hierarchy. Define `LLMError(Exception)` as the base class with a `message: str` attribute. Define `LLMTimeoutError(LLMError)` with default message "LLM request timed out". Define `LLMAuthError(LLMError)` with default message "OpenAI API authentication failed". Define `LLMRateLimitError(LLMError)` with default message "OpenAI API rate limit exceeded". Define `LLMServiceError(LLMError)` with a user-provided message. Ensure these follow the same pattern as existing `GitHubAuthError`, `ExecutorConnectionError` etc. already defined in this file.

- **File 3: `pyproject.toml`** (extend): Add `"openai>=1.0.0"` to the `[project.dependencies]` list. Add a brief inline comment: `# LLM-assisted payload generation (Phase 6)`.

**Test Requirements**:
- [ ] Unit tests: `LLMService.is_available()` returns `False` when no API key, `True` when key is set
- [ ] Unit tests: `LLMService.generate()` returns expected content with mocked OpenAI client (use `unittest.mock.patch`)
- [ ] Unit tests: `LLMService.generate()` raises `LLMAuthError` when OpenAI returns 401 (mocked)
- [ ] Unit tests: `LLMService.generate()` raises `LLMRateLimitError` when OpenAI returns 429 (mocked)
- [ ] Unit tests: `LLMService.generate()` raises `LLMTimeoutError` when request times out (mocked)
- [ ] Unit tests: `LLMService.generate()` raises `LLMServiceError` on generic API errors (mocked)
- [ ] Unit tests: Verify API key is never logged in any error scenario

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-6-component-6-1-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-6.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality (Phase 4 and 5 tests still pass)
- [ ] Core application is still working post component implementation

**Notes**:
The OpenAI Python SDK v1.x uses a synchronous client by default (`openai.OpenAI`). For NiceGUI async compatibility, the `generate()` method can be called in a thread via `asyncio.to_thread()` by the caller — the service itself stays synchronous for simplicity and testability. The `timeout` parameter on the SDK client applies to the HTTP request level. The `gpt-4o` default model balances quality and speed for payload generation tasks. Do not use `openai.AsyncOpenAI` — keeping the service synchronous simplifies testing with `unittest.mock.patch`.

---

### Component 6.2 — LLM Payload Generation Logic

**Priority**: Must-have

**Estimated Effort**: 3 hours

**Owner**: AI Agent

**Dependencies**:
- Component 6.1: `LLMService` with `generate()` method and exception hierarchy
- Component 3.5: Payload resolver service — `{{variable}}` interpolation as fallback path
- Component 3.4: Action generator — access to action data including phase, component, and type
- Component 3.2: Project service — access to loaded phase-progress data and agent file contents
- Component 2.1: Data models — `Action`, `ExecutorConfig`, `PayloadTemplate` models

**Features**:
- [AI Agent] Create `app/src/services/llm_payload_generator.py` with `LLMPayloadGenerator` class
- [AI Agent] Implement context assembly — gather phase data, component details, agent file contents, executor config, and action type from the project and action context
- [AI Agent] Implement system prompt construction that instructs the LLM to generate payload field values given the assembled context
- [AI Agent] Implement user prompt construction that provides the specific action details and template to populate
- [AI Agent] Implement response parsing — extract generated values from the LLM response and validate they conform to expected payload structure
- [AI Agent] Implement merge logic — overlay LLM-generated values onto the payload template, preserving non-generated fields (e.g., `repository`, `callback_url`) from standard interpolation
- [AI Agent] Implement fallback path — if LLM service is unavailable or call fails, fall back to standard `{{variable}}` interpolation via the payload resolver

**Description**:
This component implements the intelligent payload generation pipeline. It sits between the action data and the executor dispatch, providing an alternative to simple `{{variable}}` string interpolation. The generator assembles rich context from the project's phase data (component names, descriptions, acceptance criteria from the component breakdown doc), agent file contents (agent instructions and capabilities), and the executor's payload template. It constructs a structured prompt asking the LLM to generate the `agent_instructions` field (and optionally other fields) with context-aware, detailed instructions. The LLM response is parsed, validated, and merged into the payload template. Non-LLM fields like `repository`, `branch`, `callback_url` are still resolved via standard interpolation. If anything goes wrong, the entire payload falls back to standard interpolation.

**Acceptance Criteria**:
- [ ] `LLMPayloadGenerator` assembles context from phase-progress data, component breakdown content, and agent file contents
- [ ] System prompt instructs the LLM to generate the `agent_instructions` field value for a given Execute Action item type
- [ ] User prompt includes: action type, phase name, component name (for Implement), component acceptance criteria (if available), agent file paths, and the current payload template
- [ ] LLM response is parsed expecting a JSON object with at least an `agent_instructions` key
- [ ] Generated `agent_instructions` are merged into the payload, replacing the template's `{{variable}}`-based instructions
- [ ] Non-instruction fields (`repository`, `branch`, `callback_url`, `model`, `role`, `timeout_minutes`) are still resolved via standard `{{variable}}` interpolation — LLM does not generate these
- [ ] If `LLMService.is_available()` is `False`, `generate_payload()` immediately falls back to standard interpolation
- [ ] If `LLMService.generate()` raises any `LLMError`, the generator catches it, logs a warning, falls back to standard interpolation, and returns a `PayloadGenerationResult` with `llm_used=False` and `fallback_reason`
- [ ] `PayloadGenerationResult` dataclass includes: `payload` (resolved dict), `llm_used` (bool), `fallback_reason` (str | None)
- [ ] Context assembly respects a maximum token budget — truncates component breakdown content if it exceeds ~4000 characters to stay within LLM context limits

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/services/llm_payload_generator.py` (create)
  - `app/src/models/payload.py` (extend with `PayloadGenerationResult`)
- **Key Functions/Classes**:
  - `LLMPayloadGenerator` class with `__init__(self, llm_service: LLMService, payload_resolver: PayloadResolver)`
  - `LLMPayloadGenerator.generate_payload(action: Action, project: Project, executor_config: ExecutorConfig) -> PayloadGenerationResult`
  - `LLMPayloadGenerator._assemble_context(action: Action, project: Project) -> str` — builds the context string from phase/component/agent data
  - `LLMPayloadGenerator._build_system_prompt() -> str` — returns the system prompt for payload generation
  - `LLMPayloadGenerator._build_user_prompt(action: Action, context: str, template: dict) -> str` — returns the user prompt with action details and template
  - `LLMPayloadGenerator._parse_response(response: str) -> dict` — extracts JSON from LLM response, validates structure
  - `LLMPayloadGenerator._merge_payload(template: dict, llm_fields: dict, resolved_fields: dict) -> dict` — merges LLM-generated and standard-interpolated fields
  - `PayloadGenerationResult` dataclass: `payload: dict`, `llm_used: bool`, `fallback_reason: str | None`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: `LLMService` (Component 6.1), `PayloadResolver` (Component 3.5), project data models (Component 2.1)

**Detailed Implementation Requirements**:

- **File 1: `app/src/services/llm_payload_generator.py`**: Create the `LLMPayloadGenerator` class. `__init__` accepts `llm_service: LLMService` and `payload_resolver: PayloadResolver`. Implement `generate_payload(action, project, executor_config) -> PayloadGenerationResult`: (1) First, resolve the full payload via standard interpolation (`self._payload_resolver.resolve(action, project, executor_config)`) — this is the baseline and fallback. (2) Check `self._llm_service.is_available()` — if `False`, return `PayloadGenerationResult(payload=resolved_payload, llm_used=False, fallback_reason="OpenAI API key not configured")`. (3) Check `executor_config.use_llm` — if `False`, return the standard resolved payload with `llm_used=False, fallback_reason="LLM generation disabled in executor config"`. (4) Assemble context via `_assemble_context(action, project)`. (5) Build system and user prompts. (6) Call `self._llm_service.generate(system_prompt, user_prompt)` wrapped in try/except for `LLMError`. On error, log warning with `fallback_reason=str(exc)`, return standard payload with `llm_used=False`. (7) Parse the LLM response via `_parse_response()`. If parsing fails (invalid JSON, missing keys), log warning, return fallback. (8) Merge LLM fields into the standard payload via `_merge_payload()`. Return `PayloadGenerationResult(payload=merged, llm_used=True, fallback_reason=None)`.

  Implement `_assemble_context(action, project) -> str`: Build a structured context string. Include: (a) Project repository name. (b) Phase name and ID from the action's phase reference. (c) For Implement actions: component ID, component name, estimated effort, and the component's section from the component breakdown document (if available in the project's loaded data — truncate to 4000 characters if longer). (d) For Test/Review/Document actions: phase name and list of component names in the phase. (e) Agent file paths from the project. Format as a clear, labelled text block (not JSON) for LLM consumption.

  Implement `_build_system_prompt() -> str`: Return a static system prompt: "You are a technical assistant that generates precise agent instructions for dispatching AI coding agents. Given project context and an action type, generate the `agent_instructions` field value for the executor payload. Your response must be a valid JSON object with a single key `agent_instructions` containing the generated instructions as a string. The instructions should be specific, actionable, and reference the project's components, files, and acceptance criteria where relevant. Do not include placeholders or variables — generate concrete instructions."

  Implement `_build_user_prompt(action, context, template) -> str`: Include the action type, the current template's `agent_instructions` value (showing the `{{variable}}`-based template as a reference), and the assembled context. Ask the LLM to generate a replacement `agent_instructions` value. Format: "Action type: {action.action_type}\n\nCurrent template instructions:\n{template['agent_instructions']}\n\nProject context:\n{context}\n\nGenerate the agent_instructions for this action as a JSON object."

  Implement `_parse_response(response: str) -> dict`: Attempt `json.loads(response)`. If the response contains markdown code fences (```json ... ```), strip them first. Validate the parsed dict has an `agent_instructions` key with a non-empty string value. Raise `ValueError` if parsing fails or validation fails.

  Implement `_merge_payload(template: dict, llm_fields: dict, resolved_fields: dict) -> dict`: Start with `resolved_fields` (the standard-interpolated payload). Override `agent_instructions` with `llm_fields["agent_instructions"]`. Return the merged dict. This ensures structural fields (repository, branch, model, role, callback_url, timeout_minutes) come from standard interpolation while the LLM enhances the instruction content.

- **File 2: `app/src/models/payload.py`** (extend): Add `PayloadGenerationResult` as a dataclass: `payload: dict[str, Any]`, `llm_used: bool`, `fallback_reason: str | None = None`. This is a simple data container — no validation needed beyond type hints.

**Test Requirements**:
- [ ] Unit tests: `generate_payload()` returns standard interpolation when `is_available()` is `False`
- [ ] Unit tests: `generate_payload()` returns standard interpolation when `executor_config.use_llm` is `False`
- [ ] Unit tests: `generate_payload()` calls LLM and merges result when LLM is available and enabled (mocked)
- [ ] Unit tests: `generate_payload()` falls back to standard interpolation when LLM raises `LLMTimeoutError` (mocked)
- [ ] Unit tests: `generate_payload()` falls back to standard interpolation when LLM raises `LLMServiceError` (mocked)
- [ ] Unit tests: `_assemble_context()` includes phase name, component name, and agent paths for Implement actions
- [ ] Unit tests: `_assemble_context()` truncates component breakdown content at 4000 characters
- [ ] Unit tests: `_parse_response()` extracts JSON from clean response
- [ ] Unit tests: `_parse_response()` extracts JSON from response with markdown code fences
- [ ] Unit tests: `_parse_response()` raises `ValueError` for invalid JSON
- [ ] Unit tests: `_parse_response()` raises `ValueError` when `agent_instructions` key is missing
- [ ] Unit tests: `_merge_payload()` preserves structural fields and overrides `agent_instructions`
- [ ] Integration test: Full flow from action → context assembly → LLM call → payload merge (mocked LLM)

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-6-component-6-2-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-6.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality (Phase 4 and 5 tests still pass)
- [ ] Core application is still working post component implementation

**Notes**:
The LLM is only used to generate the `agent_instructions` field — this is the most complex and context-dependent field in the payload. Other fields like `repository`, `branch`, `model`, `role`, `callback_url`, and `timeout_minutes` are deterministic and don't benefit from LLM generation. This focused scope keeps the LLM prompt small, the response predictable, and the fallback clean. The system prompt instructs the LLM to return JSON — this makes parsing reliable. If the LLM returns non-JSON (some models occasionally do), the parse-and-fallback logic handles it gracefully. The 4000-character context truncation prevents token budget issues with smaller models and keeps response times under 5 seconds. Component breakdown content is the most variable-length input; phase names and agent paths are short.

---

### Component 6.3 — UI Integration

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 6.1: `LLMService` with `is_available()` check
- Component 6.2: `LLMPayloadGenerator` with `generate_payload()` returning `PayloadGenerationResult`
- Component 5.1: Navigation flow, loading indicators (`loading_overlay`, `with_loading`)
- Component 5.2: Error handling, toast notifications (`notify_success`, `notify_error`, `notify_warning`)
- Component 4.3: Executor configuration screen — add LLM toggle
- Component 4.7: Main screen action list — modify dispatch flow
- Component 4.9: Payload editing dialog — extend for LLM-generated payload review

**Features**:
- [AI Agent] Add "Use LLM for payload generation" toggle to executor configuration screen, persisted in executor config JSON
- [AI Agent] Disable the LLM toggle with explanatory tooltip when no OpenAI API key is configured in secrets
- [AI Agent] Add OpenAI API key and model fields to the secrets management screen (if not already present)
- [AI Agent] Modify dispatch flow: when LLM is enabled, generate payload via LLM before showing the payload editing dialog
- [AI Agent] Show loading indicator during LLM generation with "Generating payload with AI..." message
- [AI Agent] Display the LLM-generated payload in the editing dialog with a visual indicator that it was AI-generated
- [AI Agent] Show fallback warning notification when LLM generation fails and standard interpolation is used instead
- [AI Agent] Ensure the payload editing dialog allows full manual editing after LLM generation

**Description**:
This component wires the LLM payload generation service into the existing UI, modifying the executor configuration screen and the main screen dispatch flow. The executor config screen gets a new toggle for enabling LLM generation, which is disabled when no OpenAI API key is configured. The main screen dispatch flow is modified: when LLM is enabled and the user clicks an action, the system first generates the payload via LLM (with a loading indicator), then opens the payload editing dialog showing the AI-generated content (with a badge indicating it was AI-generated). The user reviews, optionally edits, and confirms dispatch. If LLM generation fails, the dialog opens with the standard-interpolated payload and a warning toast explains the fallback.

**Acceptance Criteria**:
- [ ] Executor config screen has a "Use LLM for payload generation" toggle switch below the webhook URL field
- [ ] Toggle is persisted in `executor.json` as `use_llm: bool` field
- [ ] When no OpenAI API key is configured, the toggle is disabled (greyed out) with tooltip "Configure an OpenAI API key in Manage Secrets to enable"
- [ ] When OpenAI API key is configured, the toggle is enabled and defaults to `false`
- [ ] Secrets screen includes "OpenAI API Key" and "OpenAI Model" fields (saved to `.env/.env.local` as `OPENAI_API_KEY` and `OPENAI_MODEL`)
- [ ] When LLM is enabled and user clicks an action to dispatch: loading overlay shows "Generating payload with AI..." → LLM generates payload → payload editing dialog opens with generated content
- [ ] Payload editing dialog shows a small "AI Generated" badge/chip when the payload was generated via LLM
- [ ] Payload editing dialog shows no badge when payload was generated via standard interpolation
- [ ] When LLM generation fails, a warning toast displays: "LLM generation failed: {reason}. Using standard payload." and the dialog opens with the standard-interpolated payload
- [ ] User can freely edit the payload in the dialog regardless of how it was generated
- [ ] Clicking "Dispatch" in the dialog sends the payload to the executor as before
- [ ] Loading indicator shows for the duration of the LLM call (target < 5 seconds)
- [ ] If LLM call exceeds 10 seconds (timeout), the fallback activates and the dialog opens with standard payload

**Technical Details**:
- **Files to Create/Modify**:
  - `app/src/ui/executor_config.py` (extend with LLM toggle)
  - `app/src/ui/secrets_screen.py` (extend with OpenAI fields if not present)
  - `app/src/ui/main_screen.py` (modify dispatch flow for LLM generation)
  - `app/src/ui/state.py` (add `LLMPayloadGenerator` instance to `AppState`)
  - `app/src/models/executor.py` (extend `ExecutorConfig` with `use_llm` field)
- **Key Functions/Classes**:
  - `ExecutorConfig.use_llm: bool = False` — new field on the executor config model
  - `AppState.llm_payload_generator: LLMPayloadGenerator` — initialised from secrets
  - Modified `_dispatch_action()` in main screen: check LLM toggle → generate via LLM or standard → open editing dialog
  - LLM toggle UI component with conditional disable based on `LLMService.is_available()`
- **Human/AI Agent**: AI Agent implements all logic
- **Dependencies**: NiceGUI 2.x, `LLMService` (6.1), `LLMPayloadGenerator` (6.2), notifications (5.2), loading overlay (5.1)

**Detailed Implementation Requirements**:

- **File 1: `app/src/models/executor.py`** (extend): Add `use_llm: bool = False` field to the `ExecutorConfig` Pydantic model. This field is persisted alongside the existing executor config fields in `executor.json`. Default is `False` so existing configs are backward-compatible.

- **File 2: `app/src/ui/executor_config.py`** (extend): Below the webhook URL field, add a new section with a `ui.switch("Use LLM for payload generation")` component. Bind it to `executor_config.use_llm`. Check `llm_service.is_available()` — if `False`, disable the switch with `.props('disable')` and add a `ui.tooltip("Configure an OpenAI API key in Manage Secrets to enable LLM payload generation")`. If `True`, enable the switch. When the toggle changes, auto-save to the executor config JSON. Add a brief label below the toggle: "When enabled, AI generates context-aware payload instructions before dispatch. You can always review and edit before sending."

- **File 3: `app/src/ui/secrets_screen.py`** (extend): If not already present, add "OpenAI API Key" and "OpenAI Model" input fields. The API key field should use `password=True` to mask the value. The model field should default to `gpt-4o` with a placeholder showing the default. Save both to `.env/.env.local` as `OPENAI_API_KEY` and `OPENAI_MODEL`. After saving, reinitialise the `LLMService` on `AppState` so the `is_available()` check reflects the new key.

- **File 4: `app/src/ui/state.py`** (extend): Add `llm_service: LLMService` and `llm_payload_generator: LLMPayloadGenerator` attributes to `AppState`. Initialise them during app startup (or lazily on first access). The `LLMService` reads the API key from the environment. The `LLMPayloadGenerator` takes the `LLMService` and the existing `PayloadResolver` instance. Add a `reinit_llm_service()` method that recreates the `LLMService` and `LLMPayloadGenerator` — called after secrets are updated.

- **File 5: `app/src/ui/main_screen.py`** (extend): Modify the dispatch flow in `_dispatch_action()` (or the pre-dispatch handler): (1) When the user clicks an action, check `executor_config.use_llm` and `llm_service.is_available()`. (2) If both are `True`, show the loading overlay with message "Generating payload with AI...". Call `llm_payload_generator.generate_payload(action, project, executor_config)` via `asyncio.to_thread()` (since the LLM call is synchronous). Hide the overlay when done. (3) Open the payload editing dialog with the result payload. If `result.llm_used` is `True`, display a `ui.chip("AI Generated", icon="auto_awesome", color="purple")` badge at the top of the dialog. If `result.llm_used` is `False` and `result.fallback_reason` is not `None`, show `notify_warning(f"LLM generation failed: {result.fallback_reason}. Using standard payload.")`. (4) If `executor_config.use_llm` is `False` or LLM is not available, open the editing dialog with the standard-interpolated payload (existing behaviour). (5) The dialog's "Dispatch" button behaviour remains unchanged — it sends the payload (potentially edited) to the executor.

**Test Requirements**:
- [ ] Unit tests: `ExecutorConfig` model accepts and serialises `use_llm` field
- [ ] Unit tests: `ExecutorConfig` backward-compatible — missing `use_llm` defaults to `False`
- [ ] Unit tests: `AppState.reinit_llm_service()` recreates the LLM service instance
- [ ] Manual verification: LLM toggle appears on executor config screen
- [ ] Manual verification: Toggle is disabled when no OpenAI API key is set, with tooltip
- [ ] Manual verification: Toggle is enabled and functional when API key is configured
- [ ] Manual verification: Clicking an action with LLM enabled shows loading indicator → payload dialog with "AI Generated" badge
- [ ] Manual verification: LLM failure shows warning toast and opens dialog with standard payload (no AI badge)
- [ ] Manual verification: Payload can be freely edited after LLM generation

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing
- [ ] Documentation created: Component Overview (`docs/components/phase-6-component-6-3-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-6.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality (Phase 4 and 5 screens still render and function correctly)
- [ ] Core application is still working post component implementation

**Notes**:
The LLM generation is called via `asyncio.to_thread()` because the OpenAI SDK's synchronous client blocks the event loop. NiceGUI runs on an asyncio event loop, so blocking calls must be offloaded to a thread pool. The `with_loading()` helper from Component 5.1 should handle the overlay show/hide. The "AI Generated" badge uses Quasar's QChip component via `ui.chip()` — the `auto_awesome` Material icon is a sparkle icon commonly associated with AI features. Backward compatibility is important: existing `executor.json` files without the `use_llm` field must still load correctly — Pydantic's default value handles this. The secrets screen may already have some fields from Phase 2/4 setup; only add the OpenAI fields if they are not already present.

---

### Component 6.4 — Testing & Phase Validation

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Components 6.1 through 6.3: All Phase 6 LLM integration components implemented
- Phase 4 and 5 tests still passing (no regression)

**Features**:
- [AI Agent] Create unit tests for `LLMService` (mocked OpenAI SDK) covering success, auth error, rate limit, timeout, and generic error
- [AI Agent] Create unit tests for `LLMPayloadGenerator` covering context assembly, prompt construction, response parsing, merge logic, and fallback scenarios
- [AI Agent] Create integration test for the full LLM payload generation flow: action → context assembly → LLM call → parse → merge → result (mocked LLM)
- [AI Agent] Create fallback integration test: LLM failure → standard interpolation with correct `PayloadGenerationResult`
- [AI Agent] Run full quality validation (Black, isort, pytest, evals)
- [AI Agent] Create/update Phase 6 implementation context documentation
- [AI Agent] Execute E2E scenario validation to confirm Phase 6 changes don't break existing workflows
- [AI Agent] Verify E2E scenario E2E-004 (LLM payload generation) is testable

**Description**:
This component completes Phase 6 by consolidating all tests, running quality checks, and creating phase documentation. The primary testing focus is on the LLM service and payload generator — both must be thoroughly tested with mocked external dependencies. The fallback path (LLM failure → standard interpolation) is equally important to test as the success path. All previous E2E scenarios are re-validated to confirm no regressions. Phase documentation captures all components, key decisions (focused LLM scope on `agent_instructions` only, JSON response format, 4000-char context truncation), and integration notes.

**Acceptance Criteria**:
- [ ] All Phase 4 and 5 tests continue to pass (no regression)
- [ ] `LLMService` unit tests: success, auth error, rate limit, timeout, generic error, and `is_available()` — all pass with mocked OpenAI SDK
- [ ] `LLMPayloadGenerator` unit tests: context assembly, prompt construction, response parsing (valid JSON, code fences, invalid JSON), merge logic, and all fallback scenarios — all pass
- [ ] Integration test: Full LLM generation flow (mocked) produces a `PayloadGenerationResult` with `llm_used=True` and a merged payload containing LLM-generated `agent_instructions`
- [ ] Integration test: LLM failure flow produces a `PayloadGenerationResult` with `llm_used=False`, `fallback_reason` set, and the standard-interpolated payload
- [ ] All unit tests pass: `pytest -q --cov=app/src --cov-report=term-missing`
- [ ] Test coverage on `app/src/` is ≥ 30%
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes
- [ ] `python scripts/evals.py` passes (all public functions have docstrings, no TODO/FIXME)
- [ ] `docs/implementation-context-phase-6.md` exists with entries for all Phase 6 components
- [ ] E2E scenarios E2E-001, E2E-002, and E2E-003 still pass after Phase 6 changes
- [ ] E2E scenario E2E-004 (LLM payload generation) is documented and manually verifiable

**Technical Details**:
- **Files to Create/Modify**:
  - `tests/test_llm_service.py` (create)
  - `tests/test_llm_payload_generator.py` (create)
  - `tests/test_llm_integration.py` (create)
  - `docs/implementation-context-phase-6.md` (create)
  - `docs/components/phase-6-component-6-4-overview.md` (create)
- **Key Functions/Classes**: Test functions for LLM service, payload generator, and integration flow
- **Human/AI Agent**: AI Agent writes all tests and documentation
- **Dependencies**: pytest, pytest-cov, unittest.mock, all Phase 6 modules

**Detailed Implementation Requirements**:

- **File 1: `tests/test_llm_service.py`**: Test the `LLMService` class with mocked OpenAI SDK. (1) Test `is_available()` returns `False` when initialised without API key: `svc = LLMService(api_key=None)` → `assert svc.is_available() is False`. (2) Test `is_available()` returns `True` when initialised with API key: `svc = LLMService(api_key="test-key")` → `assert svc.is_available() is True`. (3) Test `generate()` success: mock `openai.OpenAI` and its `chat.completions.create` method to return a mock response with `choices[0].message.content = '{"agent_instructions": "Test instructions"}'`. Verify the returned string matches. (4) Test `generate()` raises `LLMAuthError`: mock `chat.completions.create` to raise `openai.AuthenticationError`. Verify `LLMAuthError` is raised. (5) Test `generate()` raises `LLMRateLimitError`: mock to raise `openai.RateLimitError`. (6) Test `generate()` raises `LLMTimeoutError`: mock to raise `openai.APITimeoutError`. (7) Test `generate()` raises `LLMServiceError` for generic `openai.APIError`. (8) Test that `generate()` raises `LLMServiceError` when called without API key. (9) Verify that the API key string never appears in any logged output — use a logging capture fixture.

- **File 2: `tests/test_llm_payload_generator.py`**: Test the `LLMPayloadGenerator` class. (1) Test `_assemble_context()` with an Implement action: verify output includes phase name, component ID, component name, and agent paths. (2) Test `_assemble_context()` with a Test action: verify output includes phase name and component list. (3) Test `_assemble_context()` truncates context to 4000 chars when component breakdown content is long. (4) Test `_build_system_prompt()` returns a non-empty string containing "agent_instructions". (5) Test `_build_user_prompt()` includes action type, template instructions, and context. (6) Test `_parse_response()` with valid JSON: `'{"agent_instructions": "Do the thing"}'` → returns dict. (7) Test `_parse_response()` with JSON in code fences: `'```json\n{"agent_instructions": "Do the thing"}\n```'` → returns dict. (8) Test `_parse_response()` with invalid JSON → raises `ValueError`. (9) Test `_parse_response()` with missing `agent_instructions` key → raises `ValueError`. (10) Test `_merge_payload()` preserves `repository`, `branch`, `model` from resolved payload and overrides `agent_instructions` from LLM. (11) Test `generate_payload()` with `is_available()=False` → returns standard payload with `llm_used=False`. (12) Test `generate_payload()` with `use_llm=False` → returns standard payload with `llm_used=False`.

- **File 3: `tests/test_llm_integration.py`**: Integration tests with mocked LLM. (1) Full success flow: create a `LLMService` with mocked `generate()` returning valid JSON, create a `LLMPayloadGenerator` with real `PayloadResolver`, call `generate_payload()` with a test action and project. Verify `result.llm_used is True`, `result.payload["agent_instructions"]` contains the LLM-generated text, and `result.payload["repository"]` contains the standard-interpolated value. (2) Fallback flow: mock `LLMService.generate()` to raise `LLMTimeoutError`. Call `generate_payload()`. Verify `result.llm_used is False`, `result.fallback_reason` contains "timed out", and `result.payload` matches the standard-interpolated payload. (3) Parse failure fallback: mock `LLMService.generate()` to return invalid text ("I can't generate that"). Call `generate_payload()`. Verify fallback to standard interpolation.

- **File 4: `docs/implementation-context-phase-6.md`**: Running log with entries for Components 6.1–6.4. Each entry includes: component ID and name, status (completed), key files created/modified, notable decisions (e.g., "LLM only generates agent_instructions field — keeps scope focused and fallback clean", "JSON response format enforced via system prompt for reliable parsing", "4000-char context truncation prevents token budget issues", "synchronous OpenAI client offloaded via asyncio.to_thread() for NiceGUI compatibility", "PayloadGenerationResult dataclass provides explicit llm_used/fallback_reason for UI feedback").

- **File 5: `docs/components/phase-6-component-6-4-overview.md`**: Summary of the testing and validation component — test file inventory, coverage notes, quality check results, and E2E validation status.

**Test Requirements**:
- [ ] All new test files pass
- [ ] All Phase 4 and 5 tests still pass
- [ ] `pytest -q --cov=app/src --cov-report=term-missing` reports ≥ 30% coverage
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes
- [ ] `python scripts/evals.py` passes

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] Tests written and passing with ≥ 30% coverage
- [ ] All quality checks pass (Black, isort, pytest, evals)
- [ ] Documentation created: Component Overview (`docs/components/phase-6-component-6-4-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-6.md`). Maximum 50 lines of markdown per component.
- [ ] No regression in existing functionality (Phase 1, 2, 3, 4, and 5 tests still pass)
- [ ] Core application is still working post component implementation
- [ ] E2E scenarios E2E-001 through E2E-003 re-validated
- [ ] E2E scenario E2E-004 documented and manually verifiable

**Notes**:
Mocking the OpenAI SDK is straightforward with `unittest.mock.patch("openai.OpenAI")`. The mock needs to implement `client.chat.completions.create()` returning a mock with `choices[0].message.content`. For the integration tests, use real `PayloadResolver` and `Action`/`Project` fixtures to verify the end-to-end data flow. The logging capture fixture (`caplog` in pytest) is useful for verifying no secrets appear in log output. E2E scenario E2E-004 from the phase plan ("Enable LLM toggle → click action → LLM generates payload → review → edit → dispatch → verify response") is manual because it requires a real OpenAI API key; document the steps for human-gated execution.

---

## Phase Acceptance Criteria

- [ ] `LLMService` initialises from secrets and correctly reports availability
- [ ] LLM toggle is available in executor config, disabled when no API key is configured
- [ ] When enabled, LLM generates `agent_instructions` from project context within 5 seconds (under normal API conditions)
- [ ] Generated payloads are displayed for review in the editing dialog with an "AI Generated" badge
- [ ] Users can manually edit LLM-generated payloads before dispatch
- [ ] If OpenAI API call fails (auth, rate limit, timeout, or other error), system falls back to standard `{{variable}}` interpolation with a warning notification
- [ ] If no OpenAI API key is configured, LLM toggle is disabled with explanatory tooltip
- [ ] Non-instruction payload fields (`repository`, `branch`, `model`, `role`, `callback_url`, `timeout_minutes`) are always resolved via standard interpolation — never LLM-generated
- [ ] `PayloadGenerationResult` accurately reports whether LLM was used and the fallback reason if not
- [ ] Secrets screen supports OpenAI API key and model configuration
- [ ] All unit tests pass with mocked OpenAI SDK
- [ ] All Phase 4 and 5 tests continue to pass (no regression)
- [ ] Test coverage on `app/src/` is ≥ 30%
- [ ] `black --check app/src/` and `isort --check-only app/src/` pass
- [ ] `python scripts/evals.py` passes with no violations
- [ ] `docs/implementation-context-phase-6.md` documents all implemented components
- [ ] E2E scenarios E2E-001, E2E-002, E2E-003 still pass; E2E-004 is documented for manual verification

---

## Cross-Cutting Concerns

### Testing Strategy
- **E2E Testing Scenarios**: After Phase 6, all Phase 4 E2E scenarios (E2E-001, E2E-002, E2E-003) must still pass. Phase 6 adds E2E-004 (LLM payload generation) which requires a real OpenAI API key for full validation — gate behind `--llm-confirm` pytest flag for human-gated execution. Document the manual E2E steps for E2E-004 in the agent runbook.
- **Unit Testing**: pytest with fixtures and mocked OpenAI SDK. Focus on `LLMService` (all error paths), `LLMPayloadGenerator` (context assembly, prompt construction, response parsing, merge, fallback), and `ExecutorConfig` model extension. Target ≥ 30% coverage on `app/src/`.
- **Integration Testing**: Mocked LLM calls for full-chain tests from action through LLM generation to payload merge. Verify both success and fallback paths produce correct `PayloadGenerationResult`.
- **Performance Testing**: Verify LLM generation completes within 5 seconds under normal conditions (manual verification with real API key). Timeout at 10 seconds ensures the UI never hangs.

### Documentation Requirements
- **Developer Context Documentation**: `docs/implementation-context-phase-6.md`, `docs/components/phase-6-component-6-X-overview.md` per component
- **Agent Runbook**: Updated with LLM configuration instructions (API key setup, model selection, toggle usage) and E2E-004 manual test steps
- **Code Documentation**: Google-style docstrings on all new public functions and classes in `llm_service.py` and `llm_payload_generator.py`
- **Architecture Decision Records**: Document in implementation context: LLM scope limited to `agent_instructions` field, JSON response format, 4000-char context truncation, synchronous SDK with `asyncio.to_thread()`, `PayloadGenerationResult` pattern for explicit success/fallback reporting
