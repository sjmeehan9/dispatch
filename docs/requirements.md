# Dispatch

## Project Name
dispatch

## Goal
To organise, orchestrate and execute AI agent implementation of application deliverables in a simple, minimal way.

## Business Logic
 - This application will need the ability to be opened from a iPhone or Mac, and fully usable on both devices. Maybe a simple desktop app that can be stored on OneDrive for me to open across devices
 - This application will only be used by me on my devices, but the repo will be open source for others to clone/fork
 - The UI will open up to a screen with "load project" or "link new project" options
 - Project data will be stored in a manner that is available to all devices I'm using, not pushed to the public repo
 - The application will need to link to a user’s GitHub via their OAuth token. Should be able to enter secrets/keys/tokens into the UI to be saved in local config
 - The "link new project" workflow will ask the user for a target GitHub repository
 - Then ask for the GitHub token for the target repo. Tokens on this app's side can be project scoped
 - This app will then scan the target GitHub repository for the `phase-progress.json` file, that should be available in the target repository remote. Cannot proceed unless this file is found within the target repo. Load this file
 - Then the app will scan the target GitHub repository for Claude and GitHub copilot agent files in the `.claude/agents/` and `.github/agents/` folders respectively. Load all agents files
 - This concludes the new project setup workflow, the user can then be taken to the main screen for that project
 - Pre-configured projects can be found in this app's stored data and loaded via the "load project" workflow option
 - The main screen should have the project name at the top, alongside load project and save project buttons
 - The main screen body should be split into left and right sides
 - On the left side split of the main screen, there will be a scrollable window of clickable Execute Action items
 - The Execute Action items will derive from the `phase-progress.json` file previously loaded (details in the References section below). Clicking each item will execute an API call to the app's configured external executor application, that will handle the delivery of each Execute Action item
 - Each Execute Action item will be based on the Phase Component listed in the `phase-progress.json` file. For each Phase, there should be an Implement type Execute Action item per Component. After the list of all Component Implement Execute Action items, There will be just one Test type Execute Action item, then one Review type Execute Action item and finally one Document type Execute Action item to close out each Phase. The user can also manually insert a Debug type Execute Action item at any point in the Phase list
 - The app's configured external executor application should be whatever the user wants to choose, so be modular in the code when it comes to executor handling. The default configured executor will be the autopilot application, with the path to the autopilot runbook in the References section below
 - This means that there needs to be a "configure executor" workflow/button on the initial screen as well
 - The executor config determines the underlying payload structure that will allow each Execute Action item type to send the correct payload for its task in the left side window. It will determine the executor's API requirements and prefill draft payloads for each Execute Action item type using "variables" that point the known input data such as the `phase-progress.json` field locations and agent paths. The path to a sample autopilot application payload is in the References section below
 - If helpful, you should also build into this part of the application workflow a call to an OpenAI LLM to run the Execute Action item payload generation, from interpreting the input data and populating the Execute Action item type defaults, to filling in the Execute Action item payloads. The LLM key and model can be part of the secrets config
 - This also means that there needs to be a way to configure the default payload for each Execute Action item type, to allow for default payload edits that will populate for each Execute Action item
 - Therefore the executor and Execute Action item type configs need to be set before a project can be created or loaded
 - Each Execute Action item will have it's payload inhereted from the Execute Action item type config. Each Execute Action item payload should be editable from the left side window as well, opening up a way to modify the payload for that Execute Action item
 - This is not an exhaustive list, but each Execute Action item will send the Execute Action item type in the relevant section of the payload, as well as a reference to the Component for Implement types, and agent path if used. All depending on the executor
 - Once the Execute Action item is delivered to the executor API, the right side split of the main screen will display the API response code and the response message in separate sections
 - Also on the right side split of the main screen, below the API return information, will be sections for Webhook response code and Webhook return payload message. This will appear only if a valid webhook URL has been set in the executor config
 - Have a refresh button in the UI of required for the UI to update if the webhook has returned data
 - The user can click a button against the Execute Action item to indicate it has been completed

## Requirements
 - No cloud infrastructure, make this work entirely local
 - The solution design and phase plan need to enable all of the requirements, however keep the build as simple as possible
 - Secrets and keys are set in a local environment file that does not get pushed

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