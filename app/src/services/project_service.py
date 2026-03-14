"""Project management service for repository linking and scanning."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.src.config.settings import Settings
from app.src.models import PhaseData, Project
from app.src.services.github_client import (
    GitHubAuthError,
    GitHubClient,
    GitHubFileEntry,
    GitHubNotFoundError,
)

_LOGGER = logging.getLogger(__name__)
_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_PHASE_PROGRESS_PATH = "docs/phase-progress.json"
_AGENT_DIRECTORIES: tuple[str, str] = (".claude/agents/", ".github/agents/")
_REQUIRED_PHASE_FIELDS = ("phaseId", "phaseName", "components")


class ProjectLinkError(Exception):
    """Raised when linking a project repository fails."""


class ProjectService:
    """Service for linking a GitHub repository into a Dispatch project."""

    def __init__(self, settings: Settings, github_client: GitHubClient) -> None:
        """Initialise the project service dependencies.

        Args:
            settings: Application settings provider.
            github_client: GitHub API client used for repository scanning.
        """

        self._settings = settings
        self._github_client = github_client

    def link_project(self, repository: str, token_env_key: str) -> Project:
        """Link and scan a repository into a populated project model.

        Args:
            repository: Repository identifier in owner/repo format.
            token_env_key: Environment variable key that stores the GitHub token.

        Returns:
            A fully populated ``Project`` instance ready for persistence.

        Raises:
            ProjectLinkError: If validation, scanning, or parsing fails.
        """

        owner, repo = self._validate_repository(repository)
        token_key = token_env_key.strip()
        if not token_key:
            raise ProjectLinkError("token_env_key must be a non-empty environment key.")

        if self._settings.get_secret(token_key) is None:
            raise ProjectLinkError(
                f"GitHub token environment key '{token_key}' is not configured."
            )

        raw_phase_progress = self._scan_phase_progress(owner, repo)
        phases = self._parse_phase_progress(raw_phase_progress)
        agent_files = self._discover_agent_files(owner, repo)
        component_count = sum(len(phase.components) for phase in phases)
        now_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        project = Project(
            project_id=str(uuid.uuid4()),
            project_name=repository,
            repository=repository,
            github_token_env_key=token_key,
            phase_progress=raw_phase_progress,
            phases=phases,
            agent_files=agent_files,
            actions=[],
            created_at=now_timestamp,
            updated_at=now_timestamp,
        )
        _LOGGER.info(
            "Linked project %s: %d phases, %d components, %d agent files found",
            repository,
            len(phases),
            component_count,
            len(agent_files),
        )
        return project

    def _validate_repository(self, repository: str) -> tuple[str, str]:
        """Validate repository format and return owner/repo parts.

        Args:
            repository: Repository string to validate.

        Returns:
            Tuple of owner and repository name.

        Raises:
            ProjectLinkError: If the repository is not in owner/repo format.
        """

        repository_value = repository.strip()
        if not _REPOSITORY_PATTERN.match(repository_value):
            raise ProjectLinkError(
                "Repository must match owner/repo format using only letters, "
                "numbers, dot, underscore, or hyphen."
            )
        owner, repo = repository_value.split("/", maxsplit=1)
        return owner, repo

    def _scan_phase_progress(self, owner: str, repo: str) -> dict[str, Any]:
        """Retrieve and parse docs/phase-progress.json for a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Parsed JSON dictionary from the phase-progress file.

        Raises:
            ProjectLinkError: If the file is missing, unauthorized, or invalid JSON.
        """

        repository = f"{owner}/{repo}"
        try:
            raw_content = self._github_client.get_file_contents(
                owner, repo, _PHASE_PROGRESS_PATH
            )
        except GitHubNotFoundError as exc:
            raise ProjectLinkError(
                "phase-progress.json not found at docs/phase-progress.json in "
                f"{repository}. This file is required."
            ) from exc
        except GitHubAuthError as exc:
            raise ProjectLinkError(
                f"Authentication failed for {repository}. Check your GitHub token."
            ) from exc

        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ProjectLinkError(
                f"Invalid JSON in docs/phase-progress.json for {repository}: {exc.msg}"
            ) from exc
        if not isinstance(payload, dict):
            raise ProjectLinkError(
                "docs/phase-progress.json must contain a top-level JSON object."
            )
        return payload

    def _parse_phase_progress(self, raw_data: dict[str, Any]) -> list[PhaseData]:
        """Parse raw phase-progress data into ``PhaseData`` models.

        Args:
            raw_data: Parsed JSON object loaded from phase-progress file.

        Returns:
            Parsed list of ``PhaseData`` instances.

        Raises:
            ProjectLinkError: If required fields or model validation fail.
        """

        phases_value = raw_data.get("phases")
        if not isinstance(phases_value, list):
            raise ProjectLinkError("phase-progress.json must include a 'phases' array.")

        phases: list[PhaseData] = []
        for index, phase_entry in enumerate(phases_value, start=1):
            if not isinstance(phase_entry, dict):
                raise ProjectLinkError(
                    f"Phase at index {index} must be a JSON object, got "
                    f"{type(phase_entry).__name__}."
                )

            missing_phase_fields = [
                field for field in _REQUIRED_PHASE_FIELDS if field not in phase_entry
            ]
            if missing_phase_fields:
                missing_fields = ", ".join(missing_phase_fields)
                raise ProjectLinkError(
                    f"Phase at index {index} is missing required fields: {missing_fields}."
                )

            components = phase_entry.get("components")
            if not isinstance(components, list):
                raise ProjectLinkError(
                    f"Phase at index {index} must include a 'components' array."
                )
            for component_index, component in enumerate(components, start=1):
                if not isinstance(component, dict):
                    raise ProjectLinkError(
                        f"Component at phase index {index}, component index "
                        f"{component_index} must be a JSON object."
                    )
                required_component_fields = (
                    "componentId",
                    "componentName",
                    "owner",
                    "priority",
                    "estimatedEffort",
                    "status",
                )
                missing_component_fields = [
                    field
                    for field in required_component_fields
                    if field not in component
                ]
                if missing_component_fields:
                    missing_fields = ", ".join(missing_component_fields)
                    raise ProjectLinkError(
                        f"Component at phase index {index}, component index "
                        f"{component_index} is missing required fields: {missing_fields}."
                    )

            try:
                phases.append(PhaseData.model_validate(phase_entry))
            except ValidationError as exc:
                raise ProjectLinkError(
                    f"Invalid phase data at index {index}: {exc}"
                ) from exc
        return phases

    def _discover_agent_files(self, owner: str, repo: str) -> list[str]:
        """Discover agent files from standard repository directories.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Flattened list of file paths from supported agent directories.
        """

        discovered_files: list[str] = []
        for directory in _AGENT_DIRECTORIES:
            entries = self._github_client.list_directory(owner, repo, directory)
            discovered_files.extend(self._file_paths(entries))
        return discovered_files

    @staticmethod
    def _file_paths(entries: list[GitHubFileEntry]) -> list[str]:
        """Return file paths only from directory entries."""

        return [entry.path for entry in entries if entry.type == "file" and entry.path]
