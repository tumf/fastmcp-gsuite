import unittest
from unittest.mock import MagicMock, patch

from oauth2client.client import OAuth2Credentials

from src.mcp_gsuite.auth_helper import (
    _refresh_credentials_if_needed,
    get_authenticated_service,
    get_calendar_service,
    get_drive_service,
    get_gmail_service,
)


class TestRefreshCredentialsIfNeeded(unittest.TestCase):
    """Tests for the _refresh_credentials_if_needed function."""

    def setUp(self):
        self.mock_credentials = MagicMock(spec=OAuth2Credentials)
        self.user_id = "test@example.com"

    def test_credentials_not_expired(self):
        """Test that valid credentials are returned unchanged."""
        self.mock_credentials.access_token_expired = False

        result = _refresh_credentials_if_needed(self.mock_credentials, self.user_id)

        self.assertEqual(result, self.mock_credentials)
        self.mock_credentials.refresh.assert_not_called()

    @patch("src.mcp_gsuite.gauth.store_credentials")
    @patch("httplib2.Http")
    def test_credentials_expired_refresh_success(self, mock_http, mock_store_credentials):
        """Test that expired credentials are refreshed and stored."""
        self.mock_credentials.access_token_expired = True
        self.mock_credentials.refresh_token = "valid_refresh_token"

        result = _refresh_credentials_if_needed(self.mock_credentials, self.user_id)

        self.assertEqual(result, self.mock_credentials)
        self.mock_credentials.refresh.assert_called_once()
        mock_store_credentials.assert_called_once_with(self.mock_credentials, user_id=self.user_id)

    def test_credentials_expired_no_refresh_token(self):
        """Test that RuntimeError is raised when no refresh token is available."""
        self.mock_credentials.access_token_expired = True
        self.mock_credentials.refresh_token = None

        with self.assertRaises(RuntimeError) as context:
            _refresh_credentials_if_needed(self.mock_credentials, self.user_id)

        self.assertIn("No refresh token available", str(context.exception))
        self.assertIn(self.user_id, str(context.exception))

    @patch("httplib2.Http")
    def test_credentials_expired_refresh_failure(self, mock_http):
        """Test that RuntimeError is raised when refresh fails."""
        self.mock_credentials.access_token_expired = True
        self.mock_credentials.refresh_token = "valid_refresh_token"
        self.mock_credentials.refresh.side_effect = Exception("Refresh failed")

        with self.assertRaises(RuntimeError) as context:
            _refresh_credentials_if_needed(self.mock_credentials, self.user_id)

        self.assertIn("Failed to refresh credentials", str(context.exception))
        self.assertIn(self.user_id, str(context.exception))


