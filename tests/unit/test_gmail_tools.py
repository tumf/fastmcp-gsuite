import json
import unittest
from unittest.mock import MagicMock, patch

from src.mcp_gsuite.gmail_tools import (
    bulk_get_gmail_emails,
    bulk_save_gmail_attachments,
    create_gmail_draft,
    create_gmail_reply,
    delete_gmail_draft,
    get_email_details,
    get_gmail_attachment,
    get_gmail_labels,
    query_gmail_emails,
)
from tests.unit.mocks.context_mock import MockContext


class TestGmailTools(unittest.IsolatedAsyncioTestCase):
    """Test cases for Gmail MCP tools."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_gmail_service = MagicMock()

        self.mock_context = MockContext()

        self.test_user_id = "test@example.com"
        self.test_email_id = "test_email_123"
        self.test_draft_id = "test_draft_123"
        self.test_attachment_id = "test_attachment_123"

        self.sample_email = {
            "id": self.test_email_id,
            "threadId": "thread123",
            "subject": "Test Subject",
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "date": "2023-01-01T12:00:00Z",
            "snippet": "This is a test email",
            "body": "This is the full body of the test email.",
        }

        self.sample_attachment = {
            "id": self.test_attachment_id,
            "filename": "test.pdf",
            "mimeType": "application/pdf",
            "size": 12345,
        }

        self.sample_draft = {
            "id": self.test_draft_id,
            "message": {
                "id": "msg123",
                "threadId": "thread123",
            },
        }

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_query_gmail_emails_success(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test successful query of Gmail emails."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_gmail_service_instance.query_emails.return_value = [self.sample_email]

        result = await query_gmail_emails(
            user_id=self.test_user_id,
            query="is:unread",
            max_results=10,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(json.loads(result[0].text), self.sample_email)

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_service)
        mock_gmail_service_instance.query_emails.assert_called_once_with(query="is:unread", max_results=10)

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_query_gmail_emails_no_results(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test query of Gmail emails with no results."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_gmail_service_instance.query_emails.return_value = []

        result = await query_gmail_emails(
            user_id=self.test_user_id,
            query="is:unread",
            max_results=10,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(result[0].text, "No emails found matching the query.")

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_service)
        mock_gmail_service_instance.query_emails.assert_called_once_with(query="is:unread", max_results=10)

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_get_email_details_success(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test successful retrieval of email details."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_gmail_service_instance.get_email_by_id_with_attachments.return_value = (
            self.sample_email,
            {"attachment1": self.sample_attachment},
        )

        result = await get_email_details(
            user_id=self.test_user_id,
            email_id=self.test_email_id,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        result_data = json.loads(result[0].text)
        self.assertEqual(result_data["email"]["id"], self.sample_email["id"])
        self.assertEqual(result_data["attachments"], {"attachment1": self.sample_attachment})
        # Check body pagination info
        self.assertIn("body_pagination", result_data)
        self.assertEqual(result_data["body_pagination"]["offset"], 0)
        self.assertEqual(result_data["body_pagination"]["limit"], 5000)
        self.assertEqual(result_data["body_pagination"]["total_length"], len(self.sample_email["body"]))
        self.assertFalse(result_data["body_pagination"]["has_more"])

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_service)
        mock_gmail_service_instance.get_email_by_id_with_attachments.assert_called_once_with(
            email_id=self.test_email_id
        )

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_get_email_details_with_body_pagination(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test email details with body pagination (offset and limit)."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value

        # Create email with long body
        long_body = "A" * 100  # 100 character body
        email_with_long_body = {**self.sample_email, "body": long_body}
        mock_gmail_service_instance.get_email_by_id_with_attachments.return_value = (
            email_with_long_body,
            {},
        )

        # Test with offset=10, limit=20
        result = await get_email_details(
            user_id=self.test_user_id,
            email_id=self.test_email_id,
            body_offset=10,
            body_limit=20,
            ctx=self.mock_context,  # type: ignore
        )

        result_data = json.loads(result[0].text)
        self.assertEqual(result_data["email"]["body"], "A" * 20)  # 20 chars from position 10
        self.assertEqual(result_data["body_pagination"]["offset"], 10)
        self.assertEqual(result_data["body_pagination"]["limit"], 20)
        self.assertEqual(result_data["body_pagination"]["total_length"], 100)
        self.assertTrue(result_data["body_pagination"]["has_more"])  # 70 more chars remaining

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_get_email_details_exclude_body(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test email details with body excluded (body_limit=0)."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value

        # Use a copy to avoid mutation
        email_copy = {**self.sample_email}
        original_body_length = len(email_copy["body"])
        mock_gmail_service_instance.get_email_by_id_with_attachments.return_value = (
            email_copy,
            {},
        )

        result = await get_email_details(
            user_id=self.test_user_id,
            email_id=self.test_email_id,
            body_limit=0,
            ctx=self.mock_context,  # type: ignore
        )

        result_data = json.loads(result[0].text)
        self.assertIsNone(result_data["email"]["body"])
        self.assertEqual(result_data["body_pagination"]["total_length"], original_body_length)

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_get_gmail_labels_success(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test successful retrieval of Gmail labels."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value
        sample_labels = [
            {"id": "INBOX", "name": "INBOX"},
            {"id": "SENT", "name": "SENT"},
        ]
        mock_gmail_service_instance.get_labels.return_value = sample_labels

        result = await get_gmail_labels(
            user_id=self.test_user_id,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(json.loads(result[0].text), sample_labels)

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_service)
        mock_gmail_service_instance.get_labels.assert_called_once()

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_bulk_get_gmail_emails_success(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test successful bulk retrieval of Gmail emails."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_gmail_service_instance.get_email_by_id_with_attachments.return_value = (
            self.sample_email,
            {"attachment1": self.sample_attachment},
        )

        result = await bulk_get_gmail_emails(
            user_id=self.test_user_id,
            email_ids=["email1", "email2"],
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        expected_results = [
            {
                "email": self.sample_email,
                "attachments": {"attachment1": self.sample_attachment},
            },
            {
                "email": self.sample_email,
                "attachments": {"attachment1": self.sample_attachment},
            },
        ]
        self.assertEqual(json.loads(result[0].text), expected_results)

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_service)
        self.assertEqual(mock_gmail_service_instance.get_email_by_id_with_attachments.call_count, 2)

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_create_gmail_draft_success(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test successful creation of Gmail draft."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_gmail_service_instance.create_draft.return_value = self.sample_draft

        result = await create_gmail_draft(
            user_id=self.test_user_id,
            to="recipient@example.com",
            subject="Test Subject",
            body="Test Body",
            cc=["cc@example.com"],
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(json.loads(result[0].text), self.sample_draft)

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_service)
        mock_gmail_service_instance.create_draft.assert_called_once_with(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test Body",
            cc=["cc@example.com"],
        )

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_delete_gmail_draft_success(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test successful deletion of Gmail draft."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_gmail_service_instance.delete_draft.return_value = True

        result = await delete_gmail_draft(
            user_id=self.test_user_id,
            draft_id=self.test_draft_id,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(result[0].text, f"Successfully deleted draft ID: {self.test_draft_id}")

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_service)
        mock_gmail_service_instance.delete_draft.assert_called_once_with(draft_id=self.test_draft_id)

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_create_gmail_reply_success(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test successful creation of Gmail reply."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_gmail_service_instance.get_email_by_id_with_attachments.return_value = (
            self.sample_email,
            {"attachment1": self.sample_attachment},
        )
        mock_gmail_service_instance.create_reply.return_value = {
            "id": "reply123",
            "threadId": "thread123",
        }

        result = await create_gmail_reply(
            user_id=self.test_user_id,
            original_message_id=self.test_email_id,
            reply_body="Test Reply",
            send=False,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(json.loads(result[0].text), {"id": "reply123", "threadId": "thread123"})

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_service)
        mock_gmail_service_instance.get_email_by_id_with_attachments.assert_called_once_with(
            email_id=self.test_email_id
        )
        mock_gmail_service_instance.create_reply.assert_called_once_with(
            original_message=self.sample_email,
            reply_body="Test Reply",
            send=False,
            cc=None,
        )

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_get_gmail_attachment_success(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test successful retrieval of Gmail attachment."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_gmail_service_instance.get_attachment.return_value = self.sample_attachment

        result = await get_gmail_attachment(
            user_id=self.test_user_id,
            message_id=self.test_email_id,
            attachment_id=self.test_attachment_id,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(json.loads(result[0].text), self.sample_attachment)

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_service)
        mock_gmail_service_instance.get_attachment.assert_called_once_with(
            message_id=self.test_email_id,
            attachment_id=self.test_attachment_id,
        )

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_bulk_save_gmail_attachments_success(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test successful bulk saving of Gmail attachments."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_gmail_service_instance.get_attachment.return_value = self.sample_attachment

        attachment_info = [
            {
                "message_id": self.test_email_id,
                "attachment_id": self.test_attachment_id,
                "save_path": "/tmp/test.pdf",
            }
        ]

        result = await bulk_save_gmail_attachments(
            user_id=self.test_user_id,
            attachments=attachment_info,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertTrue("Successfully processed attachment" in result[0].text)

        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_service)
        mock_gmail_service_instance.get_attachment.assert_called_once_with(self.test_email_id, self.test_attachment_id)

    @patch("src.mcp_gsuite.gmail_tools.auth_helper.get_gmail_service")
    @patch("src.mcp_gsuite.gmail_tools.gmail_impl.GmailService")
    async def test_query_gmail_emails_error(self, mock_gmail_service_class, mock_get_gmail_service):
        """Test error handling in query_gmail_emails."""
        mock_service = MagicMock()
        mock_get_gmail_service.return_value = mock_service
        mock_gmail_service_instance = mock_gmail_service_class.return_value
        mock_gmail_service_instance.query_emails.side_effect = Exception("Test error")

        with self.assertRaises(RuntimeError) as context:
            await query_gmail_emails(
                user_id=self.test_user_id,
                query="is:unread",
                max_results=10,
                ctx=self.mock_context,  # type: ignore
            )
        self.assertTrue("Error querying emails: Test error" in str(context.exception))
        self.assertEqual(len(self.mock_context.error_messages), 1)
        self.assertTrue("Error querying emails: Test error" in self.mock_context.error_messages[0])
        mock_get_gmail_service.assert_called_once_with(self.test_user_id)
        mock_gmail_service_class.assert_called_once_with(mock_service)
        mock_gmail_service_instance.query_emails.assert_called_once_with(query="is:unread", max_results=10)
