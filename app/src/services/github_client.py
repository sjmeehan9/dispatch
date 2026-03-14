"""GitHub REST API client for repository scanning and file retrieval."""

from __future__ import annotations

import base64
import binascii
import logging
from dataclasses import dataclass

import httpx

_LOGGER = logging.getLogger(__name__)
_GITHUB_API_BASE_URL = "https://api.github.com"
_GITHUB_ACCEPT_HEADER = "application/vnd.github.v3+json"
_GITHUB_API_VERSION = "2022-11-28"
_DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class GitHubFileEntry:
    """Structured file or directory entry returned from GitHub contents API."""

    name: str
    path: str
    type: str
    size: int


class GitHubClientError(Exception):
    """Base exception for GitHub client failures."""


class GitHubAuthError(GitHubClientError):
    """Raised when GitHub authentication fails (401/403)."""


class GitHubNotFoundError(GitHubClientError):
    """Raised when a requested GitHub resource is not found (404)."""


class GitHubRateLimitError(GitHubClientError):
    """Raised when GitHub API rate limiting prevents request execution."""


class GitHubAPIError(GitHubClientError):
    """Raised for all non-auth, non-not-found GitHub API failures."""


class GitHubClient:
    """Synchronous GitHub API client for repo contents and directory scans."""

    def __init__(self, token: str) -> None:
        """Initialise the client with a GitHub token.

        Args:
            token: GitHub personal access token or GitHub app token.
        """

        if not token.strip():
            raise ValueError("GitHub token must be a non-empty string.")

        self._client = httpx.Client(
            base_url=_GITHUB_API_BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": _GITHUB_ACCEPT_HEADER,
                "X-GitHub-Api-Version": _GITHUB_API_VERSION,
            },
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )

    def get_file_contents(self, owner: str, repo: str, path: str) -> str:
        """Fetch and decode file contents from a GitHub repository.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.
            path: File path within the repository.

        Returns:
            Decoded UTF-8 file contents.

        Raises:
            GitHubNotFoundError: If the file path does not exist.
            GitHubAuthError: If token authentication/authorization fails.
            GitHubAPIError: If the API response is malformed or request fails.
        """

        endpoint = self._contents_endpoint(owner, repo, path)
        response = self._request("GET", endpoint)
        payload = response.json()
        if isinstance(payload, list):
            raise GitHubAPIError(
                f"Expected file contents for '{owner}/{repo}:{path}', got directory data."
            )

        encoded_content = payload.get("content")
        if not isinstance(encoded_content, str) or not encoded_content.strip():
            raise GitHubAPIError(
                f"GitHub contents response for '{owner}/{repo}:{path}' did not include file content."
            )

        try:
            return base64.b64decode(encoded_content).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise GitHubAPIError(
                f"Unable to decode base64 file content for '{owner}/{repo}:{path}'."
            ) from exc

    def list_directory(self, owner: str, repo: str, path: str) -> list[GitHubFileEntry]:
        """List file and directory entries for a repository path.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.
            path: Directory path within the repository.

        Returns:
            A list of GitHub file entries. Returns empty when directory is missing.
        """

        endpoint = self._contents_endpoint(owner, repo, path)
        try:
            response = self._request("GET", endpoint)
        except GitHubNotFoundError:
            return []

        payload = response.json()
        if not isinstance(payload, list):
            raise GitHubAPIError(
                f"Expected directory listing for '{owner}/{repo}:{path}', got file data."
            )

        entries: list[GitHubFileEntry] = []
        for entry in payload:
            entry_type = "dir" if entry.get("type") == "dir" else "file"
            raw_size = entry.get("size", 0)
            size = raw_size if isinstance(raw_size, int) else 0
            entries.append(
                GitHubFileEntry(
                    name=str(entry.get("name", "")),
                    path=str(entry.get("path", "")),
                    type=entry_type,
                    size=size,
                )
            )
        return entries

    def check_file_exists(self, owner: str, repo: str, path: str) -> bool:
        """Check whether a repository file exists.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.
            path: File path within the repository.

        Returns:
            True when the file exists, otherwise False for missing files.
        """

        try:
            self.get_file_contents(owner, repo, path)
        except GitHubNotFoundError:
            return False
        return True

    def close(self) -> None:
        """Close underlying HTTP resources."""

        self._client.close()

    def __enter__(self) -> GitHubClient:
        """Support context manager usage."""

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Close the client when leaving context manager scope."""

        del exc_type, exc, traceback
        self.close()

    def _request(self, method: str, url: str) -> httpx.Response:
        """Send a request with retry-once behavior for transient 5xx errors."""

        for attempt in range(2):
            _LOGGER.debug("GitHub API request: %s %s", method, url)
            response = self._client.request(method=method, url=url)
            status_code = response.status_code

            if 500 <= status_code <= 599:
                if attempt == 0:
                    _LOGGER.warning(
                        "GitHub API returned %s for %s %s; retrying once.",
                        status_code,
                        method,
                        url,
                    )
                    continue
                raise GitHubAPIError(
                    f"GitHub API server error ({status_code}) for {method} {url}."
                )

            if status_code == 404:
                raise GitHubNotFoundError(f"GitHub resource not found: {url}")
            if status_code == 401:
                raise GitHubAuthError(
                    f"GitHub authentication failed ({status_code}) for {url}; check your token."
                )
            if status_code == 403:
                retry_after = response.headers.get("retry-after")
                remaining = response.headers.get("x-ratelimit-remaining")
                if remaining == "0" or retry_after is not None:
                    raise GitHubRateLimitError(
                        "GitHub API rate limit exceeded. Wait and retry."
                    )
                raise GitHubAuthError(
                    f"GitHub authentication failed ({status_code}) for {url}; check your token."
                )
            if status_code >= 400:
                raise GitHubAPIError(
                    f"GitHub API request failed ({status_code}) for {method} {url}."
                )

            return response

        raise GitHubAPIError(
            f"GitHub API request failed unexpectedly for {method} {url}."
        )

    @staticmethod
    def _contents_endpoint(owner: str, repo: str, path: str) -> str:
        """Build and validate the repository contents endpoint path."""

        owner_value = owner.strip()
        repo_value = repo.strip()
        if not owner_value or not repo_value:
            raise ValueError("owner and repo must be non-empty strings.")

        normalised_path = path.strip().strip("/")
        if not normalised_path:
            raise ValueError("path must be a non-empty file or directory path.")

        return f"/repos/{owner_value}/{repo_value}/contents/{normalised_path}"
