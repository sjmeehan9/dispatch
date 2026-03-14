"""Main screen UI module."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Callable

from nicegui import run, ui

from app.src.models import Action, ActionStatus, ActionType, ExecutorResponse, Project
from app.src.services.project_service import ProjectNotFoundError, ProjectService
from app.src.ui.state import AppState

_ACTION_ICON_MAP: dict[str, str] = {
    ActionType.IMPLEMENT.value: "build",
    ActionType.TEST.value: "science",
    ActionType.REVIEW.value: "grading",
    ActionType.DOCUMENT.value: "description",
    ActionType.DEBUG.value: "bug_report",
}

_STATUS_COLOR_MAP: dict[str, str] = {
    ActionStatus.NOT_STARTED.value: "grey",
    ActionStatus.DISPATCHED.value: "blue",
    ActionStatus.COMPLETED.value: "green",
}

_UNRESOLVED_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def _project_service_for_main_screen(app_state: AppState) -> ProjectService:
    """Return a project service usable for load/save operations on the main screen."""
    token: str | None = None
    if app_state.current_project is not None:
        token = app_state.settings.get_secret(
            app_state.current_project.github_token_env_key
        )
    if not token:
        token = app_state.settings.get_secret("GITHUB_TOKEN")
    if not token:
        token = app_state.settings.get_secret("TOKEN")
    if not token:
        token = "local-project-access"
    return app_state.get_project_service(token)


def _action_label(project: Project, action: Action) -> str:
    """Build a human-readable action label for the action list."""
    action_type = str(action.action_type)
    if action_type != ActionType.IMPLEMENT.value:
        return f"{action_type.title()} Phase {action.phase_id}"

    component_name = action.component_id or "Unknown Component"
    phase = next(
        (item for item in project.phases if item.phase_id == action.phase_id), None
    )
    if phase is not None and action.component_id is not None:
        component = next(
            (
                item
                for item in phase.components
                if item.component_id == action.component_id
            ),
            None,
        )
        if component is not None:
            component_name = component.component_name
    return f"Implement: {component_name}"


def _status_color(action: Action) -> str:
    """Return the badge color for an action's current status."""
    return _STATUS_COLOR_MAP.get(str(action.status), "grey")


def _response_color_class(status_code: int) -> str:
    """Map an executor status code to a semantic text color class."""
    if status_code == 0:
        return "text-warning"
    if 200 <= status_code < 300:
        return "text-positive"
    if status_code >= 400:
        return "text-negative"
    return "text-grey-7"


def _poll_webhook(app_state: AppState, run_id: str) -> dict[str, object] | None:
    """Return stored webhook data for a run identifier, if available."""
    data = app_state.webhook_service.retrieve(run_id)
    if data is None:
        return None
    return dict(data)


def _mark_complete(app_state: AppState, action: Action) -> None:
    """Mark an action as completed and keep it selected in the response panel."""
    action.status = ActionStatus.COMPLETED
    app_state.last_dispatched_action = action


def _extract_run_id(action: Action) -> str | None:
    """Extract the run identifier from an action's executor response payload."""
    if action.executor_response is None:
        return None
    run_id = action.executor_response.get("run_id")
    if isinstance(run_id, str) and run_id.strip():
        return run_id
    return None


def _find_unresolved_variables(payload_json: str) -> list[str]:
    """Return unique unresolved variable names referenced as {{variable}}."""
    matches = _UNRESOLVED_VARIABLE_PATTERN.findall(payload_json)
    return list(dict.fromkeys(matches))


def _save_edited_payload(action: Action, new_payload_json: str) -> bool:
    """Validate and persist an edited payload JSON string to an action."""
    try:
        parsed_payload = json.loads(new_payload_json)
    except json.JSONDecodeError:
        return False

    if not isinstance(parsed_payload, dict):
        return False

    action.payload = parsed_payload
    return True


