"""Unit tests for setup_cli module."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from mcp_gsuite import gauth, setup_cli


class TestSetupCLI(unittest.TestCase):
    """Test cases for setup CLI functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.gauth_file = os.path.join(self.temp_dir, ".gauth.json")
        self.accounts_file = os.path.join(self.temp_dir, ".accounts.json")
        self.creds_dir = self.temp_dir

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("mcp_gsuite.setup_cli.input")
    @patch("mcp_gsuite.setup_cli.settings")
    def test_setup_client_credentials_creates_file(self, mock_settings, mock_input):
        """Test that setup_client_credentials creates .gauth.json correctly."""
        mock_settings.absolute_gauth_file = self.gauth_file
        mock_input.side_effect = ["test-client-id", "test-client-secret"]

        result = setup_cli.setup_client_credentials()

        self.assertEqual(result["client_id"], "test-client-id")
        self.assertEqual(result["client_secret"], "test-client-secret")

        # Verify file was created
        self.assertTrue(os.path.exists(self.gauth_file))

        # Verify file contents
        with open(self.gauth_file) as f:
            data = json.load(f)
            self.assertEqual(data["installed"]["client_id"], "test-client-id")
            self.assertEqual(data["installed"]["client_secret"], "test-client-secret")
            self.assertIn("urn:ietf:wg:oauth:2.0:oob", data["installed"]["redirect_uris"])

    @patch("mcp_gsuite.setup_cli.input")
    def test_setup_client_credentials_rejects_empty_input(self, mock_input):
        """Test that setup_client_credentials rejects empty credentials."""
        # First attempt: empty client ID, then valid
        # Second attempt: empty secret, then valid
        mock_input.side_effect = ["", "valid-client-id", "", "valid-secret"]

        with patch("mcp_gsuite.setup_cli.settings") as mock_settings:
            mock_settings.absolute_gauth_file = self.gauth_file
            result = setup_cli.setup_client_credentials()

        # Should have prompted 4 times (2 rejections, 2 successes)
        self.assertEqual(mock_input.call_count, 4)
        self.assertEqual(result["client_id"], "valid-client-id")

    @patch("mcp_gsuite.setup_cli.input")
    def test_collect_account_info_validates_email(self, mock_input):
        """Test that collect_account_info validates email format."""
        # First attempt: invalid email (no @), then valid
        mock_input.side_effect = [
            "invalid-email",
            "valid@example.com",
            "personal",
            "test info",
        ]

        result = setup_cli.collect_account_info()

        self.assertEqual(result.email, "valid@example.com")
        self.assertEqual(result.account_type, "personal")
        self.assertEqual(result.extra_info, "test info")
        # Should have prompted for email twice
        self.assertGreaterEqual(mock_input.call_count, 2)

    @patch("mcp_gsuite.setup_cli.settings")
    def test_save_account_to_file_creates_new_file(self, mock_settings):
        """Test that save_account_to_file creates new .accounts.json."""
        mock_settings.absolute_accounts_file = self.accounts_file

        account_info = gauth.AccountInfo(email="test@example.com", account_type="personal", extra_info="test")

        result = setup_cli.save_account_to_file(account_info)

        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.accounts_file))

        # Verify file contents
        with open(self.accounts_file) as f:
            data = json.load(f)
            self.assertEqual(len(data["accounts"]), 1)
            self.assertEqual(data["accounts"][0]["email"], "test@example.com")

    @patch("mcp_gsuite.setup_cli.input")
    @patch("mcp_gsuite.setup_cli.settings")
    def test_save_account_to_file_appends_to_existing(self, mock_settings, mock_input):
        """Test that save_account_to_file appends to existing file."""
        mock_settings.absolute_accounts_file = self.accounts_file

        # Create initial file
        initial_data = {
            "accounts": [
                {
                    "email": "existing@example.com",
                    "account_type": "work",
                    "extra_info": "",
                }
            ]
        }
        with open(self.accounts_file, "w") as f:
            json.dump(initial_data, f)

        # Add new account
        account_info = gauth.AccountInfo(email="new@example.com", account_type="personal", extra_info="")

        result = setup_cli.save_account_to_file(account_info)

        self.assertTrue(result)

        # Verify both accounts exist
        with open(self.accounts_file) as f:
            data = json.load(f)
            self.assertEqual(len(data["accounts"]), 2)
            emails = [acc["email"] for acc in data["accounts"]]
            self.assertIn("existing@example.com", emails)
            self.assertIn("new@example.com", emails)

    @patch("mcp_gsuite.setup_cli.input")
    @patch("mcp_gsuite.setup_cli.settings")
    def test_save_account_to_file_handles_duplicate(self, mock_settings, mock_input):
        """Test that save_account_to_file handles duplicate emails."""
        mock_settings.absolute_accounts_file = self.accounts_file
        mock_input.return_value = "n"  # Don't overwrite

        # Create initial file
        initial_data = {"accounts": [{"email": "test@example.com", "account_type": "work", "extra_info": ""}]}
        with open(self.accounts_file, "w") as f:
            json.dump(initial_data, f)

        # Try to add duplicate
        account_info = gauth.AccountInfo(email="test@example.com", account_type="personal", extra_info="new")

        result = setup_cli.save_account_to_file(account_info)

        self.assertFalse(result)  # Should return False when user declines overwrite

        # Verify only original account exists
        with open(self.accounts_file) as f:
            data = json.load(f)
            self.assertEqual(len(data["accounts"]), 1)
            self.assertEqual(data["accounts"][0]["account_type"], "work")

    @patch("mcp_gsuite.setup_cli.settings")
    def test_list_accounts_with_credentials(self, mock_settings):
        """Test that list_accounts shows correct status."""
        mock_settings.absolute_accounts_file = self.accounts_file
        mock_settings.absolute_credentials_dir = self.creds_dir

        # Create accounts file
        accounts_data = {
            "accounts": [
                {
                    "email": "with-creds@example.com",
                    "account_type": "personal",
                    "extra_info": "",
                },
                {
                    "email": "without-creds@example.com",
                    "account_type": "work",
                    "extra_info": "",
                },
            ]
        }
        with open(self.accounts_file, "w") as f:
            json.dump(accounts_data, f)

        # Create credential file for first account only
        cred_file = os.path.join(self.creds_dir, ".oauth2.with-creds@example.com.json")
        with open(cred_file, "w") as f:
            json.dump({"token": "test"}, f)

        # Capture output
        with patch("builtins.print") as mock_print:
            setup_cli.list_accounts()

        # Verify output mentions both accounts with correct status
        output_calls = [str(call) for call in mock_print.call_args_list]
        output = " ".join(output_calls)
        self.assertIn("with-creds@example.com", output)
        self.assertIn("without-creds@example.com", output)
        self.assertIn("Authenticated", output)
        self.assertIn("Missing credentials", output)

    @patch("mcp_gsuite.setup_cli.input")
    @patch("mcp_gsuite.setup_cli.settings")
    def test_remove_account_success(self, mock_settings, mock_input):
        """Test that remove_account removes account and credentials."""
        mock_settings.absolute_accounts_file = self.accounts_file
        mock_settings.absolute_credentials_dir = self.creds_dir
        mock_input.return_value = "y"  # Confirm removal

        # Create accounts file
        accounts_data = {
            "accounts": [
                {
                    "email": "keep@example.com",
                    "account_type": "personal",
                    "extra_info": "",
                },
                {
                    "email": "remove@example.com",
                    "account_type": "work",
                    "extra_info": "",
                },
            ]
        }
        with open(self.accounts_file, "w") as f:
            json.dump(accounts_data, f)

        # Create credential file
        cred_file = os.path.join(self.creds_dir, ".oauth2.remove@example.com.json")
        with open(cred_file, "w") as f:
            json.dump({"token": "test"}, f)

        # Remove account
        result = setup_cli.remove_account("remove@example.com")

        self.assertTrue(result)

        # Verify account was removed
        with open(self.accounts_file) as f:
            data = json.load(f)
            self.assertEqual(len(data["accounts"]), 1)
            self.assertEqual(data["accounts"][0]["email"], "keep@example.com")

        # Verify credential file was deleted
        self.assertFalse(os.path.exists(cred_file))

    @patch("mcp_gsuite.setup_cli.input")
    @patch("mcp_gsuite.setup_cli.settings")
    def test_remove_account_not_found(self, mock_settings, mock_input):
        """Test that remove_account handles non-existent account."""
        mock_settings.absolute_accounts_file = self.accounts_file

        # Create accounts file
        accounts_data = {
            "accounts": [
                {
                    "email": "existing@example.com",
                    "account_type": "personal",
                    "extra_info": "",
                }
            ]
        }
        with open(self.accounts_file, "w") as f:
            json.dump(accounts_data, f)

        # Try to remove non-existent account
        result = setup_cli.remove_account("nonexistent@example.com")

        self.assertFalse(result)

        # Verify original account still exists
        with open(self.accounts_file) as f:
            data = json.load(f)
            self.assertEqual(len(data["accounts"]), 1)


if __name__ == "__main__":
    unittest.main()
