# Dispatch End-to-End Testing Scenarios

This document defines the baseline end-to-end (E2E) test scenarios for Dispatch. These scenarios are introduced in Phase 1 and become executable as implementation phases progress.

## Scenario Readiness Matrix

| Scenario ID | Scenario Name | Earliest Validation Phase | Status in Phase 1 |
|---|---|---|---|
| E2E-001 | Configure & dispatch | Phase 4 | Planned |
| E2E-002 | Load & run full phase | Phase 4 | Planned |
| E2E-003 | Debug action workflow | Phase 4 | Planned |
| E2E-004 | LLM payload generation | Phase 6 | Planned |
| E2E-005 | Cross-device access | Phase 7 | Planned |

---

## E2E-001 — Configure & Dispatch

- **Description**: Validate the primary workflow from configuring the executor to dispatching an action and receiving a webhook response.
- **Preconditions**:
  - Dispatch application is running.
  - Valid executor endpoint and API key are available.
  - GitHub token is configured.
  - Target repository contains `phase-progress.json`.
- **Steps**:
  1. Open Dispatch and navigate to **Configure Executor**.
  2. Set Autopilot API endpoint, API key, and webhook URL.
  3. Configure action type defaults (Implement/Test/Review/Document/Debug).
  4. Link a new project using `owner/repo` and token.
  5. Verify `phase-progress.json` is discovered and action items are generated.
  6. Click an **Implement** action item to dispatch.
  7. Click **Refresh** to load webhook response data.
  8. Mark the action item complete.
- **Expected Results**:
  - Executor configuration persists.
  - Project linking succeeds and actions populate in the left panel.
  - Dispatch response status/message appears in the right panel.
  - Webhook payload/status appears after refresh.
  - Action can be marked complete.
- **Pass Criteria**: All expected results are observed with no unhandled errors.
- **Fail Criteria**: Any expected UI update or response is missing, or dispatch fails unexpectedly.

## E2E-002 — Load & Run Full Phase

- **Description**: Validate end-to-end execution of all actions in a phase for a previously saved project.
- **Preconditions**:
  - A project has been previously linked and saved.
  - Action items exist for at least Phase 1.
  - Executor configuration is valid.
- **Steps**:
  1. Open Dispatch and click **Load Project**.
  2. Select a saved project.
  3. Verify the action list renders all phase actions.
  4. Dispatch each **Implement** action for Phase 1 in sequence.
  5. Dispatch the Phase 1 **Test** action.
  6. Dispatch the Phase 1 **Review** action.
  7. Dispatch the Phase 1 **Document** action.
  8. Mark each action complete after successful response.
- **Expected Results**:
  - Saved project loads successfully.
  - Responses are displayed after each dispatch.
  - Completion state updates for each action.
- **Pass Criteria**: Full phase action sequence runs without data loss or ordering issues.
- **Fail Criteria**: Missing actions, incorrect ordering, dispatch failures, or completion state not updating.

## E2E-003 — Debug Action Workflow

- **Description**: Validate manual insertion and execution of a Debug action within a phase action list.
- **Preconditions**:
  - A project with generated actions is loaded.
  - Debug action type default payload is configured.
- **Steps**:
  1. Open the loaded project action list.
  2. Insert a **Debug** action at a specific position in Phase 1.
  3. Open the debug payload editor.
  4. Modify agent instructions and save changes.
  5. Dispatch the debug action.
  6. Review response details and mark the debug action complete.
- **Expected Results**:
  - Debug action inserts in the selected list position.
  - Payload edits persist for that action.
  - Dispatch response displays correctly.
  - Completion state updates for the debug action.
- **Pass Criteria**: Debug action can be inserted, edited, dispatched, and completed without affecting neighboring actions.
- **Fail Criteria**: Incorrect insertion index, payload edit loss, dispatch failure, or completion state failure.

## E2E-004 — LLM Payload Generation

- **Description**: Validate optional LLM-assisted payload generation and manual override before dispatch.
- **Preconditions**:
  - LLM support is enabled in configuration.
  - Valid OpenAI API key and model are configured.
  - At least one action item is available for dispatch.
- **Steps**:
  1. Enable the LLM payload generation option.
  2. Select an action item and trigger payload generation.
  3. Review generated payload content.
  4. Apply manual edits where needed.
  5. Dispatch the action.
  6. Confirm response and completion behavior.
- **Expected Results**:
  - LLM-generated payload is returned within configured timeout.
  - User can review and edit payload before dispatch.
  - Dispatch and response handling remain identical to non-LLM flow.
- **Pass Criteria**: Generated payload is usable, editable, and dispatches successfully.
- **Fail Criteria**: Generation fails without fallback path, payload is malformed, or dispatch flow breaks.

## E2E-005 — Cross-Device Access

- **Description**: Validate app accessibility and data continuity between macOS and iPhone using OneDrive-synced storage.
- **Preconditions**:
  - Dispatch data directory is configured to a OneDrive-synced path.
  - macOS host and iPhone are on the same network.
  - Application is reachable from iPhone Safari.
- **Steps**:
  1. Launch Dispatch on macOS.
  2. Open the app from iPhone Safari.
  3. Verify initial, configuration, and main screens render on both devices.
  4. Perform a state change (for example: update payload text, mark action complete).
  5. Refresh on the second device and verify the same state is visible.
- **Expected Results**:
  - UI renders and remains usable on both form factors.
  - Project data/state remains consistent across devices after sync.
- **Pass Criteria**: Cross-device interactions and persisted state are consistent and reliable.
- **Fail Criteria**: Rendering issues block workflow, or synced state is stale/inconsistent.
