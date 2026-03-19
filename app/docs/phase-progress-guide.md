# Phase Progress JSON Guide

This guide explains the structure, required fields, and usage of `phase-progress.json` — the machine-readable file that Dispatch reads to understand a project's phase plan and generate action items.

---

## Overview

`phase-progress.json` is the single source of truth for tracking which phases have been planned, what components each phase contains, and the status of each component. It lives at `docs/phase-progress.json` in the target repository and is created by the Tech Lead agent after the first phase is refined, then amended with each subsequent phase.

When you link a project in Dispatch, the application scans the target repository for this file, parses its structure, and generates sequenced action items (Implement, Review, Merge, Test, Document) for each component.

---

## File Location

```
<target-repository>/docs/phase-progress.json
```

Dispatch looks for the file at the path defined by `PHASE_PROGRESS_PATH` (`docs/phase-progress.json`).

---

## Complete Structure

```json
{
  "lastUpdated": "YYYY-MM-DD",
  "phases": [
    {
      "phaseId": 1,
      "phaseName": "Phase Name",
      "status": "refined",
      "componentBreakdownDoc": "docs/phase-1-component-breakdown.md",
      "components": [
        {
          "componentId": "1.1",
          "componentName": "Component Name",
          "owner": "AI Agent",
          "priority": "Must-have",
          "estimatedEffort": "2 hours",
          "status": "not-started"
        }
      ]
    }
  ]
}
```

---

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lastUpdated` | string | Yes | ISO 8601 date (`YYYY-MM-DD`) indicating when the file was last modified. |
| `phases` | array | Yes | Array of all phases that have been refined. Each entry represents one phase. |

---

## Phase Object Fields

Each entry in the `phases` array describes a single phase:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `phaseId` | integer | Yes | Numeric phase identifier matching the phase plan (e.g., `1`, `2`, `3`). Must be unique across all phases. |
| `phaseName` | string | Yes | Human-readable phase name (e.g., `"Project Bootstrap & Environment Setup"`). |
| `status` | string | Yes | Current phase status. Set to `"refined"` when produced by the Tech Lead agent. Downstream agents may update to `"in-progress"` or `"completed"`. |
| `componentBreakdownDoc` | string | Yes | Relative path to the full component breakdown markdown document (e.g., `"docs/phase-1-component-breakdown.md"`). |
| `components` | array | Yes | Array of components within the phase. |

### Phase Status Values

| Value | Meaning |
|-------|---------|
| `refined` | Phase has been broken down into components by the Tech Lead agent. |
| `in-progress` | At least one component is currently being implemented. |
| `completed` | All components in the phase are finished. |

---

## Component Object Fields

Each entry in a phase's `components` array describes a single implementable component:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `componentId` | string | Yes | Dotted identifier matching the phase and component number (e.g., `"1.1"`, `"2.3"`, `"4.10"`). Must be unique within the phase. |
| `componentName` | string | Yes | Descriptive name for the component (e.g., `"GitHub API Client"`, `"Executor Configuration Screen"`). |
| `owner` | string | Yes | Who is responsible for implementing this component. Either `"Human"` or `"AI Agent"`. |
| `priority` | string | Yes | Component priority level: `"Must-have"`, `"Should-have"`, or `"Nice-to-have"`. |
| `estimatedEffort` | string | Yes | Estimated implementation time (e.g., `"1 hour"`, `"2 hours"`, `"3 hours"`). Components should be sized between 1–3 hours. |
| `status` | string | Yes | Current component status. Set to `"not-started"` when first created. |

### Component Status Values

| Value | Meaning |
|-------|---------|
| `not-started` | Component has not been started. |
| `in-progress` | Component is currently being implemented. |
| `completed` | Component implementation is finished. |

### Owner Values

| Value | Meaning |
|-------|---------|
| `Human` | Requires manual human intervention (e.g., environment setup, account configuration, cross-device testing). |
| `AI Agent` | Can be implemented autonomously by an AI agent. |

### Priority Values

| Value | Meaning |
|-------|---------|
| `Must-have` | Essential for the phase to be considered complete. |
| `Should-have` | Important but the phase can function without it. |
| `Nice-to-have` | Optional enhancement. |

---

## How Dispatch Uses This File

1. **Project linking**: When you link a new project, Dispatch fetches `docs/phase-progress.json` from the target repository via the GitHub API.
2. **Phase parsing**: Each phase entry becomes a `PhaseData` object with its components as `ComponentData` objects.
3. **Action generation**: For each component, Dispatch generates a triplet of actions: **Implement → Review → Merge**. Phase-level **Test** and **Document** actions are appended after all component actions.
4. **Payload resolution**: When dispatching an action, template placeholders like `{{phase_id}}`, `{{component_id}}`, and `{{component_name}}` are resolved from the parsed phase-progress data.
5. **Status display**: Component and phase statuses are reflected in the UI's action cards and progress indicators.

---

## Example

A minimal valid file with one phase and two components:

```json
{
  "lastUpdated": "2026-03-19",
  "phases": [
    {
      "phaseId": 1,
      "phaseName": "Project Bootstrap & Environment Setup",
      "status": "refined",
      "componentBreakdownDoc": "docs/phase-1-component-breakdown.md",
      "components": [
        {
          "componentId": "1.1",
          "componentName": "Environment & Repository Initialisation",
          "owner": "Human",
          "priority": "Must-have",
          "estimatedEffort": "1 hour",
          "status": "not-started"
        },
        {
          "componentId": "1.2",
          "componentName": "Repository Structure & Package Configuration",
          "owner": "AI Agent",
          "priority": "Must-have",
          "estimatedEffort": "2 hours",
          "status": "not-started"
        }
      ]
    }
  ]
}
```

---

## Validation Rules

- The file must be valid JSON.
- `lastUpdated` must be a valid ISO 8601 date string.
- `phases` must be a non-empty array.
- Each phase must have a unique `phaseId`.
- Each component must have a unique `componentId` within its phase.
- All required fields in the tables above must be present and non-empty.
- `componentBreakdownDoc` should point to an existing markdown file in the repository.

---

## Lifecycle

1. **Created**: The Tech Lead agent creates `phase-progress.json` after refining the first phase from the phase plan.
2. **Amended**: Each subsequent phase refinement adds a new entry to the `phases` array. Previous phase entries are never removed or overwritten.
3. **Updated**: Implementation agents update `status` fields as components move through `not-started` → `in-progress` → `completed`.
4. **Consumed**: Dispatch reads the file when linking a project and uses it to generate and display action items.
