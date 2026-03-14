# Dispatch Autopilot Runbook

## Overview

This runbook provides practical instructions for launching and validating Dispatch locally, then executing the core Phase 4 workflows safely with mocked or live-compatible configuration.

## Prerequisites

- Python 3.13+
- Repository checked out locally
- Executor/API credentials configured from local environment or GitHub secrets
- Access to a repository containing `phase-progress.json`

## Secrets & Environment Guidance

- Do not commit `.env/.env.local` to source control.
- The remote `dispatch` repository should not contain `.env/.env.local`.
- In GitHub Actions (or other remote execution), use repository secrets or environment secrets from the `copilot` environment.
- Store the GitHub token as `TOKEN` in GitHub and map it to `GITHUB_TOKEN` at runtime.
- Local development can still use `.env/.env.local` for convenience, but this file remains local-only.

## Launch Dispatch

```bash
source .venv/bin/activate
pip install -e ".[dev]"
python -m app.src.main
```

Open: `http://localhost:8080`

## First-Time Setup Flow (UI)

Complete the following in order:

1. Configure Executor
2. Configure Action Type Defaults
3. Manage Secrets
4. Link New Project

After setup, run actions from the project main screen and use Refresh to poll webhook results.

## Starting the Application

```bash
pip install -e ".[dev]"
python -m app.src.main
```

## Quality Validation Commands

```bash
source .venv/bin/activate
black --check app/src tests
isort --check-only app/src tests
pytest -q --cov=app/src --cov-report=term-missing
python scripts/evals.py
```

## Running Tests

```bash
pytest -q --cov=app/src --cov-report=term-missing
```

## Running Evals

```bash
python scripts/evals.py
```

## E2E Test Execution

Follow the scenario definitions in [`docs/e2e-testing-scenarios.md`](docs/e2e-testing-scenarios.md). Start with E2E-001 through E2E-003 after Phase 4, then enable E2E-004 in Phase 6 and E2E-005 in Phase 7.

Phase 4 readiness:

- E2E-001 Configure and Dispatch: ready
- E2E-002 Load and Run Full Phase: ready
- E2E-003 Debug Action Workflow: ready

## Troubleshooting

- **Python version mismatch**: Ensure Python 3.13+ is active before installation.
- **Install errors**: Recreate the virtual environment and reinstall editable dependencies.
- **Validation failures**: Run `black`, `isort`, and `pytest` individually to isolate failures.
- **Dispatch/webhook issues**: Recheck executor endpoint, auth key, and callback URL configuration.
