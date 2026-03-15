# Phase 7 Component 7.2 — Cross-Device Verification & Merge Action Type

## Summary

Component 7.2 delivers two pieces of work:

1. **Cross-device verification** — Uvicorn binds to `0.0.0.0` for LAN access, with a verification checklist for manual cross-device testing.
2. **Merge action type (Phases A & B)** — A new `MERGE` action type integrated end-to-end through models, services, configuration, and UI.

## Cross-Device Verification

- `ui.run()` updated to `host="0.0.0.0"` for LAN access from other devices.
- `docs/cross-device-verification.md` created with structured checklists for macOS Chrome/Safari, iPhone Safari, and OneDrive sync.
- Human testing deliverables remain pending.

## Merge Action Type — Architecture

**Models:**
- `ActionType.MERGE` added to the `StrEnum` (between REVIEW and DOCUMENT).
- `ActionTypeDefaults.merge` field added to the Pydantic model.

**Action Generation (`ActionGenerator`):**
- `generate_actions` restructured: each component produces `implement → review → merge`, followed by phase-level `test` and `document`.
- New `propagate_pr_number` classmethod writes `pr_number` into review/merge payloads sharing the same phase+component when an implement action completes.

**Configuration (`ConfigManager`):**
- `get_action_type_defaults` injects merge defaults from bundled `defaults.yaml` when loading projects created before this field existed.

**defaults.yaml:**
- Merge template: `role=merge`, `pr_number={{pr_number}}`, `timeout_minutes=10`.
- Review `agent_instructions` updated to be component-scoped.

**UI:**
- `components.py` — merge icon (`merge`, green).
- `main_screen.py` — `_action_label` handles component-scoped review/merge labels; `_mark_complete` and webhook refresh trigger PR propagation.
- `action_type_defaults.py` — merge added to the editable type list.

## Key Files

| File | Change |
|------|--------|
| `app/src/models/project.py` | `MERGE` enum member |
| `app/src/models/executor.py` | `merge` field on `ActionTypeDefaults` |
| `app/config/defaults.yaml` | Merge template, updated review instructions |
| `app/src/services/action_generator.py` | Per-component grouping, `propagate_pr_number` |
| `app/src/services/config_manager.py` | Backward compat merge injection |
| `app/src/ui/components.py` | Merge icon mapping |
| `app/src/ui/main_screen.py` | Propagation wiring, component-scoped labels |
| `app/src/ui/action_type_defaults.py` | Merge in type list and variable hints |
| `app/src/main.py` | `host="0.0.0.0"` binding |

## Test Coverage

All 10 affected test files updated with merge fixtures. Two new tests added:
- `test_propagate_pr_number_updates_review_and_merge_for_same_component`
- `test_get_action_type_defaults_injects_merge_when_missing`

Full suite: **213 passed**, 1 skipped, 1 pre-existing environment-specific failure. Evals: all pass.

## Design Decisions

- Per-component `implement→review→merge` grouping aligns with the PR-per-component workflow.
- `pr_number` stored as string in payload for consistency with variable substitution.
- Backward compat reads merge defaults from bundled YAML (not hardcoded) so future template updates propagate automatically.
