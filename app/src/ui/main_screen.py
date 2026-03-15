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
    ActionGenerator,
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

    # Component-scoped actions: implement, review, merge
    if (
        action_type
        in (
            ActionType.IMPLEMENT.value,
            ActionType.REVIEW.value,
            ActionType.MERGE.value,
        )
        and action.component_id
    ):
        component_name = _resolve_component_name(project, action)
        type_label = action_type.title()
        return f"{type_label}: {component_name}"

    # Phase-scoped actions: test, document, debug
    return f"{action_type.title()} Phase {action.phase_id}"


def _resolve_component_name(project: Project, action: Action) -> str:
    """Resolve a friendly component name from a project and action."""
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
    return component_name


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

    if app_state.current_project is not None:
        _try_propagate_pr_number(app_state, action)


def _extract_pr_number_from_webhook(action: Action) -> str | None:
    """Extract PR number from an action's webhook response, if present."""
    if action.webhook_response is None:
        return None
    result = action.webhook_response.get("result")
    if isinstance(result, dict):
        pr_number = result.get("pr_number")
        if pr_number is not None and str(pr_number).strip():
            return str(pr_number)
    pr_number = action.webhook_response.get("pr_number")
    if pr_number is not None and str(pr_number).strip():
        return str(pr_number)
    return None


def _try_propagate_pr_number(app_state: AppState, action: Action) -> None:
    """Attempt to propagate PR number from a completed implement action."""
    if action.action_type != ActionType.IMPLEMENT:
        return
    if app_state.current_project is None:
        return

    pr_number = _extract_pr_number_from_webhook(action)
    if pr_number is None:
        return

    ActionGenerator.propagate_pr_number(
        app_state.current_project.actions, action, pr_number
    )


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


def _is_llm_dispatch_enabled(app_state: AppState, executor_config: object) -> bool:
    """Return whether LLM payload generation should be used for dispatch flow."""

    use_llm = bool(getattr(executor_config, "use_llm", False))
    return use_llm and app_state.llm_service.is_available()


def _resolve_standard_payload_for_action(
    app_state: AppState,
    action: Action,
    executor_config: object,
) -> dict[str, object]:
    """Resolve action payload via deterministic variable interpolation."""

    if app_state.current_project is None:
        raise ValueError("No project loaded.")

    context = app_state.payload_resolver.build_context(
        project=app_state.current_project,
        phase_id=action.phase_id,
        component_id=action.component_id,
        executor_config=executor_config,
    )
    return app_state.payload_resolver.resolve_payload(action.payload, context).payload


async def _prepare_payload_for_dispatch_review(
    app_state: AppState,
    action: Action,
    executor_config: object,
) -> tuple[dict[str, object], bool, str | None]:
    """Build payload for review, optionally using LLM generation before dispatch."""

    if app_state.current_project is None:
        raise ValueError("No project loaded.")

    if not bool(getattr(executor_config, "use_llm", False)):
        return (
            _resolve_standard_payload_for_action(app_state, action, executor_config),
            False,
            None,
        )

    result = await asyncio.to_thread(
        app_state.llm_payload_generator.generate_payload,
        action,
        app_state.current_project,
        executor_config,
    )
    return result.payload, result.llm_used, result.fallback_reason


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
    ai_generated: bool = False,
    allow_dispatch: bool = False,
    dispatch_overlay: LoadingOverlay | None = None,
) -> None:
    """Open a dialog to view and edit an action payload as JSON."""
    dialog = ui.dialog()
    with dialog, ui.card().classes("q-pa-md dispatch-dialog-card"):
        ui.label("Edit Payload").classes("text-h6")
        if ai_generated:
            ui.chip("AI Generated", icon="auto_awesome", color="purple")
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

            async def _dispatch() -> None:
                saved = _save_edited_payload(action, str(editor.value or ""))
                if not saved:
                    notify_error("Invalid JSON. Payload must be a JSON object.")
                    return

                dialog.close()
                if dispatch_overlay is None:
                    response = await _dispatch_action(
                        app_state, project_service, action
                    )
                else:
                    response = await with_loading(
                        lambda: _dispatch_action(app_state, project_service, action),
                        dispatch_overlay,
                    )

                refresh_action_list()
                if refresh_response_panel is not None:
                    refresh_response_panel()

                if response is None:
                    return

            if allow_dispatch:
                ui.button(
                    "Dispatch",
                    icon="send",
                    on_click=_dispatch,
                    color="primary",
                ).classes("dispatch-touch-target")

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


