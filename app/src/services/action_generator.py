"""Action generation service."""

from __future__ import annotations

import copy
import logging
import uuid

from app.src.models import (
    Action,
    ActionStatus,
    ActionType,
    ActionTypeDefaults,
    PhaseData,
)

_LOGGER = logging.getLogger(__name__)


class ActionGenerator:
    """Generate and manipulate execute action items for project phases."""

    @classmethod
    def generate_actions(
        cls, phases: list[PhaseData], action_type_defaults: ActionTypeDefaults
    ) -> list[Action]:
        """Generate ordered actions for all phases.

        Args:
            phases: Parsed project phases.
            action_type_defaults: Default payload templates by action type.

        Returns:
            Flat ordered action list.
        """

        actions: list[Action] = []
        for phase in sorted(phases, key=lambda phase_item: phase_item.phase_id):
            sorted_components = sorted(
                phase.components,
                key=lambda component: cls._component_sort_key(component.component_id),
            )
            for component in sorted_components:
                actions.append(
                    cls._create_action(
                        action_type=ActionType.IMPLEMENT,
                        phase_id=phase.phase_id,
                        component_id=component.component_id,
                        template=action_type_defaults.implement,
                    )
                )

            actions.append(
                cls._create_action(
                    action_type=ActionType.TEST,
                    phase_id=phase.phase_id,
                    component_id=None,
                    template=action_type_defaults.test,
                )
            )
            actions.append(
                cls._create_action(
                    action_type=ActionType.REVIEW,
                    phase_id=phase.phase_id,
                    component_id=None,
                    template=action_type_defaults.review,
                )
            )
            actions.append(
                cls._create_action(
                    action_type=ActionType.DOCUMENT,
                    phase_id=phase.phase_id,
                    component_id=None,
                    template=action_type_defaults.document,
                )
            )

        _LOGGER.info("Generated %d actions for %d phases", len(actions), len(phases))
        return actions

    @classmethod
    def insert_debug_action(
        cls,
        actions: list[Action],
        phase_id: int,
        position: int,
        action_type_defaults: ActionTypeDefaults,
    ) -> list[Action]:
        """Insert a debug action at a position within one phase's sublist.

        Args:
            actions: Existing flat action list.
            phase_id: Phase identifier whose actions should receive the insert.
            position: Zero-based insertion position within the phase action subset.
            action_type_defaults: Default payload templates by action type.

        Returns:
            The same list with a debug action inserted.

        Raises:
            ValueError: If no actions exist for phase_id or position is invalid.
        """

        phase_indices = [
            index
            for index, action in enumerate(actions)
            if action.phase_id == phase_id
        ]
        if not phase_indices:
            raise ValueError(f"No actions found for phase {phase_id}.")

        phase_action_count = len(phase_indices)
        if position < 0 or position > phase_action_count:
            raise ValueError(
                f"position must be between 0 and {phase_action_count} for phase "
                f"{phase_id}, got {position}."
            )

        insertion_index = phase_indices[0] + position
        debug_action = cls._create_action(
            action_type=ActionType.DEBUG,
            phase_id=phase_id,
            component_id=None,
            template=action_type_defaults.debug,
        )
        actions.insert(insertion_index, debug_action)

        _LOGGER.info(
            "Inserted debug action at position %d in phase %d", position, phase_id
        )
        return actions

    @staticmethod
    def _create_action(
        action_type: ActionType,
        phase_id: int,
        component_id: str | None,
        template: dict[str, object],
    ) -> Action:
        """Create a single action with copied payload template and default metadata."""

        return Action(
            action_id=str(uuid.uuid4()),
            phase_id=phase_id,
            component_id=component_id,
            action_type=action_type,
            payload=copy.deepcopy(template),
            status=ActionStatus.NOT_STARTED,
            executor_response=None,
            webhook_response=None,
        )

    @staticmethod
    def _component_sort_key(component_id: str) -> tuple[tuple[int, int | str], ...]:
        """Build a natural-sort key for dotted component IDs.

        Examples:
            ``1.2`` sorts before ``1.10`` because each dot-delimited segment is
            compared numerically when possible.
        """

        sort_key: list[tuple[int, int | str]] = []
        for segment in component_id.split("."):
            if segment.isdigit():
                sort_key.append((0, int(segment)))
            else:
                sort_key.append((1, segment))
        return tuple(sort_key)
