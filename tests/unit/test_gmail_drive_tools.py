import json
import unittest
from unittest.mock import MagicMock, patch

from src.mcp_gsuite.gmail_drive_tools import (
    bulk_save_gmail_attachments_to_drive,
    save_gmail_attachment_to_drive,
)
from tests.unit.mocks.context_mock import MockContext


class TestGmailDriveTools(unittest.IsolatedAsyncioTestCase):
    """Test cases for Gmail to Drive MCP tools."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_gmail_service = MagicMock()
        self.mock_drive_service = MagicMock()
        self.mock_context = MockContext()

        self.test_user_id = "test@example.com"
        self.test_email_id = "test_email_123"
        self.test_attachment_id = "test_attachment_123"
        self.test_folder_id = "test_folder_123"

        self.sample_email = {
            "id": self.test_email_id,
            "threadId": "thread123",
            "subject": "Test Subject",
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "date": "2023-01-01T12:00:00Z",
            "snippet": "This is a test email",
        }

        self.sample_attachment_metadata = {
            "attachmentId": self.test_attachment_id,
            "filename": "test.pdf",
            "mimeType": "application/pdf",
            "size": 12345,
        }

        self.sample_attachment_data = {
            "data": "base64encodeddata",
            "size": 12345,
        }

        self.sample_drive_file = {
            "id": "drive_file_123",
            "name": "test.pdf",
            "mimeType": "application/pdf",
            "webViewLink": "https://drive.google.com/file/d/drive_file_123/view",
        }

    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_drive_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.gmail_impl.GmailService")
    @patch("src.mcp_gsuite.gmail_drive_tools.DriveService")
    async def test_save_gmail_attachment_to_drive_success(
        self, mock_drive_service_class, mock_gmail_service_class, mock_get_drive_service, mock_get_gmail_service
    ):
        """Test successful saving of Gmail attachment to Drive."""
        mock_gmail_service = MagicMock()
        mock_drive_service = MagicMock()
        mock_get_gmail_service.return_value = mock_gmail_service
        mock_get_drive_service.return_value = mock_drive_service

        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_drive_service_instance = mock_drive_service_class.return_value

        mock_gmail_service_instance.get_email_by_id_with_attachments.return_value = (
            self.sample_email,
            {"part1": self.sample_attachment_metadata},
        )
        mock_gmail_service_instance.get_attachment.return_value = self.sample_attachment_data
        mock_drive_service_instance.upload_file.return_value = self.sample_drive_file

        result = await save_gmail_attachment_to_drive(
            user_id=self.test_user_id,
            message_id=self.test_email_id,
            attachment_id=self.test_attachment_id,
            folder_id=self.test_folder_id,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(json.loads(result[0].text), self.sample_drive_file)

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_get_drive_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_gmail_service)
        mock_drive_service_class.assert_called_once_with(mock_drive_service)

        mock_gmail_service_instance.get_email_by_id_with_attachments.assert_called_once_with(
            email_id=self.test_email_id
        )
        mock_gmail_service_instance.get_attachment.assert_called_once_with(
            message_id=self.test_email_id, attachment_id=self.test_attachment_id
        )

        mock_drive_service_instance.upload_file.assert_called_once_with(
            file_content=self.sample_attachment_data["data"],
            file_name=self.sample_attachment_metadata["filename"],
            mime_type=self.sample_attachment_metadata["mimeType"],
            parent_folder_id=self.test_folder_id,
        )

    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_drive_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.gmail_impl.GmailService")
    @patch("src.mcp_gsuite.gmail_drive_tools.DriveService")
    async def test_save_gmail_attachment_to_drive_attachment_not_found(
        self, mock_drive_service_class, mock_gmail_service_class, mock_get_drive_service, mock_get_gmail_service
    ):
        """Test handling when attachment is not found."""
        mock_gmail_service = MagicMock()
        mock_drive_service = MagicMock()
        mock_get_gmail_service.return_value = mock_gmail_service
        mock_get_drive_service.return_value = mock_drive_service

        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_drive_service_instance = mock_drive_service_class.return_value

        mock_gmail_service_instance.get_email_by_id_with_attachments.return_value = (
            self.sample_email,
            {},  # No attachments
        )

        result = await save_gmail_attachment_to_drive(
            user_id=self.test_user_id,
            message_id=self.test_email_id,
            attachment_id=self.test_attachment_id,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(
            result[0].text, f"Attachment ID {self.test_attachment_id} not found in message {self.test_email_id}"
        )

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_get_drive_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_gmail_service)
        mock_drive_service_class.assert_called_once_with(mock_drive_service)

        mock_gmail_service_instance.get_email_by_id_with_attachments.assert_called_once_with(
            email_id=self.test_email_id
        )

        mock_drive_service_instance.upload_file.assert_not_called()

    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_drive_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.gmail_impl.GmailService")
    @patch("src.mcp_gsuite.gmail_drive_tools.DriveService")
    async def test_save_gmail_attachment_to_drive_with_rename(
        self, mock_drive_service_class, mock_gmail_service_class, mock_get_drive_service, mock_get_gmail_service
    ):
        """Test saving attachment with a new filename."""
        mock_gmail_service = MagicMock()
        mock_drive_service = MagicMock()
        mock_get_gmail_service.return_value = mock_gmail_service
        mock_get_drive_service.return_value = mock_drive_service

        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_drive_service_instance = mock_drive_service_class.return_value

        mock_gmail_service_instance.get_email_by_id_with_attachments.return_value = (
            self.sample_email,
            {"part1": self.sample_attachment_metadata},
        )
        mock_gmail_service_instance.get_attachment.return_value = self.sample_attachment_data

        renamed_file = self.sample_drive_file.copy()
        renamed_file["name"] = "renamed.pdf"
        mock_drive_service_instance.upload_file.return_value = renamed_file

        new_filename = "renamed.pdf"
        result = await save_gmail_attachment_to_drive(
            user_id=self.test_user_id,
            message_id=self.test_email_id,
            attachment_id=self.test_attachment_id,
            rename=new_filename,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(json.loads(result[0].text), renamed_file)

        mock_drive_service_instance.upload_file.assert_called_once_with(
            file_content=self.sample_attachment_data["data"],
            file_name=new_filename,
            mime_type=self.sample_attachment_metadata["mimeType"],
            parent_folder_id=None,
        )

    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_drive_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.gmail_impl.GmailService")
    @patch("src.mcp_gsuite.gmail_drive_tools.DriveService")
    async def test_save_gmail_attachment_to_drive_error(
        self, mock_drive_service_class, mock_gmail_service_class, mock_get_drive_service, mock_get_gmail_service
    ):
        """Test error handling in save_gmail_attachment_to_drive."""
        mock_gmail_service = MagicMock()
        mock_drive_service = MagicMock()
        mock_get_gmail_service.return_value = mock_gmail_service
        mock_get_drive_service.return_value = mock_drive_service

        mock_gmail_service_instance = mock_gmail_service_class.return_value

        mock_gmail_service_instance.get_email_by_id_with_attachments.side_effect = Exception("Test error")

        with self.assertRaises(RuntimeError) as context:
            await save_gmail_attachment_to_drive(
                user_id=self.test_user_id,
                message_id=self.test_email_id,
                attachment_id=self.test_attachment_id,
                ctx=self.mock_context,  # type: ignore
            )

        self.assertTrue("Error saving attachment to Drive: Test error" in str(context.exception))

        self.assertEqual(len(self.mock_context.error_messages), 1)
        self.assertTrue("Error saving attachment to Drive: Test error" in self.mock_context.error_messages[0])

    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_drive_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.gmail_impl.GmailService")
    @patch("src.mcp_gsuite.gmail_drive_tools.DriveService")
    async def test_bulk_save_gmail_attachments_to_drive_success(
        self, mock_drive_service_class, mock_gmail_service_class, mock_get_drive_service, mock_get_gmail_service
    ):
        """Test successful bulk saving of Gmail attachments to Drive."""
        mock_gmail_service = MagicMock()
        mock_drive_service = MagicMock()
        mock_get_gmail_service.return_value = mock_gmail_service
        mock_get_drive_service.return_value = mock_drive_service

        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_drive_service_instance = mock_drive_service_class.return_value

        mock_gmail_service_instance.get_email_by_id_with_attachments.return_value = (
            self.sample_email,
            {"part1": self.sample_attachment_metadata},
        )
        mock_gmail_service_instance.get_attachment.return_value = self.sample_attachment_data
        mock_drive_service_instance.upload_file.return_value = self.sample_drive_file

        attachments = [
            {
                "message_id": self.test_email_id,
                "attachment_id": self.test_attachment_id,
                "folder_id": self.test_folder_id,
            },
            {
                "message_id": self.test_email_id,
                "attachment_id": self.test_attachment_id,
                "rename": "renamed.pdf",
            },
        ]

        result = await bulk_save_gmail_attachments_to_drive(
            user_id=self.test_user_id,
            attachments=attachments,
            folder_id=None,  # Default folder
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 2)  # Two results for two attachments
        for item in result:
            self.assertEqual(item.type, "text")
            self.assertEqual(json.loads(item.text), self.sample_drive_file)

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_get_drive_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_gmail_service)
        mock_drive_service_class.assert_called_once_with(mock_drive_service)

        self.assertEqual(mock_gmail_service_instance.get_email_by_id_with_attachments.call_count, 2)
        self.assertEqual(mock_gmail_service_instance.get_attachment.call_count, 2)

        self.assertEqual(mock_drive_service_instance.upload_file.call_count, 2)

        mock_drive_service_instance.upload_file.assert_any_call(
            file_content=self.sample_attachment_data["data"],
            file_name=self.sample_attachment_metadata["filename"],
            mime_type=self.sample_attachment_metadata["mimeType"],
            parent_folder_id=self.test_folder_id,
        )

        mock_drive_service_instance.upload_file.assert_any_call(
            file_content=self.sample_attachment_data["data"],
            file_name="renamed.pdf",
            mime_type=self.sample_attachment_metadata["mimeType"],
            parent_folder_id=None,
        )

    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_drive_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.gmail_impl.GmailService")
    @patch("src.mcp_gsuite.gmail_drive_tools.DriveService")
    async def test_bulk_save_gmail_attachments_to_drive_missing_fields(
        self, mock_drive_service_class, mock_gmail_service_class, mock_get_drive_service, mock_get_gmail_service
    ):
        """Test handling of missing required fields in bulk save."""
        mock_gmail_service = MagicMock()
        mock_drive_service = MagicMock()
        mock_get_gmail_service.return_value = mock_gmail_service
        mock_get_drive_service.return_value = mock_drive_service

        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_drive_service_instance = mock_drive_service_class.return_value

        attachments = [
            {
                "attachment_id": self.test_attachment_id,
            },
            {
                "message_id": self.test_email_id,
            },
        ]

        result = await bulk_save_gmail_attachments_to_drive(
            user_id=self.test_user_id,
            attachments=attachments,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 2)  # Two error results
        for item in result:
            self.assertEqual(item.type, "text")
            self.assertEqual(item.text, "Missing required fields in attachment info (message_id, attachment_id)")

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_get_drive_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_gmail_service)
        mock_drive_service_class.assert_called_once_with(mock_drive_service)

        mock_gmail_service_instance.get_email_by_id_with_attachments.assert_not_called()
        mock_gmail_service_instance.get_attachment.assert_not_called()
        mock_drive_service_instance.upload_file.assert_not_called()

    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.auth_helper.get_drive_service")
    @patch("src.mcp_gsuite.gmail_drive_tools.gmail_impl.GmailService")
    @patch("src.mcp_gsuite.gmail_drive_tools.DriveService")
    async def test_bulk_save_gmail_attachments_to_drive_error(
        self, mock_drive_service_class, mock_gmail_service_class, mock_get_drive_service, mock_get_gmail_service
    ):
        """Test error handling in bulk_save_gmail_attachments_to_drive."""
        mock_gmail_service = MagicMock()
        mock_drive_service = MagicMock()
        mock_get_gmail_service.return_value = mock_gmail_service
        mock_get_drive_service.return_value = mock_drive_service

        mock_get_gmail_service.side_effect = Exception("Test error")

        with self.assertRaises(RuntimeError) as context:
            await bulk_save_gmail_attachments_to_drive(
                user_id=self.test_user_id,
                attachments=[{"message_id": self.test_email_id, "attachment_id": self.test_attachment_id}],
                ctx=self.mock_context,  # type: ignore
            )

        self.assertTrue("Error saving attachments to Drive: Test error" in str(context.exception))

        self.assertEqual(len(self.mock_context.error_messages), 1)
        self.assertTrue("Error saving attachments to Drive: Test error" in self.mock_context.error_messages[0])
