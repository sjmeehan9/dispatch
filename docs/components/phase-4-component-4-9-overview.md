# Phase 4 Component 4.9 Overview: Debug Action Insertion & Payload Editing

## Summary
Component 4.9 adds two operator-facing controls to the main dispatch workflow: in-phase debug action insertion and per-action payload editing. Users can now inject ad-hoc Debug actions at precise points in a phase and directly adjust payload JSON before dispatch.

## What Was Implemented
- Extended `app/src/ui/main_screen.py` with debug insertion and payload edit flows.
- Added debug insertion helpers:
  - `_insert_debug_action(app_state, phase_id, position)`
  - `_show_insert_debug_dialog(app_state, phase_id, phase_action_count, refresh_action_list, refresh_response_panel)`
- Added payload editing helpers:
  - `_show_payload_editor(app_state, project_service, action, refresh_action_list, refresh_response_panel)`
  - `_save_edited_payload(action, new_payload_json)`
  - `_find_unresolved_variables(payload_json)`

## Debug Action Insertion Behavior
- Each phase section now exposes an `Add Debug` button.
- Clicking it opens a dialog with a bounded insertion position (`0..N`, where `N` is actions in the phase).
- Confirming insertion calls `ActionGenerator.insert_debug_action(...)`.
- New debug actions are payload-resolved through `PayloadResolver` and saved to disk immediately.
- Success/failure feedback is surfaced with NiceGUI notifications.

## Payload Editing Behavior
- Each action row now includes an `Edit Payload` control.
- The editor opens a modal JSON textarea (20 rows, wide dialog) pre-filled with formatted payload JSON.
- Save validates JSON via `json.loads(...)` and requires a JSON object payload.
- Invalid JSON blocks save and shows an error notification.
- Valid edits update `action.payload`, persist the project, and refresh the action/response panels.

## Unresolved Variable Highlighting
- The editor scans for placeholder patterns like `{{phase_id}}`.
- Detected unresolved placeholders are listed as warning labels below the editor.
- Warnings are informational only; users can still save valid JSON containing placeholders.

## Tests Added
- Updated `tests/test_main_screen.py` with:
  - invalid JSON rejection test for `_save_edited_payload`
  - valid JSON update test for `_save_edited_payload`
  - insertion-order/persistence test for `_insert_debug_action`

## Outcome
Component 4.9 acceptance goals are implemented: users can insert Debug actions at selected positions, edit payload JSON safely, identify unresolved placeholders, and persist all updates through existing project save flows.
