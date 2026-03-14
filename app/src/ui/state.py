"""Shared application state for NiceGUI screens."""

from __future__ import annotations

from app.src.config import ACTION_DEFAULTS_FILENAME, EXECUTOR_CONFIG_FILENAME, Settings
from app.src.models import Project
from app.src.services import (
    ActionGenerator,
    AutopilotExecutor,
    GitHubClient,
    PayloadResolver,
    ProjectService,
    WebhookService,
)
from app.src.services.config_manager import ConfigManager


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

        self.current_project: Project | None = None

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
