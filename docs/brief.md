# Project Brief: Dispatch

## Overview

Dispatch is a local-first desktop application that orchestrates AI agent execution against software project deliverables. It reads a project's phase plan (`phase-progress.json`) from a linked GitHub repository, generates structured Execute Action items for each component, and dispatches them to a configurable external executor API (defaulting to the Autopilot service). The app runs on macOS and is accessible cross-device via OneDrive-stored application data, with a clean UI for managing projects, configuring executors, and monitoring agent run results.

## Problem Statement

Managing AI agent-driven software delivery across multiple phases and components requires manual orchestration — constructing payloads, sequencing actions, tracking progress, and interpreting results. This is repetitive, error-prone, and breaks flow. Dispatch solves this for a solo developer who uses AI agents (via Autopilot or similar services) to implement, test, review, and document phased project deliverables. It eliminates the manual overhead of dispatching agent runs by automating payload generation, sequencing, and result monitoring from a single UI.

## Goals & Success Metrics

- **Streamline AI agent orchestration**: Reduce the time from "decide what to build next" to "agent is executing" to under 30 seconds per action item
- **Cross-device accessibility**: Application and project data accessible from both macOS desktop and iPhone without cloud infrastructure
- **Modular executor support**: Default Autopilot integration works out of the box; other executors can be configured without code changes
- **Full phase lifecycle coverage**: Every phase can be driven from Implement through Test, Review, and Document without leaving the app
- **Open source reusability**: Repository is publicly cloneable/forkable; all user-specific data (secrets, project configs) is excluded from the repo

## Target Users

- **Solo Developer (Primary)**: A developer who uses AI coding agents to deliver phased software projects. Needs a fast, reliable way to dispatch agent runs against specific components, monitor results, and track phase progress across devices. Works from both macOS desktop and iPhone. Values simplicity, local-first operation, and full control over secrets and configuration.

## Functional Requirements

### Project Management
1. **Link New Project**: User provides a target GitHub repository and a GitHub token (project-scoped). The app scans the remote repo for `phase-progress.json` (required — cannot proceed without it) and loads agent files from `.claude/agents/` and `.github/agents/`
2. **Load Project**: Pre-configured projects are persisted in local app storage and can be loaded from the initial screen
3. **Save Project**: Project state can be saved from the main screen
4. **Project Data Portability**: Project data is stored in a manner accessible across all user devices (e.g., OneDrive-synced local storage), never pushed to the public repo

### Executor Configuration
5. **Configure Executor**: Users can configure which external executor API to use. The default executor is the Autopilot application (see `docs/autopilot-runbook.md`)
6. **Executor Modularity**: Executor handling is modular in the codebase — swapping or adding executors requires no structural changes
7. **Execute Action Item Type Defaults**: Each Execute Action item type (Implement, Test, Review, Document, Debug) has a configurable default payload template. These templates use "variables" that reference known input data such as `phase-progress.json` field locations and agent paths
8. **Executor and type configs required first**: Executor and Execute Action item type configurations must be set before a project can be created or loaded

### Execute Action Items
9. **Derive from phase-progress.json**: Execute Action items are generated from the loaded `phase-progress.json`. For each Phase: one Implement action per Component, followed by one Test action, one Review action, and one Document action for the Phase
10. **Debug action insertion**: Users can manually insert a Debug-type Execute Action item at any point in a Phase's action list
11. **Payload inheritance and editing**: Each Execute Action item inherits its payload from the corresponding type default. Individual payloads are editable from the left-side window
12. **Payload content**: Each payload includes the Execute Action item type, component reference (for Implement types), agent paths (if used), and other executor-dependent fields
13. **LLM-assisted payload generation** (optional): An OpenAI LLM call can be used to interpret input data and populate Execute Action item payloads from the type defaults and project context. The LLM API key and model are part of the secrets configuration
14. **Mark complete**: Users can click a button on each Execute Action item to mark it as completed

### Main Screen UI
15. **Header**: Project name displayed at the top, with Load Project and Save Project buttons
16. **Left panel**: Scrollable list of clickable Execute Action items. Clicking an item dispatches its payload to the configured executor API
17. **Right panel (top)**: Displays the executor API response code and response message after an action is dispatched
18. **Right panel (bottom)**: Displays webhook response code and webhook return payload message, visible only when a valid webhook URL is configured in the executor config
19. **Refresh button**: Available in the UI to update the display when webhook data has been returned

### Secrets & Authentication
20. **GitHub OAuth token**: The app links to the user's GitHub via their OAuth token. Tokens are entered in the UI and saved to local configuration
21. **Secrets UI**: Users can enter secrets/keys/tokens (GitHub token, LLM API key, etc.) into the UI, which saves them to a local config file
22. **Local environment file**: Secrets and keys are stored in a local environment file that is excluded from version control

