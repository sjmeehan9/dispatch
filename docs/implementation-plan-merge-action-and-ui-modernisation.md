# Implementation Plan: Merge Action Type & UI Modernisation

**Date:** 2025-03-15  
**Status:** Draft — awaiting approval  
**Scope:** Two independent requirements delivered as a single coordinated plan

---

## Table of Contents

1. [Requirement Summary](#requirement-summary)
2. [Requirement 1 — Merge Action Type & Per-Component Review/Merge Flow](#requirement-1--merge-action-type--per-component-reviewmerge-flow)
3. [Requirement 2 — UI Modernisation](#requirement-2--ui-modernisation)
4. [Implementation Phases](#implementation-phases)
5. [Risk & Migration Notes](#risk--migration-notes)

---

## Requirement Summary

### R1 — Merge Action Type & Per-Component Review/Merge
Since the Autopilot executor's `implement` role creates a PR, every implement action must now be followed by a `review` action and then a `merge` action (operating on that PR). The current flow generates one `review` at the phase level; the new flow pairs review+merge with each implement at the component level. The existing phase-level test/document actions remain.

### R2 — UI Modernisation
A visual polish pass across all screens, with the main project dispatch page as the primary focus. Key issues: left/right panels don't fill vertical space, action items lack visual distinction, and phase boundaries are not visually obvious.

---

## Requirement 1 — Merge Action Type & Per-Component Review/Merge Flow

### Current Architecture

**Action generation** (`app/src/services/action_generator.py` → `generate_actions`):
```
For each phase (sorted):
  For each component (sorted):
    → IMPLEMENT action (component-scoped)
  → TEST action (phase-scoped)
  → REVIEW action (phase-scoped)
  → DOCUMENT action (phase-scoped)
```

**ActionType enum** (`app/src/models/project.py`):
```python
class ActionType(StrEnum):
    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"
    DOCUMENT = "document"
    DEBUG = "debug"
```

**ActionTypeDefaults model** (`app/src/models/executor.py`):
```python
class ActionTypeDefaults(BaseModel):
    implement: dict[str, object]
    test: dict[str, object]
    review: dict[str, object]
    document: dict[str, object]
    debug: dict[str, object]
```

**Default payload templates** (`app/config/defaults.yaml`):
- `implement`: role=implement, no pr_number
- `review`: role=review, pr_number={{pr_number}}
- No `merge` template exists

**Payload resolver** (`app/src/services/payload_resolver.py`):
- `build_context()` already includes `pr_number` in the context dict (currently empty string)
- The review default template already has `pr_number: "{{pr_number}}"` — but today it resolves to "" because the context sets it to empty

**Key observation — PR number flow**: When `implement` is dispatched, the Autopilot executor creates a PR. The `run_id` is returned in the executor response, and the webhook callback (when received) contains the full run result including `result.pr_number`. This PR number must flow from the implement action's webhook response into the subsequent review and merge actions' `pr_number` field.

### Proposed Changes

#### 1.1 — Add `MERGE` to `ActionType` enum

**File:** `app/src/models/project.py`

```python
class ActionType(StrEnum):
    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"
    MERGE = "merge"          # ← NEW
    DOCUMENT = "document"
    DEBUG = "debug"
```

#### 1.2 — Add `merge` field to `ActionTypeDefaults`

**File:** `app/src/models/executor.py`

```python
class ActionTypeDefaults(BaseModel):
    implement: dict[str, object]
    test: dict[str, object]
    review: dict[str, object]
    merge: dict[str, object]   # ← NEW
    document: dict[str, object]
    debug: dict[str, object]
```

#### 1.3 — Add `merge` default template to `defaults.yaml`

**File:** `app/config/defaults.yaml`

Add a new `merge` section under `action_type_defaults`:

```yaml
  merge:
    repository: "{{repository}}"
    branch: "{{branch}}"
    agent_instructions: "Merge the PR for {{component_name}} ({{component_id}}) of Phase {{phase_id}}."
    model: "claude-opus-4.6"
    role: "merge"
    pr_number: "{{pr_number}}"
    agent_paths: "{{agent_paths}}"
    callback_url: "{{webhook_url}}"
    timeout_minutes: 10
```

#### 1.4 — Restructure action generation order

**File:** `app/src/services/action_generator.py`

Change from:
```
For each phase:
  [implement, implement, ...] → test → review → document
```

To:
```
For each phase:
  For each component:
    implement → review → merge
  test → document
```

The phase-level `review` is removed (review is now per-component). `test` and `document` remain at phase level.

**Updated `generate_actions` method:**

```python
for phase in sorted(phases, key=...):
    for component in sorted(phase.components, key=...):
        # Implement
        actions.append(cls._create_action(
            ActionType.IMPLEMENT, phase.phase_id,
            component.component_id, action_type_defaults.implement,
        ))
        # Review (per-component, follows its implement)
        actions.append(cls._create_action(
            ActionType.REVIEW, phase.phase_id,
            component.component_id, action_type_defaults.review,
        ))
        # Merge (per-component, follows its review)
        actions.append(cls._create_action(
            ActionType.MERGE, phase.phase_id,
            component.component_id, action_type_defaults.merge,
        ))
    
    # Phase-level actions
    actions.append(cls._create_action(
        ActionType.TEST, phase.phase_id, None, action_type_defaults.test,
    ))
    actions.append(cls._create_action(
        ActionType.DOCUMENT, phase.phase_id, None, action_type_defaults.document,
    ))
```

Note: The phase-level `REVIEW` is removed entirely. Each component now gets its own implement → review → merge triplet. The reasoning: since implement creates a PR, commit review and merge are inherently tied to that specific PR.

#### 1.5 — Update `_action_label` in main_screen.py

**File:** `app/src/ui/main_screen.py`

The current `_action_label` function returns `"{Type} Phase {N}"` for non-implement actions. Since review and merge are now component-scoped, update the label logic to show component names for these types too:

```python
def _action_label(project: Project, action: Action) -> str:
    action_type = str(action.action_type)
    
    # Component-scoped actions: implement, review, merge
    if action_type in (ActionType.IMPLEMENT, ActionType.REVIEW, ActionType.MERGE) and action.component_id:
        component_name = _resolve_component_name(project, action)
        type_label = action_type.title()
        return f"{type_label}: {component_name}"
    
    # Phase-scoped actions: test, document, debug
    return f"{action_type.title()} Phase {action.phase_id}"
```

#### 1.6 — Add merge icon mapping

**File:** `app/src/ui/components.py`

Add to `_ACTION_TYPE_ICON_MAP`:

```python
ActionType.MERGE.value: ("merge", "green"),
```

#### 1.7 — Update Action Type Defaults UI

**File:** `app/src/ui/action_type_defaults.py`

Add `"merge"` to the `_ACTION_TYPES` tuple:

```python
_ACTION_TYPES: tuple[str, ...] = ("implement", "test", "review", "merge", "document", "debug")
```

#### 1.8 — PR Number Propagation Strategy

This is the most architecturally significant change. Currently, `pr_number` resolves to `""` because no mechanism populates it dynamically. After an implement action is dispatched and the webhook response contains a PR number, the subsequent review and merge actions for the same component need that PR number injected.

**Proposed approach — Automatic PR number propagation:**

Add a method to `ActionGenerator` (or create a lightweight helper) that, after an implement action receives its webhook response, scans the webhook payload for `result.pr_number` and writes it into the `payload.pr_number` field of the next review and merge actions for the same component:

```python
@classmethod
def propagate_pr_number(
    cls,
    actions: list[Action],
    source_action: Action,
    pr_number: int,
) -> None:
    """Set pr_number on review/merge actions that follow a completed implement."""
    if source_action.action_type != ActionType.IMPLEMENT:
        return
    
    for action in actions:
        if (
            action.phase_id == source_action.phase_id
            and action.component_id == source_action.component_id
            and action.action_type in (ActionType.REVIEW, ActionType.MERGE)
            and action.status == ActionStatus.NOT_STARTED
        ):
            action.payload["pr_number"] = pr_number
```

**Trigger point:** Call `propagate_pr_number` in two places:
1. When `_mark_complete` is called on an implement action and its webhook response contains a PR number
2. When a webhook response is received and stored (in `_render_response_panel`'s refresh webhook handler)

**UI indicator:** When a review/merge action has `pr_number` set (non-empty, non-placeholder), show a small badge/chip like `PR #42` next to the action label. When `pr_number` is still `{{pr_number}}` or empty, show a warning indicator that the implement step hasn't completed yet.

#### 1.9 — Update `build_context` in PayloadResolver

**File:** `app/src/services/payload_resolver.py`

The `pr_number` context value currently defaults to `""`. Since PR number propagation now writes directly to `action.payload["pr_number"]`, the resolver's context-based approach still works as a fallback, but the direct payload write in 1.8 takes precedence (the resolver only replaces `{{pr_number}}` placeholders — if the value is already a concrete number, it stays).

No change required here, but document this interaction clearly.

#### 1.10 — Update defaults.yaml placeholder comments

**File:** `app/config/defaults.yaml`

Update the placeholder comment block to include:
```yaml
  # - {{pr_number}} pull request number (review, merge)
```

#### 1.11 — Test Updates

**Files affected:**
- `tests/test_action_generator.py` — Update expected action sequences: each component now produces 3 actions (implement→review→merge) instead of 1, and the phase-level review is gone
- `tests/test_action_type_defaults.py` — Add `merge` field to test fixtures
- `tests/test_models.py` — Add MERGE to ActionType assertions
- `tests/test_payload_resolver.py` — Add test for pr_number resolution with merge payloads
- New: `tests/test_pr_number_propagation.py` — Test the propagation logic
- Update all test fixtures that create `ActionTypeDefaults` to include the `merge` field

**Breaking change for existing saved projects:** Existing projects have actions generated under the old pattern (no merge type, phase-level review). These projects will still load fine since `Action` is schema-flexible, but they won't have merge actions. Options:
1. **Regenerate actions** — add a "Regenerate Actions" button on the main screen that re-runs `generate_actions` and replaces the action list (losing dispatch history)
2. **Graceful coexistence** — old projects work as-is; only newly linked/regenerated projects get the new pattern

Recommend option 2 for backward compatibility, with option 1 available as an explicit user action.

---

## Requirement 2 — UI Modernisation

### Current State Assessment

**Framework:** NiceGUI (built on Quasar/Vue3) — no framework change required.

**Current issues identified:**
1. **Panels don't fill vertical space** — `dispatch-panel-scroll` uses `max-height: calc(100vh - 220px)` but no `min-height`, so panels shrink to content height
2. **No visual distinction between action items** — Actions render as flat `ui.item()` elements in a `ui.list()` with minimal styling
3. **Phase boundaries not visually obvious** — Phases use `ui.expansion()` which provides some grouping, but the boundary between phases is just whitespace
4. **General look is utilitarian** — White header, default Quasar styling, no brand colours or visual hierarchy

### Proposed UI Changes

#### 2.1 — Full-Height Panel Layout

**File:** `app/src/static/styles.css`

Change the panel layout to fill available viewport height:

```css
.dispatch-panel-scroll {
  min-height: calc(100vh - 220px);
  max-height: calc(100vh - 220px);
  height: calc(100vh - 220px);
}
```

**File:** `app/src/ui/main_screen.py`

Ensure the outer container uses flex column with `flex-grow`:

```python
with ui.element("div").classes(
    "row q-col-gutter-md w-full dispatch-main-panels"
):
```

Add CSS:
```css
.dispatch-main-panels {
  flex: 1 1 auto;
  min-height: 0;
}
```

#### 2.2 — Action Item Card/Pill Treatment

Replace the current flat `ui.item()` rendering with distinct card-style containers for each action:

**Current rendering (simplified):**
```python
with ui.list().classes("w-full"):
    for action in actions:
        with ui.item().classes("w-full"):
            # icon, label, status badge, buttons
```

**Proposed rendering:**
```python
with ui.column().classes("w-full q-gutter-sm"):
    for action in actions:
        with ui.card().classes(
            f"w-full q-pa-sm dispatch-action-card dispatch-action-{action.action_type}"
        ):
            with ui.row().classes("w-full items-center justify-between no-wrap"):
                # Left: icon + label + status
                with ui.row().classes("items-center q-gutter-sm"):
                    icon_name, icon_color = action_type_icon(action.action_type)
                    ui.icon(icon_name).props(f'color="{icon_color}" size="sm"')
                    ui.label(_action_label(project, action)).classes("text-body2 text-weight-medium")
                    action_status_badge(action.status)
                # Right: action buttons
                with ui.row().classes("items-center q-gutter-xs"):
                    # dispatch, mark complete, edit buttons
```

**CSS for action cards:**
```css
.dispatch-action-card {
  border-left: 4px solid transparent;
  border-radius: 8px;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.dispatch-action-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

/* Color-coded left border by action type */
.dispatch-action-implement { border-left-color: #1976d2; }  /* primary blue */
.dispatch-action-review    { border-left-color: #ff9800; }  /* orange */
.dispatch-action-merge     { border-left-color: #4caf50; }  /* green */
.dispatch-action-test      { border-left-color: #9c27b0; }  /* purple */
.dispatch-action-document  { border-left-color: #009688; }  /* teal */
.dispatch-action-debug     { border-left-color: #f44336; }  /* red */

/* Completed action visual treatment */
.dispatch-action-completed {
  opacity: 0.65;
  border-left-color: #4caf50 !important;
}

/* Dispatched (in-progress) pulsing indicator */
.dispatch-action-dispatched {
  border-left-color: #2196f3;
  animation: dispatch-pulse 2s ease-in-out infinite;
}

@keyframes dispatch-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(33, 150, 243, 0.3); }
  50% { box-shadow: 0 0 0 4px rgba(33, 150, 243, 0.1); }
}
```

#### 2.3 — Phase Section Visual Treatment

Replace the plain `ui.expansion()` with a more structured phase header:

```python
for phase_id, phase_name, actions in filtered_groups:
    phase_completed = sum(1 for a in actions if a.status == ActionStatus.COMPLETED)
    phase_total = len(actions)
    all_complete = phase_completed == phase_total
    
    with ui.card().classes("w-full dispatch-phase-card"):
        # Phase header bar
        with ui.element("div").classes(
            f"dispatch-phase-header {'dispatch-phase-complete' if all_complete else ''}"
        ):
            with ui.row().classes("w-full items-center justify-between q-px-md q-py-sm"):
                with ui.row().classes("items-center q-gutter-sm"):
                    ui.icon("folder" if not all_complete else "check_circle").props(
                        f'color="{"primary" if not all_complete else "positive"}"'
                    )
                    ui.label(f"Phase {phase_id}: {phase_name}").classes(
                        "text-subtitle1 text-weight-bold"
                    )
                with ui.row().classes("items-center q-gutter-sm"):
                    ui.badge(f"{phase_completed}/{phase_total}").props(
                        'color="primary" text-color="white"'
                    )
                    # Expand/collapse toggle
        
        # Action items inside the phase card
        with ui.column().classes("w-full q-pa-sm q-gutter-xs"):
            # ... action cards as described in 2.2
```

**CSS for phase cards:**
```css
.dispatch-phase-card {
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 12px;
}

.dispatch-phase-header {
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  border-bottom: 1px solid #e0e0e0;
}

.dispatch-phase-complete .dispatch-phase-header {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
}

/* Visual separator between implement→review→merge groups */
.dispatch-component-group {
  border-bottom: 1px dashed #e0e0e0;
  padding-bottom: 8px;
  margin-bottom: 8px;
}

.dispatch-component-group:last-child {
  border-bottom: none;
  padding-bottom: 0;
  margin-bottom: 0;
}
```

#### 2.4 — Component Grouping Within Phases

Since actions now follow implement → review → merge per component, visually group these triplets:

```python
# Group actions by component within a phase
component_groups = _group_by_component(actions)  # returns list of (component_id, [actions])
phase_level_actions = [a for a in actions if a.component_id is None]

for component_id, component_actions in component_groups:
    component_name = _resolve_component_name(project, component_actions[0])
    with ui.element("div").classes("dispatch-component-group"):
        ui.label(component_name).classes("text-caption text-grey-7 q-pl-sm")
        for action in component_actions:
            # render action card (2.2)

# Phase-level actions (test, document)
if phase_level_actions:
    ui.separator().classes("q-my-sm")
    for action in phase_level_actions:
        # render action card (2.2)
```

#### 2.5 — Global Style Polish

**Header modernisation:**
```css
/* Modern header with subtle gradient */
.dispatch-page-header {
  background: linear-gradient(90deg, #1a237e 0%, #283593 100%) !important;
  color: white !important;
}
```

Update `page_layout` in `components.py` to use dark header classes:
```python
with active_ui.header().classes(
    "text-white shadow-2 q-px-md q-py-sm dispatch-page-header"
):
```

**Card and form modernisation across all screens:**
```css
/* Consistent card styling */
.q-card {
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
}

/* Better input fields */
.q-field--outlined .q-field__control {
  border-radius: 8px;
}

/* Button refinements */
.q-btn {
  border-radius: 8px;
  text-transform: none;
  font-weight: 500;
  letter-spacing: 0.01em;
}
```

#### 2.6 — Response Panel Modernisation

The right panel (executor response + webhook response) also needs a polish:

- Use status-coloured header bars on response cards (green for 2xx, red for 4xx/5xx, grey for pending)
- Show the run ID prominently with a copy button
- Better visual hierarchy for webhook data
- Add a "PR: #42" chip when PR number is known from webhook response

#### 2.7 — Progress Bar Enhancement

Replace the simple linear progress with a more informative progress section:

```python
def progress_summary(actions, ui_module=None):
    completed, total, ratio = progress_counts(actions)
    with ui.row().classes("w-full items-center q-gutter-sm"):
        ui.circular_progress(value=ratio, show_value=True).props('size="50px"')
        with ui.column():
            ui.label(f"{completed} of {total} complete").classes("text-subtitle2")
            ui.label(f"{total - completed} remaining").classes("text-caption text-grey-7")
```

---

## Implementation Phases

### Phase A — Merge Action Type (Backend)
**Effort estimate:** 2–3 hours  
**Files modified:** 5–6 files, ~100 lines changed

| Step | File | Change |
|------|------|--------|
| A.1 | `app/src/models/project.py` | Add `MERGE` to `ActionType` enum |
| A.2 | `app/src/models/executor.py` | Add `merge` field to `ActionTypeDefaults` |
| A.3 | `app/config/defaults.yaml` | Add `merge` template section |
| A.4 | `app/src/services/action_generator.py` | Restructure `generate_actions` to implement→review→merge per component |
| A.5 | `app/src/services/action_generator.py` | Add `propagate_pr_number` class method |
| A.6 | `app/src/services/payload_resolver.py` | Ensure `pr_number` context works for merge actions (likely no-change) |
| A.7 | Tests | Update all action generator tests, add PR propagation tests |

### Phase B — Merge Action Type (UI)
**Effort estimate:** 1–2 hours  
**Files modified:** 4 files, ~50 lines changed

| Step | File | Change |
|------|------|--------|
| B.1 | `app/src/ui/components.py` | Add merge icon/colour mapping |
| B.2 | `app/src/ui/main_screen.py` | Update `_action_label` for component-scoped review/merge |
| B.3 | `app/src/ui/main_screen.py` | Wire PR number propagation into mark-complete and webhook-refresh flows |
| B.4 | `app/src/ui/action_type_defaults.py` | Add `"merge"` to `_ACTION_TYPES` |
| B.5 | Tests | Update UI-related tests |

### Phase C — UI Modernisation (Main Screen)
**Effort estimate:** 3–4 hours  
**Files modified:** 3 files, ~200 lines changed

| Step | File | Change |
|------|------|--------|
| C.1 | `app/src/static/styles.css` | Full-height panels, action cards, phase cards, animations |
| C.2 | `app/src/ui/main_screen.py` | Rewrite `_render_action_list` with card-based layout, component grouping |
| C.3 | `app/src/ui/main_screen.py` | Rewrite `_render_response_panel` with modernised styling |
| C.4 | `app/src/ui/main_screen.py` | Add `_group_by_component` helper |
| C.5 | `app/src/ui/components.py` | Update `progress_summary` with circular progress |

### Phase D — UI Modernisation (Global & Other Screens)
**Effort estimate:** 2–3 hours  
**Files modified:** 5–6 files, ~100 lines changed

| Step | File | Change |
|------|------|--------|
| D.1 | `app/src/static/styles.css` | Global card/button/input refinements |
| D.2 | `app/src/ui/components.py` | Modernise header (dark gradient) |
| D.3 | `app/src/ui/initial_screen.py` | Polish initial screen layout |
| D.4 | `app/src/ui/executor_config.py` | Polish executor config form |
| D.5 | `app/src/ui/action_type_defaults.py` | Polish action type defaults form |
| D.6 | `app/src/ui/secrets_screen.py` | Polish secrets screen |
| D.7 | `app/src/ui/link_project.py` | Polish link project flow |
| D.8 | `app/src/ui/load_project.py` | Polish load project flow |

### Phase E — Testing & Validation
**Effort estimate:** 1–2 hours

| Step | Description |
|------|-------------|
| E.1 | Run full test suite, fix regressions from action generation changes |
| E.2 | Run evals (`python scripts/evals.py`), fix any quality gate failures |
| E.3 | Run Black + isort formatting checks |
| E.4 | Manual visual verification of all screens |
| E.5 | Verify backward compatibility: load an existing saved project |

---

## Risk & Migration Notes

### Backward Compatibility

**Saved projects:** Existing projects saved to disk have actions generated under the old pattern (no merge type, phase-level review). These projects will still load because the `Action` model is flexible (any `action_type` string is accepted via `use_enum_values=True`). However:
- They won't have merge actions
- They'll have phase-level review instead of component-level review

**Mitigation:** Add a "Regenerate Actions" button on the main screen that re-runs `generate_actions` with current defaults. This replaces the action list but loses dispatch history. Users should complete in-progress phases before regenerating.

**ActionTypeDefaults persistence:** Existing saved `action_type_defaults.json` files won't have a `merge` field. When `ActionTypeDefaults.model_validate()` is called, Pydantic will raise a validation error.

**Mitigation:** Update `ConfigManager.get_action_type_defaults()` to handle missing `merge` field by injecting the default merge template from `defaults.yaml` before validation. This is a one-line defensive check.

### PR Number Flow

The PR number propagation is the riskiest new behaviour:
- **Happy path:** Implement dispatches → webhook returns with `result.pr_number` → user marks complete → PR number propagates to review/merge actions → review dispatches with correct PR → merge dispatches with correct PR
- **Missing PR number:** If the webhook doesn't include a PR number, or the user marks complete before receiving the webhook, the review/merge actions will have an empty `pr_number` — the user can manually edit the payload to add it
- **Autopilot behaviour variance:** Verify the exact webhook response field path for PR number. The autopilot runbook shows `result.pr_url` and `result.pr_number` for implement results. Confirm this is consistent.

### NiceGUI CSS Considerations

NiceGUI uses Quasar components which have their own CSS specificity. Custom styles may need `!important` or deeper selectors to override Quasar defaults. Test thoroughly on both desktop and mobile viewports.
