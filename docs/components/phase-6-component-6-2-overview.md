# Component 6.2 Overview - LLM Payload Generation Logic

## Summary
Component 6.2 adds a production LLM payload generation pipeline that enhances only the `agent_instructions` field while preserving deterministic payload structure through standard interpolation.

## Delivered Implementation
- Added `LLMPayloadGenerator` at `app/src/services/llm_payload_generator.py`.
- Added `PayloadGenerationResult` dataclass at `app/src/models/payload.py`.
- Exported new symbols via:
  - `app/src/models/__init__.py`
  - `app/src/services/__init__.py`
- Added `use_llm: bool = False` to `ExecutorConfig` in `app/src/models/executor.py` to support LLM gating.
- Added comprehensive tests in `tests/test_llm_payload_generator.py`.

## Core Flow
1. Resolve baseline payload via `PayloadResolver`.
2. If LLM unavailable or disabled, return baseline payload with fallback metadata.
3. Assemble context from repository, phase, component (for implement), and agent paths.
4. Build system/user prompts for strict JSON output.
5. Parse LLM output and validate non-empty `agent_instructions`.
6. Merge `agent_instructions` into resolved payload.

## Context Assembly Details
- Includes repository, phase ID/name, action type.
- Implement actions include component ID/name/estimated effort.
- Non-implement actions include phase component list.
- Includes agent file paths.
- Attempts to extract optional component breakdown text from `phase_progress` and truncates to 4000 characters.

## Fallback Behavior
Fallback returns baseline payload with `llm_used=False` and reason when:
- OpenAI key is not configured.
- `executor_config.use_llm` is disabled.
- LLM call raises `LLMError`.
- LLM response is invalid JSON or missing `agent_instructions`.

## Validation Coverage
`tests/test_llm_payload_generator.py` covers:
- Unavailable/disabled fallback branches.
- Successful LLM merge behavior.
- Timeout and service-error fallback.
- Context assembly and truncation.
- Prompt construction.
- Response parsing (plain JSON, fenced JSON, invalid JSON, missing key).
- Merge semantics and integration-style success/failure flows.

## Notes
This component intentionally limits LLM output scope to one field (`agent_instructions`) to improve reliability, simplify validation, and ensure deterministic fallback for executor-critical fields.
