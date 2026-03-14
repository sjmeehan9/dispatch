"""Unit tests for application settings module."""

from __future__ import annotations

from pathlib import Path

from app.src.config import settings as settings_module
from app.src.config.constants import DEFAULT_DATA_DIR
from app.src.config.settings import Settings


def test_settings_uses_dispatch_data_dir_from_environment(
    monkeypatch, tmp_data_dir
) -> None:
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(tmp_data_dir))

    settings = Settings()

    assert settings.data_dir == tmp_data_dir
    assert settings.projects_dir == tmp_data_dir / "projects"
    assert settings.config_dir == tmp_data_dir / "config"


def test_settings_falls_back_to_default_dispatch_data_dir(monkeypatch) -> None:
    monkeypatch.delenv("DISPATCH_DATA_DIR", raising=False)

    settings = Settings()

    assert settings.data_dir == Path(DEFAULT_DATA_DIR).expanduser()


def test_initialise_data_dir_creates_directory_structure(tmp_path, monkeypatch) -> None:
    custom_data_dir = tmp_path / "dispatch"
    monkeypatch.setenv("DISPATCH_DATA_DIR", str(custom_data_dir))

    settings = Settings()
    settings.initialise_data_dir()

    assert settings.data_dir.exists()
    assert settings.projects_dir.exists()
    assert settings.config_dir.exists()


def test_get_secret_returns_env_value_and_none_for_missing(
    monkeypatch, mock_env
) -> None:
    monkeypatch.setenv("EXAMPLE_SECRET", "value-123")
    monkeypatch.delenv("MISSING_SECRET", raising=False)

    settings = Settings()

    assert settings.get_secret("EXAMPLE_SECRET") == "value-123"
    assert settings.get_secret("AUTOPILOT_API_KEY") == mock_env["AUTOPILOT_API_KEY"]
    assert settings.get_secret("MISSING_SECRET") is None


def test_get_secret_supports_github_token_ci_alias(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("TOKEN", "alias-token")

    settings = Settings()

    assert settings.get_secret("GITHUB_TOKEN") == "alias-token"


def test_get_settings_returns_singleton_instance(monkeypatch) -> None:
    monkeypatch.setattr(settings_module, "_settings", None)

    first = settings_module.get_settings()
    second = settings_module.get_settings()

    assert first is second