def _insert_debug_action(app_state: AppState, phase_id: int, position: int) -> None:
    """Insert a debug action into a phase and persist project changes."""
    if app_state.current_project is None:
        ui.notify("No project loaded.", type="negative")
        return

    try:
        action_type_defaults = app_state.config_manager.get_action_type_defaults()
    except (OSError, ValueError) as exc:
        ui.notify(f"Unable to load action defaults: {exc}", type="negative")
        return

    phase_indices = [
        index
        for index, item in enumerate(app_state.current_project.actions)
        if item.phase_id == phase_id
    ]
    if not phase_indices:
        ui.notify(f"No actions found for phase {phase_id}.", type="negative")
        return

    insertion_index = phase_indices[0] + position
    try:
        app_state.action_generator.insert_debug_action(
            app_state.current_project.actions,
            phase_id,
            position,
            action_type_defaults,
        )
    except ValueError as exc:
        ui.notify(str(exc), type="negative")
        return

    inserted_action = app_state.current_project.actions[insertion_index]
    try:
        executor_config = app_state.config_manager.get_executor_config()
        context = app_state.payload_resolver.build_context(
            project=app_state.current_project,
            phase_id=phase_id,
            component_id=None,
            executor_config=executor_config,
        )
        resolved = app_state.payload_resolver.resolve_payload(
            inserted_action.payload,
            context,
        )
        inserted_action.payload = resolved.payload
    except (OSError, ValueError) as exc:
        ui.notify(
            f"Debug action inserted, but payload resolution failed: {exc}",
            type="warning",
        )

    project_service = _project_service_for_main_screen(app_state)
    try:
        project_service.save_project(app_state.current_project)
    except OSError as exc:
        ui.notify(f"Debug action inserted, but save failed: {exc}", type="warning")
        return

    ui.notify("Debug action inserted", type="positive")


def _show_payload_editor(
    app_state: AppState,
    project_service: ProjectService,
    action: Action,
    refresh_action_list: Callable[[], None],
    refresh_response_panel: Callable[[], None] | None = None,
) -> None:
    """Open a dialog to view and edit an action payload as JSON."""
    dialog = ui.dialog()
    with dialog, ui.card().classes("q-pa-md").style("width: 900px; max-width: 95vw"):
        ui.label("Edit Payload").classes("text-h6")
        ui.label(
            "Edit the JSON payload. Unresolved variables like {{phase_id}} are listed below."
        ).classes("text-caption text-grey-7")

        editor = ui.textarea(value=json.dumps(action.payload, indent=2)).props(
            "rows=20"
        )
        editor.classes("w-full")

        unresolved_label = ui.label("Unresolved placeholders").classes(
            "text-warning text-subtitle2"
        )
        unresolved_container = ui.column().classes("q-gutter-xs")

        def _refresh_unresolved() -> None:
            unresolved = _find_unresolved_variables(str(editor.value or ""))
            unresolved_container.clear()
            unresolved_label.visible = bool(unresolved)
            if not unresolved:
                return
            for variable_name in unresolved:
                ui.label(f"{{{{{variable_name}}}}}").classes("text-warning")

        _refresh_unresolved()

        editor.on_value_change(lambda _: _refresh_unresolved())

        with ui.row().classes("w-full justify-end q-gutter-sm"):

            def _cancel() -> None:
                dialog.close()

            async def _save() -> None:
                saved = _save_edited_payload(action, str(editor.value or ""))
                if not saved:
                    ui.notify(
                        "Invalid JSON. Payload must be a JSON object.",
                        type="negative",
                    )
                    return

                if app_state.current_project is not None:
                    try:
                        await run.io_bound(
                            project_service.save_project, app_state.current_project
                        )
                    except OSError as exc:
                        ui.notify(
                            f"Payload updated, but save failed: {exc}", type="warning"
                        )
                        return

                ui.notify("Payload updated", type="positive")
                dialog.close()
                refresh_action_list()
                if refresh_response_panel is not None:
                    refresh_response_panel()

            ui.button("Cancel", on_click=_cancel).props("outline")
            ui.button("Save", icon="save", on_click=_save, color="primary")

    dialog.open()


def _group_actions_by_phase(
    project: Project,
) -> list[tuple[int, str, list[Action]]]:
    """Group actions by phase while preserving phase/action ordering."""
    phase_name_map = {phase.phase_id: phase.phase_name for phase in project.phases}
    phase_actions: dict[int, list[Action]] = defaultdict(list)
    for action in project.actions:
        phase_actions[action.phase_id].append(action)

    grouped: list[tuple[int, str, list[Action]]] = []
    for phase_id in sorted(phase_actions):
        grouped.append(
            (
                phase_id,
                phase_name_map.get(phase_id, f"Phase {phase_id}"),
                phase_actions[phase_id],
            )
        )
    return grouped


