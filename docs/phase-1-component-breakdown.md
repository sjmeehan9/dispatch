# Phase 1: Project Bootstrap & Environment Setup

## Phase Overview

**Objective**: Establish the repository structure, development environment, CI/CD pipeline, and quality tooling. Define the end-to-end testing scenarios that will be validated at the end of each subsequent phase. All foundational conventions are locked in before any application code is written.

**Deliverables**:
- Complete folder layout per solution design with `pyproject.toml` for editable install
- GitHub Actions CI/CD workflow running Black, isort, pytest, and evals
- `scripts/evals.py` quality gate script
- E2E testing scenarios documented with clear pass/fail criteria
- `README.md` skeleton with project overview
- `.env/.env.example` template with all required environment variable placeholders

**Dependencies**:
- GitHub repository must exist (already created)
- Python 3.13+ available on the developer's machine
- Virtual environment created and activated

## Phase Goals

- Repository is fully scaffolded with the canonical folder structure from the solution design
- `pip install -e .` succeeds in the virtual environment
- `pytest`, `black --check`, `isort --check-only`, and `python scripts/evals.py` all pass cleanly
- CI/CD pipeline triggers on push and runs all quality checks
- E2E testing scenarios are documented for use throughout all subsequent phases
- All developer conventions and patterns are established before any application code is written

---

## Components

### Component 1.1 — Environment & Repository Initialisation

**Priority**: Must-have

**Estimated Effort**: 1 hour

**Owner**: Human

**Dependencies**:
- None (first component)

**Features**:
- [Human] Confirm GitHub repository exists and is accessible
- [Human] Create Python 3.13+ virtual environment (`.venv/`)
- [Human] Create `.env/.env.local` from `.env/.env.example` template (after Component 1.2 creates the template)
- [Human] Verify `source .venv/bin/activate` works correctly
- [Human] Confirm the developer can push to the repository

**Description**:
This component covers the human-gated initial setup that cannot be automated by an AI agent. The developer confirms the GitHub repository is ready, creates the Python virtual environment locally, and sets up the initial `.env/.env.local` file from the template. This must be done before any subsequent components can install the package or run tools.

**Acceptance Criteria**:
- [ ] GitHub repository is accessible at the expected URL
- [ ] `.venv/` directory exists with Python 3.13+
- [ ] `source .venv/bin/activate` activates the virtual environment
- [ ] `python --version` within the venv reports 3.13+
- [ ] `.env/.env.local` exists with placeholder values populated from `.env/.env.example`
- [ ] Developer can `git push` to the repository

**Technical Details**:
- **Files to Create/Modify**: `.venv/` (created via `python3.13 -m venv .venv`), `.env/.env.local` (copy from template)
- **Human/AI Agent**: Entirely human — requires local machine access and credentials
- **Dependencies**: Python 3.13+ installed on macOS

**Detailed Implementation Requirements**:
- **File 1: `.venv/`**: Create the virtual environment using `python3.13 -m venv .venv`. Verify activation with `source .venv/bin/activate && python --version`. This directory is already gitignored.
- **File 2: `.env/.env.local`**: Copy from `.env/.env.example` (created in Component 1.2) and fill in placeholder values. At minimum, set `DISPATCH_DATA_DIR` to a local path (e.g., `~/.dispatch/` or an OneDrive-synced equivalent). Leave API keys as empty strings for now. This file must never be committed.

**Test Requirements**:
- [ ] Manual verification: `source .venv/bin/activate && python --version` outputs 3.13+
- [ ] Manual verification: `.env/.env.local` exists and contains expected variable keys

**Definition of Done**:
- [ ] Virtual environment created and activatable
- [ ] `.env/.env.local` created with required variable placeholders
- [ ] Developer confirms push access to the repository
- [ ] Documentation created: Component Overview (`docs/components/phase-1-component-1-1-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-1.md`). Maximum 50 lines of markdown per component.

**Notes**:
This component can be performed in parallel with Component 1.2 review, but `.env/.env.local` depends on the `.env/.env.example` template from Component 1.2. The developer should activate the venv first, then return to create `.env/.env.local` after Component 1.2 is complete.

---

### Component 1.2 — Repository Structure & Package Configuration

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.1: GitHub repository must exist and be accessible

**Features**:
- [AI Agent] Create complete folder layout per solution design
- [AI Agent] Create `pyproject.toml` with package metadata, dependencies, and editable install configuration
- [AI Agent] Create `.env/.env.example` template with all required environment variable placeholders
- [AI Agent] Update `.gitignore` to cover all required patterns (`.env/`, `~/.dispatch/`, `.venv/`, `__pycache__/`)
- [AI Agent] Create all `__init__.py` files for the package structure
- [AI Agent] Create empty placeholder modules for each source directory to establish the import structure

