"""Bridge error hierarchy -- structured errors for bridge operations."""

from __future__ import annotations


class BridgeError(Exception):
    """Base error for all bridge operations.

    Stores the *operation* that failed and optionally chains a *cause*
    exception via ``__cause__``.
    """

    def __init__(
        self,
        operation: str,
        message: str,
        *,
        cause: Exception | None = None,
    ) -> None:
        self.operation = operation
        super().__init__(message)
        self.__cause__ = cause


class BridgeTimeoutError(BridgeError):
    """Bridge operation timed out."""

    def __init__(
        self,
        operation: str,
        timeout_seconds: float,
        *,
        cause: Exception | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(
            operation,
            (
                f"OmniFocus did not respond within {timeout_seconds}s "
                f"(operation: '{operation}'). Is OmniFocus running?"
            ),
            cause=cause,
        )


class BridgeConnectionError(BridgeError):
    """Cannot connect to OmniFocus."""

    def __init__(
        self,
        operation: str,
        reason: str,
        *,
        cause: Exception | None = None,
    ) -> None:
        self.reason = reason
        super().__init__(
            operation,
            f"Cannot connect to OmniFocus: {reason}",
            cause=cause,
        )


class BridgeProtocolError(BridgeError):
    """Response from OmniFocus was malformed or unparseable."""

    def __init__(
        self,
        operation: str,
        detail: str,
        *,
        cause: Exception | None = None,
    ) -> None:
        self.detail = detail
        super().__init__(
            operation,
            f"Protocol error on '{operation}': {detail}",
            cause=cause,
        )
