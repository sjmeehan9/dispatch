# Dispatch

Dispatch is a local-first desktop application for orchestrating AI agent execution against phased software delivery plans.

## Prerequisites

- Python 3.13+
- macOS (primary host for local execution)
- OneDrive (or equivalent synced local storage) for cross-device data portability
- Access to target GitHub repositories with a valid token

## Quick Start

1. Clone the repository.
2. Create and activate a Python 3.13 virtual environment.
3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
4. Configure environment variables by copying `.env/.env.example` to a local-only environment file.
5. Run quality checks:
   ```bash
   black --check app/src/
   isort --check-only app/src/
   pytest -q --cov=app/src --cov-report=term-missing
   python scripts/evals.py
   ```
6. Start the application:
   ```bash
   python -m app.src.main
   ```

## Configuration

- Configure executor endpoint, authentication key, and optional webhook URL.
- Configure default payload templates for Implement, Test, Review, Document, and Debug action types.
- Configure project secrets locally. In GitHub Actions, store token as `TOKEN` and map it to runtime `GITHUB_TOKEN`.

## Usage Outline

1. Link a GitHub project containing `phase-progress.json`.
2. Generate and review action items for each phase/component.
3. Dispatch action items to the configured executor.
4. Monitor dispatch and webhook responses.
5. Mark actions complete as work is verified.

## Architecture

See [Solution Design](docs/solution-design.md) and [Project Brief](docs/brief.md).

## Documentation

- [Project Brief](docs/brief.md)
- [Solution Design](docs/solution-design.md)
- [Phase Plan](docs/phase_plan.md)
- [Phase Progress](docs/phase-progress.json)
- [Phase 1 Component Breakdown](docs/phase-1-component-breakdown.md)
- [E2E Testing Scenarios](docs/e2e-testing-scenarios.md)
- [Dispatch Autopilot Runbook](docs/autopilot-runbook-dispatch.md)

## License

This project is licensed under the [MIT License](LICENSE).