def _group_by_component(
    actions: list[Action],
) -> tuple[list[tuple[str, list[Action]]], list[Action]]:
    """Split phase actions into per-component groups and phase-level actions.

    Returns:
        A tuple of (component_groups, phase_level_actions) where component_groups
        is a list of (component_id, actions) tuples preserving original ordering.
    """
    component_order: list[str] = []
    component_map: dict[str, list[Action]] = {}
    phase_level: list[Action] = []

    for action in actions:
        if action.component_id is None:
            phase_level.append(action)
        else:
            if action.component_id not in component_map:
                component_order.append(action.component_id)
                component_map[action.component_id] = []
            component_map[action.component_id].append(action)

    component_groups = [(cid, component_map[cid]) for cid in component_order]
    return component_groups, phase_level


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
    llm_generation_overlay: LoadingOverlay,
    refresh_response_panel: Callable[[], None] | None = None,
) -> None:
    """Render the left-panel phase-grouped action list with card-based layout."""
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

        phase_options: dict[int | None, str] = {None: "All Phases"}
        for phase_id, phase_name, _ in grouped_actions:
            phase_options[phase_id] = f"Phase {phase_id}: {phase_name}"

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

        def _render_action_card(
            app_state: AppState,
            project_service: ProjectService,
            action: Action,
            dispatching_action_id: str | None,
            completing_action_id: str | None,
            refresh_response_panel: Callable[[], None] | None,
        ) -> None:
            """Render a single action as a styled card with left-border colour coding."""
            status_class = ""
            if action.status == ActionStatus.COMPLETED:
                status_class = " dispatch-action-completed"
            elif action.status == ActionStatus.DISPATCHED:
                status_class = " dispatch-action-dispatched"

            action_type_value = str(action.action_type)
            with (
                ui.card()
                .classes(
                    f"w-full q-pa-sm dispatch-action-card"
                    f" dispatch-action-{action_type_value}{status_class}"
                )
                .props("flat bordered")
            ):
                with ui.row().classes("w-full items-center justify-between no-wrap"):
                    with ui.row().classes("items-center q-gutter-sm"):
                        icon_name, icon_color = action_type_icon(action.action_type)
                        ui.icon(icon_name).props(f'color="{icon_color}" size="sm"')
                        ui.label(
                            _action_label(app_state.current_project, action)
                        ).classes("text-body2 text-weight-medium")
                        action_status_badge(action.status)
                    with ui.row().classes("items-center q-gutter-xs"):
                        dispatch_button = ui.button(
                            icon="send",
                            on_click=lambda current_action=action: _request_dispatch(
                                current_action
                            ),
                            color="primary",
                        ).props("dense flat round size=sm")
                        if dispatching_action_id == action.action_id:
                            dispatch_button.props("loading")

                        complete_button = ui.button(
                            icon="check_circle",
                            on_click=lambda current_action=action: _handle_mark_complete(
                                current_action
                            ),
                            color="positive",
                        ).props("dense flat round size=sm")
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
                        ).props("dense flat round size=sm")

        for phase_id, phase_name, actions in filtered_groups:
            phase_completed = sum(
                1 for action in actions if action.status == ActionStatus.COMPLETED
            )
            phase_total = len(actions)
            all_complete = phase_completed == phase_total

            with ui.card().classes(
                f"w-full dispatch-phase-card"
                f"{' dispatch-phase-complete' if all_complete else ''}"
            ):
                # Phase header
                with ui.element("div").classes("dispatch-phase-header"):
                    with ui.row().classes(
                        "w-full items-center justify-between q-px-md q-py-sm"
                    ):
                        with ui.row().classes("items-center q-gutter-sm"):
                            ui.icon("check_circle" if all_complete else "folder").props(
                                f'color="{"positive" if all_complete else "primary"}"'
                            )
                            ui.label(f"Phase {phase_id}: {phase_name}").classes(
                                "text-subtitle1 text-weight-bold"
                            )
                        ui.badge(f"{phase_completed}/{phase_total}").props(
                            'color="primary" text-color="white"'
                        )

                # Action items grouped by component
                with ui.column().classes("w-full q-pa-sm q-gutter-xs"):
                    component_groups, phase_level_actions = _group_by_component(actions)

                    for component_id, component_actions in component_groups:
                        component_name = _resolve_component_name(
                            app_state.current_project, component_actions[0]
                        )
                        with ui.element("div").classes("dispatch-component-group"):
                            ui.label(component_name).classes(
                                "text-caption text-grey-7 q-pl-sm"
                            )
                            for action in component_actions:
                                _render_action_card(
                                    app_state,
                                    project_service,
                                    action,
                                    dispatching_action_id,
                                    completing_action_id,
                                    refresh_response_panel,
                                )

                    if phase_level_actions:
                        if component_groups:
                            ui.separator().classes("q-my-sm")
                        for action in phase_level_actions:
                            _render_action_card(
                                app_state,
                                project_service,
                                action,
                                dispatching_action_id,
                                completing_action_id,
                                refresh_response_panel,
                            )

                # Add Debug button
                with ui.row().classes("w-full justify-end q-px-sm q-pb-sm"):
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
                    ).props("outline dense")

    def _request_dispatch(action: Action) -> None:
        client = ui.context.client
        if _requires_redispatch_confirmation(action):
            dialog = confirm_redispatch(
                action,
                on_confirm=lambda current_action=action: asyncio.create_task(
                    _handle_dispatch(current_action, client)
                ),
            )
            dialog.open()
            return

        asyncio.create_task(_handle_dispatch(action, client))

    async def _handle_dispatch(action: Action, client: object) -> None:
        with client:  # type: ignore[attr-defined]
            app_state.dispatching_action_id = action.action_id
            _render_action_list.refresh()

            try:
                executor_config = app_state.config_manager.get_executor_config()
            except (OSError, ValueError) as exc:
                notify_error(f"Dispatch failed: {exc}")
                app_state.dispatching_action_id = None
                _render_action_list.refresh()
                return

            if _is_llm_dispatch_enabled(app_state, executor_config):
                try:
                    payload, llm_used, fallback_reason = await with_loading(
                        lambda: _prepare_payload_for_dispatch_review(
                            app_state,
                            action,
                            executor_config,
                        ),
                        llm_generation_overlay,
                    )
                except (OSError, ValueError) as exc:
                    notify_error(f"Dispatch failed: {exc}")
                    app_state.dispatching_action_id = None
                    _render_action_list.refresh()
                    return

                action.payload = payload
                if not llm_used and fallback_reason:
                    notify_warning(
                        f"LLM generation failed: {fallback_reason}. Using standard payload."
                    )

                _show_payload_editor(
                    app_state,
                    project_service,
                    action,
                    _render_action_list.refresh,
                    refresh_response_panel,
                    ai_generated=llm_used,
                    allow_dispatch=True,
                    dispatch_overlay=dispatch_overlay,
                )
            else:
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


