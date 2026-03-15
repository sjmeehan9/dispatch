# Phase 7 Component 7.2 — Cross-Device Verification, Merge Action Type & UI Modernisation

## Summary

Component 7.2 delivers four pieces of work:

1. **Cross-device verification** — Uvicorn binds to `0.0.0.0` for LAN access, with a verification checklist for manual cross-device testing.
2. **Merge action type (Phases A & B)** — A new `MERGE` action type integrated end-to-end through models, services, configuration, and UI.
3. **UI modernisation — Main screen (Phase C)** — Card-based action layout, phase cards with gradient headers, component grouping, modernised response panel, circular progress.
4. **UI modernisation — Global & other screens (Phases D & E)** — Dark header gradient, global CSS refinements (card/button/input rounding), section icons on all screens, full validation.

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

## UI Modernisation — Phase C (Main Screen)

- Rewrote `styles.css`: full-height panels, action card styles with colour-coded left borders, phase card gradient headers, component group separators, dispatch pulse animation, response panel status-coloured headers.
- Replaced flat `ui.list()`/`ui.item()` with card-based layout — each action card colour-coded by type.
- `_group_by_component()` helper splits actions into per-component triplets and phase-level actions.
- Phase sections use `ui.card()` with gradient headers, completion icons, and progress badges.
- Response panel: status-coloured headers, run ID with copy button, PR number chip.
- `progress_summary` replaced with `ui.circular_progress` and remaining-count labels.

## UI Modernisation — Phase D (Global & Other Screens)

- Global CSS: card border-radius 12px, button border-radius 8px with non-uppercase text, input border-radius 8px.
- Header: dark indigo gradient (`#1a237e` → `#283593`), white text, semi-transparent separators.
- Initial screen: rocket icon on title, settings/play_circle section icons, dns/tune/vpn_key button icons.
- Executor config: dns section icon.
- Action type defaults: tune section icon.
- Secrets screen: vpn_key section icon with info callout.
- Link project: link section icon.
- Load project: folder_open section icon.

## Validation — Phase E

- **Tests:** 216 passed, 1 skipped, 0 failures.
- **Evals:** 0 violations.
- **Formatting:** Black + isort clean for `app/src/`.
- 4 test `_FakeUI` stubs updated to add `icon()` method.

## Key Files

| File | Change |
|------|--------|
| `app/src/models/project.py` | `MERGE` enum member |
| `app/src/models/executor.py` | `merge` field on `ActionTypeDefaults` |
| `app/config/defaults.yaml` | Merge template, updated review instructions |
| `app/src/services/action_generator.py` | Per-component grouping, `propagate_pr_number` |
| `app/src/services/config_manager.py` | Backward compat merge injection |
| `app/src/ui/components.py` | Merge icon, circular progress, dark header |
| `app/src/ui/main_screen.py` | Card layout, component grouping, response panel |
| `app/src/ui/action_type_defaults.py` | Merge type list, section icon |
| `app/src/ui/executor_config.py` | Section icon |
| `app/src/ui/initial_screen.py` | Title icon, section icons, button icons |
| `app/src/ui/secrets_screen.py` | Section icon, info callout |
| `app/src/ui/link_project.py` | Section icon |
| `app/src/ui/load_project.py` | Section icon |
| `app/src/static/styles.css` | All Phase C + D global/card/header styles |
| `app/src/main.py` | `host="0.0.0.0"` binding |

## Test Coverage

All affected test files updated. Full suite: **216 passed**, 1 skipped. Evals: all pass.

## Design Decisions

- Per-component `implement→review→merge` grouping aligns with the PR-per-component workflow.
- `pr_number` stored as string in payload for consistency with variable substitution.
- Backward compat reads merge defaults from bundled YAML (not hardcoded) so future template updates propagate automatically.
