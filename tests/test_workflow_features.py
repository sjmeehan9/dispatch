"""Workflow quality-of-life logic tests for Phase 5.5 validation."""

from __future__ import annotations

from app.src.models import Action, ActionStatus, ActionType
from app.src.ui import components, main_screen


def test_action_type_icon_mapping() -> None:
    """Each action type should map to the expected icon and color."""
    assert components.action_type_icon(ActionType.IMPLEMENT) == ("code", "primary")
    assert components.action_type_icon(ActionType.TEST) == ("science", "purple")
    assert components.action_type_icon(ActionType.REVIEW) == ("rate_review", "orange")
    assert components.action_type_icon(ActionType.DOCUMENT) == ("description", "teal")
    assert components.action_type_icon(ActionType.DEBUG) == ("bug_report", "red")


def test_action_status_presentation_mapping() -> None:
    """Action statuses should map to the expected badge label and color."""
    assert components.action_status_presentation(ActionStatus.NOT_STARTED) == (
        "Pending",
        "grey",
    )
    assert components.action_status_presentation(ActionStatus.DISPATCHED) == (
        "Dispatched",
        "blue",
    )
    assert components.action_status_presentation(ActionStatus.COMPLETED) == (
        "Complete",
        "green",
    )


def test_progress_counts_with_mixed_statuses() -> None:
    """Progress helper should return completed, total, and ratio values."""
    actions = [
        Action(
            action_id="a1",
            phase_id=1,
            action_type=ActionType.IMPLEMENT,
            payload={},
            status=ActionStatus.COMPLETED,
        ),
        Action(
            action_id="a2",
            phase_id=1,
            action_type=ActionType.TEST,
            payload={},
            status=ActionStatus.DISPATCHED,
        ),
        Action(
            action_id="a3",
            phase_id=2,
            action_type=ActionType.IMPLEMENT,
            payload={},
            status=ActionStatus.NOT_STARTED,
        ),
    ]

    completed, total, ratio = components.progress_counts(actions)

    assert completed == 1
    assert total == 3
    assert ratio == 1 / 3


def test_filter_grouped_actions_by_phase() -> None:
    """Phase filter helper should return only the selected phase group."""
    grouped = [
        (
            1,
            "Phase 1",
            [
                Action(
                    action_id="a1",
                    phase_id=1,
                    action_type=ActionType.IMPLEMENT,
                    payload={},
                )
            ],
        ),
        (
            2,
            "Phase 2",
            [
                Action(
                    action_id="a2", phase_id=2, action_type=ActionType.TEST, payload={}
                )
            ],
        ),
    ]

    filtered = main_screen._filter_grouped_actions(grouped, 2)

    assert len(filtered) == 1
    assert filtered[0][0] == 2
    assert filtered[0][1] == "Phase 2"


def test_requires_redispatch_confirmation_logic() -> None:
    """Only dispatched/completed actions should require redispatch confirmation."""
    not_started = Action(
        action_id="a1",
        phase_id=1,
        action_type=ActionType.IMPLEMENT,
        payload={},
        status=ActionStatus.NOT_STARTED,
    )
    dispatched = Action(
        action_id="a2",
        phase_id=1,
        action_type=ActionType.IMPLEMENT,
        payload={},
        status=ActionStatus.DISPATCHED,
    )
    completed = Action(
        action_id="a3",
        phase_id=1,
        action_type=ActionType.IMPLEMENT,
        payload={},
        status=ActionStatus.COMPLETED,
    )

    assert main_screen._requires_redispatch_confirmation(not_started) is False
    assert main_screen._requires_redispatch_confirmation(dispatched) is True
    assert main_screen._requires_redispatch_confirmation(completed) is True
