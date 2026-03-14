"""Project-domain model definitions."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.src.config.constants import REPOSITORY_PATTERN


class ActionType(StrEnum):
    """Supported execute action types."""

    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"
    DOCUMENT = "document"
    DEBUG = "debug"


class ActionStatus(StrEnum):
    """Supported lifecycle states for an action item."""

    NOT_STARTED = "not_started"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"


class ComponentData(BaseModel):
    """Structured component information loaded from phase-progress data."""

    model_config = ConfigDict(populate_by_name=True)

    component_id: str = Field(alias="componentId")
    component_name: str = Field(alias="componentName")
    owner: str
    priority: str
    estimated_effort: str = Field(alias="estimatedEffort")
    status: str


class PhaseData(BaseModel):
    """Structured phase information loaded from phase-progress data."""

    model_config = ConfigDict(populate_by_name=True)

    phase_id: int = Field(alias="phaseId")
    phase_name: str = Field(alias="phaseName")
    status: str
    component_breakdown_doc: str = Field(alias="componentBreakdownDoc")
    components: list[ComponentData] = Field(default_factory=list)


class Action(BaseModel):
    """A generated execute action item for a project phase/component."""

    model_config = ConfigDict(use_enum_values=True)

    action_id: str
    phase_id: int
    component_id: str | None = None
    action_type: ActionType
    payload: dict[str, object] = Field(default_factory=dict)
    status: ActionStatus = ActionStatus.NOT_STARTED
    executor_response: dict[str, object] | None = None
    webhook_response: dict[str, object] | None = None


class Project(BaseModel):
    """Top-level persisted project state."""

    model_config = ConfigDict(populate_by_name=True)

    project_id: str
    project_name: str
    repository: str
    github_token_env_key: str
    phase_progress: dict[str, object]
    phases: list[PhaseData] = Field(default_factory=list)
    agent_files: list[str] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    created_at: str
    updated_at: str

    @model_validator(mode="after")
    def validate_repository(self) -> Project:
        """Validate repository format as owner/repo."""

        if not REPOSITORY_PATTERN.match(self.repository):
            raise ValueError(
                "repository must match the owner/repo format (for example, 'org/repo')."
            )
        return self
