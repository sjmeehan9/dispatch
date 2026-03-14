"""Project-level pytest configuration and shared fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register custom pytest command-line options."""

    parser.addoption(
        "--autopilot-confirm",
        action="store_true",
        default=False,
        help="Run live Autopilot executor tests (requires running Autopilot service)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip Autopilot-marked tests unless explicitly confirmed."""

    if config.getoption("--autopilot-confirm"):
        return

    skip_marker = pytest.mark.skip(
        reason="Need --autopilot-confirm to run live executor tests",
    )
    for item in items:
        if item.get_closest_marker("requires_autopilot"):
            item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def confirm_autopilot_gateway(request: pytest.FixtureRequest) -> dict[str, str]:
    """Confirm live Autopilot connectivity details for human-gated tests.

    Returns:
        Dictionary containing the API endpoint and API key.

    Raises:
        pytest.SkipTest: If confirmation is not provided or configuration is missing.
    """

    if not request.config.getoption("--autopilot-confirm"):
        pytest.skip("Need --autopilot-confirm to run live executor tests")

    api_endpoint = os.environ.get("AUTOPILOT_API_ENDPOINT", "").strip()
    api_key = os.environ.get("AUTOPILOT_API_KEY", "").strip()

    if not api_endpoint or not api_key:
        pytest.skip(
            "AUTOPILOT_API_ENDPOINT and AUTOPILOT_API_KEY must be set for live tests"
        )

    try:
        confirmed = input(
            f"Is the Autopilot executor running at {api_endpoint}? [y/N]: "
        )
    except EOFError:
        pytest.skip("Interactive confirmation unavailable (likely CI environment)")

    if confirmed.strip().lower() not in {"y", "yes"}:
        pytest.skip("Live Autopilot test declined by user")

    return {"api_endpoint": api_endpoint, "api_key": api_key}


@pytest.fixture(scope="session")
def tmp_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create an isolated temporary data directory for tests."""

    return tmp_path_factory.mktemp("dispatch-data")


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch, tmp_data_dir: Path) -> dict[str, str]:
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