async def _dispatch_action(
    app_state: AppState,
    project_service: ProjectService,
    action: Action,
) -> ExecutorResponse | None:
    """Resolve and dispatch an action payload, then persist updated state."""
    if app_state.current_project is None:
        ui.notify("No project loaded.", type="negative")
        return None

    try:
        executor_config = app_state.config_manager.get_executor_config()
        context = app_state.payload_resolver.build_context(
            project=app_state.current_project,
            phase_id=action.phase_id,
            component_id=action.component_id,
            executor_config=executor_config,
        )
        resolved_payload = app_state.payload_resolver.resolve_payload(
            action.payload, context
        )
        response = await run.io_bound(
            app_state.autopilot_executor.dispatch,
            resolved_payload.payload,
            executor_config,
        )
    except (OSError, ValueError) as exc:
        ui.notify(f"Dispatch failed: {exc}", type="negative")
        return None

    action.payload = resolved_payload.payload
    action.executor_response = response.model_dump()
    app_state.last_dispatched_action = action

    dispatch_succeeded = 200 <= response.status_code < 300
    if dispatch_succeeded:
        action.status = ActionStatus.DISPATCHED

    try:
        await run.io_bound(project_service.save_project, app_state.current_project)
    except OSError as exc:
        ui.notify(f"Dispatched, but save failed: {exc}", type="warning")
    else:
        if dispatch_succeeded:
            ui.notify("Action dispatched", type="positive")
        else:
            ui.notify(f"Dispatch failed: {response.message}", type="negative")

    return response


@ui.refreshable
def _render_action_list(
    app_state: AppState,
    project_service: ProjectService,
    refresh_response_panel: Callable[[], None] | None = None,
) -> None:
    """Render the left-panel phase-grouped action list."""
    if app_state.current_project is None:
        ui.label("No project loaded.").classes("text-negative")
        return

    grouped_actions = _group_actions_by_phase(app_state.current_project)
    if not grouped_actions:
        ui.label("No actions generated yet.").classes("text-grey-7")
        return

    dispatching_action_id = getattr(app_state, "dispatching_action_id", None)
    completing_action_id = getattr(app_state, "completing_action_id", None)

    with ui.column().classes("w-full q-gutter-sm"):
        for phase_id, phase_name, actions in grouped_actions:
            with ui.expansion(f"Phase {phase_id}: {phase_name}", value=True).classes(
                "w-full"
            ):
                with ui.list().classes("w-full"):
                    for action in actions:
                        with ui.item().classes("w-full"):
                            with ui.item_section().classes("w-full"):
                                with ui.row().classes(
                                    "w-full items-center justify-between no-wrap q-gutter-sm"
                                ):
                                    with ui.row().classes("items-center q-gutter-sm"):
                                        ui.icon(
                                            _ACTION_ICON_MAP.get(
                                                str(action.action_type),
                                                "play_arrow",
                                            )
                                        )
                                        ui.label(
                                            _action_label(
                                                app_state.current_project, action
                                            )
                                        ).classes("text-body2")
                                    ui.badge(
                                        str(action.status).replace("_", " ").title(),
                                        color=_status_color(action),
                                    )
                            with ui.item_section(side=True):
                                dispatch_button = ui.button(
                                    "Dispatch",
                                    icon="send",
                                    on_click=lambda current_action=action: _handle_dispatch(
                                        current_action
                                    ),
                                    color="primary",
                                ).props("dense")
                                if dispatching_action_id == action.action_id:
                                    dispatch_button.props("loading")

                                complete_button = ui.button(
                                    "Mark Complete",
                                    icon="check_circle",
                                    on_click=lambda current_action=action: _handle_mark_complete(
                                        current_action
                                    ),
                                    color="positive",
                                ).props("dense outline")
                                if action.status == ActionStatus.COMPLETED:
                                    complete_button.props("disable")
                                if completing_action_id == action.action_id:
                                    complete_button.props("loading")

                                ui.button(
                                    icon="edit",
                                    on_click=lambda current_action=action: _show_payload_editor(
                                        app_state,
                                        project_service,
                                        current_action,
                                        _render_action_list.refresh,
                                        refresh_response_panel,
                                    ),
                                    color="secondary",
                                ).props("dense flat")

                with ui.row().classes("w-full justify-end q-mt-sm"):
                    ui.button(
                        "Add Debug",
                        icon="bug_report",
                        color="warning",
                        on_click=lambda current_phase_id=phase_id, phase_count=len(
                            actions
                        ): _show_insert_debug_dialog(
                            app_state,
                            current_phase_id,
                            phase_count,
                            _render_action_list.refresh,
                            refresh_response_panel,
                        ),
                    ).props("outline")

    async def _handle_dispatch(action: Action) -> None:
        app_state.dispatching_action_id = action.action_id
        _render_action_list.refresh()
        await _dispatch_action(app_state, project_service, action)
        app_state.dispatching_action_id = None
        _render_action_list.refresh()
        if refresh_response_panel is not None:
            refresh_response_panel()

    async def _handle_mark_complete(action: Action) -> None:
        app_state.completing_action_id = action.action_id
        _mark_complete(app_state, action)

        if app_state.current_project is not None:
            try:
                await run.io_bound(
                    project_service.save_project, app_state.current_project
                )
            except OSError as exc:
                ui.notify(f"Unable to save project: {exc}", type="negative")
            else:
                ui.notify("Action marked complete", type="positive")

        app_state.completing_action_id = None
        _render_action_list.refresh()
        if refresh_response_panel is not None:
            refresh_response_panel()


