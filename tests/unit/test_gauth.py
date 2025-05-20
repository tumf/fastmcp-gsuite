import unittest
from unittest.mock import MagicMock, mock_open, patch

from google.oauth2.credentials import Credentials

from src.mcp_gsuite.gauth import (
    AccountInfo,
    CodeExchangeError,
    NoUserIdError,
    exchange_code,
    get_account_info,
    get_authorization_url,
    get_stored_credentials,
    get_user_info,
    store_credentials,
)


class TestGAuth(unittest.TestCase):
    def setUp(self):
        # Set up common mocks
        self.mock_credentials = MagicMock(spec=Credentials)
        self.mock_credentials.token = "mock_token"
        self.mock_credentials.refresh_token = "mock_refresh_token"
        self.mock_credentials.token_uri = "https://oauth2.googleapis.com/token"
        self.mock_credentials.client_id = "mock_client_id"
        self.mock_credentials.client_secret = "mock_client_secret"  # pragma: allowlist secret
        self.mock_credentials.scopes = ["scope1", "scope2"]

    @patch("src.mcp_gsuite.gauth.settings")
    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"accounts": [{"email": "test@example.com", "account_type": "personal"}]}',
    )
    def test_get_account_info(self, mock_file, mock_exists, mock_settings):
        # Configure mocks
        mock_settings.absolute_accounts_file = "/path/to/accounts.json"
        mock_exists.return_value = True

        # Call the function
        accounts = get_account_info()

        # Verify results
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].email, "test@example.com")
        self.assertEqual(accounts[0].account_type, "personal")

        # Verify file was opened correctly
        mock_file.assert_called_once_with("/path/to/accounts.json")

    @patch("src.mcp_gsuite.gauth.settings")
    @patch("os.path.exists")
    def test_get_account_info_no_file(self, mock_exists, mock_settings):
        # Configure mocks
        mock_settings.absolute_accounts_file = "/path/to/accounts.json"
        mock_exists.return_value = False

        # Call the function
        accounts = get_account_info()

        # Verify results
        self.assertEqual(accounts, [])

    @patch("src.mcp_gsuite.gauth.settings")
    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"token": "mock_token", "refresh_token": "mock_refresh_token", '
        '"token_uri": "https://oauth2.googleapis.com/token", "client_id": "mock_client_id", '
        '"client_secret": "mock_client_secret", "scopes": ["scope1", "scope2"]}',  # pragma: allowlist secret
    )
    def test_get_stored_credentials(self, mock_file, mock_exists, mock_settings):
        # Configure mocks
        mock_settings.absolute_credentials_dir = "/path/to/creds"
        mock_exists.return_value = True

        # Call the function with a user ID
        with patch("src.mcp_gsuite.gauth.Credentials") as mock_credentials_class:
            mock_credentials_class.return_value = self.mock_credentials
            result = get_stored_credentials("test@example.com")

        # Verify results
        self.assertEqual(result, self.mock_credentials)

        # Verify the correct file was opened
        mock_file.assert_called_once_with("/path/to/creds/.oauth2.test@example.com.json")

    @patch("src.mcp_gsuite.gauth.settings")
    @patch("os.path.exists")
    def test_get_stored_credentials_no_file(self, mock_exists, mock_settings):
        # Configure mocks
        mock_settings.absolute_credentials_dir = "/path/to/creds"
        mock_exists.return_value = False

        # Call the function with a user ID
        result = get_stored_credentials("test@example.com")

        # Verify results
        self.assertIsNone(result)

    @patch("src.mcp_gsuite.gauth.settings")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_store_credentials(self, mock_json_dump, mock_file, mock_makedirs, mock_settings):
        # Configure mocks
        mock_settings.absolute_credentials_dir = "/path/to/creds"

        # Call the function
        store_credentials(self.mock_credentials, "test@example.com")

        # Verify directories were created
        mock_makedirs.assert_called_once_with("/path/to/creds", exist_ok=True)

        # Verify file was written with the correct content
        mock_file.assert_called_once_with("/path/to/creds/.oauth2.test@example.com.json", "w")

        expected_data = {
            "token": "mock_token",
            "refresh_token": "mock_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "mock_client_id",
            "client_secret": "mock_client_secret",  # pragma: allowlist secret
            "scopes": ["scope1", "scope2"],
        }
        mock_json_dump.assert_called_once_with(expected_data, mock_file(), indent=2)

    @patch("src.mcp_gsuite.gauth.Flow.from_client_config")
    @patch("src.mcp_gsuite.gauth.CLIENTSECRETS_LOCATION", "/path/to/client_secrets.json")
    @patch("src.mcp_gsuite.gauth.SCOPES", ["scope1", "scope2"])
    @patch("src.mcp_gsuite.gauth.REDIRECT_URI", "http://localhost:4100/code")
    @patch("builtins.open", new_callable=mock_open, read_data='{"installed": {"client_id": "mock_client_id"}}')
    def test_exchange_code_success(self, mock_file, mock_flow_from_client_config):
        # Configure mocks
        mock_flow = MagicMock()
        mock_flow_from_client_config.return_value = mock_flow
        mock_flow.credentials = self.mock_credentials

        # Call the function
        result = exchange_code("authorization_code")

        # Verify results
        self.assertEqual(result, self.mock_credentials)

        # Verify flow was created correctly
        mock_flow_from_client_config.assert_called_once_with(
            client_config={"installed": {"client_id": "mock_client_id"}},
            scopes=["scope1", "scope2"],
            redirect_uri="http://localhost:4100/code",
        )
        mock_flow.fetch_token.assert_called_once_with(code="authorization_code")

    @patch("src.mcp_gsuite.gauth.Flow.from_client_config")
    @patch("src.mcp_gsuite.gauth.CLIENTSECRETS_LOCATION", "/path/to/client_secrets.json")
    @patch("src.mcp_gsuite.gauth.SCOPES", ["scope1", "scope2"])
    @patch("src.mcp_gsuite.gauth.REDIRECT_URI", "http://localhost:4100/code")
    @patch("builtins.open", new_callable=mock_open, read_data='{"installed": {"client_id": "mock_client_id"}}')
    def test_exchange_code_failure(self, mock_file, mock_flow_from_client_config):
        # Configure mocks
        mock_flow = MagicMock()
        mock_flow_from_client_config.return_value = mock_flow
        mock_flow.fetch_token.side_effect = Exception("Flow exchange error")

        # Call the function and expect an exception
        with self.assertRaises(CodeExchangeError):
            exchange_code("invalid_code")

    @patch("src.mcp_gsuite.gauth.requests.get")
    def test_get_user_info_success(self, mock_requests_get):
        # Configure mocks
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "user123",  # OAuth 2.0 uses 'sub' as the ID
            "email": "test@example.com",
        }
        mock_requests_get.return_value = mock_response

        # Call the function
        user_info = get_user_info(self.mock_credentials)

        # Verify results
        self.assertEqual(user_info["sub"], "user123")
        self.assertEqual(user_info["email"], "test@example.com")

        # Verify API calls
        mock_requests_get.assert_called_once_with(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {self.mock_credentials.token}"},
        )

    @patch("src.mcp_gsuite.gauth.requests.get")
    def test_get_user_info_no_id(self, mock_requests_get):
        # Configure mocks
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "test@example.com"}  # No sub/id
        mock_requests_get.return_value = mock_response

        # Call the function and expect an exception
        with self.assertRaises(NoUserIdError):
            get_user_info(self.mock_credentials)

    @patch("src.mcp_gsuite.gauth.Flow.from_client_config")
    @patch("src.mcp_gsuite.gauth.CLIENTSECRETS_LOCATION", "/path/to/client_secrets.json")
    @patch("src.mcp_gsuite.gauth.SCOPES", ["scope1", "scope2"])
    @patch("src.mcp_gsuite.gauth.REDIRECT_URI", "http://localhost:4100/code")
    @patch("builtins.open", new_callable=mock_open, read_data='{"installed": {"client_id": "mock_client_id"}}')
    def test_get_authorization_url(self, mock_file, mock_flow_from_client_config):
        # Configure mocks
        mock_flow = MagicMock()
        mock_flow_from_client_config.return_value = mock_flow
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?client_id=123&scope=scope1+scope2",
            "state123",
        )

        # Call the function
        auth_url = get_authorization_url("test@example.com")

        # Verify the returned URL is valid
        self.assertIsInstance(auth_url, str)
        self.assertTrue("https://" in auth_url)

        # Verify flow was created correctly
        mock_flow_from_client_config.assert_called_once_with(
            client_config={"installed": {"client_id": "mock_client_id"}},
            scopes=["scope1", "scope2"],
            redirect_uri="http://localhost:4100/code",
        )

        mock_flow.authorization_url.assert_called_once_with(
            access_type="offline",
            prompt="consent",
            login_hint="test@example.com",
            include_granted_scopes="true",
        )

    def test_account_info(self):
        # Create an AccountInfo instance
        account = AccountInfo(email="test@example.com", account_type="personal", extra_info="Test account")

        # Verify properties
        self.assertEqual(account.email, "test@example.com")
        self.assertEqual(account.account_type, "personal")
        self.assertEqual(account.extra_info, "Test account")

        # Verify description
        expected_description = "Account for email: test@example.com of type: personal. Extra info for: Test account"
        self.assertEqual(account.to_description(), expected_description)


if __name__ == "__main__":
    unittest.main()