def _response_header_class(status_code: int) -> str:
    """Return the CSS class for a response panel header based on status code."""
    if status_code == 0:
        return "dispatch-response-header dispatch-response-header-pending"
    if 200 <= status_code < 300:
        return "dispatch-response-header dispatch-response-header-success"
    if status_code >= 400:
        return "dispatch-response-header dispatch-response-header-error"
    return "dispatch-response-header dispatch-response-header-dispatched"


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
        # ── Executor Response card ──
        with ui.card().classes("w-full"):
            if current_action is None or current_action.executor_response is None:
                with ui.element("div").classes(
                    "dispatch-response-header dispatch-response-header-pending"
                ):
                    ui.label("Executor Response").classes(
                        "text-subtitle1 text-weight-bold"
                    )
                with ui.element("div").classes("q-pa-md"):
                    ui.label("No action dispatched yet.").classes("text-grey-7")
            else:
                status_code = int(
                    current_action.executor_response.get("status_code", 0)
                )
                message = str(current_action.executor_response.get("message", ""))
                with ui.element("div").classes(_response_header_class(status_code)):
                    with ui.row().classes("items-center justify-between"):
                        ui.label("Executor Response").classes(
                            "text-subtitle1 text-weight-bold"
                        )
                        ui.badge(str(status_code)).props(
                            f'color="{"positive" if 200 <= status_code < 300 else "negative"}"'
                            ' text-color="white"'
                        )
                with ui.element("div").classes("q-pa-md"):
                    ui.label(message).classes("text-body2")

                    run_id = _extract_run_id(current_action)
                    if run_id is not None:
                        with ui.row().classes("items-center q-gutter-xs q-mt-sm"):
                            ui.label("Run ID:").classes("text-caption text-grey-7")
                            ui.label(run_id).classes("text-caption text-weight-medium")
                            ui.button(
                                icon="content_copy",
                                on_click=lambda: ui.run_javascript(
                                    f"navigator.clipboard.writeText('{run_id}')"
                                ),
                            ).props("dense flat round size=xs")

        # ── Webhook Response card ──
        has_webhook_url = (
            executor_config is not None and executor_config.webhook_url is not None
        )
        if has_webhook_url:
            with ui.card().classes("w-full"):
                if current_action is None or current_action.executor_response is None:
                    with ui.element("div").classes(
                        "dispatch-response-header dispatch-response-header-pending"
                    ):
                        ui.label("Webhook Response").classes(
                            "text-subtitle1 text-weight-bold"
                        )
                    with ui.element("div").classes("q-pa-md"):
                        ui.label("No action dispatched yet.").classes("text-grey-7")
                else:
                    run_id = _extract_run_id(current_action)

                    if current_action.webhook_response is not None:
                        webhook_status = current_action.webhook_response.get(
                            "status_code"
                        ) or current_action.webhook_response.get("status", "")
                        webhook_status_int = (
                            int(webhook_status) if str(webhook_status).isdigit() else 0
                        )
                        header_cls = _response_header_class(webhook_status_int)
                    else:
                        header_cls = (
                            "dispatch-response-header"
                            " dispatch-response-header-dispatched"
                        )

                    with ui.element("div").classes(header_cls):
                        with ui.row().classes("items-center justify-between"):
                            ui.label("Webhook Response").classes(
                                "text-subtitle1 text-weight-bold"
                            )
                            # PR chip when known
                            pr_number = _extract_pr_number_from_webhook(current_action)
                            if pr_number is not None:
                                ui.chip(f"PR #{pr_number}", icon="merge").props(
                                    'color="green" text-color="white" dense'
                                )

                    with ui.element("div").classes("q-pa-md"):
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
                                    notify_warning(
                                        "Webhook response not available yet."
                                    )
                                    _render_response_panel.refresh()
                                    return

                                current_action.webhook_response = webhook_payload
                                _try_propagate_pr_number(app_state, current_action)
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
                                refresh_action_list()

                            ui.button(
                                "Refresh",
                                icon="refresh",
                                on_click=_refresh_webhook,
                                color="secondary",
                            ).props("outline")
                        else:
                            webhook_status = current_action.webhook_response.get(
                                "status_code"
                            ) or current_action.webhook_response.get("status")
                            webhook_message = current_action.webhook_response.get(
                                "message"
                            ) or current_action.webhook_response.get("result")
                            ui.label(f"Status: {webhook_status}").classes("text-body2")
                            ui.label(f"Result: {webhook_message}").classes(
                                "text-body2 q-mt-xs"
                            )

        # ── Mark Complete button ──
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
    llm_generation_overlay = loading_overlay(
        "Generating payload with AI...",
        ui_module=ui,
    )

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
            "row q-col-gutter-md w-full dispatch-mobile-grid dispatch-main-panels"
        ):
            with ui.element("div").classes("col-12 col-md-5 dispatch-mobile-stack"):
                with ui.scroll_area().classes("w-full dispatch-panel-scroll"):
                    _render_action_list(
                        app_state,
                        project_service,
                        dispatch_overlay,
                        llm_generation_overlay,
                        refresh_response_panel=_render_response_panel.refresh,
                    )

            with ui.element("div").classes("col-12 col-md-7 dispatch-mobile-stack"):
                with ui.scroll_area().classes("w-full dispatch-panel-scroll"):
                    _render_response_panel(
                        app_state,
                        project_service,
                        refresh_action_list=_render_action_list.refresh,
                    )
