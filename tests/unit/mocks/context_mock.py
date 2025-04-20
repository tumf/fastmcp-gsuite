"""Mock implementation of the Context class from fastmcp."""

from typing import Any, TypeVar

from fastmcp import Context

T = TypeVar("T")
U = TypeVar("U")


class MockContext(Context[Any, Any]):
    """Mock implementation of the Context class from fastmcp."""

    def __init__(self):
        self.info_messages = []
        self.error_messages = []
        self.warning_messages = []
        self.debug_messages = []

    async def info(self, message: str, **extra: Any) -> None:
        """Record an info message."""
        self.info_messages.append(message)

    async def error(self, message: str, **extra: Any) -> None:
        """Record an error message."""
        self.error_messages.append(message)

    async def warning(self, message: str, **extra: Any) -> None:
        """Record a warning message."""
        self.warning_messages.append(message)

    async def debug(self, message: str, **extra: Any) -> None:
        """Record a debug message."""
        self.debug_messages.append(message)
