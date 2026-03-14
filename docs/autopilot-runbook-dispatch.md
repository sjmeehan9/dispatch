# Dispatch Autopilot Runbook (Skeleton)

## Overview

This runbook provides baseline instructions for AI agents to run Dispatch locally and execute validation workflows. It is intentionally lightweight in Phase 1 and will be expanded in later phases.

## Prerequisites

- Python 3.13+
- Repository checked out locally
- Executor/API credentials configured from local environment or CI secrets
- Access to a repository containing `phase-progress.json`

## Secrets & Environment Guidance

- Do not commit `.env/.env.local` to source control.
- In GitHub Actions, use repository or environment secrets from the `copilot` environment.
- Store GitHub token as `TOKEN` in GitHub secrets and map to `GITHUB_TOKEN` at runtime.

## Starting the Application

```bash
pip install -e ".[dev]"
python -m app.src.main
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

## Troubleshooting

- **Python version mismatch**: Ensure Python 3.13+ is active before installation.
- **Install errors**: Recreate the virtual environment and reinstall editable dependencies.
- **Validation failures**: Run `black`, `isort`, and `pytest` individually to isolate failures.
- **Dispatch/webhook issues**: Recheck executor endpoint, auth key, and callback URL configuration.
