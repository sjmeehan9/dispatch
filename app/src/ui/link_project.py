"""Link-project screen UI module."""

from __future__ import annotations

from nicegui import run, ui

from app.src.config.constants import REPOSITORY_PATTERN
from app.src.models import Action, Project
from app.src.services.project_service import ProjectLinkError
from app.src.ui.components import loading_overlay, page_layout, with_loading
from app.src.ui.state import AppState


def _normalise_link_error(message: str, repository: str) -> str:
    """Convert low-level link errors into user-facing messages."""
    repository_value = repository.strip()
    if "phase-progress.json not found" in message:
        return (
            "phase-progress.json not found at docs/phase-progress.json in "
            f"{repository_value}"
        )
    if "Authentication failed" in message:
        return "Authentication failed. Check your GitHub token."
    return message


async def _scan_and_link(
    app_state: AppState, repository: str, token_env_key: str
) -> Project:
    """Link a repository, generate actions, resolve payloads, and persist project."""
    token_key = token_env_key.strip()
    token = app_state.settings.get_secret(token_key) if token_key else None
    if not token:
        raise ProjectLinkError(
            "Token not found in environment. Add "
            f"{token_key or 'GITHUB_TOKEN'} to repository or environment secrets. "
            "In GitHub Actions, use TOKEN for GITHUB_TOKEN."
        )

    project_service = app_state.get_project_service(token)
    project = await run.io_bound(project_service.link_project, repository, token_key)

    action_defaults = app_state.config_manager.get_action_type_defaults()
    executor_config = app_state.config_manager.get_executor_config()
    generated_actions = app_state.action_generator.generate_actions(
        project.phases, action_defaults
    )

    resolved_actions: list[Action] = []
    for action in generated_actions:
        context = app_state.payload_resolver.build_context(
            project=project,
            phase_id=action.phase_id,
            component_id=action.component_id,
            executor_config=executor_config,
        )
        resolved_payload = app_state.payload_resolver.resolve_payload(
            action.payload, context
        )
        action.payload = resolved_payload.payload
        resolved_actions.append(action)

    project.actions = resolved_actions
    await run.io_bound(project_service.save_project, project)
    app_state.current_project = project
    return project


def render_link_project(app_state: AppState) -> None:
    """Render the link new project screen."""
    page_layout("Link New Project", back_url="/", ui_module=ui)
    link_overlay = loading_overlay("Scanning and linking project...", ui_module=ui)

    with ui.column().classes(
        "items-center mx-auto justify-center q-pa-xl q-gutter-md w-full max-w-xl"
    ):
        with ui.card().classes("w-full q-pa-md q-gutter-sm"):
            ui.label("Link New Project").classes("text-h5 q-mb-sm")

            repo_input = ui.input(
                "GitHub Repository",
                placeholder="owner/repo-name",
                validation={
                    "Repository must be in owner/repo format.": lambda value: bool(
                        REPOSITORY_PATTERN.match(str(value).strip())
                    )
                },
            ).classes("w-full")

            token_var_input = ui.input(
                "GitHub Token Env Var",
                value="GITHUB_TOKEN",
                validation={
                    "GitHub token env var is required.": lambda value: bool(
                        str(value).strip()
                    )
                },
            ).classes("w-full")
            ui.label(
                "Use a repository/environment secret name (default: GITHUB_TOKEN; "
                "GitHub Actions uses TOKEN as alias)."
            ).classes("text-caption text-grey-7")

            result_label = ui.label("").classes("text-body2")
            result_label.set_visibility(False)

            async def _handle_scan() -> None:
                repository = str(repo_input.value).strip()
                token_env_key = str(token_var_input.value).strip()

                if not repo_input.validate() or not token_var_input.validate():
                    ui.notify(
                        "Please fix validation errors before scanning.", type="negative"
                    )
                    return

                result_label.set_visibility(False)
                result_label.text = ""
                try:
                    project = await with_loading(
                        lambda: _scan_and_link(app_state, repository, token_env_key),
                        link_overlay,
                    )
                except ProjectLinkError as exc:
                    result_label.text = _normalise_link_error(str(exc), repository)
                    result_label.classes(replace="text-body2 text-negative")
                    result_label.set_visibility(True)
                except (OSError, ValueError) as exc:
                    result_label.text = f"Failed to link project: {exc}"
                    result_label.classes(replace="text-body2 text-negative")
                    result_label.set_visibility(True)
                else:
                    phase_count = len(project.phases)
                    component_count = sum(
                        len(phase.components) for phase in project.phases
                    )
                    agent_count = len(project.agent_files)
                    result_label.text = (
                        f"Found {phase_count} phases, {component_count} components, "
                        f"{agent_count} agent files"
                    )
                    result_label.classes(replace="text-body2 text-positive")
                    result_label.set_visibility(True)
                    ui.navigate.to(f"/project/{project.project_id}")

            with ui.row().classes("w-full justify-end q-gutter-sm q-mt-md"):
                ui.button("Scan & Link", on_click=_handle_scan, color="primary")
