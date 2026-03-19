# Dispatch — Agent Runbook

This runbook enables AI agents to operate and test the Dispatch application autonomously. All commands are exact; copy-paste and execute in order.

---

## 1. Starting the Application

```bash
source .venv/bin/activate
set -o allexport; source .env/.env.local; set +o allexport
python -m app.src.main
```

Verify the application is running:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080
# Expected: 200
```

The UI is now available at `http://localhost:8080`.

---

## 2. Running Tests

### Full test suite with coverage

```bash
source .venv/bin/activate
pytest -q --cov=app/src --cov-report=term-missing
```

### E2E tests only (mocked services)

```bash
pytest tests/e2e/ -q -k "not requires_autopilot"
```

### E2E tests with live Autopilot executor

Requires a running Autopilot service and interactive confirmation:

```bash
pytest tests/e2e/ -q --autopilot-confirm
```

The `--autopilot-confirm` flag triggers a session-scoped prompt asking the developer to confirm the Autopilot executor is available. Tests marked `requires_autopilot` auto-skip when the flag is omitted.

### Run a specific test file

```bash
pytest tests/test_action_generator.py -q
```

---

## 3. Quality Checks

### Code formatting

```bash
black --check app/src/ tests/
isort --check-only app/src/ tests/
```

To auto-fix formatting issues:

```bash
black app/src/ tests/
isort app/src/ tests/
```

### Project evals

```bash
python scripts/evals.py
```

Evals check for:
- Missing docstrings on public functions, classes, and modules
- TODO/FIXME placeholders in production code

Expected output: `0 violations`.

---

## 4. Common Operations

### Save and load project data

Project data is stored as JSON files in the directory specified by `DISPATCH_DATA_DIR` (default: `~/.dispatch/`). To inspect:

```bash
ls -la "${DISPATCH_DATA_DIR:-$HOME/.dispatch/}"
```

### View application logs

The application logs to stdout via Python's `logging` module. Logs are visible in the terminal where `python -m app.src.main` was started.

### Check webhook data

Poll for stored webhook data by run ID:

```bash
curl http://localhost:8080/webhook/poll/<run_id>
```

Returns `200` with the webhook payload if received, or `404` with `{"status": "pending"}` if not yet received.

### Reset application state

Clear all local project data:

```bash
rm -rf "${DISPATCH_DATA_DIR:-$HOME/.dispatch/}"/*
```

Restart the application to begin from a clean state.

---

## 5. Troubleshooting

| Problem | Cause | Resolution |
|---------|-------|------------|
| `Address already in use` on port 8080 | Another process is using the port | `lsof -i :8080` to find and stop the process |
| `ModuleNotFoundError: No module named 'app'` | Package not installed in editable mode | `pip install -e ".[dev]"` from the repo root |
| Missing environment variables | `.env/.env.local` not loaded | `set -o allexport; source .env/.env.local; set +o allexport` |
| GitHub API 401 Unauthorized | Invalid or expired `GITHUB_TOKEN` | Regenerate the token and update `.env/.env.local` |
| Executor 401 Unauthorized | Invalid `AUTOPILOT_API_KEY` | Verify the API key in `.env/.env.local` matches the Autopilot service |
| Executor connection refused | Autopilot service not running | Start the Autopilot service or verify `AUTOPILOT_API_ENDPOINT` URL |
| Webhook data not appearing | Webhook callback URL misconfigured | Verify `AUTOPILOT_WEBHOOK_URL` points to the Dispatch instance (e.g., `https://<ngrok-url>`) |
| OneDrive sync conflicts | Concurrent writes from multiple devices | Dispatch writes atomic JSON files; resolve by keeping the newer file |
| evals report violations | Docstrings missing or TODOs in code | Fix the reported files — evals list the exact file and line |
| Tests fail with import errors | Virtual environment not activated | `source .venv/bin/activate` before running pytest |
