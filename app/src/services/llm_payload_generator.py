"""LLM-assisted payload generation service."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.src.exceptions import LLMError
from app.src.models import Action, ExecutorConfig, PayloadGenerationResult, Project
from app.src.models.project import ActionType, ComponentData, PhaseData
from app.src.services.llm_service import LLMService
from app.src.services.payload_resolver import PayloadResolver

_LOGGER = logging.getLogger(__name__)
_CODE_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class LLMPayloadGenerator:
    """Generate action payloads with optional LLM instruction enhancement."""

    def __init__(
        self,
        llm_service: LLMService,
        payload_resolver: PayloadResolver,
        context_char_limit: int = 4000,
    ) -> None:
        """Initialise generator dependencies.

        Args:
                llm_service: LLM API wrapper used for instruction generation.
                payload_resolver: Deterministic resolver for baseline/fallback payloads.
                context_char_limit: Maximum number of characters for long context blocks.
        """

        self._llm_service = llm_service
        self._payload_resolver = payload_resolver
        self._context_char_limit = context_char_limit

    def generate_payload(
        self,
        action: Action,
        project: Project,
        executor_config: ExecutorConfig,
    ) -> PayloadGenerationResult:
        """Generate an action payload with optional LLM-enhanced instructions.

        Args:
                action: Execute action to generate payload for.
                project: Project containing phase and component context.
                executor_config: Active executor settings.

        Returns:
                Payload generation result containing payload and fallback metadata.
        """

        baseline_payload = self._resolve_standard_payload(
            action, project, executor_config
        )

        if not self._llm_service.is_available():
            return PayloadGenerationResult(
                payload=baseline_payload,
                llm_used=False,
                fallback_reason="OpenAI API key not configured",
            )

        if not bool(getattr(executor_config, "use_llm", False)):
            return PayloadGenerationResult(
                payload=baseline_payload,
                llm_used=False,
                fallback_reason="LLM generation disabled in executor config",
            )

        context = self._assemble_context(action, project)
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(action, context, action.payload)

        try:
            llm_response = self._llm_service.generate(system_prompt, user_prompt)
            llm_fields = self._parse_response(llm_response)
        except LLMError as exc:
            fallback_reason = str(exc)
            _LOGGER.warning(
                "LLM payload generation failed; using standard interpolation: %s",
                fallback_reason,
            )
            return PayloadGenerationResult(
                payload=baseline_payload,
                llm_used=False,
                fallback_reason=fallback_reason,
            )
        except ValueError as exc:
            fallback_reason = str(exc)
            _LOGGER.warning(
                "LLM response parsing failed; using standard interpolation: %s",
                fallback_reason,
            )
            return PayloadGenerationResult(
                payload=baseline_payload,
                llm_used=False,
                fallback_reason=fallback_reason,
            )

        merged_payload = self._merge_payload(
            action.payload, llm_fields, baseline_payload
        )
        return PayloadGenerationResult(
            payload=merged_payload,
            llm_used=True,
            fallback_reason=None,
        )

    def _resolve_standard_payload(
        self,
        action: Action,
        project: Project,
        executor_config: ExecutorConfig,
    ) -> dict[str, object]:
        """Resolve payload using deterministic placeholder interpolation."""

        context = self._payload_resolver.build_context(
            project=project,
            phase_id=action.phase_id,
            component_id=action.component_id,
            executor_config=executor_config,
        )
        return self._payload_resolver.resolve_payload(action.payload, context).payload

    def _assemble_context(self, action: Action, project: Project) -> str:
        """Assemble text context for LLM instruction generation."""

        phase = self._find_phase(project, action.phase_id)
        action_type = self._action_type_value(action)

        lines: list[str] = [
            f"Repository: {project.repository}",
            f"Phase ID: {phase.phase_id}",
            f"Phase Name: {phase.phase_name}",
            f"Action Type: {action_type}",
        ]

        if action_type == ActionType.IMPLEMENT.value:
            component = self._find_component(phase, action.component_id)
            lines.extend(
                [
                    f"Component ID: {component.component_id}",
                    f"Component Name: {component.component_name}",
                    f"Component Estimated Effort: {component.estimated_effort}",
                ]
            )
            component_breakdown = self._extract_component_breakdown_text(
                project=project,
                phase_id=phase.phase_id,
                component_id=component.component_id,
            )
            if component_breakdown:
                truncated = component_breakdown[: self._context_char_limit]
                lines.append("Component Breakdown Context:")
                lines.append(truncated)
        else:
            component_names = ", ".join(
                component.component_name for component in phase.components
            )
            lines.append(f"Phase Components: {component_names}")

        agent_paths = ", ".join(project.agent_files) if project.agent_files else "None"
        lines.append(f"Agent Files: {agent_paths}")

        return "\n".join(lines)

    @staticmethod
    def _build_system_prompt() -> str:
        """Return fixed system prompt used for payload generation."""

        return (
            "You are a technical assistant that generates precise agent instructions "
            "for dispatching AI coding agents. Given project context and an action "
            "type, generate the `agent_instructions` field value for the executor "
            "payload. Your response must be a valid JSON object with a single key "
            "`agent_instructions` containing the generated instructions as a string. "
            "The instructions should be specific, actionable, and reference the "
            "project's components, files, and acceptance criteria where relevant. "
            "Do not include placeholders or variables - generate concrete instructions."
        )

    def _build_user_prompt(
        self,
        action: Action,
        context: str,
        template: dict[str, Any],
    ) -> str:
        """Return user prompt with action details, template, and context."""

        action_type = self._action_type_value(action)
        template_instructions = str(template.get("agent_instructions", ""))

        return (
            f"Action type: {action_type}\n\n"
            "Current template instructions:\n"
            f"{template_instructions}\n\n"
            "Project context:\n"
            f"{context}\n\n"
            "Generate the agent_instructions for this action as a JSON object."
        )

    @classmethod
    def _parse_response(cls, response: str) -> dict[str, str]:
        """Parse and validate a JSON response containing agent instructions.

        Args:
                response: Raw text returned by the LLM.

        Returns:
                Dictionary containing the validated ``agent_instructions`` value.

        Raises:
                ValueError: If response is not valid JSON or is missing required key.
        """

        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = _CODE_FENCE_PATTERN.sub("", cleaned).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM response was not valid JSON") from exc

        if not isinstance(parsed, dict):
            raise ValueError("LLM response JSON must be an object")

        instructions = parsed.get("agent_instructions")
        if not isinstance(instructions, str) or not instructions.strip():
            raise ValueError(
                "LLM response JSON must include a non-empty 'agent_instructions' string"
            )

        return {"agent_instructions": instructions.strip()}

    @staticmethod
    def _merge_payload(
        template: dict[str, Any],
        llm_fields: dict[str, str],
        resolved_fields: dict[str, object],
    ) -> dict[str, object]:
        """Merge LLM fields into deterministic resolved payload values."""

        merged = dict(resolved_fields)
        if "agent_instructions" in template or "agent_instructions" in llm_fields:
            merged["agent_instructions"] = llm_fields["agent_instructions"]
        return merged

    @staticmethod
    def _action_type_value(action: Action) -> str:
        """Normalize an action type enum/string to its string value."""

        action_type = action.action_type
        if isinstance(action_type, ActionType):
            return action_type.value
        return str(action_type)

    @staticmethod
    def _find_phase(project: Project, phase_id: int) -> PhaseData:
        """Locate a phase in project data by phase identifier."""

        for phase in project.phases:
            if phase.phase_id == phase_id:
                return phase
        raise ValueError(
            f"Phase {phase_id} not found for project '{project.project_id}'."
        )

    @staticmethod
    def _find_component(phase: PhaseData, component_id: str | None) -> ComponentData:
        """Locate a component in a phase by component identifier."""

        if component_id is None:
            raise ValueError("Implement action requires a component_id.")

        for component in phase.components:
            if component.component_id == component_id:
                return component
        raise ValueError(
            f"Component '{component_id}' not found in phase {phase.phase_id}."
        )

    def _extract_component_breakdown_text(
        self,
        project: Project,
        phase_id: int,
        component_id: str,
    ) -> str:
        """Extract optional component breakdown text from phase-progress payload.

        The phase-progress schema varies by repository, so this method checks a set of
        commonly used keys at both phase and component levels and composes any values
        found into a single text block.
        """

        raw_phases = project.phase_progress.get("phases")
        if not isinstance(raw_phases, list):
            return ""

        raw_phase: dict[str, Any] | None = None
        for candidate in raw_phases:
            if isinstance(candidate, dict) and candidate.get("phaseId") == phase_id:
                raw_phase = candidate
                break
        if raw_phase is None:
            return ""

        parts: list[str] = []
        for phase_key in (
            "description",
            "summary",
            "notes",
            "acceptanceCriteria",
            "componentBreakdownContent",
            "componentBreakdown",
        ):
            phase_value = raw_phase.get(phase_key)
            if isinstance(phase_value, str) and phase_value.strip():
                parts.append(phase_value.strip())

        raw_components = raw_phase.get("components")
        if isinstance(raw_components, list):
            for candidate in raw_components:
                if not isinstance(candidate, dict):
                    continue
                if candidate.get("componentId") != component_id:
                    continue
                for component_key in (
                    "description",
                    "details",
                    "requirements",
                    "acceptanceCriteria",
                    "implementationNotes",
                ):
                    component_value = candidate.get(component_key)
                    if isinstance(component_value, str) and component_value.strip():
                        parts.append(component_value.strip())
                break

        return "\n\n".join(parts)
