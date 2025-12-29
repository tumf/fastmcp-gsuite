import logging

from googleapiclient.discovery import build

from .gauth import get_account_info as original_get_account_info
from .gauth import get_stored_credentials

logger = logging.getLogger(__name__)


def _refresh_credentials_if_needed(credentials, user_id: str):
    """
    Refresh credentials if they are expired or about to expire.

    Args:
        credentials: OAuth2Credentials instance to check and refresh.
        user_id: The email address (user ID) for storing refreshed credentials.

    Returns:
        Refreshed credentials or original credentials if still valid.

    Raises:
        RuntimeError: If credentials cannot be refreshed.
    """
    if not credentials.access_token_expired:
        return credentials

    logger.info(f"Access token expired for {user_id}, attempting to refresh...")

    if not credentials.refresh_token:
        logger.error(f"No refresh token available for {user_id}. Re-authentication required.")
        raise RuntimeError(f"No refresh token available for {user_id}. Please re-authenticate.")

    try:
        import httplib2

        http = httplib2.Http()
        credentials.refresh(http)
        # Store refreshed credentials
        from .gauth import store_credentials

        store_credentials(credentials, user_id=user_id)
        logger.info(f"Successfully refreshed and stored credentials for {user_id}")
        return credentials
    except Exception as e:
        logger.error(f"Failed to refresh credentials for {user_id}: {e}")
        raise RuntimeError(f"Failed to refresh credentials for {user_id}. Please re-authenticate.") from e


def get_authenticated_service(service_name: str, version: str, user_id: str, scopes: list[str]):
    """
    Retrieves stored credentials, refreshes if necessary, and builds an authenticated Google API service client.

    This function handles token expiration by:
    1. Proactively refreshing tokens that are expired or about to expire
    2. Storing refreshed credentials for future use

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
    credentials = get_stored_credentials(user_id=user_id)
    if not credentials:
        logger.error(f"No stored OAuth2 credentials found for {user_id}. Please run the authentication flow first.")
        raise RuntimeError(f"No stored OAuth2 credentials found for {user_id}. Please run the authentication flow.")

    # Refresh credentials if expired or about to expire
    credentials = _refresh_credentials_if_needed(credentials, user_id)

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


def get_drive_service(user_id: str):
    """Helper to get an authenticated Google Drive service client."""
    drive_scopes = [
        "https://www.googleapis.com/auth/drive",  # Full access to Drive
        "https://www.googleapis.com/auth/userinfo.email",  # Needed for user info/verification
        "openid",
    ]
    return get_authenticated_service("drive", "v3", user_id, scopes=drive_scopes)


def get_account_info():
    """Gets account information from the configured accounts file."""
    return original_get_account_info()
