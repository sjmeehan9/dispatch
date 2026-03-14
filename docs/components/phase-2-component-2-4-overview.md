# Phase 2 Component 2.4 Overview — Default Executor Configuration

## Summary
Component 2.4 delivers the bundled default executor configuration used when Dispatch has no saved executor/action template JSON files yet.

## Implemented Scope
- Updated `app/config/defaults.yaml` to the required Phase 2.4 format:
  - Top-level `executor` section
  - Top-level `action_type_defaults` section
- Configured default Autopilot executor values:
  - `executor_id: autopilot`
  - `executor_name: Autopilot`
  - `api_endpoint: http://localhost:8000/agent/run`
  - `api_key_env_key: AUTOPILOT_API_KEY`
  - `webhook_url: ""` (user-supplied)
- Added complete payload templates for all five action types:
  - `implement`, `test`, `review`, `document`, `debug`
- Ensured templates align with the Autopilot runbook payload fields and role constraints:
  - common fields: `repository`, `branch`, `agent_instructions`, `model`, `role`, `agent_paths`, `callback_url`, `timeout_minutes`
  - review-only field: `pr_number`
  - role mapping: review => `review`; others => `implement`

## Placeholder Strategy
- Uses explicit `{{variable}}` placeholders to support Phase 3 payload resolution.
- Includes placeholders for repository context, phase/component context, callback URL, and PR number.
- Documents placeholders inline in YAML comments for maintainability.

## Integration Changes
- Updated `app/src/services/config_manager.py` `_load_defaults()` to read `executor` from YAML.
- Retained fallback support for legacy `executor_config` key to avoid breaking older default files during transition.
- Added a strict validation guard to raise `ValueError` if either required section is missing.

## Validation Coverage
`tests/test_config_manager.py` now includes Component 2.4-focused tests for:
- YAML parse + model validation (`ExecutorConfig`, `ActionTypeDefaults`)
- Presence/values of required placeholders and role mappings for all templates
- Review template `pr_number` placeholder and debug empty instructions behavior

## Notes
- No secrets are stored in defaults; only environment variable key names are referenced.
- This component remains compatible with environments where `.env/.env.local` is absent and secrets are provided via process environment (for example GitHub Actions repository/environment secrets).
