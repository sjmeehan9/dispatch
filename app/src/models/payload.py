"""Payload model definitions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from pydantic import BaseModel, Field

_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


class PayloadTemplate(BaseModel):
    """Default payload template containing optional placeholder variables."""

    template_fields: dict[str, object]

    def get_variables(self) -> set[str]:
        """Return all placeholder variable names found in template fields."""

        variables: set[str] = set()
        for text in self._iter_string_values(self.template_fields):
            variables.update(
                match.group(1) for match in _VARIABLE_PATTERN.finditer(text)
            )
        return variables

    @classmethod
    def _iter_string_values(cls, value: object) -> Iterable[str]:
        """Yield all string values recursively from nested mappings/collections."""

        if isinstance(value, str):
            yield value
            return

        if isinstance(value, dict):
            for nested in value.values():
                yield from cls._iter_string_values(nested)
            return

        if isinstance(value, list):
            for nested in value:
                yield from cls._iter_string_values(nested)


class ResolvedPayload(BaseModel):
    """Dispatch-ready payload and any unresolved placeholder names."""

    payload: dict[str, object]
    unresolved_variables: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class PayloadGenerationResult:
    """Payload generation result with LLM usage metadata."""

    payload: dict[str, Any]
    llm_used: bool
    fallback_reason: str | None = None