**Description**:
This component scaffolds the entire repository according to the solution design's project structure. It creates every directory, initialises the Python package via `pyproject.toml` (with all core dependencies declared), sets up the `.env/.env.example` template, ensures `.gitignore` is comprehensive, and creates the module initialisation files that allow `pip install -e .` to work. After this component, the repo has a clean, installable structure ready for CI/CD and application code.

**Acceptance Criteria**:
- [ ] Folder structure matches the solution design exactly (all directories exist)
- [ ] `pyproject.toml` declares the `app` package with correct entry point and all core dependencies
- [ ] `pip install -e .` succeeds in the virtual environment without errors
- [ ] `python -c "import app.src"` succeeds without import errors
- [ ] `.env/.env.example` lists all required environment variables with comments
- [ ] `.gitignore` includes patterns for `.env/`, `__pycache__/`, `.venv/`, `*.egg-info/`, `.DS_Store`
- [ ] All `__init__.py` files exist for `app/`, `app/src/`, `app/src/ui/`, `app/src/services/`, `app/src/models/`, `app/src/config/`

**Technical Details**:
- **Files to Create/Modify**:
  - `pyproject.toml`
  - `.env/.env.example`
  - `.gitignore` (update existing)
  - `app/__init__.py`
  - `app/src/__init__.py`
  - `app/src/ui/__init__.py`
  - `app/src/services/__init__.py`
  - `app/src/models/__init__.py`
  - `app/src/config/__init__.py`
  - `app/config/` (directory for YAML defaults)
  - `app/docs/` (directory for internal app docs)
  - `tests/__init__.py`
- **Key Functions/Classes**: None — structural scaffolding only
- **Human/AI Agent**: AI Agent implements all files; human verifies `pip install -e .`
- **Dependencies**: nicegui>=2.0, httpx>=0.27, pydantic>=2.0, python-dotenv>=1.0, pyyaml>=6.0, openai>=1.0 (optional), black, isort, pytest, pytest-cov

**Detailed Implementation Requirements**:
- **File 1: `pyproject.toml`**: Define under `[project]` with name `dispatch`, version `0.1.0`, Python `>=3.13`. List core dependencies: `nicegui>=2.0`, `httpx>=0.27`, `pydantic>=2.0`, `python-dotenv>=1.0`, `pyyaml>=6.0`. List optional dependencies under `[project.optional-dependencies]` for `dev` (black, isort, pytest, pytest-cov) and `llm` (openai>=1.0). Configure `[tool.black]` with `line-length = 88` and `target-version = ["py313"]`. Configure `[tool.isort]` with `profile = "black"`. Configure `[tool.pytest.ini_options]` with `testpaths = ["tests"]`. Declare the package finder under `[tool.setuptools.packages.find]` with `where = ["."]` to discover the `app` package.
- **File 2: `.env/.env.example`**: Template file listing all environment variables with comments: `DISPATCH_DATA_DIR` (path to data directory, default `~/.dispatch/`), `GITHUB_TOKEN` (GitHub personal access token), `AUTOPILOT_API_KEY` (Autopilot executor API key), `AUTOPILOT_API_ENDPOINT` (Autopilot API URL, default `http://localhost:8000/agent/run`), `AUTOPILOT_WEBHOOK_URL` (ngrok webhook URL), `OPENAI_API_KEY` (optional — for LLM payload generation), `OPENAI_MODEL` (optional — default `gpt-4o`). Each variable should have a descriptive comment and an empty or default value.
- **File 3: `.gitignore` (update)**: Ensure the existing `.gitignore` also includes patterns for `.env/`, `.env.local`, `.env.test`, `~/.dispatch/`, `.DS_Store`, `*.egg-info/`, `.venv/`. Do not duplicate patterns already present.
- **File 4: `__init__.py` files**: Create empty `__init__.py` files in `app/`, `app/src/`, `app/src/ui/`, `app/src/services/`, `app/src/models/`, `app/src/config/`, and `tests/`. These establish the Python package structure for absolute imports.
- **File 5: `app/config/`**: Create the directory for YAML default configuration files (will be populated in Phase 2). Include an empty `.gitkeep` file.
- **File 6: `app/docs/`**: Create the directory for internal app documentation. Include an empty `.gitkeep` file.

