# Phase 1 Component 1.3 Overview: CI/CD Pipeline & Quality Tooling

## Summary

Component 1.3 establishes the automated quality gates for Dispatch by introducing a GitHub Actions CI workflow, a custom AST-based evaluation script, and foundational pytest project fixtures/hooks.

## Delivered Scope

1. **CI Workflow**
   - Added `.github/workflows/ci.yml`
   - Triggers on `push` and `pull_request` to `main`
   - Uses Python 3.13
   - Installs dev dependencies with editable install: `pip install -e ".[dev]"`
   - Runs quality checks in sequence:
     - Black (`black --check app/src/`)
     - isort (`isort --check-only app/src/`)
     - pytest with coverage (`pytest -q --cov=app/src --cov-report=term-missing`)
     - project evals (`python scripts/evals.py`)
   - Exposes `GITHUB_TOKEN` from `secrets.TOKEN` to align with repository secret naming constraints

2. **Quality Gate Script**
   - Added `scripts/evals.py`
   - Implements:
     - `check_docstrings(path)` for public classes/functions
     - `check_no_todos(path)` for TODO/FIXME/NotImplementedError and placeholder bodies (`pass`/`...`)
     - `main()` orchestration and non-zero exit on violations
   - Uses AST parsing for structural checks and line-level violation reporting

3. **Pytest Conftest Skeleton**
   - Added `tests/conftest.py`
   - Registers `--autopilot-confirm` flag via `pytest_addoption`
   - Skips tests marked `requires_autopilot` unless the flag is passed
   - Provides `tmp_data_dir` session fixture for isolated dispatch data paths
   - Provides `mock_env` fixture for environment isolation in tests

4. **Focused Validation Tests**
   - Added `tests/test_evals.py` to verify eval script behavior
   - Added `tests/test_conftest.py` to verify hook/fixture behavior

## Key Design Decisions

- **Scoped source checks**: `scripts/evals.py` targets only `app/src/` per Phase 1 requirements to keep early quality gates strict and relevant.
- **Secret handling in CI**: Workflow uses GitHub Actions secrets (`TOKEN` → `GITHUB_TOKEN`) and does not rely on committed local env files.
- **Extensible pytest foundation**: Hooks/fixtures are intentionally minimal while establishing patterns needed for later live executor integration tests.

## Deviations from Spec

- None.
