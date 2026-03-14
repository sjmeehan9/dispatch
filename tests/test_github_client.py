"""Unit tests for GitHub API client service."""

from __future__ import annotations

import base64

import httpx
import pytest

from app.src.services.github_client import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubClient,
    GitHubFileEntry,
    GitHubNotFoundError,
    GitHubRateLimitError,
)


class _StubHttpxClient:
    """Simple httpx.Client stub that returns a predefined response sequence."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = responses
        self.request_calls: list[tuple[str, str]] = []
        self.closed = False

    def request(self, method: str, url: str) -> httpx.Response:
        self.request_calls.append((method, url))
        if not self._responses:
            raise AssertionError("No more stub responses configured.")
        return self._responses.pop(0)

    def close(self) -> None:
        self.closed = True


def _response(status_code: int, payload: object) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=payload)


def _response_with_headers(
    status_code: int, payload: object, headers: dict[str, str]
) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=payload, headers=headers)


def test_github_client_initializes_required_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    stub_client = _StubHttpxClient([])

    def _build_client(*, base_url: str, headers: dict[str, str], timeout: float):
        captured["base_url"] = base_url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return stub_client

    monkeypatch.setattr("app.src.services.github_client.httpx.Client", _build_client)

    GitHubClient(token="token-123")

    assert captured["base_url"] == "https://api.github.com"
    assert captured["headers"] == {
        "Authorization": "Bearer token-123",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    assert captured["timeout"] == 30.0


def test_get_file_contents_returns_decoded_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encoded = base64.b64encode("hello dispatch".encode("utf-8")).decode("utf-8")
    stub_client = _StubHttpxClient([_response(200, {"content": encoded})])
    monkeypatch.setattr(
        "app.src.services.github_client.httpx.Client", lambda **_: stub_client
    )

    client = GitHubClient(token="token-123")

    assert (
        client.get_file_contents("owner", "repo", "docs/phase-progress.json")
        == "hello dispatch"
    )
    assert stub_client.request_calls == [
        ("GET", "/repos/owner/repo/contents/docs/phase-progress.json")
    ]


def test_get_file_contents_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_client = _StubHttpxClient([_response(404, {"message": "Not Found"})])
    monkeypatch.setattr(
        "app.src.services.github_client.httpx.Client", lambda **_: stub_client
    )

    client = GitHubClient(token="token-123")

    with pytest.raises(GitHubNotFoundError):
        client.get_file_contents("owner", "repo", "missing.txt")


def test_get_file_contents_raises_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_client = _StubHttpxClient([_response(401, {"message": "Bad credentials"})])
    monkeypatch.setattr(
        "app.src.services.github_client.httpx.Client", lambda **_: stub_client
    )

    client = GitHubClient(token="token-123")

    with pytest.raises(GitHubAuthError):
        client.get_file_contents("owner", "repo", "docs/phase-progress.json")


def test_get_file_contents_raises_rate_limit_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """403 responses with exhausted rate headers should map to rate-limit errors."""
    stub_client = _StubHttpxClient(
        [
            _response_with_headers(
                403,
                {"message": "API rate limit exceeded"},
                {"x-ratelimit-remaining": "0"},
            )
        ]
    )
    monkeypatch.setattr(
        "app.src.services.github_client.httpx.Client", lambda **_: stub_client
    )

    client = GitHubClient(token="token-123")

    with pytest.raises(GitHubRateLimitError):
        client.get_file_contents("owner", "repo", "docs/phase-progress.json")


def test_get_file_contents_raises_auth_error_for_non_rate_limit_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """403 responses without rate-limit headers should be treated as auth failures."""
    stub_client = _StubHttpxClient([_response(403, {"message": "Forbidden"})])
    monkeypatch.setattr(
        "app.src.services.github_client.httpx.Client", lambda **_: stub_client
    )

    client = GitHubClient(token="token-123")

    with pytest.raises(GitHubAuthError):
        client.get_file_contents("owner", "repo", "docs/phase-progress.json")


def test_list_directory_returns_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_client = _StubHttpxClient(
        [
            _response(
                200,
                [
                    {
                        "name": "implement.agent.md",
                        "path": ".claude/agents/implement.agent.md",
                        "type": "file",
                        "size": 123,
                    },
                    {
                        "name": "nested",
                        "path": ".claude/agents/nested",
                        "type": "dir",
                        "size": 0,
                    },
                ],
            )
        ]
    )
    monkeypatch.setattr(
        "app.src.services.github_client.httpx.Client", lambda **_: stub_client
    )

    client = GitHubClient(token="token-123")
    entries = client.list_directory("owner", "repo", ".claude/agents/")

    assert entries == [
        GitHubFileEntry(
            name="implement.agent.md",
            path=".claude/agents/implement.agent.md",
            type="file",
            size=123,
        ),
        GitHubFileEntry(
            name="nested",
            path=".claude/agents/nested",
            type="dir",
            size=0,
        ),
    ]


def test_list_directory_returns_empty_list_on_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_client = _StubHttpxClient([_response(404, {"message": "Not Found"})])
    monkeypatch.setattr(
        "app.src.services.github_client.httpx.Client", lambda **_: stub_client
    )

    client = GitHubClient(token="token-123")

    assert client.list_directory("owner", "repo", ".github/agents/") == []


def test_check_file_exists_returns_true_or_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = base64.b64encode("exists".encode("utf-8")).decode("utf-8")
    stub_client = _StubHttpxClient(
        [
            _response(200, {"content": first}),
            _response(404, {"message": "Not Found"}),
        ]
    )
    monkeypatch.setattr(
        "app.src.services.github_client.httpx.Client", lambda **_: stub_client
    )

    client = GitHubClient(token="token-123")

    assert client.check_file_exists("owner", "repo", "docs/phase-progress.json") is True
    assert client.check_file_exists("owner", "repo", "docs/missing.json") is False


def test_request_retries_once_then_raises_on_5xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_client = _StubHttpxClient(
        [
            _response(500, {"message": "server error"}),
            _response(502, {"message": "bad gateway"}),
        ]
    )
    monkeypatch.setattr(
        "app.src.services.github_client.httpx.Client", lambda **_: stub_client
    )

    client = GitHubClient(token="token-123")

    with pytest.raises(GitHubAPIError):
        client.get_file_contents("owner", "repo", "docs/phase-progress.json")
    assert len(stub_client.request_calls) == 2
