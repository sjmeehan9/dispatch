"""Project-level pytest configuration and shared fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register custom pytest command-line options."""

    parser.addoption(
        "--autopilot-confirm",
        action="store_true",
        default=False,
        help="Run tests marked with requires_autopilot against a live external executor.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip Autopilot-marked tests unless explicitly confirmed."""

    if config.getoption("--autopilot-confirm"):
        return

    skip_marker = pytest.mark.skip(
        reason="requires --autopilot-confirm to run live Autopilot integration tests",
    )
    for item in items:
        if item.get_closest_marker("requires_autopilot"):
            item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def tmp_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create an isolated temporary data directory for tests."""

    return tmp_path_factory.mktemp("dispatch-data")


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch, tmp_data_dir: Path) -> dict[str, Any]:
    """Provide a standard isolated environment variable set for tests."""

    values: dict[str, str] = {
        "DISPATCH_DATA_DIR": str(tmp_data_dir),
        "TOKEN": "test-github-token",
        "GITHUB_TOKEN": "test-github-token",
        "AUTOPILOT_API_KEY": "test-autopilot-api-key",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return values
