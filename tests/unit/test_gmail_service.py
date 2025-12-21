import base64
import unittest
from typing import Any, cast
from unittest.mock import MagicMock

from src.mcp_gsuite.gmail import GmailService


class TestGmailService(unittest.TestCase):
    def setUp(self):
        # Create a mock for the service
        self.mock_service = MagicMock()

        # Configure users().messages().get().execute() chain
        self.mock_message_get = MagicMock()
        self.mock_messages = MagicMock()
        self.mock_messages.get.return_value = self.mock_message_get

        # Configure users().messages().list().execute() chain
        self.mock_message_list = MagicMock()
        self.mock_messages.list.return_value = self.mock_message_list

        # Configure users().labels().list().execute() chain
        self.mock_labels_list = MagicMock()
        self.mock_labels = MagicMock()
        self.mock_labels.list.return_value = self.mock_labels_list

        # Configure users() to return objects with messages() and labels() methods
        self.mock_users = MagicMock()
        self.mock_users.messages.return_value = self.mock_messages
        self.mock_users.labels.return_value = self.mock_labels

        # Configure service.users() to return the mock_users
        self.mock_service.users.return_value = self.mock_users

        # Create the GmailService instance with the mock service
        self.gmail_service = GmailService(self.mock_service)

    def test_init_with_valid_service(self):
        # Test that initialization works with a valid service
        gmail_service = GmailService(self.mock_service)
        self.assertEqual(gmail_service.service, self.mock_service)

    def test_init_with_invalid_service(self):
        # Test that initialization fails with invalid service
        with self.assertRaises(ValueError):
            GmailService(None)

    def test_get_labels(self):
        # Mock the response
        mock_response = {
            "labels": [
                {"id": "INBOX", "name": "INBOX"},
                {"id": "SENT", "name": "SENT"},
            ]
        }
        self.mock_labels_list.execute.return_value = mock_response

        # Call the method
        labels = self.gmail_service.get_labels()

        # Verify the result
        self.assertEqual(labels, mock_response["labels"])

        # Verify that the correct API calls were made
        self.mock_service.users.assert_called_once()
        self.mock_users.labels.assert_called_once()
        self.mock_labels.list.assert_called_once_with(userId="me")
        self.mock_labels_list.execute.assert_called_once()

    def test_get_labels_exception(self):
        # Mock an exception in the API call
        self.mock_labels_list.execute.side_effect = Exception("API Error")

        # Call the method
        labels = self.gmail_service.get_labels()

        # Verify the result is an empty list
        self.assertEqual(labels, [])

    def test_parse_message(self):
        # Create a mock message
        mock_message = {
            "id": "123",
            "threadId": "thread123",
            "historyId": "history123",
            "internalDate": "1621234567890",
            "sizeEstimate": 12345,
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "This is a snippet",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "test@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 17 May 2021 12:00:00 +0000"},
                    {"name": "Cc", "value": "cc@example.com"},
                    {"name": "Bcc", "value": "bcc@example.com"},
                    {"name": "Message-ID", "value": "<message123@example.com>"},
                    {"name": "In-Reply-To", "value": "<parent123@example.com>"},
                    {"name": "References", "value": "<ref123@example.com>"},
                    {"name": "Delivered-To", "value": "delivered@example.com"},
                ]
            },
        }

        # Parse the message without body
        parsed = self.gmail_service._parse_message(mock_message, parse_body=False)

        # Verify the result - explicitly cast to avoid type errors
        parsed_dict = cast(dict[str, Any], parsed)
        self.assertEqual(parsed_dict["id"], "123")
        self.assertEqual(parsed_dict["threadId"], "thread123")
        self.assertEqual(parsed_dict["subject"], "Test Subject")
        self.assertEqual(parsed_dict["from"], "test@example.com")
        self.assertEqual(parsed_dict["to"], "recipient@example.com")
        self.assertEqual(parsed_dict["date"], "Mon, 17 May 2021 12:00:00 +0000")
        self.assertEqual(parsed_dict["cc"], "cc@example.com")
        self.assertEqual(parsed_dict["bcc"], "bcc@example.com")
        self.assertEqual(parsed_dict["message_id"], "<message123@example.com>")
        self.assertEqual(parsed_dict["in_reply_to"], "<parent123@example.com>")
        self.assertEqual(parsed_dict["references"], "<ref123@example.com>")
        self.assertEqual(parsed_dict["delivered_to"], "delivered@example.com")
        self.assertNotIn("body", parsed_dict)

    def test_parse_message_with_body(self):
        # Create a mock message with a text/plain body
        encoded_body = base64.urlsafe_b64encode(b"Test body").decode()
        mock_message = {
            "id": "123",
            "threadId": "thread123",
            "payload": {
                "mimeType": "text/plain",
                "headers": [{"name": "Subject", "value": "Test Subject"}],
                "body": {"data": encoded_body},
            },
        }

        # Parse the message with body
        parsed = self.gmail_service._parse_message(mock_message, parse_body=True)

        # Verify the result - explicitly cast to avoid type errors
        parsed_dict = cast(dict[str, Any], parsed)
        self.assertEqual(parsed_dict["id"], "123")
        self.assertEqual(parsed_dict["subject"], "Test Subject")
        self.assertEqual(parsed_dict["body"], "Test body")
        self.assertEqual(parsed_dict["mimeType"], "text/plain")

    def test_extract_body_text_plain(self):
        # Create a mock payload with text/plain body
        encoded_body = base64.urlsafe_b64encode(b"Test plain text").decode()
        payload = {"mimeType": "text/plain", "body": {"data": encoded_body}}

        # Extract the body
        body = self.gmail_service._extract_body(payload)

        # Verify the result
        self.assertEqual(body, "Test plain text")

    def test_extract_body_text_html(self):
        # Create a mock payload with text/html body
        encoded_body = base64.urlsafe_b64encode(b"<p>Test HTML</p>").decode()
        payload = {"mimeType": "text/html", "body": {"data": encoded_body}}

        # Extract the body
        body = self.gmail_service._extract_body(payload)

        # Verify the result
        self.assertEqual(body, "<p>Test HTML</p>")

    def test_extract_body_multipart(self):
        # Create a mock payload with multipart body
        encoded_body = base64.urlsafe_b64encode(b"Test multipart").decode()
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": encoded_body}},
                {
                    "mimeType": "text/html",
                    "body": {"data": base64.urlsafe_b64encode(b"<p>HTML version</p>").decode()},
                },
            ],
        }

        # Extract the body
        body = self.gmail_service._extract_body(payload)

        # Verify the result (should extract the text/plain part)
        self.assertEqual(body, "Test multipart")

    def test_query_emails(self):
        # Mock the response for messages.list
        mock_list_response = {
            "messages": [
                {"id": "msg1", "threadId": "thread1"},
                {"id": "msg2", "threadId": "thread2"},
            ]
        }
        self.mock_message_list.execute.return_value = mock_list_response

        # Mock responses for messages.get
        mock_get_responses = [
            {
                "id": "msg1",
                "threadId": "thread1",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Subject 1"},
                        {"name": "From", "value": "from1@example.com"},
                    ]
                },
            },
            {
                "id": "msg2",
                "threadId": "thread2",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Subject 2"},
                        {"name": "From", "value": "from2@example.com"},
                    ]
                },
            },
        ]

        # Configure the mock to return different responses
        self.mock_message_get.execute.side_effect = mock_get_responses

        # Call the method
        emails = self.gmail_service.query_emails(query="is:unread", max_results=10)

        # Verify the result
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0]["id"], "msg1")
        self.assertEqual(emails[0]["subject"], "Subject 1")
        self.assertEqual(emails[1]["id"], "msg2")
        self.assertEqual(emails[1]["subject"], "Subject 2")

        # Verify API calls
        self.mock_messages.list.assert_called_once_with(userId="me", maxResults=10, q="is:unread")

        # Verify that get was called for each message
        self.assertEqual(self.mock_messages.get.call_count, 2)
        self.mock_messages.get.assert_any_call(userId="me", id="msg1")
        self.mock_messages.get.assert_any_call(userId="me", id="msg2")

    def test_get_email_by_id_with_attachments_flat(self):
        """Test attachment extraction from flat (non-nested) message structure."""
        mock_message = {
            "id": "msg123",
            "threadId": "thread123",
            "payload": {
                "mimeType": "multipart/mixed",
                "headers": [{"name": "Subject", "value": "Test with attachment"}],
                "parts": [
                    {
                        "partId": "0",
                        "mimeType": "text/plain",
                        "body": {"data": base64.urlsafe_b64encode(b"Body text").decode()},
                    },
                    {
                        "partId": "1",
                        "mimeType": "application/pdf",
                        "filename": "invoice.pdf",
                        "body": {"attachmentId": "attach123", "size": 12345},
                    },
                ],
            },
        }
        self.mock_message_get.execute.return_value = mock_message

        email, attachments = self.gmail_service.get_email_by_id_with_attachments("msg123")

        self.assertIsNotNone(email)
        self.assertEqual(len(attachments), 1)
        self.assertIn("1", attachments)
        self.assertEqual(attachments["1"]["attachmentId"], "attach123")
        self.assertEqual(attachments["1"]["filename"], "invoice.pdf")
        self.assertEqual(attachments["1"]["mimeType"], "application/pdf")

    def test_get_email_by_id_with_attachments_nested(self):
        """Test attachment extraction from nested multipart structure."""
        # This simulates a common email structure:
        # multipart/mixed
        #   ├── multipart/alternative
        #   │   ├── text/plain
        #   │   └── text/html
        #   └── application/pdf (attachment)
        mock_message = {
            "id": "msg456",
            "threadId": "thread456",
            "payload": {
                "mimeType": "multipart/mixed",
                "headers": [{"name": "Subject", "value": "Nested attachment test"}],
                "parts": [
                    {
                        "partId": "0",
                        "mimeType": "multipart/alternative",
                        "parts": [
                            {
                                "partId": "0.0",
                                "mimeType": "text/plain",
                                "body": {"data": base64.urlsafe_b64encode(b"Plain text").decode()},
                            },
                            {
                                "partId": "0.1",
                                "mimeType": "text/html",
                                "body": {"data": base64.urlsafe_b64encode(b"<p>HTML</p>").decode()},
                            },
                        ],
                    },
                    {
                        "partId": "1",
                        "mimeType": "application/pdf",
                        "filename": "receipt.pdf",
                        "body": {"attachmentId": "attach456", "size": 54321},
                    },
                ],
            },
        }
        self.mock_message_get.execute.return_value = mock_message

        email, attachments = self.gmail_service.get_email_by_id_with_attachments("msg456")

        self.assertIsNotNone(email)
        self.assertEqual(len(attachments), 1)
        self.assertIn("1", attachments)
        self.assertEqual(attachments["1"]["attachmentId"], "attach456")
        self.assertEqual(attachments["1"]["filename"], "receipt.pdf")

    def test_get_email_by_id_with_attachments_deeply_nested(self):
        """Test attachment extraction from deeply nested multipart structure."""
        # Deeply nested structure with attachment inside nested multipart
        mock_message = {
            "id": "msg789",
            "threadId": "thread789",
            "payload": {
                "mimeType": "multipart/mixed",
                "headers": [{"name": "Subject", "value": "Deeply nested test"}],
                "parts": [
                    {
                        "partId": "0",
                        "mimeType": "multipart/related",
                        "parts": [
                            {
                                "partId": "0.0",
                                "mimeType": "multipart/alternative",
                                "parts": [
                                    {
                                        "partId": "0.0.0",
                                        "mimeType": "text/plain",
                                        "body": {"data": base64.urlsafe_b64encode(b"Text").decode()},
                                    },
                                ],
                            },
                            {
                                "partId": "0.1",
                                "mimeType": "image/png",
                                "filename": "inline_image.png",
                                "body": {"attachmentId": "inline123", "size": 1000},
                            },
                        ],
                    },
                    {
                        "partId": "1",
                        "mimeType": "application/pdf",
                        "filename": "document.pdf",
                        "body": {"attachmentId": "attach789", "size": 99999},
                    },
                ],
            },
        }
        self.mock_message_get.execute.return_value = mock_message

        email, attachments = self.gmail_service.get_email_by_id_with_attachments("msg789")

        self.assertIsNotNone(email)
        # Should find both the inline image and the PDF attachment
        self.assertEqual(len(attachments), 2)
        self.assertIn("0.1", attachments)
        self.assertIn("1", attachments)
        self.assertEqual(attachments["0.1"]["attachmentId"], "inline123")
        self.assertEqual(attachments["0.1"]["filename"], "inline_image.png")
        self.assertEqual(attachments["1"]["attachmentId"], "attach789")
        self.assertEqual(attachments["1"]["filename"], "document.pdf")

    def test_get_email_by_id_with_attachments_no_parts(self):
        """Test handling of single-part message without attachments."""
        mock_message = {
            "id": "msg_simple",
            "threadId": "thread_simple",
            "payload": {
                "mimeType": "text/plain",
                "headers": [{"name": "Subject", "value": "Simple message"}],
                "body": {"data": base64.urlsafe_b64encode(b"Just text").decode()},
            },
        }
        self.mock_message_get.execute.return_value = mock_message

        email, attachments = self.gmail_service.get_email_by_id_with_attachments("msg_simple")

        self.assertIsNotNone(email)
        self.assertEqual(len(attachments), 0)


if __name__ == "__main__":
    unittest.main()
