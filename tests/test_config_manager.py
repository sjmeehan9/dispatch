"""Unit tests for config and secrets manager service."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from app.src.config import ACTION_DEFAULTS_FILENAME
from app.src.config.settings import Settings
from app.src.models import ActionTypeDefaults, ExecutorConfig
from app.src.services.config_manager import ConfigManager


def _build_settings(monkeypatch, tmp_path: Path) -> Settings:
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_path / "dispatch-data"))
    env_file = tmp_path / ".env" / ".env.local"
    monkeypatch.setattr(
        Settings,
        "_resolve_env_file_path",
        staticmethod(lambda: env_file),
    )
    return Settings()


def _sample_executor_config() -> ExecutorConfig:
    return ExecutorConfig(
        executor_id="autopilot",
        executor_name="Autopilot",
        api_endpoint="http://localhost:8000/agent/run",
        api_key_env_key="AUTOPILOT_API_KEY",
        webhook_url="http://localhost:9000/webhook/callback",
    )


def _sample_action_defaults() -> ActionTypeDefaults:
    return ActionTypeDefaults(
        implement={"role": "implement", "repository": "{{repository}}"},
        test={"role": "test", "repository": "{{repository}}"},
        review={"role": "review", "repository": "{{repository}}"},
        document={"role": "document", "repository": "{{repository}}"},
        debug={"role": "debug", "repository": "{{repository}}"},
    )


def test_executor_config_round_trip_save_and_load(tmp_path, monkeypatch) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    manager = ConfigManager(settings)
    expected = _sample_executor_config()

    manager.save_executor_config(expected)
    loaded = manager.get_executor_config()

    assert loaded == expected


def test_action_type_defaults_round_trip_save_and_load(tmp_path, monkeypatch) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    manager = ConfigManager(settings)
    expected = _sample_action_defaults()

    manager.save_action_type_defaults(expected)
    loaded = manager.get_action_type_defaults()

    assert loaded == expected


def test_get_executor_config_loads_defaults_when_missing(tmp_path, monkeypatch) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    manager = ConfigManager(settings)

    loaded = manager.get_executor_config()

    assert loaded.executor_id == "autopilot"
    assert (settings.config_dir / "executor.json").exists()


def test_get_action_type_defaults_loads_defaults_when_missing(
    tmp_path, monkeypatch
) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    manager = ConfigManager(settings)

    loaded = manager.get_action_type_defaults()

    assert loaded.implement["role"] == "implement"
    assert (settings.config_dir / ACTION_DEFAULTS_FILENAME).exists()


def test_set_secret_writes_and_updates_secret_value(tmp_path, monkeypatch) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    manager = ConfigManager(settings)

    manager.set_secret("EXAMPLE_TOKEN", "initial")
    manager.set_secret("EXAMPLE_TOKEN", "updated")

    monkeypatch.delenv("EXAMPLE_TOKEN", raising=False)
    reloaded_settings = Settings()
    assert reloaded_settings.get_secret("EXAMPLE_TOKEN") == "updated"


def test_list_secret_keys_returns_expected_keys(tmp_path, monkeypatch) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    manager = ConfigManager(settings)

    manager.set_secret("GITHUB_TOKEN", "one")
    manager.set_secret("AUTOPILOT_API_KEY", "two")
    settings.env_file_path.write_text(
        settings.env_file_path.read_text(encoding="utf-8") + "\n# ignored\n\n",
        encoding="utf-8",
    )

    assert manager.list_secret_keys() == ["GITHUB_TOKEN", "AUTOPILOT_API_KEY"]


def test_has_config_false_before_saving_and_true_after(tmp_path, monkeypatch) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    manager = ConfigManager(settings)

    assert manager.has_config() is False

    manager.save_executor_config(_sample_executor_config())
    manager.save_action_type_defaults(_sample_action_defaults())

    assert manager.has_config() is True


def test_atomic_json_write_replaces_temporary_file(tmp_path, monkeypatch) -> None:
    settings = _build_settings(monkeypatch, tmp_path)
    manager = ConfigManager(settings)

    manager.save_executor_config(_sample_executor_config())

    config_path = settings.config_dir / "executor.json"
    tmp_path_for_file = config_path.with_suffix(".json.tmp")

    assert config_path.exists()
    assert tmp_path_for_file.exists() is False
    persisted = json.loads(config_path.read_text(encoding="utf-8"))
    assert persisted["executor_id"] == "autopilot"


def test_defaults_yaml_parses_into_required_models() -> None:
    defaults_path = (
        Path(__file__).resolve().parents[1] / "app" / "config" / "defaults.yaml"
    )
    defaults_payload = yaml.safe_load(defaults_path.read_text(encoding="utf-8"))

    executor = ExecutorConfig.model_validate(defaults_payload["executor"])
    action_defaults = ActionTypeDefaults.model_validate(
        defaults_payload["action_type_defaults"]
    )

    assert executor.executor_id == "autopilot"
    assert executor.webhook_url is None
    assert action_defaults.review["role"] == "review"


def test_defaults_yaml_templates_include_required_placeholders() -> None:
    defaults_path = (
        Path(__file__).resolve().parents[1] / "app" / "config" / "defaults.yaml"
    )
    action_defaults = yaml.safe_load(defaults_path.read_text(encoding="utf-8"))[
        "action_type_defaults"
    ]

    expected_common = {
        "repository": "{{repository}}",
        "branch": "{{branch}}",
        "model": "claude-opus-4.6",
        "agent_paths": "{{agent_paths}}",
        "callback_url": "{{webhook_url}}",
    }
    for action_type in ("implement", "test", "review", "document", "debug"):
        for key, expected_value in expected_common.items():
            assert action_defaults[action_type][key] == expected_value

    assert "{{component_id}}" in action_defaults["implement"]["agent_instructions"]
    assert "{{component_name}}" in action_defaults["implement"]["agent_instructions"]
    assert (
        "{{component_breakdown_doc}}"
        in action_defaults["implement"]["agent_instructions"]
    )
    assert "{{phase_id}}" in action_defaults["test"]["agent_instructions"]
    assert "{{phase_name}}" in action_defaults["test"]["agent_instructions"]
    assert action_defaults["review"]["pr_number"] == "{{pr_number}}"
    assert action_defaults["review"]["role"] == "review"
    assert action_defaults["debug"]["agent_instructions"] == ""
