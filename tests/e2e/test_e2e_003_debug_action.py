"""E2E-003: Insert, edit, dispatch, and complete a debug action."""

from __future__ import annotations

from app.src.models import ActionStatus
from app.src.services.action_generator import ActionGenerator


def _action_type_value(action_type: object) -> str:
    """Normalise action type values to strings for assertions."""

    return getattr(action_type, "value", str(action_type))


def test_e2e_003_debug_action_insert_edit_dispatch_complete(
    sample_project,
    sample_action_type_defaults,
    mock_executor_response,
) -> None:
    """Validate debug action insertion position, payload edit, dispatch, and completion."""

    original_phase_one_ids = [
        action.action_id for action in sample_project.actions if action.phase_id == 1
    ]

    requested_position = 2
    insertion_position = requested_position - 1
    ActionGenerator.insert_debug_action(
        actions=sample_project.actions,
        phase_id=1,
        position=insertion_position,
        action_type_defaults=sample_action_type_defaults,
    )

    phase_one_actions = [
        action for action in sample_project.actions if action.phase_id == 1
    ]
    debug_action = phase_one_actions[insertion_position]

    assert _action_type_value(debug_action.action_type) == "debug"
    assert (
        _action_type_value(phase_one_actions[insertion_position - 1].action_type)
        == "implement"
    )
    assert (
        _action_type_value(phase_one_actions[insertion_position + 1].action_type)
        == "review"
    )

    debug_action.payload["agent_instructions"] = (
        "Investigate failing workflow in phase 1."
    )
    response = mock_executor_response(run_id="debug-run-1", message="debug-dispatched")
    debug_action.executor_response = response.model_dump(mode="json")
    debug_action.status = ActionStatus.DISPATCHED
    debug_action.status = ActionStatus.COMPLETED

    assert (
        debug_action.payload["agent_instructions"]
        == "Investigate failing workflow in phase 1."
    )
    assert debug_action.executor_response is not None
    assert debug_action.executor_response["run_id"] == "debug-run-1"
    assert _action_type_value(debug_action.status) == "completed"

    remaining_phase_one_ids = [
        action.action_id
        for action in phase_one_actions
        if _action_type_value(action.action_type) != "debug"
    ]
    assert remaining_phase_one_ids == original_phase_one_ids
