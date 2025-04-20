import asyncio
import base64
import json
import os
from collections.abc import Callable, Generator
from datetime import UTC
from typing import Any, TypeVar, cast

import pytest
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

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


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def oauth_token(check_env_vars) -> Generator[dict[str, Any], None, None]:
    """
    Create and maintain a single OAuth token for the entire test session.
    This prevents requesting a new token for each test case.
    """
    # Get authentication information from environment variables
    credentials_json_str = os.environ.get("GSUITE_CREDENTIALS_JSON", "")
    google_email = os.environ.get("GOOGLE_ACCOUNT_EMAIL", "")
    google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Decode credentials JSON
    try:
        # Base64 decode if needed
        try:
            credentials_json_decoded = base64.b64decode(credentials_json_str).decode("utf-8")
            decoded_credentials = json.loads(credentials_json_decoded)
        except Exception:
            # Try direct JSON parsing if not base64 encoded
            decoded_credentials = json.loads(credentials_json_str)

        # Create credentials object
        credentials = Credentials(
            token=decoded_credentials.get("token", decoded_credentials.get("access_token")),
            refresh_token=decoded_credentials.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=google_client_id,
            client_secret=google_client_secret,
            scopes=decoded_credentials.get("scopes", ["https://mail.google.com/"]),
        )

        # Refresh token if needed
        if not credentials.valid:
            credentials.refresh(Request())
            print("OAuth token refreshed for test session")

        # Get current time for token_expiry
        from datetime import datetime, timedelta

        now = datetime.now(UTC)
        token_expiry = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Create credentials file content in the format expected by the MCP server
        credentials_json = {
            "access_token": credentials.token,
            "client_id": google_client_id,
            "client_secret": google_client_secret,
            "refresh_token": credentials.refresh_token,
            "token_expiry": token_expiry,
            "token_uri": credentials.token_uri,
            "user_agent": "fastmcp-gsuite-e2e-tests",
            "revoke_uri": "https://oauth2.googleapis.com/revoke",
            "id_token": None,
            "id_token_jwt": None,
            "token_response": {
                "access_token": credentials.token,
                "expires_in": 3600,
                "refresh_token": credentials.refresh_token,
                "scope": " ".join(credentials.scopes),
                "token_type": "Bearer",
            },
            "scopes": credentials.scopes,
            "token_info_uri": "https://oauth2.googleapis.com/tokeninfo",
            "invalid": False,
            "_class": "OAuth2Credentials",
            "_module": "oauth2client.client",
        }

        # Create temporary credentials file
        credentials_file = ".e2e_test_credentials.json"
        with open(credentials_file, "w") as f:
            json.dump(credentials_json, f)

        # Create OAuth2 authentication file in the format expected by MCP server
        oauth2_file = f".oauth2.{google_email}.json"
        with open(oauth2_file, "w") as f:
            json.dump(credentials_json, f)

        # Also create .gauth.json file expected by fastmcp-gsuite
        gauth_file = ".gauth.json"
        gauth_data = {
            "installed": {
                "client_id": google_client_id,
                "client_secret": google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            }
        }
        with open(gauth_file, "w") as f:
            json.dump(gauth_data, f)

        # Set environment variables for MCP server
        os.environ["GSUITE_CREDENTIALS_FILE"] = credentials_file
        os.environ["GSUITE_EMAIL"] = google_email

        # Get project ID with default value
        project_id = os.environ.get("GOOGLE_PROJECT_ID", "")

        # Return the credentials info
        token_info = {
            "credentials_file": credentials_file,
            "oauth2_file": oauth2_file,
            "gauth_file": gauth_file,
            "email": google_email,
            "client_id": google_client_id,
            "client_secret": google_client_secret,
            "project_id": project_id,
            "credentials": credentials,
        }

        yield token_info

        # Clean up files after testing
        if os.environ.get("KEEP_E2E_CREDENTIALS") != "1":
            if os.path.exists(credentials_file):
                os.remove(credentials_file)
            if os.path.exists(oauth2_file):
                os.remove(oauth2_file)
            if os.path.exists(gauth_file):
                os.remove(gauth_file)

    except Exception as e:
        pytest.fail(f"Failed to setup OAuth token: {e!s}")


# 明示的に例外の型を定義
ExcType = type[BaseException]
ExcTypes = tuple[ExcType, ...]


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    initial_backoff: float = 1.0,
    backoff_factor: float = 2.0,
    expected_exceptions: ExcType | ExcTypes = (
        RuntimeError,
        ConnectionError,
        TimeoutError,
    ),
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