**Test Requirements**:
- [ ] `pip install -e .` succeeds without errors
- [ ] `python -c "import app; import app.src"` succeeds
- [ ] `black --check app/src/` passes (all files are empty/valid)
- [ ] `isort --check-only app/src/` passes

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] All directories and files exist per solution design
- [ ] `pip install -e .` succeeds
- [ ] No regression in existing functionality
- [ ] Documentation created: Component Overview (`docs/components/phase-1-component-1-2-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-1.md`). Maximum 50 lines of markdown per component.

**Notes**:
The `pyproject.toml` must use `[tool.setuptools.packages.find]` with `where = ["."]` so that `app.src.*` imports resolve correctly when the package is installed in editable mode. This is critical — without it, imports like `from app.src.services.auth import AuthService` will fail per the project's absolute import convention.

---

### Component 1.3 — CI/CD Pipeline & Quality Tooling

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.2: Repository structure and `pyproject.toml` must exist for tools to run against

**Features**:
- [AI Agent] Create GitHub Actions CI workflow file (`.github/workflows/ci.yml`)
- [AI Agent] Create `scripts/evals.py` quality gate script
- [AI Agent] Create `tests/conftest.py` pytest skeleton with project-level fixtures
- [AI Agent] Verify all quality tools run cleanly against the scaffolded repository

**Description**:
This component sets up the automated quality pipeline that will gate all future changes. It creates a GitHub Actions workflow that runs Black, isort, pytest, and the custom evals script on every push and pull request. The `scripts/evals.py` script enforces project-specific quality gates: all public functions have docstrings, no TODO/FIXME comments remain in delivered code. The `conftest.py` skeleton provides the foundation for test fixtures including the human-gated external system test pattern.

**Acceptance Criteria**:
- [ ] `.github/workflows/ci.yml` exists and defines a valid GitHub Actions workflow
- [ ] CI workflow runs: `black --check app/src/`, `isort --check-only app/src/`, `pytest -q --cov=app/src --cov-report=term-missing`, `python scripts/evals.py`
- [ ] `scripts/evals.py` passes against the current (empty) codebase
- [ ] `scripts/evals.py` correctly detects: missing docstrings on public functions, TODO/FIXME comments in `app/src/`
- [ ] `tests/conftest.py` exists with project-level fixture structure
- [ ] `pytest` runs and exits cleanly (0 tests collected, exit code 0 or 5)
- [ ] All quality checks pass locally: `black --check`, `isort --check-only`, `pytest`, `evals.py`

**Technical Details**:
- **Files to Create/Modify**:
  - `.github/workflows/ci.yml`
  - `scripts/evals.py`
  - `tests/conftest.py`
- **Key Functions/Classes**:
  - `scripts/evals.py`: `check_docstrings(path)`, `check_no_todos(path)`, `main()`
  - `tests/conftest.py`: `pytest_addoption()` hook, session-scoped fixtures
