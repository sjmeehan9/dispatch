# Executor Configuration Guide

This guide explains how to configure an executor in Dispatch. The executor is the external service that receives dispatched action payloads and runs AI agent operations against your target repositories.

---

## Overview

Dispatch sends action payloads (implement, review, merge, test, document, debug) to a configured executor API. The default executor is **Autopilot**, which orchestrates GitHub Copilot agents via GitHub Actions workflows. You can point Dispatch at any executor that conforms to the dispatch protocol.

Configuration is managed through the **Configure Executor** screen in the UI (`/config/executor`), or by editing the bundled defaults in `app/config/defaults.yaml`.

---

## Configuration Fields

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| **Executor Name** | Yes | Human-readable name for the executor (used to derive the executor ID slug) | `Autopilot` |
| **API Endpoint URL** | Yes | Full URL of the executor's action dispatch endpoint. Must start with `http://` or `https://`. | `http://localhost:8000/agent/run` |
| **API Key Environment Variable** | Yes | Name of the environment variable that holds the executor API key. Dispatch reads this variable at dispatch time to authenticate requests. | `AUTOPILOT_API_KEY` |
| **Webhook URL** | No | Public URL where the executor sends result callbacks. If a root URL is provided (e.g., `https://abc123.ngrok-free.app`), Dispatch automatically appends `/webhook/callback`. | *(empty)* |
| **Use LLM for payload generation** | No | When enabled and an OpenAI API key is configured, Dispatch uses an LLM to generate context-aware `agent_instructions` before dispatch. Falls back to standard template interpolation if unavailable. | `false` |

### Executor ID

The executor ID is automatically derived from the Executor Name by converting it to a lowercase slug (e.g., `Autopilot` becomes `autopilot`, `My Custom Executor` becomes `my-custom-executor`). You do not set this directly.

---

## Setup Steps

### 1. Navigate to Configure Executor

From the initial screen (`/`), click **Configure Executor** or navigate directly to `/config/executor`.

### 2. Fill in the form

- **Executor Name** — enter the name of your executor (e.g., `Autopilot`).
- **API Endpoint URL** — enter the full dispatch endpoint URL.
- **API Key Environment Variable** — enter the environment variable name that holds your API key. You must also store the actual key value via the **Manage Secrets** screen or in `.env/.env.local`.
- **Webhook URL** — optionally enter a public callback URL. This is where the executor posts results when an action completes. If you use ngrok, enter the ngrok HTTPS URL here.
- **Use LLM for payload generation** — toggle on if you want AI-generated payload instructions. Requires an OpenAI API key configured in Manage Secrets.

### 3. Save

Click **Save**. Dispatch validates the configuration (URL format, required fields) and persists it as `executor.json` in the config directory (`~/.dispatch/config/` by default).

---

## How Configuration is Stored

- **Bundled defaults**: `app/config/defaults.yaml` contains the factory-default executor settings and action type templates. These are loaded when no saved configuration exists.
- **Persisted config**: Once saved through the UI, executor configuration is written to `<DISPATCH_DATA_DIR>/config/executor.json` as human-readable JSON. This file takes precedence over bundled defaults on subsequent loads.
- **Config directory**: Controlled by the `DISPATCH_DATA_DIR` environment variable (default: `~/.dispatch/`). The config subdirectory is created automatically.

---

## Webhook URL Behaviour

When a webhook URL is configured:

1. Dispatch includes it as `callback_url` in every dispatched payload.
2. The executor calls back to this URL with the run result when the action reaches a terminal state (success, failure, timeout).
3. Results appear in the **Webhook Response** panel on the main project screen when you click **Refresh**.

If you provide a root URL (e.g., `https://abc123.ngrok-free.app` or `https://abc123.ngrok-free.app/`), Dispatch normalises it to `https://abc123.ngrok-free.app/webhook/callback`.

### Local webhook testing with ngrok

```bash
# Start Dispatch
python -m app.src.main

# In a separate terminal, start ngrok
ngrok http 8080

# Copy the ngrok HTTPS URL and enter it as the Webhook URL in Configure Executor
```

---

## Authentication

Dispatch reads the API key from the environment variable named in **API Key Environment Variable** at dispatch time. Ensure the key is available:

- **Local development**: Store the key in `.env/.env.local` via the **Manage Secrets** screen or by editing the file directly.
- **GitHub Actions / CI**: Store the key as a repository secret or environment secret in the `copilot` environment.

The key is sent as an `X-API-Key` header with each dispatch request.

---

## Action Type Defaults

After configuring the executor, configure **Action Type Defaults** (`/config/action-types`). These define the payload template for each action type (Implement, Test, Review, Merge, Document, Debug) using `{{variable}}` placeholders that are resolved at dispatch time.

See the README for the full list of available template variables.

---

## Troubleshooting

| Problem | Likely Cause | Resolution |
|---------|-------------|------------|
| Save fails with URL validation error | Endpoint or webhook URL missing `http://` or `https://` prefix | Add the protocol prefix |
| Dispatch returns "API key not configured" | The environment variable named in the config is not set | Add the key via Manage Secrets or `.env/.env.local` |
| Dispatch returns connection error | Executor is not running or endpoint URL is wrong | Verify the executor is reachable at the configured URL |
| Dispatch returns 401/403 | API key is invalid or expired | Regenerate the key and update via Manage Secrets |
| Webhook results not appearing | Webhook URL is not reachable from the executor | Ensure ngrok (or equivalent) is running and the URL is correct |
| LLM toggle is disabled | No OpenAI API key configured | Add `OPENAI_API_KEY` via Manage Secrets |
