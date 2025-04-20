"""Mock implementation of the Context class from fastmcp."""

from typing import Any


class MockContext:
    """Mock implementation of the Context class from fastmcp."""

    def __init__(self):
        self.info_messages: list[str] = []
        self.error_messages: list[str] = []
        self.warning_messages: list[str] = []
        self.debug_messages: list[str] = []

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
