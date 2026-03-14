"""Shared application state for NiceGUI screens."""

from __future__ import annotations

from app.src.config import ACTION_DEFAULTS_FILENAME, EXECUTOR_CONFIG_FILENAME, Settings
from app.src.models import Project
from app.src.services import (
    ActionGenerator,
    AutopilotExecutor,
    GitHubClient,
    LLMPayloadGenerator,
    LLMService,
    PayloadResolver,
    ProjectService,
    WebhookService,
)
from app.src.services.config_manager import ConfigManager
from app.src.services.project_service import ProjectNotFoundError


class AppState:
    """Central in-memory state container for the running application."""

    def __init__(self) -> None:
        """Initialise shared service instances and runtime project state."""
        self.settings = Settings()
        self.config_manager = ConfigManager(self.settings)
        self.webhook_service = WebhookService()
        self.action_generator = ActionGenerator()
        self.payload_resolver = PayloadResolver()
        self.autopilot_executor = AutopilotExecutor(self.settings)
        self.llm_service = LLMService()
        self.llm_payload_generator = LLMPayloadGenerator(
            self.llm_service,
            self.payload_resolver,
        )

        self.current_project: Project | None = None
        self.last_dispatched_action = None
        self.dispatching_action_id: str | None = None
        self.completing_action_id: str | None = None
        self.selected_phase_filter_phase_id: int | None = None
        self.navigation_stack: list[str] = []

    def get_github_client(self, token: str) -> GitHubClient:
        """Create a GitHub client for a provided token."""
        return GitHubClient(token)

    def get_project_service(self, token: str) -> ProjectService:
        """Create a project service wired with a token-bound GitHub client."""
        github_client = self.get_github_client(token)
        return ProjectService(settings=self.settings, github_client=github_client)

    @property
    def is_executor_configured(self) -> bool:
        """Return whether executor config exists and validates."""
        config_path = self.settings.config_dir / EXECUTOR_CONFIG_FILENAME
        if not config_path.exists():
            return False

        try:
            self.config_manager.get_executor_config()
        except (OSError, ValueError):
            return False
        return True

    @property
    def is_action_types_configured(self) -> bool:
        """Return whether action-type defaults exist and validate."""
        defaults_path = self.settings.config_dir / ACTION_DEFAULTS_FILENAME
        if not defaults_path.exists():
            return False

        try:
            self.config_manager.get_action_type_defaults()
        except (OSError, ValueError):
            return False
        return True

    @property
    def is_fully_configured(self) -> bool:
        """Return whether executor and action-type config are both ready."""
        return self.is_executor_configured and self.is_action_types_configured

    def reload_config(self) -> None:
        """Reload and validate persisted configuration from disk."""
        if self.is_executor_configured:
            self.config_manager.get_executor_config()
        if self.is_action_types_configured:
            self.config_manager.get_action_type_defaults()

    def reinit_llm_service(self) -> None:
        """Reinitialize LLM service objects after secret updates."""
        self.llm_service = LLMService()
        self.llm_payload_generator = LLMPayloadGenerator(
            self.llm_service,
            self.payload_resolver,
        )

    def clear_project(self) -> None:
        """Clear project-scoped runtime state when leaving project context."""
        self.current_project = None
        self.last_dispatched_action = None
        self.dispatching_action_id = None
        self.completing_action_id = None
        self.selected_phase_filter_phase_id = None

    def ensure_project(self, project_id: str) -> Project | None:
        """Return the requested project from memory or disk, otherwise redirect home."""
        if (
            self.current_project is not None
            and self.current_project.project_id == project_id
        ):
            return self.current_project

        token: str | None = None
        if self.current_project is not None:
            current_token_key = getattr(
                self.current_project, "github_token_env_key", ""
            )
            if isinstance(current_token_key, str) and current_token_key:
                token = self.settings.get_secret(current_token_key)
        if not token:
            token = self.settings.get_secret("GITHUB_TOKEN")
        if not token:
            token = self.settings.get_secret("TOKEN")
        if not token:
            token = "local-project-access"

        try:
            project = self.get_project_service(token).load_project(project_id)
        except (ProjectNotFoundError, OSError, ValueError):
            self.clear_project()
            return None

        self.current_project = project
        return project
