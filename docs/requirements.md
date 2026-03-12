# Requirements

## Project Name
dispatch

## Goal
To organise, orchestrate and execute AI agent implementation of application deliverables in a simple, minimal way.

## Business Logic
 - This application will ideally be entirely desktop based, a working UI I can open from a location on OneDrive via my phone or Mac, usable on both devices. It’s ok if this has to be a website hosted on AWS Amplify
 - This application will only be used by me on my device, but the repo will be open source for others to clone/fork
 - The UI will open up to a screen with "load project" or "link new project" options
 - Project data will be stored in a manner that is available to all devices I'm using, not pushed to the public repo
 - The application will need to link to a user’s GitHub via their OAuth token. Should be able to enter tokens in the UI
 - The "link new project" workflow will ask the user for a target GitHub repository
 - Then ask for the GitHub token for the target repo. Tokens on this app's side can be project scoped
 - This app will then scan the app for the `phase-progress.json` file within the target GitHub repo. Cannot proceed unless this file is found within the target repo. Load this file
 - Then the app will scan for Claude and GitHub copilot agent files in the `.claude/agents/` and `.github/agents/` folders respectively. Load all agents files
 - This concludes the new project setup workflow, the user can then be taken to the main screen for that project
 - Pre-configured projects can be found in this app's stored data and loaded via the "load project" workflow option
 - The main screen should have the project name at the top, alongside load project and save project buttons
 - The main screen body should be split into left and right sides
 - On the left side split of the main screen, there will be a scrollable window of clickable Execute Action items
 - The Execute Action items will derive from the `phase-progress.json` file previously loaded (details in the References section below). Clicking each item will execute an API call to the app's configured external executor application, that will handle the delivery of each Execute Action item
 - Each Execute Action item will be based on the Phase Component listed in the `phase-progress.json` file. For each Phase, there should be an Implement type Execute Action item per Component. After the list of all Component Implement Execute Action items, There will be a Test type Execute Action item, then a Review type Execute Action item and finally a Document type Execute Action item to close out each Phase. The user can also manually insert a Debug type Execute Action item at any point in the Phase list
 - The app's configured external executor application should be whatever the user wants to choose, so be modular in the code. The default configured executor will be the autopilot application, with the path to the autopilot runbook in the References section below
 - This means that there needs to be a "configure executor" workflow/button on the initial screen as well
 - The executor config determines the underlying payload structure that will allow each Execute Action item type to send the correct payload for it's task in the left side window. The path to a sample autopilot application payload isin the References section below
 - This also means that there needs to be a way to configure the payload for each Execute Action item type
 - Each Execute Action item will have it's payload inhereted from the Execute Action item type config. Each Execute Action item payload should be editable from the left side window as well, opening up a way to modify the payload for that Execute Action item
 - Each Execute Action item will send the Execute Action item type in the relevant section of the payload (depending on the executor), as well as a reference to the Component for Implement types

## Requirements
 - If any AWS infrastructure needs to be created, use the AWS CDK (Python)

## References

### Default Executor
See `docs/autopilot-runbook` for information about how to configure the autopilot app as the default executor for this dispatch application

### Sample Autopilot Payload
See `docs/sample-payload.json`

### phase-progress.json

**JSON structure:**

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
          "owner": "Human | AI Agent",
          "priority": "Must-have | Should-have | Nice-to-have",
          "estimatedEffort": "1-3 hours",
          "status": "not-started"
        }
      ]
    }
  ]
}
```

**Field definitions:**
- `lastUpdated`: The date this file was last modified (ISO 8601 date).
- `phases[]`: Array of all phases that have been refined so far.
- `phaseId`: Numeric phase identifier matching the phase plan.
- `phaseName`: Human-readable phase name.
- `status`: Always `"refined"` when produced by this agent (downstream agents may update to `"in-progress"` or `"completed"`).
- `componentBreakdownDoc`: Relative path to the full component breakdown markdown document.
- `components[]`: Array of components within the phase.
- `componentId`: Dotted identifier (e.g., `"1.1"`, `"2.3"`).
- `componentName`: Descriptive name matching the component breakdown document.
- `owner`: Who is responsible — `"Human"` or `"AI Agent"`.
- `priority`: Component priority level.
- `estimatedEffort`: Estimated implementation time.
- `status`: Always `"not-started"` when first created (downstream agents update this).