def _show_insert_debug_dialog(
    app_state: AppState,
    phase_id: int,
    phase_action_count: int,
    refresh_action_list: Callable[[], None],
    refresh_response_panel: Callable[[], None] | None = None,
) -> None:
    """Open a dialog to choose insertion position for a debug action."""
    dialog = ui.dialog()
    with dialog, ui.card().classes("q-pa-md").style("width: 420px; max-width: 90vw"):
        ui.label(f"Insert Debug Action: Phase {phase_id}").classes("text-h6")
        ui.label(f"Choose a position between 0 and {phase_action_count}.").classes(
            "text-caption text-grey-7"
        )

        position_input = ui.number(
            "Insert at position",
            value=phase_action_count,
            min=0,
            max=phase_action_count,
            step=1,
        ).classes("w-full")

        with ui.row().classes("w-full justify-end q-gutter-sm"):

            def _cancel() -> None:
                dialog.close()

            def _confirm() -> None:
                raw_position = position_input.value
                try:
                    position = int(raw_position) if raw_position is not None else -1
                except (TypeError, ValueError):
                    ui.notify(
                        "Insert position must be a valid number.", type="negative"
                    )
                    return

                _insert_debug_action(app_state, phase_id, position)
                refresh_action_list()
                if refresh_response_panel is not None:
                    refresh_response_panel()
                dialog.close()

            ui.button("Cancel", on_click=_cancel).props("outline")
            ui.button("Insert", icon="add", on_click=_confirm, color="warning")

    dialog.open()


