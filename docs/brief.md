# Project Brief: Dispatch

## Overview

Dispatch is a cross-device application for organising, orchestrating, and executing AI agent implementation of application deliverables. It provides a visual interface to load phased project plans from GitHub repositories and dispatch execution tasks to a configurable external executor (defaulting to the Autopilot Copilot agent orchestration service), enabling a single developer to manage AI-driven software delivery from an iPhone or Mac.

## Problem Statement

Managing AI agent–driven software delivery across phased project plans is currently a manual, fragmented process. A developer working across multiple devices (iPhone, Mac) has no unified interface to view phase/component progress, configure execution payloads, dispatch work to an AI agent executor, and inspect results — all in one place. Dispatch solves this by providing a lightweight, cross-device UI that reads a project's `phase-progress.json`, generates executor-compatible payloads for each deliverable, and dispatches them with a single click. The target user is a solo developer orchestrating AI agents across multiple open-source repositories.

## Goals & Success Metrics

- **Unified orchestration UI**: A single screen to view all phases/components and dispatch execution — measured by the ability to load a project and execute an action item end-to-end from both iPhone and Mac.
- **Cross-device availability**: Fully usable on iPhone and Mac — measured by responsive layout functioning correctly on both Safari mobile and desktop browsers.
- **Modular executor integration**: Support any external executor, with Autopilot as the default — measured by the ability to swap executor configs without code changes.
- **Payload generation with optional LLM assistance**: Auto-populate Execute Action item payloads from project data, optionally enhanced by an OpenAI LLM — measured by correct payload generation for all five action item types (Implement, Test, Review, Document, Debug).
- **Minimal friction project setup**: Link a GitHub repo, load `phase-progress.json`, and be ready to dispatch in under two minutes.

## Target Users

- **Solo Developer (primary)**: A single developer who manages multiple GitHub repositories and uses AI agents (via Autopilot or similar) to implement, test, review, and document code. Needs a streamlined way to orchestrate phased delivery from any device without context-switching between terminals, GitHub Actions, and API clients. The repo will be open source for others to clone/fork, but the app is designed for single-user operation.

## Functional Requirements

1. **Cross-device access**: The application must be usable on both iPhone and Mac. Acceptable implementations include a responsive web app hosted on AWS Amplify or a simple desktop app stored on OneDrive.
2. **Initial screen with three workflows**: On launch, present "Load Project", "Link New Project", and "Configure Executor" options. Executor and Execute Action item type configs must be set before a project can be created or loaded.
3. **GitHub OAuth token entry**: Allow the user to enter and persist secrets/keys/tokens (including GitHub OAuth tokens) in a local configuration. Tokens can be project-scoped.
4. **Link New Project workflow**: Prompt for a target GitHub repository, then prompt for the GitHub token for that repo. Scan the remote repository for `phase-progress.json` — block project creation unless the file is found. Load the file. Scan for Claude agent files (`.claude/agents/`) and GitHub Copilot agent files (`.github/agents/`). Complete setup and navigate to the main screen.
5. **Load Project workflow**: List pre-configured projects from stored data and load the selected project's main screen.
6. **Main screen layout**: Project name at the top with "Load Project" and "Save Project" buttons. Body split into left and right panes.
7. **Left pane — Execute Action items**: A scrollable list of clickable Execute Action items derived from `phase-progress.json`. For each Phase: one Implement action per Component, then one Test action, one Review action, and one Document action to close out the Phase. The user can manually insert a Debug action at any point in a Phase's list.
8. **Execute Action item types**: Five types — Implement (per component), Test (per phase), Review (per phase), Document (per phase), and Debug (user-inserted at any point).
9. **Executor configuration**: A "Configure Executor" workflow/button on the initial screen. The executor config determines the underlying payload structure for each Execute Action item type. Default executor is the Autopilot application (see `docs/autopilot-runbook.md`). Executor handling must be modular to support swapping to other executors.
10. **Execute Action item type default payloads**: Configurable default payload templates for each action item type, using variables that reference known input data (e.g., `phase-progress.json` field locations, agent file paths). The defaults are editable and populate for each new Execute Action item.
11. **Per-item payload editing**: Each Execute Action item inherits its payload from the type-level default but can be individually edited from the left pane before dispatch.
12. **Optional LLM-assisted payload generation**: Optionally call an OpenAI LLM to interpret input data and populate/refine Execute Action item payloads. The LLM API key and model are part of the secrets config.
13. **Dispatch execution**: Clicking an Execute Action item sends its payload to the configured executor's API endpoint.
14. **Right pane — API response display**: After dispatch, display the API response code and response message in separate sections.
15. **Right pane — Webhook response display**: Below the API response, display Webhook response code and Webhook return payload message sections. These appear only if a valid webhook URL is set in the executor config.
16. **Refresh button**: A UI refresh button to update the display when webhook data has been returned.
17. **Completion marking**: A button against each Execute Action item to mark it as completed.
18. **Project data persistence**: Project data must be stored in a manner available across all user devices and must not be pushed to the public repo.