## Non-Functional Requirements

- **Performance**: UI interactions must feel instant. Executor API calls should be dispatched within 1 second of clicking an Execute Action item. Payload generation (including optional LLM calls) should complete within 5 seconds
- **Security**: All secrets (GitHub tokens, API keys, LLM keys) are stored locally and never committed to the repository. `.env` files are gitignored. No secrets are logged or transmitted except to their intended API endpoint
- **Scalability**: The app needs to support a single user with multiple projects. No concurrent multi-user requirements
- **Availability**: Local-only — no uptime requirements beyond the user's own machine. Data portability across devices is handled via file sync (OneDrive)
- **Cross-Device Compatibility**: Must be fully usable on both macOS desktop and iPhone. Consider a simple desktop app format that can be stored on OneDrive and opened across devices

## Requirements Solution

Dispatch is a lightweight, local-first desktop application that bridges the gap between a project's phased delivery plan and the AI agent executor that performs the work. It reads the project's `phase-progress.json` from a linked GitHub repository, generates a sequenced list of Execute Action items (Implement per component, then Test, Review, Document per phase), and lets the user dispatch each action to a configurable executor API with a single click.

The executor configuration layer is modular: it defines the API endpoint, authentication, and payload structure for the target executor. The default executor is Autopilot — a REST API that dispatches GitHub Copilot agent runs via GitHub Actions workflows and returns results via webhook. Each Execute Action item type has a default payload template with variable placeholders (e.g., `{{repository}}`, `{{componentId}}`, `{{agentPaths}}`), and individual action payloads can be edited before dispatch.

Optionally, an OpenAI LLM can be called during payload generation to intelligently populate fields based on the project context, component details, and agent file contents — reducing manual editing for complex or nuanced instructions.

The UI is a split-panel layout: the left panel is a scrollable, clickable list of Execute Action items; the right panel shows executor API responses (status code + message) and, when configured, webhook return data. Users manage secrets, tokens, and executor config through the UI, with all sensitive data persisted to local files excluded from version control.

Project data is stored locally in a format that can be synced across devices via OneDrive, enabling cross-device access from macOS and iPhone without any cloud infrastructure.

## Application Logic

### Startup Flow
1. App opens to an initial screen with three options: **Load Project**, **Link New Project**, and **Configure Executor**
2. Executor and Execute Action item type configs must be set before project operations are available

### Link New Project Flow
1. User enters a target GitHub repository (owner/repo format)
2. User enters a GitHub token for the target repo (project-scoped)
3. App authenticates and scans the target repo for `phase-progress.json` — blocks with an error if not found
4. App scans `.claude/agents/` and `.github/agents/` directories in the target repo and loads all agent files
5. App generates Execute Action items from the loaded phase data
6. User is taken to the main screen for the newly linked project

### Configure Executor Flow
1. User selects or defines an executor (default: Autopilot)
2. User sets the executor API endpoint URL, authentication (API key), and optional webhook URL
3. User configures default payload templates for each Execute Action item type (Implement, Test, Review, Document, Debug)
4. Templates use variable placeholders referencing `phase-progress.json` fields and agent paths

### Execute Action Item Generation
For each Phase in `phase-progress.json`:
1. One **Implement** action per Component (ordered by componentId)
2. One **Test** action for the Phase
3. One **Review** action for the Phase
4. One **Document** action for the Phase
5. User can manually insert **Debug** actions at any position within a Phase

### Dispatch Flow
1. User clicks an Execute Action item in the left panel
2. App sends the item's payload to the configured executor API
3. Right panel displays the API response code and message
4. If a webhook URL is configured, the app listens for or polls for webhook responses
5. Webhook response code and payload message are displayed in the lower right panel
6. User clicks refresh if needed to update webhook data
7. User marks the Execute Action item as completed when satisfied

### Payload Structure
Each payload is determined by the executor configuration and includes:
- Execute Action item type (implement, test, review, document, debug)
- Repository and branch
- Agent instructions (generated or manually edited)
- Component reference (for Implement type)
- Agent paths (if applicable)
- Model selection
- Callback/webhook URL
- Timeout

Reference payload structure (Autopilot executor): see `docs/sample-payload.json`

## User Flows

### First-Time Setup
1. Open app → Initial screen
2. Configure Executor → Set Autopilot API endpoint, API key, webhook URL
3. Configure Execute Action item type defaults → Set payload templates for each type
4. Enter secrets (GitHub token, LLM key) via secrets UI
5. Link New Project → Enter repo and token → phase-progress.json loaded → Main screen

### Returning User — Existing Project
1. Open app → Initial screen
2. Load Project → Select from saved projects → Main screen

