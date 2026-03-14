# Phase 3 Component 3.5 Overview — Payload Resolver Service

## Summary
Component 3.5 delivers the payload templating bridge between generated actions and executor-ready payload bodies. It resolves `{{variable}}` placeholders from project/phase/component/executor context, supports nested payload structures, and reports unresolved placeholders back to the caller for UI surfacing.

## Implemented Scope
- Added `app/src/services/payload_resolver.py` with `PayloadResolver`:
  - `build_context(project, phase_id, component_id, executor_config) -> dict[str, str]`
  - `resolve_payload(payload, context) -> ResolvedPayload`
  - `_resolve_value(value, context, unresolved) -> Any`
  - `_replace_match(match, context, unresolved) -> str`
- Updated `app/src/services/__init__.py` export surface with `PayloadResolver`.

## Key Behavior
- **Context assembly**
  - Resolves phase and optional component references from `Project`.
  - Returns the required key set:
    - `repository`, `branch`, `phase_id`, `phase_name`
    - `component_id`, `component_name`, `component_breakdown_doc`
    - `agent_paths` (JSON-serialized list string)
    - `webhook_url`, `pr_number`
  - Ensures all context values are strings for deterministic text substitution.
- **Placeholder replacement**
  - Uses strict regex `r"\{\{(\w+)\}\}"` to match only word-character variable names.
  - Replaces placeholders recursively in string values nested inside dicts/lists.
  - Leaves non-string values unchanged (`int`, `bool`, `None`, etc.).
- **Unresolved tracking**
  - Unknown placeholders remain in-place (e.g., `{{missing_var}}`).
  - Missing variable names are collected once and returned via `ResolvedPayload.unresolved_variables`.
- **Validation**
  - Raises `ValueError` when requested `phase_id` or `component_id` does not exist in the project context.

## Tests Added
- New file: `tests/test_payload_resolver.py`
- Coverage includes:
  - full context map generation,
  - component-optional context behavior,
  - missing phase/component validation errors,
  - recursive nested/list replacement,
  - multiple substitutions in one string,
  - non-string passthrough,
  - unresolved variable tracking and preservation.

## Notes
- `agent_paths` is intentionally serialized with `json.dumps(...)` to satisfy downstream payload expectations for JSON-compatible list content.
- `branch` defaults to `"main"` and `pr_number` defaults to `""` per current phase requirements.
