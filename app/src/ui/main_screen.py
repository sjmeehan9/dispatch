"""Main screen UI module."""

from __future__ import annotations

import asyncio
import json
import re
from collections import defaultdict
from typing import Callable

from nicegui import run, ui

from app.src.models import Action, ActionStatus, ActionType, ExecutorResponse, Project
from app.src.services import (
    ExecutorAuthError,
    ExecutorConnectionError,
    ExecutorDispatchError,
)
from app.src.services.project_service import ProjectService
from app.src.ui.components import (
    LoadingOverlay,
    action_status_badge,
    action_type_icon,
    confirm_redispatch,
    loading_overlay,
    map_executor_error,
    notify_error,
    notify_success,
    notify_warning,
    page_layout,
    progress_summary,
    with_loading,
)
from app.src.ui.state import AppState

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
        notify_error("No project loaded.")
        return

    try:
        action_type_defaults = app_state.config_manager.get_action_type_defaults()
    except (OSError, ValueError) as exc:
        notify_error(f"Unable to load action defaults: {exc}")
        return

    phase_indices = [
        index
        for index, item in enumerate(app_state.current_project.actions)
        if item.phase_id == phase_id
    ]
    if not phase_indices:
        notify_error(f"No actions found for phase {phase_id}.")
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
        notify_error(str(exc))
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
        notify_warning(f"Debug action inserted, but payload resolution failed: {exc}")

    project_service = _project_service_for_main_screen(app_state)
    try:
        project_service.save_project(app_state.current_project)
    except OSError as exc:
        notify_warning(f"Debug action inserted, but save failed: {exc}")
        return

    notify_success("Debug action inserted")


def _show_payload_editor(
    app_state: AppState,
    project_service: ProjectService,
    action: Action,
    refresh_action_list: Callable[[], None],
    refresh_response_panel: Callable[[], None] | None = None,
) -> None:
    """Open a dialog to view and edit an action payload as JSON."""
    dialog = ui.dialog()
    with dialog, ui.card().classes("q-pa-md dispatch-dialog-card"):
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
                    notify_error("Invalid JSON. Payload must be a JSON object.")
                    return

                if app_state.current_project is not None:
                    try:
                        await run.io_bound(
                            project_service.save_project, app_state.current_project
                        )
                    except OSError as exc:
                        notify_warning(f"Payload updated, but save failed: {exc}")
                        return

                notify_success("Payload updated")
                dialog.close()
                refresh_action_list()
                if refresh_response_panel is not None:
                    refresh_response_panel()

            ui.button("Cancel", on_click=_cancel).props("outline")
            ui.button("Save", icon="save", on_click=_save, color="primary").classes(
                "dispatch-touch-target"
            )

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


def _filter_grouped_actions(
    grouped_actions: list[tuple[int, str, list[Action]]],
    phase_id: int | None,
) -> list[tuple[int, str, list[Action]]]:
    """Return grouped actions filtered to a specific phase when requested."""
    if phase_id is None:
        return grouped_actions
    return [group for group in grouped_actions if group[0] == phase_id]


def _requires_redispatch_confirmation(action: Action) -> bool:
    """Return whether dispatch should require user confirmation."""
    return action.status in (ActionStatus.DISPATCHED, ActionStatus.COMPLETED)


async def _dispatch_action(
    app_state: AppState,
    project_service: ProjectService,
    action: Action,
) -> ExecutorResponse | None:
    """Resolve and dispatch an action payload, then persist updated state."""
    if app_state.current_project is None:
        notify_error("No project loaded.")
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
    except (ExecutorConnectionError, ExecutorAuthError, ExecutorDispatchError) as exc:
        notify_error(map_executor_error(exc))
        return None
    except (OSError, ValueError) as exc:
        notify_error(f"Dispatch failed: {exc}")
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
        notify_warning(f"Dispatched, but save failed: {exc}")
    else:
        if dispatch_succeeded:
            notify_success("Action dispatched")
        else:
            notify_error(f"Dispatch failed: {response.message}")

    return response


