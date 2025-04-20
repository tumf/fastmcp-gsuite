import logging

from googleapiclient.discovery import build

from .gauth import get_account_info as original_get_account_info
from .gauth import get_stored_credentials

logger = logging.getLogger(__name__)


def get_authenticated_service(service_name: str, version: str, user_id: str, scopes: list[str]):
    """
    Retrieves stored credentials, refreshes if necessary, and builds an authenticated Google API service client.

    Args:
        service_name: The name of the Google API service (e.g., 'gmail', 'calendar').
        version: The version of the Google API service (e.g., 'v1', 'v3').
        user_id: The email address (user ID) for which to get the service.
        scopes: List of required OAuth scopes for the service.

    Returns:
        An authorized Google API service client instance.

    Raises:
        RuntimeError: If credentials are not found or cannot be refreshed/used.
    """
    credentials = get_stored_credentials(user_id=user_id)  # Uses settings internally now
    if not credentials:
        logger.error(f"No stored OAuth2 credentials found for {user_id}. Please run the authentication flow first.")
        raise RuntimeError(f"No stored OAuth2 credentials found for {user_id}. Please run the authentication flow.")

    try:
        service = build(service_name, version, credentials=credentials)
        logger.info(f"Successfully built Google service {service_name} v{version} for {user_id}")
        return service
    except Exception as e:
        logger.error(f"Failed to build Google service {service_name} v{version} for {user_id}: {e}")

        raise RuntimeError(f"Failed to build Google service for {user_id}.") from e


def get_gmail_service(user_id: str):
    """Helper to get an authenticated Gmail service client."""
    gmail_scopes = [
        "https://mail.google.com/",  # Full access
        "https://www.googleapis.com/auth/userinfo.email",  # Needed for user info/verification
        "openid",
    ]
    return get_authenticated_service("gmail", "v1", user_id, scopes=gmail_scopes)


def get_calendar_service(user_id: str):
    """Helper to get an authenticated Calendar service client."""
    calendar_scopes = [
        "https://www.googleapis.com/auth/calendar",  # Full access
        "https://www.googleapis.com/auth/userinfo.email",  # Needed for user info/verification
        "openid",
    ]
    return get_authenticated_service("calendar", "v3", user_id, scopes=calendar_scopes)


def get_account_info():
    """Gets account information from the configured accounts file."""
    return original_get_account_info()
