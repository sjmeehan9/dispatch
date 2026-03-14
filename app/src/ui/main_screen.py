"""Main screen UI module."""

from __future__ import annotations

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
