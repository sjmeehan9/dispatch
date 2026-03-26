"""Payload resolution service module."""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from app.src.models import ExecutorConfig, Project, ResolvedPayload

_PLACEHOLDER_PATTERN = re.compile(r"\{\{(\w+)\}\}")
_FULL_PLACEHOLDER_PATTERN = re.compile(r"^\{\{(\w+)\}\}$")


class PayloadResolver:
    """Resolve payload template placeholders using project/action context."""

    @classmethod
    def build_context(
        cls,
        project: Project,
        phase_id: int,
        component_id: str | None,
        executor_config: ExecutorConfig,
    ) -> dict[str, str]:
        """Build a string-only context map for placeholder replacement.

        Args:
            project: Project data source.
            phase_id: Phase identifier for the target action.
            component_id: Optional component identifier for implement actions.
            executor_config: Active executor configuration.

        Returns:
            Mapping of placeholder names to string values.

        Raises:
            ValueError: If the phase or provided component cannot be found.
        """

        phase = next(
            (item for item in project.phases if item.phase_id == phase_id), None
        )
        if phase is None:
            raise ValueError(
                f"Phase {phase_id} not found in project '{project.project_id}'."
            )

        component_name = ""
        resolved_component_id = ""
        if component_id is not None:
            component = next(
                (
                    item
                    for item in phase.components
                    if item.component_id == component_id
                ),
                None,
            )
            if component is None:
                raise ValueError(
                    f"Component '{component_id}' not found in phase {phase_id}."
                )
            resolved_component_id = component.component_id
            component_name = component.component_name

        return {
            "repository": project.repository,
            "branch": "main",
            "phase_id": str(phase.phase_id),
            "phase_name": phase.phase_name,
            "component_id": resolved_component_id,
            "component_name": component_name,
            "component_breakdown_doc": phase.component_breakdown_doc,
            "agent_paths": json.dumps(project.agent_files),
            "webhook_url": (
                str(executor_config.webhook_url) if executor_config.webhook_url else ""
            ),
            "pr_number": "",
        }

    @classmethod
    def resolve_payload(
        cls, payload: dict[str, Any], context: dict[str, str]
    ) -> ResolvedPayload:
        """Resolve placeholders in a payload structure.

        Args:
            payload: Source payload template.
            context: Placeholder replacement map.

        Returns:
            Resolved payload and unresolved variable names.
        """

        unresolved: list[str] = []
        payload_copy = copy.deepcopy(payload)
        resolved_payload = cls._resolve_value(payload_copy, context, unresolved)
        unique_unresolved = list(dict.fromkeys(unresolved))

        if not isinstance(resolved_payload, dict):
            raise ValueError("Resolved payload must be a dictionary.")
        return ResolvedPayload(
            payload=resolved_payload,
            unresolved_variables=unique_unresolved,
        )

    @classmethod
    def _resolve_value(
        cls, value: Any, context: dict[str, str], unresolved: list[str]
    ) -> Any:
        """Recursively resolve placeholder values for nested payload objects."""

        if isinstance(value, str):
            full_match = _FULL_PLACEHOLDER_PATTERN.match(value)
            if full_match:
                variable_name = full_match.group(1)
                if variable_name in context:
                    raw = context[variable_name]
                    try:
                        parsed = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        return raw
                    if isinstance(parsed, (list, dict)):
                        return parsed
                    return raw
                unresolved.append(variable_name)
                return value
            return _PLACEHOLDER_PATTERN.sub(
                lambda match: cls._replace_match(match, context, unresolved),
                value,
            )

        if isinstance(value, dict):
            return {
                key: cls._resolve_value(item, context, unresolved)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [cls._resolve_value(item, context, unresolved) for item in value]

        return value

    @staticmethod
    def _replace_match(
        match: re.Match[str], context: dict[str, str], unresolved: list[str]
    ) -> str:
        """Resolve one regex placeholder match against context."""

        variable_name = match.group(1)
        if variable_name in context:
            return context[variable_name]
        unresolved.append(variable_name)
        return match.group(0)