### Executing a Phase
1. Main screen → Left panel shows Execute Action items for all phases
2. Click first Implement action → Payload dispatched → Right panel shows response
3. Wait for webhook result (if configured) → Review result → Mark complete
4. Repeat for remaining Implement actions
5. Click Test action → dispatch → review → mark complete
6. Click Review action → dispatch → review → mark complete
7. Click Document action → dispatch → review → mark complete
8. Phase complete — proceed to next phase

### Inserting a Debug Action
1. Main screen → Left panel
2. User triggers "Add Debug" at a specific position in the phase list
3. Debug Execute Action item appears with inherited Debug-type default payload
4. User edits payload as needed → clicks to dispatch

## Constraints

- **Technical**: Must run entirely locally — no cloud infrastructure. Application format should support cross-device use via OneDrive (macOS desktop + iPhone). Must integrate with GitHub API for repo scanning. Default executor is Autopilot (REST API). Modular executor design is required
- **Timeline**: No hard deadline. Quality and completeness over speed
- **Budget**: Zero infrastructure cost — local only. Open source repo with no paid services required for core functionality
- **Team**: Solo developer. AI agents handle implementation. The app itself is the orchestration layer for this workflow

## Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Cross-device app format may be complex (macOS + iPhone) | High | Medium | Research lightweight cross-platform frameworks early; consider PWA or Electron-based approaches that can be synced via OneDrive |
| LLM payload generation produces inaccurate payloads | Medium | Medium | Make LLM-assisted generation optional; always allow manual editing; show generated payload before dispatch |
| Executor API changes break payload compatibility | Medium | Low | Modular executor config absorbs changes in templates; payload structure is user-editable |
| OneDrive sync conflicts with concurrent device access | Medium | Low | Design data storage with atomic file operations; advise single-device-at-a-time usage in docs |
| GitHub API rate limits during repo scanning | Low | Low | Cache loaded data locally; only re-scan on explicit user action |
| Webhook responses not received (network issues, executor down) | Medium | Medium | Display clear status indicators; provide refresh mechanism; don't block UI on webhook receipt |

## Assumptions

- The user has an active GitHub account and can generate personal access tokens for target repositories
- Target repositories contain a valid `phase-progress.json` file at the expected location
- The Autopilot executor service is running and reachable at a known URL when dispatching actions
- OneDrive (or equivalent file sync) is configured on all devices the user wants to access the app from
- The user has an OpenAI API key if they want to use LLM-assisted payload generation (optional feature)
- Agent files in target repos follow the `.claude/agents/` and `.github/agents/` directory conventions

## Out of Scope

- Multi-user support or collaboration features
- Cloud hosting or deployment of the Dispatch application itself
- Building or modifying the Autopilot executor service (Dispatch only integrates with it)
- Automatic execution of action items (all dispatches are user-initiated via click)
- Real-time sync between devices (relies on OneDrive file sync)
- Phase planning or phase-progress.json creation (Dispatch consumes this file, does not create it)
- CI/CD pipeline management for target repositories
- Direct code editing or IDE integration

## Success Criteria

- [ ] App launches locally on macOS and presents the initial screen with Load Project, Link New Project, and Configure Executor options
- [ ] Executor configuration can be set and persisted, with default payload templates for all five Execute Action item types
- [ ] A new project can be linked by providing a GitHub repo and token, with automatic scanning for `phase-progress.json` and agent files
- [ ] Execute Action items are correctly generated from `phase-progress.json` (Implement per component, then Test/Review/Document per phase)
- [ ] Clicking an Execute Action item dispatches the correct payload to the configured executor API and displays the response
- [ ] Webhook responses are displayed when a webhook URL is configured
- [ ] Individual Execute Action item payloads can be edited before dispatch
- [ ] Debug Execute Action items can be manually inserted at any position in a phase
- [ ] Users can mark Execute Action items as completed
- [ ] Secrets and tokens are stored locally and excluded from version control
- [ ] Project data can be saved and loaded across sessions
- [ ] Application data is portable across devices via file sync (OneDrive)

## Open Questions

- What specific cross-platform framework/format best supports macOS desktop + iPhone with OneDrive-based portability? (e.g., Electron, Tauri, PWA, SwiftUI with shared data)
- Should the webhook listener be a persistent local server or should the app poll the executor for updates?
- What is the expected format/location of the `phase-progress.json` within target repos — root or a specific directory?
- Should completed action items update the `phase-progress.json` in the target repo (write-back), or is completion tracking purely local?
- How should payload variable resolution work — simple string interpolation, or a more structured template engine?

## Approval

- [ ] Reviewed by: Sean Meehan
- [ ] Approved on: ___
