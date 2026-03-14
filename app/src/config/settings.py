"""Application settings and environment loading module."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from app.src.config.constants import (
    CONFIG_DIR_NAME,
    DEFAULT_DATA_DIR,
    ENV_DIR_NAME,
    ENV_FILE_NAME,
    PROJECTS_DIR_NAME,
)

_GITHUB_TOKEN_ENV_KEY = "GITHUB_TOKEN"
_GITHUB_TOKEN_CI_ALIAS = "TOKEN"


class Settings:
    """Centralized environment-backed application settings."""

    def __init__(self) -> None:
        """Initialise settings from environment variables and defaults."""
        self.env_file_path = self._resolve_env_file_path()
        load_dotenv(dotenv_path=self.env_file_path, override=False)

        data_dir_value = os.environ.get("DISPATCH_DATA_DIR", DEFAULT_DATA_DIR)
        self.data_dir = Path(data_dir_value).expanduser()
        self.projects_dir = self.data_dir / PROJECTS_DIR_NAME
        self.config_dir = self.data_dir / CONFIG_DIR_NAME

    def initialise_data_dir(self) -> None:
        """Create the Dispatch data directory structure if missing."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def get_secret(self, env_key: str) -> str | None:
        """Return a secret from the process environment by key name."""
        value = os.environ.get(env_key)
        if value is not None:
            return value

        if env_key == _GITHUB_TOKEN_ENV_KEY:
            return os.environ.get(_GITHUB_TOKEN_CI_ALIAS)

        return None

    @staticmethod
    def _resolve_env_file_path() -> Path:
        """Resolve the local env file path relative to the repository root."""
        project_root = Path(__file__).resolve().parents[3]
        return project_root / ENV_DIR_NAME / ENV_FILE_NAME


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the lazily initialised settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
