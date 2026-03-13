"""Tests for pytest hooks and fixtures in tests.conftest."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests import conftest


class _DummyParser:
    def __init__(self) -> None:
        self.options: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def addoption(self, *args: str, **kwargs: object) -> None:
        self.options.append((args, kwargs))


class _DummyConfig:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def getoption(self, option_name: str) -> bool:
        assert option_name == "--autopilot-confirm"
        return self.enabled


class _DummyItem:
    def __init__(self, requires_autopilot: bool) -> None:
        self.requires_autopilot = requires_autopilot
        self.markers: list[pytest.MarkDecorator] = []

    def get_closest_marker(self, name: str) -> pytest.MarkDecorator | None:
        if name == "requires_autopilot" and self.requires_autopilot:
            return pytest.mark.requires_autopilot
        return None

    def add_marker(self, marker: pytest.MarkDecorator) -> None:
        self.markers.append(marker)


def test_pytest_addoption_registers_autopilot_flag() -> None:
    parser = _DummyParser()

    conftest.pytest_addoption(parser)  # type: ignore[arg-type]

    assert any(option[0] == ("--autopilot-confirm",) for option in parser.options)


def test_collection_modifyitems_adds_skip_marker_without_flag() -> None:
    item = _DummyItem(requires_autopilot=True)

    conftest.pytest_collection_modifyitems(  # type: ignore[arg-type]
        _DummyConfig(enabled=False),
        [item],
    )

    assert item.markers
    assert item.markers[0].mark.name == "skip"


def test_collection_modifyitems_does_not_skip_with_flag() -> None:
    item = _DummyItem(requires_autopilot=True)

    conftest.pytest_collection_modifyitems(  # type: ignore[arg-type]
        _DummyConfig(enabled=True),
        [item],
    )

    assert item.markers == []


def test_tmp_data_dir_fixture_creates_directory(tmp_data_dir: Path) -> None:
    assert tmp_data_dir.exists()
    assert tmp_data_dir.is_dir()


def test_mock_env_fixture_sets_environment_variables(mock_env: dict[str, str]) -> None:
    for key, value in mock_env.items():
        assert os.environ[key] == value
