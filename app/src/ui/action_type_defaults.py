"""Action type defaults configuration UI module."""

from __future__ import annotations

from typing import Any

from nicegui import ui
from pydantic import ValidationError

from app.src.models import ActionTypeDefaults
from app.src.ui.components import notify_error, notify_success, page_layout
from app.src.ui.state import AppState

_ACTION_TYPES: tuple[str, ...] = (
    "implement",
    "test",
    "review",
    "merge",
    "document",
    "debug",
)
_FIELD_ORDER: tuple[str, ...] = (
    "repository",
    "branch",
    "agent_instructions",
    "model",
    "role",
    "agent_paths",
    "callback_url",
    "timeout_minutes",
    "pr_number",
)
_FIELD_LABELS: dict[str, str] = {
    "repository": "Repository",
    "branch": "Branch",
    "agent_instructions": "Agent Instructions",
    "model": "Model",
    "role": "Role",
    "agent_paths": "Agent Paths",
    "callback_url": "Callback URL",
    "timeout_minutes": "Timeout Minutes",
    "pr_number": "PR Number",
}
_VARIABLE_HINTS: tuple[tuple[str, str], ...] = (
    ("{{repository}}", "Target repository in owner/repo format."),
    ("{{branch}}", "Target branch for execution."),
    ("{{phase_id}}", "Current phase identifier."),
    ("{{phase_name}}", "Current phase name."),
    ("{{component_id}}", "Current component identifier for implement actions."),
    ("{{component_name}}", "Current component display name."),
    ("{{component_breakdown_doc}}", "Path to the phase component breakdown document."),
    ("{{agent_paths}}", "JSON array of discovered repository agent instruction paths."),
    ("{{webhook_url}}", "Configured webhook callback URL."),
    ("{{pr_number}}", "Pull request number for review and merge actions."),
)


def _ordered_keys(payload_template: dict[str, Any]) -> list[str]:
    """Return template keys in UI order, appending unknown keys at the end."""
    known = [key for key in _FIELD_ORDER if key in payload_template]
    unknown = [key for key in payload_template if key not in _FIELD_ORDER]
    return [*known, *unknown]


def _string_value(value: object) -> str:
    """Convert payload values to displayable text values for input controls."""
    if value is None:
        return ""
    return str(value)


def render_action_type_defaults(app_state: AppState) -> None:
    """Render the action type defaults configuration screen."""
    defaults = app_state.config_manager.get_action_type_defaults()
    templates: dict[str, dict[str, Any]] = {
        action_type: dict(getattr(defaults, action_type))
        for action_type in _ACTION_TYPES
    }
    controls: dict[str, dict[str, Any]] = {
        action_type: {} for action_type in _ACTION_TYPES
    }

    page_layout("Action Type Defaults", back_url="/", ui_module=ui)
    with ui.column().classes(
        "items-center mx-auto justify-center q-pa-md md:q-pa-xl q-gutter-md w-full"
    ):
        with ui.card().classes(
            "w-full col-12 col-md-10 col-lg-8 q-mx-auto q-pa-md q-gutter-sm"
        ):
            ui.label("Action Type Defaults").classes("text-h5 q-mb-sm")

            with ui.expansion("Available Variables", value=False).classes("w-full"):
                for variable, description in _VARIABLE_HINTS:
                    ui.label(f"{variable} — {description}").classes("text-body2")

            with ui.tabs().classes("w-full").props("scrollable") as tabs:
                tab_controls = {
                    action_type: ui.tab(action_type.title())
                    for action_type in _ACTION_TYPES
                }

            with ui.tab_panels(tabs, value=tab_controls["implement"]).classes("w-full"):
                for action_type in _ACTION_TYPES:
                    template = templates[action_type]
                    with ui.tab_panel(tab_controls[action_type]):
                        ui.label(f"{action_type.title()} Template").classes(
                            "text-subtitle1"
                        )
                        for key in _ordered_keys(template):
                            label = (
                                f"{action_type.title()}: {_FIELD_LABELS.get(key, key)}"
                            )
                            current_value = template.get(key)
                            if key == "agent_instructions":
                                control = ui.textarea(
                                    label,
                                    value=_string_value(current_value),
                                ).classes("w-full")
                            elif key == "timeout_minutes":
                                numeric_value: float = 0.0
                                if isinstance(current_value, int | float):
                                    numeric_value = float(current_value)
                                elif str(current_value).strip().isdigit():
                                    numeric_value = float(str(current_value))
                                control = ui.number(label, value=numeric_value).classes(
                                    "w-full"
                                )
                            else:
                                control = ui.input(
                                    label,
                                    value=_string_value(current_value),
                                ).classes("w-full")
                            controls[action_type][key] = control

            def _save_defaults() -> None:
                payloads: dict[str, dict[str, Any]] = {}
                for action_type in _ACTION_TYPES:
                    action_payload: dict[str, Any] = {}
                    for key in templates[action_type]:
                        value = controls[action_type][key].value
                        if key == "timeout_minutes":
                            if value in (None, ""):
                                action_payload[key] = 0
                            else:
                                action_payload[key] = int(float(value))
                        else:
                            action_payload[key] = _string_value(value)
                    payloads[action_type] = action_payload

                try:
                    updated_defaults = ActionTypeDefaults.model_validate(payloads)
                except ValidationError as exc:
                    notify_error(f"Unable to save action type defaults: {exc}")
                    return

                app_state.config_manager.save_action_type_defaults(updated_defaults)
                app_state.reload_config()
                notify_success("Action type defaults saved")

            with ui.row().classes("w-full justify-end q-gutter-sm q-mt-md"):
                ui.button("Save", on_click=_save_defaults, color="primary").classes(
                    "dispatch-touch-target"
                )
