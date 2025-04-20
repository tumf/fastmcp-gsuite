import unittest
from unittest.mock import MagicMock, mock_open, patch

from oauth2client.client import FlowExchangeError, OAuth2Credentials

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
        self.mock_credentials = MagicMock(spec=OAuth2Credentials)
        self.mock_credentials.to_json.return_value = '{"token": "mock_token"}'

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
    @patch("builtins.open", new_callable=mock_open, read_data='{"token": "mock_token"}')
    def test_get_stored_credentials(self, mock_file, mock_exists, mock_settings):
        # Configure mocks
        mock_settings.absolute_credentials_dir = "/path/to/creds"
        mock_exists.return_value = True

        # Call the function with a user ID
        with patch("src.mcp_gsuite.gauth.Credentials.new_from_json") as mock_new_from_json:
            mock_new_from_json.return_value = self.mock_credentials
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
    def test_store_credentials(self, mock_file, mock_makedirs, mock_settings):
        # Configure mocks
        mock_settings.absolute_credentials_dir = "/path/to/creds"

        # Call the function
        store_credentials(self.mock_credentials, "test@example.com")

        # Verify directories were created
        mock_makedirs.assert_called_once_with("/path/to/creds", exist_ok=True)

        # Verify file was written with the correct content
        mock_file.assert_called_once_with("/path/to/creds/.oauth2.test@example.com.json", "w")
        mock_file().write.assert_called_once_with('{"token": "mock_token"}')

    @patch("src.mcp_gsuite.gauth.flow_from_clientsecrets")
    @patch("src.mcp_gsuite.gauth.CLIENTSECRETS_LOCATION", "/path/to/client_secrets.json")
    @patch("src.mcp_gsuite.gauth.SCOPES", ["scope1", "scope2"])
    @patch("src.mcp_gsuite.gauth.REDIRECT_URI", "http://localhost:4100/code")
    def test_exchange_code_success(self, mock_flow_from_clientsecrets):
        # Configure mocks
        mock_flow = MagicMock()
        mock_flow_from_clientsecrets.return_value = mock_flow
        mock_flow.step2_exchange.return_value = self.mock_credentials

        # Call the function
        result = exchange_code("authorization_code")

        # Verify results
        self.assertEqual(result, self.mock_credentials)

        # Verify flow was created correctly
        mock_flow_from_clientsecrets.assert_called_once_with("/path/to/client_secrets.json", "scope1 scope2")
        self.assertEqual(mock_flow.redirect_uri, "http://localhost:4100/code")
        mock_flow.step2_exchange.assert_called_once_with("authorization_code")

    @patch("src.mcp_gsuite.gauth.flow_from_clientsecrets")
    @patch("src.mcp_gsuite.gauth.CLIENTSECRETS_LOCATION", "/path/to/client_secrets.json")
    @patch("src.mcp_gsuite.gauth.SCOPES", ["scope1", "scope2"])
    @patch("src.mcp_gsuite.gauth.REDIRECT_URI", "http://localhost:4100/code")
    def test_exchange_code_failure(self, mock_flow_from_clientsecrets):
        # Configure mocks
        mock_flow = MagicMock()
        mock_flow_from_clientsecrets.return_value = mock_flow
        mock_flow.step2_exchange.side_effect = FlowExchangeError("Flow exchange error")

        # Call the function and expect an exception
        with self.assertRaises(CodeExchangeError):
            exchange_code("invalid_code")

    @patch("src.mcp_gsuite.gauth.build")
    def test_get_user_info_success(self, mock_build):
        # Configure mocks
        mock_userinfo_service = MagicMock()
        mock_build.return_value = mock_userinfo_service
        mock_userinfo_get = MagicMock()
        mock_userinfo = MagicMock()
        mock_userinfo.get.return_value = mock_userinfo_get
        mock_userinfo_service.userinfo.return_value = mock_userinfo
        mock_userinfo_get.execute.return_value = {
            "id": "user123",
            "email": "test@example.com",
        }

        # Call the function
        result = get_user_info(self.mock_credentials)

        # Verify results
        self.assertEqual(result["id"], "user123")
        self.assertEqual(result["email"], "test@example.com")

        # Verify API calls
        mock_build.assert_called_once_with(
            serviceName="oauth2",
            version="v2",
            http=self.mock_credentials.authorize.return_value,
        )

    @patch("src.mcp_gsuite.gauth.build")
    def test_get_user_info_no_id(self, mock_build):
        # Configure mocks
        mock_userinfo_service = MagicMock()
        mock_build.return_value = mock_userinfo_service
        mock_userinfo_get = MagicMock()
        mock_userinfo = MagicMock()
        mock_userinfo.get.return_value = mock_userinfo_get
        mock_userinfo_service.userinfo.return_value = mock_userinfo
        mock_userinfo_get.execute.return_value = {"email": "test@example.com"}  # No id

        # Call the function and expect an exception
        with self.assertRaises(NoUserIdError):
            get_user_info(self.mock_credentials)

    @patch("src.mcp_gsuite.gauth.flow_from_clientsecrets")
    @patch("src.mcp_gsuite.gauth.CLIENTSECRETS_LOCATION", "/path/to/client_secrets.json")
    @patch("src.mcp_gsuite.gauth.SCOPES", ["scope1", "scope2"])
    @patch("src.mcp_gsuite.gauth.REDIRECT_URI", "http://localhost:4100/code")
    def test_get_authorization_url(self, mock_flow_from_clientsecrets):
        # Configure mocks
        mock_flow = MagicMock()
        mock_flow_from_clientsecrets.return_value = mock_flow
        mock_flow.params = {}

        # Call the function
        get_authorization_url("test@example.com", "state123")

        # Verify flow was created correctly
        mock_flow_from_clientsecrets.assert_called_once_with(
            "/path/to/client_secrets.json",
            "scope1 scope2",
            redirect_uri="http://localhost:4100/code",
        )

        # Verify params were set
        self.assertEqual(mock_flow.params["access_type"], "offline")
        self.assertEqual(mock_flow.params["approval_prompt"], "force")
        self.assertEqual(mock_flow.params["user_id"], "test@example.com")
        self.assertEqual(mock_flow.params["state"], "state123")

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
