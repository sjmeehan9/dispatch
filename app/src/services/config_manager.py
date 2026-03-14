"""Configuration and secret persistence service."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml
from dotenv import set_key

from app.src.config import (
    ACTION_DEFAULTS_FILENAME,
    DEFAULTS_YAML_FILENAME,
    EXECUTOR_CONFIG_FILENAME,
    Settings,
)
from app.src.models import ActionTypeDefaults, ExecutorConfig

_LOGGER = logging.getLogger(__name__)


class ConfigManager:
    """Manage persisted executor configuration, defaults, and local secrets."""

    def __init__(self, settings: Settings) -> None:
        """Initialise the manager with application settings.

        Args:
            settings: Application settings with configured data and env paths.
        """

        self._settings = settings
        self._settings.initialise_data_dir()
        self._executor_config_path = (
            self._settings.config_dir / EXECUTOR_CONFIG_FILENAME
        )
        self._action_defaults_path = (
            self._settings.config_dir / ACTION_DEFAULTS_FILENAME
        )

    def get_executor_config(self) -> ExecutorConfig:
        """Load persisted executor configuration.

        Returns:
            The saved executor configuration, or bundled defaults when missing.
        """

        if self._executor_config_path.exists():
            _LOGGER.info(
                "Loading executor config from %s",
                self._executor_config_path.as_posix(),
            )
            payload = json.loads(self._executor_config_path.read_text(encoding="utf-8"))
            return ExecutorConfig.model_validate(payload)

        defaults_executor, _ = self._load_defaults()
        self.save_executor_config(defaults_executor)
        return defaults_executor

    def save_executor_config(self, config: ExecutorConfig) -> None:
        """Persist executor configuration as human-readable JSON.

        Args:
            config: Executor configuration to persist.
        """

        _LOGGER.info(
            "Saving executor config to %s", self._executor_config_path.as_posix()
        )
        self._write_json_atomic(
            path=self._executor_config_path,
            payload=config.model_dump(mode="json"),
        )

    def get_action_type_defaults(self) -> ActionTypeDefaults:
        """Load persisted action-type payload templates.

        Returns:
            The saved action-type defaults, or bundled defaults when missing.
        """

        if self._action_defaults_path.exists():
            _LOGGER.info(
                "Loading action type defaults from %s",
                self._action_defaults_path.as_posix(),
            )
            payload = json.loads(self._action_defaults_path.read_text(encoding="utf-8"))
            return ActionTypeDefaults.model_validate(payload)

        _, defaults = self._load_defaults()
        self.save_action_type_defaults(defaults)
        return defaults

    def save_action_type_defaults(self, defaults: ActionTypeDefaults) -> None:
        """Persist action-type payload templates as human-readable JSON.

        Args:
            defaults: Action-type default templates to persist.
        """

        _LOGGER.info(
            "Saving action type defaults to %s", self._action_defaults_path.as_posix()
        )
        self._write_json_atomic(
            path=self._action_defaults_path,
            payload=defaults.model_dump(mode="json"),
        )

    def set_secret(self, key: str, value: str) -> None:
        """Create or update a secret entry in the local env file.

        Args:
            key: Environment variable key to write.
            value: Environment variable value to write.
        """

        env_file = self._settings.env_file_path
        env_file.parent.mkdir(parents=True, exist_ok=True)
        if not env_file.exists():
            env_file.touch()

        _LOGGER.info("Saving secret key %s to %s", key, env_file.as_posix())
        set_key(str(env_file), key, value, quote_mode="never")

    def list_secret_keys(self) -> list[str]:
        """Return all key names currently stored in the local env file.

        Returns:
            Secret key names from `.env/.env.local`.
        """

        env_file = self._settings.env_file_path
        if not env_file.exists():
            return []

        keys: list[str] = []
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key_part = line.split("=", maxsplit=1)[0].strip()
            if key_part.startswith("export "):
                key_part = key_part.removeprefix("export ").strip()

            if key_part:
                keys.append(key_part)
        return keys

    def has_config(self) -> bool:
        """Return whether both executor and action defaults files exist."""

        return (
            self._executor_config_path.exists() and self._action_defaults_path.exists()
        )

    def _load_defaults(self) -> tuple[ExecutorConfig, ActionTypeDefaults]:
        """Load bundled default executor settings and action templates.

        Returns:
            A tuple of default executor configuration and action type defaults.
        """

        defaults_path = (
            Path(__file__).resolve().parents[3]
            / "app"
            / "config"
            / DEFAULTS_YAML_FILENAME
        )
        _LOGGER.info("Loading bundled defaults from %s", defaults_path.as_posix())
        raw_defaults = yaml.safe_load(defaults_path.read_text(encoding="utf-8"))

        executor_payload = raw_defaults.get(
            "executor", raw_defaults.get("executor_config")
        )
        action_defaults_payload = raw_defaults.get("action_type_defaults")

        if executor_payload is None or action_defaults_payload is None:
            raise ValueError(
                "defaults.yaml must include 'executor' and 'action_type_defaults' keys."
            )

        return (
            ExecutorConfig.model_validate(executor_payload),
            ActionTypeDefaults.model_validate(action_defaults_payload),
        )

    @staticmethod
    def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
        """Write JSON to disk atomically using a temporary file and replace.

        Args:
            path: Final output path.
            payload: JSON-serializable payload to persist.
        """

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(path)
