"""Configuration constants for Dispatch."""

from __future__ import annotations

import re

DEFAULT_DATA_DIR = "~/.dispatch/"
PROJECTS_DIR_NAME = "projects"
CONFIG_DIR_NAME = "config"
EXECUTOR_CONFIG_FILENAME = "executor.json"
ACTION_DEFAULTS_FILENAME = "action-type-defaults.json"
DEFAULTS_YAML_FILENAME = "defaults.yaml"
ENV_FILE_NAME = ".env.local"
ENV_DIR_NAME = ".env"

PHASE_PROGRESS_PATH = "docs/phase-progress.json"
CLAUDE_AGENTS_PATH = ".claude/agents/"
GITHUB_AGENTS_PATH = ".github/agents/"

REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
