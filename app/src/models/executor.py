"""Executor-domain model definitions."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, field_validator

_WEBHOOK_CALLBACK_PATH = "/webhook/callback"


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
    def _normalise_webhook_url(cls, value: object) -> object:
        """Normalise blank webhook URLs and root-only URLs for Dispatch callbacks."""

        if value is None:
            return None
        if not isinstance(value, str):
            return value

        cleaned = value.strip()
        if cleaned == "":
            return None

        parsed = urlsplit(cleaned)
        if (
            parsed.scheme in {"http", "https"}
            and parsed.netloc
            and parsed.path
            in {
                "",
                "/",
            }
        ):
            return urlunsplit(
                (
                    parsed.scheme,
                    parsed.netloc,
                    _WEBHOOK_CALLBACK_PATH,
                    parsed.query,
                    parsed.fragment,
                )
            )

        return cleaned


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
