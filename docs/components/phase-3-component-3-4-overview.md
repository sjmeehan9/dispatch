# Phase 3 Component 3.4 Overview — Action Generator Service

## Summary
Component 3.4 delivers the action derivation engine that converts parsed phase data into executable Dispatch actions. It guarantees deterministic ordering, UUID assignment, per-action payload template isolation, and phase-local Debug action insertion.

## Implemented Scope
- Added `app/src/services/action_generator.py` with `ActionGenerator`:
  - `generate_actions(phases, action_type_defaults) -> list[Action]`
  - `insert_debug_action(actions, phase_id, position, action_type_defaults) -> list[Action]`
  - `_create_action(action_type, phase_id, component_id, template) -> Action`
  - `_component_sort_key(component_id)` for dotted natural sort
- Updated `app/src/services/__init__.py` exports to include `ActionGenerator`.

## Key Behavior
- **Generation order**:
  1. phases sorted by `phase_id`,
  2. components sorted by natural dotted order (`1.1`, `1.2`, `1.10`),
  3. per phase actions emitted as: Implement* → Test → Review → Document.
- **Field mapping**:
  - Implement actions include `component_id`.
  - Test/Review/Document/Debug actions set `component_id=None`.
- **Defaults and mutability safety**:
  - Payload templates are deep-copied during action creation to prevent edits from mutating shared defaults.
- **Action metadata**:
  - Every action gets a unique UUID `action_id`.
  - Initial state is `status=not_started`, `executor_response=None`, `webhook_response=None`.
- **Debug insertion**:
  - Inserts at a zero-based position relative to a phase’s action subset.
  - Validates range and raises `ValueError` for invalid positions.
  - Returns the mutated list for chaining.

## Observability
- INFO logs added for:
  - total actions generated vs phase count,
  - debug insertion position and phase ID.

## Tests Added
- New file: `tests/test_action_generator.py`
- Coverage includes:
  - single-phase generation order and action types,
  - component natural sort behavior,
  - multi-phase ordering and UUID uniqueness,
  - payload deep-copy isolation,
  - Debug insertion at beginning/middle/end,
  - out-of-range insertion error handling.

## Notes
- The component breakdown text mentions “3 components generates 7 actions”; the implemented logic follows the explicit sequence definition, which yields 6 actions for 3 components (3 Implement + Test + Review + Document).