@ui.refreshable
def _render_response_panel(
    app_state: AppState,
    project_service: ProjectService,
    refresh_action_list: Callable[[], None],
) -> None:
    """Render executor/webhook responses for the most recently dispatched action."""
    current_action: Action | None = getattr(app_state, "last_dispatched_action", None)

    try:
        executor_config = app_state.config_manager.get_executor_config()
    except (OSError, ValueError):
        executor_config = None

    with ui.column().classes("w-full q-gutter-md"):
        with ui.card().classes("w-full q-pa-md"):
            ui.label("Executor Response").classes("text-h6")
            if current_action is None or current_action.executor_response is None:
                ui.label("No action dispatched yet.").classes("text-grey-7")
            else:
                status_code = int(
                    current_action.executor_response.get("status_code", 0)
                )
                message = str(current_action.executor_response.get("message", ""))
                ui.label(f"Response: {status_code}").classes(
                    _response_color_class(status_code)
                )
                ui.label(f"Message: {message}")

                run_id = _extract_run_id(current_action)
                if run_id is not None:
                    ui.label(f"Run ID: {run_id}").classes("text-caption text-grey-7")

        has_webhook_url = (
            executor_config is not None and executor_config.webhook_url is not None
        )
        if has_webhook_url:
            with ui.card().classes("w-full q-pa-md"):
                ui.label("Webhook Response").classes("text-h6")

                if current_action is None or current_action.executor_response is None:
                    ui.label("No action dispatched yet.").classes("text-grey-7")
                else:
                    run_id = _extract_run_id(current_action)
                    if run_id is None:
                        ui.label("No run ID; webhook polling unavailable.").classes(
                            "text-warning"
                        )
                    elif current_action.webhook_response is None:
                        ui.label("Waiting for webhook response...").classes(
                            "text-grey-7"
                        )

                        async def _refresh_webhook() -> None:
                            webhook_payload = _poll_webhook(app_state, run_id)
                            if webhook_payload is None:
                                ui.notify(
                                    "Webhook response not available yet.",
                                    type="warning",
                                )
                                _render_response_panel.refresh()
                                return

                            current_action.webhook_response = webhook_payload
                            if app_state.current_project is not None:
                                try:
                                    await run.io_bound(
                                        project_service.save_project,
                                        app_state.current_project,
                                    )
                                except OSError as exc:
                                    ui.notify(
                                        f"Webhook received but save failed: {exc}",
                                        type="warning",
                                    )

                            _render_response_panel.refresh()

                        ui.button(
                            "Refresh",
                            icon="refresh",
                            on_click=_refresh_webhook,
                            color="secondary",
                        )
                    else:
                        webhook_status = current_action.webhook_response.get(
                            "status_code"
                        ) or current_action.webhook_response.get("status")
                        webhook_message = current_action.webhook_response.get(
                            "message"
                        ) or current_action.webhook_response.get("result")
                        ui.label(f"Status: {webhook_status}")
                        ui.label(f"Message: {webhook_message}")

        if current_action is not None:

            async def _mark_current_action_complete() -> None:
                _mark_complete(app_state, current_action)
                if app_state.current_project is not None:
                    try:
                        await run.io_bound(
                            project_service.save_project, app_state.current_project
                        )
                    except OSError as exc:
                        ui.notify(f"Unable to save project: {exc}", type="negative")
                        return

                ui.notify("Action marked complete", type="positive")
                refresh_action_list()
                _render_response_panel.refresh()

            ui.button(
                "Mark Complete",
                icon="check_circle",
                color="positive",
                on_click=_mark_current_action_complete,
            ).props("outline")


def render_main_screen(app_state: AppState, project_id: str) -> None:
    """Render the main dispatch workspace for a linked project."""
    project_service = _project_service_for_main_screen(app_state)

    if (
        app_state.current_project is None
        or app_state.current_project.project_id != project_id
    ):
        try:
            app_state.current_project = project_service.load_project(project_id)
        except ProjectNotFoundError as exc:
            ui.notify(str(exc), type="negative")
            ui.navigate.to("/")
            return
        except OSError as exc:
            ui.notify(f"Unable to load project: {exc}", type="negative")
            ui.navigate.to("/")
            return

    if app_state.current_project is None:
        ui.notify("No project loaded.", type="negative")
        ui.navigate.to("/")
        return

    def _save_project() -> None:
        if app_state.current_project is None:
            ui.notify("No project loaded.", type="negative")
            return
        try:
            project_service.save_project(app_state.current_project)
        except OSError as exc:
            ui.notify(f"Unable to save project: {exc}", type="negative")
            return
        ui.notify("Project saved", type="positive")

    with ui.column().classes("w-full q-pa-md q-gutter-md"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(app_state.current_project.project_name).classes("text-h4")
            with ui.row().classes("items-center q-gutter-sm"):
                ui.button("Save", icon="save", on_click=_save_project)
                ui.button(
                    "Home", icon="home", on_click=lambda: ui.navigate.to("/")
                ).props("outline")

        with (
            ui.splitter(value=40)
            .classes("w-full")
            .style("height: calc(100vh - 180px)") as splitter
        ):
            with splitter.before:
                with ui.scroll_area().classes("w-full h-full q-pr-sm"):
                    _render_action_list(
                        app_state,
                        project_service,
                        refresh_response_panel=_render_response_panel.refresh,
                    )

            with splitter.after:
                with ui.scroll_area().classes("w-full h-full q-pl-sm"):
                    _render_response_panel(
                        app_state,
                        project_service,
                        refresh_action_list=_render_action_list.refresh,
                    )