## Non-Functional Requirements

- **Performance**: UI interactions (load project, dispatch action) should feel instant (<500 ms perceived latency). Executor API calls are network-bound and their latency depends on the external service.
- **Security**: Secrets (GitHub tokens, API keys, LLM keys) must be stored in local environment files (`.env/.env.local`) that are never committed. OAuth tokens are project-scoped. No secrets in source control.
- **Scalability**: Single-user application. No multi-tenancy or concurrent user concerns. Must handle projects with dozens of phases and hundreds of components without UI degradation.
- **Availability**: Runs locally or on AWS Amplify. No uptime SLA, but the app should gracefully handle executor unavailability and network errors.
- **Compatibility**: Fully functional on Safari (iOS) and Safari/Chrome (macOS). Responsive layout for phone and desktop viewports.

## Requirements Solution

Dispatch will be built as a responsive web application, likely hosted on **AWS Amplify**, making it accessible from any device with a browser (satisfying the iPhone + Mac requirement). The frontend will provide a split-pane interface: the left pane lists Execute Action items derived from the loaded `phase-progress.json`, and the right pane displays execution results and webhook responses.

The backend handles GitHub repository scanning (to locate `phase-progress.json` and agent definition files), project data persistence (stored locally or in a device-synced location like OneDrive, never pushed to the public repo), and executor dispatch (sending configured payloads to the executor's REST API).

The executor layer is **modular by design**. An executor configuration defines the API endpoint, authentication, and payload templates for each Execute Action item type. The default executor is the **Autopilot** service (documented in `docs/autopilot-runbook.md`), which exposes a `POST /agent/run` endpoint accepting fields like `repository`, `branch`, `agent_instructions`, `model`, `role`, `agent_paths`, `callback_url`, and `timeout_minutes`. Swapping to a different executor requires only a new configuration — no code changes.

Payload generation uses a **variable interpolation** system: templates reference `phase-progress.json` fields (phase name, component ID/name, component breakdown doc path) and discovered agent paths. An optional **OpenAI LLM integration** can enhance payload generation by interpreting project context and producing richer agent instructions.

If any AWS infrastructure is needed (e.g., for Amplify hosting), it will be provisioned via **AWS CDK (Python)**, consistent with the project's Python-first tooling.

## Application Logic

### Core Data Flow

1. **Project Linking**: User provides a GitHub repo URL and token → App scans the repo for `phase-progress.json` → Loads phase/component data → Scans `.claude/agents/` and `.github/agents/` for agent definition files → Stores project config locally.

2. **Execute Action Item Generation**: From the loaded `phase-progress.json`, the app generates an ordered list of Execute Action items per phase:
   - One **Implement** item per component (in component order)
   - One **Test** item (per phase, after all Implement items)
   - One **Review** item (per phase, after Test)
   - One **Document** item (per phase, after Review)
   - User can insert **Debug** items at any position

3. **Payload Assembly**: Each Execute Action item's payload is assembled by:
   - Starting from the configured default template for that action type
   - Interpolating variables from `phase-progress.json` (component ID, name, phase name, etc.) and agent paths
   - Optionally refining via OpenAI LLM call
   - Allowing manual user edits

4. **Dispatch**: On click, the assembled payload is sent to the executor's API endpoint (e.g., `POST /agent/run` for Autopilot). The API response (status code + body) is displayed on the right pane.

5. **Webhook Handling**: If a webhook URL is configured, the executor will POST results back. The right pane displays the webhook response when received. A refresh button allows manual polling.

6. **Completion Tracking**: User marks items as completed via a button. This state is persisted with the project data.

### Key Components

- **Project Manager**: Handles project CRUD, GitHub repo scanning, and `phase-progress.json` parsing.
- **Executor Config Manager**: Manages executor endpoint, auth, and per-type payload templates.
- **Payload Generator**: Assembles payloads from templates + variables, with optional LLM enrichment.
- **Dispatch Service**: Sends payloads to the executor API and handles responses.
- **Webhook Listener**: Receives and displays async webhook callbacks from the executor.
- **Secrets Manager**: Manages local storage of tokens, API keys, and LLM keys in `.env/.env.local`.

## User Flows

### Flow 1: First-Time Setup

1. User opens Dispatch → Sees initial screen with "Load Project", "Link New Project", "Configure Executor".
2. User clicks "Configure Executor" → Selects or configures an executor (default: Autopilot) → Enters executor API URL, auth details, webhook URL (optional) → Configures default payload templates for each Execute Action item type (Implement, Test, Review, Document, Debug).
3. User enters secrets (GitHub token, LLM API key) into the secrets config UI → Saved to local `.env/.env.local`.

### Flow 2: Link New Project

1. User clicks "Link New Project" → Enters target GitHub repository (e.g., `owner/repo-name`).
2. Enters GitHub token for that repo (project-scoped).
3. App scans the remote repo for `phase-progress.json` → If not found, displays error and blocks. If found, loads the file.
4. App scans for agent files in `.claude/agents/` and `.github/agents/` → Loads all discovered agent definitions.
5. User is navigated to the main project screen.

### Flow 3: Load Existing Project

1. User clicks "Load Project" → Sees list of previously configured projects.
2. Selects a project → Main screen loads with that project's data.

### Flow 4: Dispatch an Execute Action Item

1. User is on the main screen → Left pane shows scrollable list of Execute Action items grouped by phase.
2. User clicks an Execute Action item (e.g., "Implement Component 1.1") → Can optionally edit the payload.
3. User confirms dispatch → Payload is sent to the executor API.
4. Right pane displays: API response code + API response message.
5. If webhook URL is set, right pane later shows: Webhook response code + Webhook payload.
6. User clicks refresh if needed to update webhook data.
7. Once satisfied, user clicks the completion button against the Execute Action item.

### Flow 5: Insert Debug Action

1. User is on the main screen → Identifies a point in a Phase's action list where debugging is needed.
2. User inserts a Debug Execute Action item at that position.
3. Edits the Debug item's payload as needed → Dispatches it like any other action item.

## Constraints

- **Technical**: The app must use AWS CDK (Python) for any AWS infrastructure provisioning. Secrets and keys are set in a local environment file that does not get pushed. Python 3.13+ for backend; TypeScript strict (Next.js 16+, Node.js 24+) for frontend. Must follow coding standards in `copilot.instructions.md`.
- **Platform**: Must work on iPhone (Safari mobile) and Mac (Safari/Chrome desktop). Hosting on AWS Amplify or as a OneDrive-stored desktop app are acceptable.
- **Executor dependency**: The default executor (Autopilot) is an external service with its own API contract (`POST /agent/run`). Dispatch depends on Autopilot being deployed and accessible, but must not hard-code this dependency.
- **Single user**: Designed for personal use by one developer. No multi-user auth, RBAC, or tenant isolation needed.
- **Open source**: The repository is public. No secrets, credentials, or personal project data may be committed.

## Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Executor API unavailability | High — cannot dispatch work | Medium | Display clear error messages; allow retry; support payload export for manual execution |
| Cross-device data sync issues | Medium — project state mismatch between devices | Medium | Use a cloud-synced storage mechanism (e.g., Amplify backend or OneDrive); document sync limitations |
| GitHub API rate limiting | Medium — repo scanning may fail | Low | Cache `phase-progress.json` and agent files locally after first scan; show rate limit warnings |
| LLM payload generation produces incorrect payloads | Medium — dispatched work may be wrong | Medium | Always show generated payloads for user review before dispatch; LLM is optional, not required |
| Webhook delivery failures from executor | Low — user misses async results | Medium | Provide refresh button and polling fallback via executor status endpoint |
| Secrets accidentally committed | High — credential exposure | Low | `.gitignore` excludes `.env/` directory; pre-commit checks; no secrets in source code |

## Assumptions

- The target GitHub repositories will contain a valid `phase-progress.json` file at the repository root or a known path, following the documented JSON structure.
- The Autopilot executor service (or an alternative) is deployed and accessible via REST API before Dispatch is used.
- The user has valid GitHub OAuth tokens with sufficient permissions (`repo` scope) for the target repositories.
- AWS Amplify is the preferred hosting platform (or alternatively, the app can be run as a local web server accessible across devices on the same network / via OneDrive).
- A single user will operate the application — no concurrent access or multi-user data isolation is required.
- Agent definition files in `.claude/agents/` and `.github/agents/` follow the Markdown + YAML frontmatter format documented in the Autopilot runbook.

## Out of Scope

- Multi-user authentication, authorization, or tenant isolation.
- Direct AI agent execution — Dispatch only orchestrates; actual agent execution is handled by the configured executor (e.g., Autopilot).
- Automated merging or PR management — these are executor responsibilities.
- Real-time streaming of agent execution logs (Dispatch shows API and webhook responses, not live logs).
- Mobile native app builds (iOS/Android) — a responsive web app is sufficient.
- Modifications to the Autopilot executor service itself.
- CI/CD pipeline setup for target repositories.

## Success Criteria

- [ ] A user can open Dispatch on both iPhone and Mac and interact with all features.
- [ ] A user can configure an executor (defaulting to Autopilot) and set per-type payload templates.
- [ ] A user can link a new GitHub repository, with `phase-progress.json` validation and agent file discovery.
- [ ] A user can load a previously configured project.
- [ ] Execute Action items are correctly generated from `phase-progress.json` (Implement per component, then Test, Review, Document per phase).
- [ ] A user can insert Debug Execute Action items at any position in a Phase's list.
- [ ] Payloads are correctly assembled from templates, variables, and optional LLM enrichment.
- [ ] A user can edit any Execute Action item's payload before dispatch.
- [ ] Dispatching an Execute Action item sends the correct payload to the executor API and displays the response.
- [ ] Webhook responses are displayed when a valid webhook URL is configured.
- [ ] A user can mark Execute Action items as completed.
- [ ] No secrets or project data are committed to the public repository.
- [ ] All infrastructure (if any) is provisioned via AWS CDK (Python).

## Open Questions

- What is the preferred storage mechanism for cross-device project data persistence — AWS Amplify backend (e.g., DynamoDB or S3), OneDrive file sync, or another approach?
- Should the app support offline mode (cached project data) or require network connectivity at all times?
- Is there a preferred UI framework (e.g., Next.js with React, plain HTML/CSS/JS) or should the solution design phase determine this?
- How should the app discover `phase-progress.json` — always at the repo root, or should the user specify the path?
- Should completed Execute Action item state be written back to the target repo's `phase-progress.json` (updating component statuses), or tracked only within Dispatch's local data?

## Approval

- [ ] Reviewed by: Project Owner
- [ ] Approved on: TBD
