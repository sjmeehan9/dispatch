"""Shared application exception types."""

from __future__ import annotations


class LLMError(Exception):
    """Base exception for all LLM-related failures."""

    def __init__(self, message: str) -> None:
        """Initialise the exception with a user-facing message.

        Args:
            message: Error detail describing the failure.
        """

        self.message = message
        super().__init__(message)


class LLMTimeoutError(LLMError):
    """Raised when an LLM request exceeds the configured timeout."""

    def __init__(self, message: str = "LLM request timed out") -> None:
        """Initialise timeout error with a default message.

        Args:
            message: Optional override for the timeout message.
        """

        super().__init__(message)


class LLMAuthError(LLMError):
    """Raised when OpenAI authentication or authorization fails."""

    def __init__(self, message: str = "OpenAI API authentication failed") -> None:
        """Initialise auth error with a default message.

        Args:
            message: Optional override for the auth error message.
        """

        super().__init__(message)


class LLMRateLimitError(LLMError):
    """Raised when OpenAI applies a rate limit response."""

    def __init__(self, message: str = "OpenAI API rate limit exceeded") -> None:
        """Initialise rate-limit error with a default message.

        Args:
            message: Optional override for the rate-limit message.
        """

        super().__init__(message)


class LLMServiceError(LLMError):
    """Raised when a non-auth, non-timeout OpenAI error occurs."""
