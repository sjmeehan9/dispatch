"""Executor-domain model definitions."""

from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel, ConfigDict


class ExecutorConfig(BaseModel):
    """Executor endpoint and authentication key-reference configuration."""

    model_config = ConfigDict(use_enum_values=True)

    executor_id: str
    executor_name: str
    api_endpoint: AnyHttpUrl
    api_key_env_key: str
    webhook_url: AnyHttpUrl | None = None


class ActionTypeDefaults(BaseModel):
    """Default payload templates keyed by action type."""

    implement: dict[str, object]
    test: dict[str, object]
    review: dict[str, object]
    document: dict[str, object]
    debug: dict[str, object]


class ExecutorResponse(BaseModel):
    """Normalized executor API response metadata."""

    status_code: int
    message: str
    run_id: str | None = None
    raw_response: dict[str, object] | None = None