- **Human/AI Agent**: AI Agent creates all files; CI runs automatically on push
- **Dependencies**: black, isort, pytest, pytest-cov (declared in Component 1.2's `pyproject.toml`)

**Detailed Implementation Requirements**:
- **File 1: `.github/workflows/ci.yml`**: Create a GitHub Actions workflow triggered on `push` and `pull_request` to `main`. Use `ubuntu-latest` runner with Python 3.13. Steps: checkout code, set up Python 3.13, install package in editable mode with dev dependencies (`pip install -e ".[dev]"`), run `black --check app/src/`, run `isort --check-only app/src/`, run `pytest -q --cov=app/src --cov-report=term-missing`, run `python scripts/evals.py`. Each step should fail the workflow on non-zero exit. Name the workflow `CI` and the job `quality-checks`.
- **File 2: `scripts/evals.py`**: Implement a quality gate script that: (1) walks `app/src/` recursively finding all `.py` files, (2) uses `ast` module to parse each file and check that all public functions (not starting with `_`) and public classes have docstrings — report violations but don't fail on empty `__init__.py` files or files with no public functions, (3) scans for `TODO`, `FIXME`, `NotImplementedError`, `pass` (as sole function body), and `...` (as sole function body) patterns in delivered code — report violations, (4) prints a summary of pass/fail with file:line references for each violation, (5) exits with code 0 if all checks pass, code 1 if any fail. The script should be executable directly (`python scripts/evals.py`). Use `from __future__ import annotations` and type hints throughout. Include a Google-style docstring on all public functions.
- **File 3: `tests/conftest.py`**: Create a pytest conftest that: (1) registers a `--autopilot-confirm` flag via `pytest_addoption` for human-gated external system tests, (2) adds a `pytest_collection_modifyitems` hook that auto-skips tests marked `requires_autopilot` unless the flag is passed, (3) defines a session-scoped `tmp_data_dir` fixture that creates a temporary directory for test data (simulating `~/.dispatch/` without touching the real directory), (4) defines a `mock_env` fixture that patches environment variables for test isolation. Keep the skeleton minimal but extensible.

**Test Requirements**:
- [ ] `python scripts/evals.py` exits with code 0 on the scaffolded codebase
- [ ] `pytest` runs and exits cleanly
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes

**Definition of Done**:
- [ ] Code implemented and reviewed
- [ ] All quality tools pass locally
- [ ] GitHub Actions workflow file is valid YAML
- [ ] CI pipeline runs successfully on push (verified after Component 1.1 human pushes)
- [ ] Documentation created: Component Overview (`docs/components/phase-1-component-1-3-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-1.md`). Maximum 50 lines of markdown per component.

**Notes**:
The `evals.py` script should use `ast.parse()` to avoid false positives from string matching. For detecting `pass` and `...` as sole function bodies, check that the function's AST body contains exactly one statement which is either a `Pass` node or a `Constant(value=Ellipsis)` node — but ignore this check if the file is an `__init__.py` or if the function also has a docstring (docstring + `pass` is acceptable in skeleton files during scaffolding, but should be flagged in delivered components). At this bootstrap stage, no application code exists, so evals should pass trivially. The `--autopilot-confirm` flag in `conftest.py` prepares for Phase 7's live executor tests.

---

### Component 1.4 — E2E Testing Scenarios, README & Phase Validation

**Priority**: Must-have

**Estimated Effort**: 2 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.2: Repository structure must exist for file placement
- Component 1.3: Quality tooling must be in place for final validation

**Features**:
- [AI Agent] Create E2E testing scenario definitions document (`docs/e2e-testing-scenarios.md`)
- [AI Agent] Create `README.md` skeleton with project overview, setup instructions, and usage outline
- [AI Agent] Create agent runbook skeleton (`docs/autopilot-runbook-dispatch.md`) for AI agent application execution
- [AI Agent] Run full validation suite to confirm all Phase 1 acceptance criteria are met
- [AI Agent] Create phase implementation context document (`docs/implementation-context-phase-1.md`)

**Description**:
This component documents the end-to-end testing scenarios that will drive validation throughout all subsequent phases, creates the `README.md` that serves as the project's external documentation, and sets up the agent runbook skeleton for AI agent-driven application running. It concludes with a full validation pass confirming all Phase 1 acceptance criteria — editable install, quality tools, CI configuration, and documentation — are satisfied.

**Acceptance Criteria**:
- [ ] `docs/e2e-testing-scenarios.md` exists with all five E2E scenarios documented (from the phase plan's cross-cutting concerns)
- [ ] Each E2E scenario has: description, preconditions, step-by-step instructions, expected results, pass/fail criteria
- [ ] `README.md` exists with project overview, prerequisites, setup instructions, usage outline, and links to documentation
- [ ] `docs/autopilot-runbook-dispatch.md` exists with a skeleton structure for AI agent application execution
- [ ] Full validation passes: `pip install -e .`, `pytest`, `black --check`, `isort --check-only`, `python scripts/evals.py`
- [ ] `docs/implementation-context-phase-1.md` created with Phase 1 summary

**Technical Details**:
- **Files to Create/Modify**:
  - `docs/e2e-testing-scenarios.md`
  - `README.md`
  - `docs/autopilot-runbook-dispatch.md`
  - `docs/implementation-context-phase-1.md`
- **Key Functions/Classes**: None — documentation only
- **Human/AI Agent**: AI Agent creates all documentation; AI Agent runs validation suite
- **Dependencies**: All prior components (1.1, 1.2, 1.3)

**Detailed Implementation Requirements**:
- **File 1: `docs/e2e-testing-scenarios.md`**: Document all five E2E testing scenarios from the phase plan's cross-cutting concerns section: (1) Configure & dispatch — configure executor, link project, generate actions, dispatch, webhook, mark complete; (2) Load & run full phase — load saved project, run all actions for a phase sequentially; (3) Debug action workflow — insert debug action, edit payload, dispatch, complete; (4) LLM payload generation — enable LLM toggle, generate payload, review, edit, dispatch; (5) Cross-device access — launch on macOS, access from iPhone Safari, verify data sync. Each scenario should include: a unique ID (E2E-001 through E2E-005), description, preconditions, step-by-step actions, expected results, pass/fail criteria, and which phases the scenario becomes executable (e.g., E2E-001 is fully testable after Phase 4). Include a summary table mapping scenarios to the earliest phase they can be validated.
- **File 2: `README.md`**: Create the project README with sections: Project Name & Description (Dispatch — local-first desktop application for AI agent orchestration), Prerequisites (Python 3.13+, macOS, OneDrive for cross-device sync), Quick Start (clone, venv, install, configure, run), Configuration (executor setup, secrets, action type defaults), Usage (link project, dispatch actions, monitor results), Architecture (link to solution design), Documentation (links to all docs), License. Keep it concise — this is a skeleton that will be expanded in Phase 7. Reference `docs/solution-design.md` and `docs/brief.md` for detailed context.
- **File 3: `docs/autopilot-runbook-dispatch.md`**: Create a skeleton runbook for AI agents to run the Dispatch application and execute E2E tests. Sections: Overview, Prerequisites, Starting the Application (`python -m app.src.main`), Running Tests (`pytest -q --cov=app/src`), Running Evals (`python scripts/evals.py`), E2E Test Execution (reference `docs/e2e-testing-scenarios.md`), Troubleshooting. This will be fleshed out as the application is built.
- **File 4: `docs/implementation-context-phase-1.md`**: Running log of implemented components in Phase 1. For each component: component ID, name, status (completed/in-progress), key files created or modified, notable decisions or deviations. Maximum 50 lines per component entry.

**Test Requirements**:
- [ ] `pip install -e .` succeeds without errors
- [ ] `pytest` runs and exits cleanly
- [ ] `black --check app/src/` passes
- [ ] `isort --check-only app/src/` passes
- [ ] `python scripts/evals.py` passes
- [ ] All documentation files exist and are well-formed Markdown

**Definition of Done**:
- [ ] All documentation created
- [ ] Full validation suite passes
- [ ] No regression in existing functionality
- [ ] Core application package installs correctly
- [ ] Documentation created: Component Overview (`docs/components/phase-1-component-1-4-overview.md`). Maximum 100 lines of markdown.
- [ ] Documentation updated/created: Phase Component Overview (`docs/implementation-context-phase-1.md`). Maximum 50 lines of markdown per component.

**Notes**:
The E2E scenarios are critical — they define the test plan for the entire project and will be referenced in every subsequent phase's final component. Write them with enough detail that an AI agent can execute them programmatically where possible (Phases 4+). The `README.md` is intentionally a skeleton; Phase 7 will flesh it out with complete setup instructions and a usage walkthrough. The implementation context document should be started here and will be updated by every subsequent component in Phase 1 (Components 1.1–1.3 entries should be added retroactively during this component).

---

## Phase Acceptance Criteria

- [ ] `pip install -e .` succeeds in the virtual environment
- [ ] `pytest` runs (even with zero tests) and exits cleanly
- [ ] `black --check app/src/` and `isort --check-only app/src/` pass
- [ ] `python scripts/evals.py` passes
- [ ] GitHub Actions CI pipeline runs successfully on push
- [ ] `.env/.env.example` includes all required environment variable placeholders
- [ ] E2E testing scenarios are documented with clear pass/fail criteria
- [ ] Repository folder structure matches the solution design
- [ ] All `__init__.py` files exist for the package hierarchy
- [ ] `README.md` exists with project overview and setup instructions
- [ ] Agent runbook skeleton exists for AI agent application execution
- [ ] `docs/implementation-context-phase-1.md` documents all implemented components

---

## Cross-Cutting Concerns

### Testing Strategy
- **E2E Testing Scenarios**: Defined in `docs/e2e-testing-scenarios.md` — not yet executable (no application logic). These drive validation in Phases 4–7.
- **Unit Testing**: pytest configured with `conftest.py` skeleton. No unit tests in this phase (no application code).
- **Integration Testing**: Not applicable in this phase.

### Documentation Requirements
- **Developer Context Documentation**: `docs/implementation-context-phase-1.md`, `docs/components/phase-1-component-1-X-overview.md` per component
- **Agent Runbook**: `docs/autopilot-runbook-dispatch.md` skeleton created
- **Code Documentation**: Not applicable in this phase (no application code)
- **API Documentation**: Not applicable in this phase
- **Architecture Decision Records**: No new ADRs in this phase (decisions documented in solution design)
- **User Documentation**: `README.md` skeleton created
- **Deployment Documentation**: Setup instructions in `README.md`