@ui.refreshable
def _render_action_list(
    app_state: AppState,
    project_service: ProjectService,
    dispatch_overlay: LoadingOverlay,
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

    selected_phase_id = getattr(app_state, "selected_phase_filter_phase_id", None)

    dispatching_action_id = app_state.dispatching_action_id
    completing_action_id = app_state.completing_action_id

    with ui.column().classes("w-full q-gutter-sm"):

        progress_summary(app_state.current_project.actions)

        phase_options: dict[str, int | None] = {"All Phases": None}
        for phase_id, phase_name, _ in grouped_actions:
            phase_options[f"Phase {phase_id}: {phase_name}"] = phase_id

        def _on_phase_filter_change(event: object) -> None:
            value = getattr(event, "value", None)
            app_state.selected_phase_filter_phase_id = int(value) if value else None
            _render_action_list.refresh()

        ui.select(
            options=phase_options,
            value=selected_phase_id,
            label="Filter by Phase",
            on_change=_on_phase_filter_change,
        ).classes("w-full")

        filtered_groups = _filter_grouped_actions(grouped_actions, selected_phase_id)
        if not filtered_groups:
            ui.label("No actions match the selected phase.").classes("text-grey-7")
            return

        for phase_id, phase_name, actions in filtered_groups:
            phase_completed = sum(
                1 for action in actions if action.status == ActionStatus.COMPLETED
            )
            phase_total = len(actions)
            with ui.expansion(f"Phase {phase_id}: {phase_name}", value=True).classes(
                "w-full"
            ):
                with ui.row().classes("w-full justify-end q-px-sm q-pt-sm"):
                    ui.badge(f"{phase_completed}/{phase_total}").props(
                        'color="primary" text-color="white"'
                    )

                with ui.list().classes("w-full"):
                    for action in actions:
                        with ui.item().classes("w-full"):
                            with ui.item_section().classes("w-full"):
                                with ui.row().classes(
                                    "w-full items-center justify-between no-wrap q-gutter-sm"
                                ):
                                    with ui.row().classes("items-center q-gutter-sm"):
                                        icon_name, icon_color = action_type_icon(
                                            action.action_type
                                        )
                                        ui.icon(icon_name).props(
                                            f'color="{icon_color}"'
                                        )
                                        ui.label(
                                            _action_label(
                                                app_state.current_project, action
                                            )
                                        ).classes("text-body2")
                                    action_status_badge(action.status)
                            with ui.item_section(side=True):
                                dispatch_button = ui.button(
                                    "Dispatch",
                                    icon="send",
                                    on_click=lambda current_action=action: _request_dispatch(
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

    def _request_dispatch(action: Action) -> None:
        if _requires_redispatch_confirmation(action):
            dialog = confirm_redispatch(
                action,
                on_confirm=lambda current_action=action: asyncio.create_task(
                    _handle_dispatch(current_action)
                ),
            )
            dialog.open()
            return

        asyncio.create_task(_handle_dispatch(action))

    async def _handle_dispatch(action: Action) -> None:
        app_state.dispatching_action_id = action.action_id
        _render_action_list.refresh()
        await with_loading(
            lambda: _dispatch_action(app_state, project_service, action),
            dispatch_overlay,
        )
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
                notify_error(f"Unable to save project: {exc}")
            else:
                notify_success("Action marked complete")

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
    with dialog, ui.card().classes("q-pa-md dispatch-debug-dialog"):
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
                    notify_error("Insert position must be a valid number.")
                    return

                _insert_debug_action(app_state, phase_id, position)
                refresh_action_list()
                if refresh_response_panel is not None:
                    refresh_response_panel()
                dialog.close()

            ui.button("Cancel", on_click=_cancel).props("outline")
            ui.button("Insert", icon="add", on_click=_confirm, color="warning").classes(
                "dispatch-touch-target"
            )

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
                                notify_warning("Webhook response not available yet.")
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
                                    notify_warning(
                                        f"Webhook received but save failed: {exc}"
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
                        notify_error(f"Unable to save project: {exc}")
                        return

                notify_success("Action marked complete")
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
    project = app_state.ensure_project(project_id)
    if project is None:
        notify_error("Project not found. Redirected to home.")
        ui.navigate.to("/")
        return

    project_service = _project_service_for_main_screen(app_state)

    save_overlay = loading_overlay("Saving project...", ui_module=ui)
    dispatch_overlay = loading_overlay("Dispatching action...", ui_module=ui)

    def _go_home() -> None:
        app_state.clear_project()
        ui.navigate.to("/")

    page_layout(
        f"Project: {project.project_name}",
        back_url="/",
        ui_module=ui,
        on_back=_go_home,
    )

    async def _save_project() -> None:
        if app_state.current_project is None:
            notify_error("No project loaded.")
            return
        try:
            await with_loading(
                lambda: run.io_bound(
                    project_service.save_project, app_state.current_project
                ),
                save_overlay,
            )
        except OSError as exc:
            notify_error(f"Unable to save project: {exc}")
            return
        notify_success("Project saved")

    with ui.column().classes("w-full q-pa-md q-gutter-md"):
        with ui.row().classes("w-full items-center justify-between wrap q-gutter-sm"):
            ui.label(app_state.current_project.project_name).classes(
                "text-h5 md:text-h4"
            )
            with ui.row().classes("items-center q-gutter-sm"):
                ui.button("Save", icon="save", on_click=_save_project).classes(
                    "dispatch-touch-target"
                )

        with ui.element("div").classes(
            "row q-col-gutter-md w-full dispatch-mobile-grid"
        ):
            with ui.element("div").classes("col-12 col-md-5 dispatch-mobile-stack"):
                with ui.scroll_area().classes("w-full dispatch-panel-scroll"):
                    _render_action_list(
                        app_state,
                        project_service,
                        dispatch_overlay,
                        refresh_response_panel=_render_response_panel.refresh,
                    )

            with ui.element("div").classes("col-12 col-md-7 dispatch-mobile-stack"):
                with ui.scroll_area().classes("w-full dispatch-panel-scroll"):
                    _render_response_panel(
                        app_state,
                        project_service,
                        refresh_action_list=_render_action_list.refresh,
                    )
