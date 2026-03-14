"""Load-project screen UI module."""

from __future__ import annotations

from nicegui import run, ui

from app.src.services.project_service import ProjectNotFoundError, ProjectService
from app.src.ui.components import loading_overlay, page_layout, with_loading
from app.src.ui.state import AppState


def _project_service_for_saved_projects(app_state: AppState) -> ProjectService:
    """Return a project service usable for local project list/load/delete operations."""
    token = app_state.settings.get_secret("GITHUB_TOKEN")
    if not token:
        token = app_state.settings.get_secret("TOKEN")
    if not token and app_state.current_project is not None:
        token = app_state.settings.get_secret(
            app_state.current_project.github_token_env_key
        )
    if not token:
        token = "local-project-access"
    return app_state.get_project_service(token)


def render_load_project(app_state: AppState) -> None:
    """Render the saved-project load screen."""
    project_service = _project_service_for_saved_projects(app_state)
    page_layout("Load Project", back_url="/", ui_module=ui)
    load_overlay = loading_overlay("Loading project...", ui_module=ui)

    async def _load_project(project_id: str) -> None:
        try:
            project = await with_loading(
                lambda: run.io_bound(project_service.load_project, project_id),
                load_overlay,
            )
        except ProjectNotFoundError as exc:
            ui.notify(str(exc), type="negative")
            _project_list.refresh()
            return
        except OSError as exc:
            ui.notify(f"Unable to load project: {exc}", type="negative")
            return

        app_state.current_project = project
        ui.navigate.to(f"/project/{project.project_id}")

    def _delete_project(project_id: str) -> None:
        try:
            project_service.delete_project(project_id)
        except ProjectNotFoundError as exc:
            ui.notify(str(exc), type="warning")
        except OSError as exc:
            ui.notify(f"Unable to delete project: {exc}", type="negative")
        else:
            ui.notify("Project deleted", type="positive")
        finally:
            _project_list.refresh()

    with ui.column().classes(
        "items-center mx-auto justify-center q-pa-xl q-gutter-md w-full max-w-2xl"
    ):
        with ui.card().classes("w-full q-pa-md q-gutter-sm"):
            ui.label("Load Project").classes("text-h5 q-mb-sm")

            @ui.refreshable
            def _project_list() -> None:
                try:
                    projects = project_service.list_projects()
                except OSError as exc:
                    ui.label(f"Unable to list projects: {exc}").classes("text-negative")
                    return

                if not projects:
                    ui.label("No saved projects. Link a new project to get started.")
                    ui.button(
                        "Link New Project",
                        on_click=lambda: ui.navigate.to("/project/link"),
                    )
                    return

                with ui.column().classes("w-full q-gutter-sm"):
                    for project in projects:
                        with ui.card().classes("w-full q-pa-sm"):
                            with ui.row().classes(
                                "w-full items-center justify-between no-wrap"
                            ):
                                with ui.column().classes("q-gutter-xs"):
                                    ui.button(
                                        project.project_name,
                                        on_click=lambda project_id=project.project_id: _load_project(
                                            project_id
                                        ),
                                    ).props("flat no-caps align=left")
                                    ui.label(project.repository).classes(
                                        "text-caption text-grey-8"
                                    )
                                    ui.label(f"Updated: {project.updated_at}").classes(
                                        "text-caption text-grey-7"
                                    )

                                with (
                                    ui.dialog() as confirm_dialog,
                                    ui.card().classes("q-pa-md q-gutter-sm"),
                                ):
                                    ui.label(
                                        f"Delete project {project.project_name}?"
                                    ).classes("text-body1")
                                    with ui.row().classes(
                                        "w-full justify-end q-gutter-sm"
                                    ):
                                        ui.button(
                                            "Cancel", on_click=confirm_dialog.close
                                        ).props("flat")
                                        ui.button(
                                            "Delete",
                                            color="negative",
                                            on_click=lambda dialog=confirm_dialog, project_id=project.project_id: (
                                                dialog.close(),
                                                _delete_project(project_id),
                                            ),
                                        )

                                ui.button(
                                    icon="delete",
                                    color="negative",
                                    on_click=confirm_dialog.open,
                                ).props("flat round")

            _project_list()