class TestGetAuthenticatedService(unittest.TestCase):
    """Tests for the get_authenticated_service function."""

    def setUp(self):
        self.mock_credentials = MagicMock(spec=OAuth2Credentials)
        self.mock_credentials.access_token_expired = False
        self.user_id = "test@example.com"
        self.service_name = "gmail"
        self.version = "v1"
        self.scopes = ["https://mail.google.com/"]

    @patch("src.mcp_gsuite.auth_helper.build")
    @patch("src.mcp_gsuite.auth_helper.get_stored_credentials")
    def test_service_build_success(self, mock_get_stored_credentials, mock_build):
        """Test successful service build with valid credentials."""
        mock_get_stored_credentials.return_value = self.mock_credentials
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        result = get_authenticated_service(self.service_name, self.version, self.user_id, self.scopes)

        self.assertEqual(result, mock_service)
        mock_get_stored_credentials.assert_called_once_with(user_id=self.user_id)
        mock_build.assert_called_once_with(self.service_name, self.version, credentials=self.mock_credentials)

    @patch("src.mcp_gsuite.auth_helper.get_stored_credentials")
    def test_no_stored_credentials(self, mock_get_stored_credentials):
        """Test RuntimeError when no credentials are stored."""
        mock_get_stored_credentials.return_value = None

        with self.assertRaises(RuntimeError) as context:
            get_authenticated_service(self.service_name, self.version, self.user_id, self.scopes)

        self.assertIn("No stored OAuth2 credentials found", str(context.exception))
        self.assertIn(self.user_id, str(context.exception))

    @patch("src.mcp_gsuite.auth_helper.build")
    @patch("src.mcp_gsuite.auth_helper.get_stored_credentials")
    @patch("src.mcp_gsuite.gauth.store_credentials")
    @patch("httplib2.Http")
    def test_service_build_with_expired_credentials(
        self, mock_http, mock_store_credentials, mock_get_stored_credentials, mock_build
    ):
        """Test that expired credentials are refreshed before building service."""
        self.mock_credentials.access_token_expired = True
        self.mock_credentials.refresh_token = "valid_refresh_token"
        mock_get_stored_credentials.return_value = self.mock_credentials
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        result = get_authenticated_service(self.service_name, self.version, self.user_id, self.scopes)

        self.assertEqual(result, mock_service)
        self.mock_credentials.refresh.assert_called_once()
        mock_store_credentials.assert_called_once_with(self.mock_credentials, user_id=self.user_id)

    @patch("src.mcp_gsuite.auth_helper.build")
    @patch("src.mcp_gsuite.auth_helper.get_stored_credentials")
    def test_service_build_failure(self, mock_get_stored_credentials, mock_build):
        """Test RuntimeError when service build fails."""
        mock_get_stored_credentials.return_value = self.mock_credentials
        mock_build.side_effect = Exception("Build failed")

        with self.assertRaises(RuntimeError) as context:
            get_authenticated_service(self.service_name, self.version, self.user_id, self.scopes)

        self.assertIn("Failed to build Google service", str(context.exception))


class TestServiceHelpers(unittest.TestCase):
    """Tests for the service helper functions."""

    def setUp(self):
        self.user_id = "test@example.com"

    @patch("src.mcp_gsuite.auth_helper.get_authenticated_service")
    def test_get_gmail_service(self, mock_get_authenticated_service):
        """Test get_gmail_service calls get_authenticated_service correctly."""
        mock_service = MagicMock()
        mock_get_authenticated_service.return_value = mock_service

        result = get_gmail_service(self.user_id)

        self.assertEqual(result, mock_service)
        mock_get_authenticated_service.assert_called_once()
        args, kwargs = mock_get_authenticated_service.call_args
        self.assertEqual(args[0], "gmail")
        self.assertEqual(args[1], "v1")
        self.assertEqual(args[2], self.user_id)
        self.assertIn("https://mail.google.com/", kwargs["scopes"])

    @patch("src.mcp_gsuite.auth_helper.get_authenticated_service")
    def test_get_calendar_service(self, mock_get_authenticated_service):
        """Test get_calendar_service calls get_authenticated_service correctly."""
        mock_service = MagicMock()
        mock_get_authenticated_service.return_value = mock_service

        result = get_calendar_service(self.user_id)

        self.assertEqual(result, mock_service)
        mock_get_authenticated_service.assert_called_once()
        args, kwargs = mock_get_authenticated_service.call_args
        self.assertEqual(args[0], "calendar")
        self.assertEqual(args[1], "v3")
        self.assertEqual(args[2], self.user_id)
        self.assertIn("https://www.googleapis.com/auth/calendar", kwargs["scopes"])

    @patch("src.mcp_gsuite.auth_helper.get_authenticated_service")
    def test_get_drive_service(self, mock_get_authenticated_service):
        """Test get_drive_service calls get_authenticated_service correctly."""
        mock_service = MagicMock()
        mock_get_authenticated_service.return_value = mock_service

        result = get_drive_service(self.user_id)

        self.assertEqual(result, mock_service)
        mock_get_authenticated_service.assert_called_once()
        args, kwargs = mock_get_authenticated_service.call_args
        self.assertEqual(args[0], "drive")
        self.assertEqual(args[1], "v3")
        self.assertEqual(args[2], self.user_id)
        self.assertIn("https://www.googleapis.com/auth/drive", kwargs["scopes"])


if __name__ == "__main__":
    unittest.main()
