"""Executor-domain model definitions."""

from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, field_validator


class ExecutorConfig(BaseModel):
    """Executor endpoint and authentication key-reference configuration."""

    model_config = ConfigDict(use_enum_values=True)

    executor_id: str
    executor_name: str
    api_endpoint: AnyHttpUrl
    api_key_env_key: str
    webhook_url: AnyHttpUrl | None = None
    use_llm: bool = False

    @field_validator("webhook_url", mode="before")
    @classmethod
    def _normalise_empty_webhook_url(cls, value: object) -> object:
        """Normalise blank webhook strings to None for optional URL validation."""

        if value == "":
            return None
        return value


class ActionTypeDefaults(BaseModel):
    """Default payload templates keyed by action type."""

    implement: dict[str, object]
    test: dict[str, object]
    review: dict[str, object]
    merge: dict[str, object]
    document: dict[str, object]
    debug: dict[str, object]


class ExecutorResponse(BaseModel):
    """Normalized executor API response metadata."""

    status_code: int
    message: str
    run_id: str | None = None
    raw_response: dict[str, object] | None = None
