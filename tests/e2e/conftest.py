import asyncio
import os
from collections.abc import Callable
from typing import Any, TypeVar, cast

import pytest

T = TypeVar("T")


def pytest_configure(config):
    """Register e2e marker"""
    config.addinivalue_line("markers", "e2e: mark a test as an end-to-end test")


def pytest_addoption(parser):
    """Add e2e command line option"""
    parser.addoption("--run-e2e", action="store_true", default=False, help="Run e2e tests")


def pytest_collection_modifyitems(config, items):
    """Skip e2e tests unless --run-e2e is specified"""
    if config.getoption("--run-e2e"):
        # --run-e2e given in cli: do not skip e2e tests
        return

    skip_e2e = pytest.mark.skip(reason="Need --run-e2e option to run")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)


@pytest.fixture(scope="session", autouse=True)
def check_env_vars():
    """Check if required environment variables are set for e2e tests"""
    required_vars = [
        "GSUITE_CREDENTIALS_JSON",
        "GOOGLE_ACCOUNT_EMAIL",
        "GOOGLE_PROJECT_ID",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
    ]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        pytest.skip(f"Missing required environment variables for e2e tests: {', '.join(missing_vars)}")


# 明示的に例外の型を定義
ExcType = type[BaseException]
ExcTypes = tuple[ExcType, ...]


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    initial_backoff: float = 1.0,
    backoff_factor: float = 2.0,
    expected_exceptions: ExcType | ExcTypes = (RuntimeError, ConnectionError, TimeoutError),
    **kwargs: Any,
) -> T:
    """
    Retry an async function with exponential backoff.

    Args:
        func: The async function to retry
        *args: Positional arguments to pass to func
        max_attempts: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        backoff_factor: Factor to multiply backoff by after each failure
        expected_exceptions: Exception type or tuple of exception types that should trigger a retry
                           Defaults to (RuntimeError, ConnectionError, TimeoutError)
        **kwargs: Keyword arguments to pass to func

    Returns:
        The return value of the function call

    Raises:
        The last exception encountered if all attempts fail
    """
    attempt = 0
    backoff = initial_backoff
    last_exception = None

    # Convert single exception to tuple for consistent handling
    if not isinstance(expected_exceptions, tuple):
        expected_exceptions = (expected_exceptions,)

    # 型チェックのために明示的な型キャスト
    expected_exceptions = cast(ExcTypes, expected_exceptions)

    while attempt < max_attempts:
        try:
            attempt += 1
            return await func(*args, **kwargs)
        except expected_exceptions as e:
            last_exception = e
            if attempt >= max_attempts:
                break

            # Log the error and retry info
            print(f"Attempt {attempt} failed: {e!s}. Retrying in {backoff:.1f} seconds...")

            # Wait before retrying
            await asyncio.sleep(backoff)

            # Increase backoff for next attempt
            backoff *= backoff_factor

    # If we get here, all attempts failed
    assert last_exception is not None  # mypy に last_exception が None でないことを教える
    print(f"All {max_attempts} attempts failed. Last error: {last_exception!s}")
    raise last_exception
