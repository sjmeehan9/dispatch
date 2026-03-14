"""Unit tests for action generation service."""

from __future__ import annotations

import pytest

from app.src.models import ActionTypeDefaults, PhaseData
from app.src.services.action_generator import ActionGenerator


def _sample_defaults() -> ActionTypeDefaults:
    return ActionTypeDefaults(
        implement={"role": "implement", "metadata": {"type": "implement"}},
        test={"role": "test"},
        review={"role": "review"},
        document={"role": "document"},
        debug={"role": "debug"},
    )


def _phase(phase_id: int, component_ids: list[str]) -> PhaseData:
    components = [
        {
            "componentId": component_id,
            "componentName": f"Component {component_id}",
            "owner": "AI Agent",
            "priority": "Must-have",
            "estimatedEffort": "2 hours",
            "status": "not-started",
        }
        for component_id in component_ids
    ]
    return PhaseData.model_validate(
        {
            "phaseId": phase_id,
            "phaseName": f"Phase {phase_id}",
            "status": "refined",
            "componentBreakdownDoc": f"docs/phase-{phase_id}-component-breakdown.md",
            "components": components,
        }
    )


def test_generate_actions_single_phase_component_order_and_types() -> None:
    actions = ActionGenerator.generate_actions(
        phases=[_phase(1, ["1.1", "1.2", "1.3"])],
        action_type_defaults=_sample_defaults(),
    )

    assert len(actions) == 6
    assert [action.action_type for action in actions] == [
        "implement",
        "implement",
        "implement",
        "test",
        "review",
        "document",
    ]
    assert [action.component_id for action in actions] == [
        "1.1",
        "1.2",
        "1.3",
        None,
        None,
        None,
    ]


def test_generate_actions_orders_components_with_natural_sort() -> None:
    actions = ActionGenerator.generate_actions(
        phases=[_phase(1, ["1.10", "1.2", "1.1"])],
        action_type_defaults=_sample_defaults(),
    )

    implement_component_ids = [
        action.component_id for action in actions if action.action_type == "implement"
    ]
    assert implement_component_ids == ["1.1", "1.2", "1.10"]


def test_generate_actions_orders_multiple_phases_and_assigns_unique_ids() -> None:
    actions = ActionGenerator.generate_actions(
        phases=[_phase(2, ["2.1"]), _phase(1, ["1.1", "1.2"])],
        action_type_defaults=_sample_defaults(),
    )

    assert len(actions) == 9
    assert [action.phase_id for action in actions] == [1, 1, 1, 1, 1, 2, 2, 2, 2]
    assert len({action.action_id for action in actions}) == len(actions)
    assert all(action.status == "not_started" for action in actions)


def test_generate_actions_deep_copies_payload_templates() -> None:
    defaults = _sample_defaults()
    actions = ActionGenerator.generate_actions(
        phases=[_phase(1, ["1.1"])],
        action_type_defaults=defaults,
    )

    actions[0].payload["role"] = "changed"
    metadata = actions[0].payload["metadata"]
    assert isinstance(metadata, dict)
    metadata["type"] = "changed"

    assert defaults.implement["role"] == "implement"
    implement_metadata = defaults.implement["metadata"]
    assert isinstance(implement_metadata, dict)
    assert implement_metadata["type"] == "implement"


def test_insert_debug_action_supports_start_middle_and_end_positions() -> None:
    defaults = _sample_defaults()
    actions = ActionGenerator.generate_actions(
        phases=[_phase(1, ["1.1", "1.2"])],
        action_type_defaults=defaults,
    )

    ActionGenerator.insert_debug_action(
        actions, phase_id=1, position=0, action_type_defaults=defaults
    )
    ActionGenerator.insert_debug_action(
        actions, phase_id=1, position=3, action_type_defaults=defaults
    )
    ActionGenerator.insert_debug_action(
        actions, phase_id=1, position=7, action_type_defaults=defaults
    )

    assert [action.action_type for action in actions] == [
        "debug",
        "implement",
        "implement",
        "debug",
        "test",
        "review",
        "document",
        "debug",
    ]
    assert [action.phase_id for action in actions] == [1, 1, 1, 1, 1, 1, 1, 1]


def test_insert_debug_action_raises_for_out_of_range_position() -> None:
    defaults = _sample_defaults()
    actions = ActionGenerator.generate_actions(
        phases=[_phase(1, ["1.1"])],
        action_type_defaults=defaults,
    )

    with pytest.raises(ValueError, match="position must be between"):
        ActionGenerator.insert_debug_action(
            actions,
            phase_id=1,
            position=6,
            action_type_defaults=defaults,
        )
