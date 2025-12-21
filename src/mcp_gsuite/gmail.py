import base64
import logging
import traceback
from email.mime.text import MIMEText


class GmailService:
    def __init__(self, service):
        # credentials = gauth.get_stored_credentials(user_id=user_id) # Handled by auth_helper
        # if not credentials:
        #     raise RuntimeError("No Oauth2 credentials stored")
        # self.service = build('gmail', 'v1', credentials=credentials) # Service is now passed in
        if not service:
            raise ValueError("A valid Google API service client must be provided.")
        self.service = service

    def _parse_message(self, txt, parse_body=False) -> dict | None:
        """
        Parse a Gmail message into a structured format.

        Args:
            txt (dict): Raw message from Gmail API
            parse_body (bool): Whether to parse and include the message body (default: False)

        Returns:
            dict: Parsed message containing comprehensive metadata
            None: If parsing fails
        """
        try:
            message_id = txt.get("id")
            thread_id = txt.get("threadId")
            payload = txt.get("payload", {})
            headers = payload.get("headers", [])

            metadata = {
                "id": message_id,
                "threadId": thread_id,
                "historyId": txt.get("historyId"),
                "internalDate": txt.get("internalDate"),
                "sizeEstimate": txt.get("sizeEstimate"),
                "labelIds": txt.get("labelIds", []),
                "snippet": txt.get("snippet"),
            }

            for header in headers:
                name = header.get("name", "").lower()
                value = header.get("value", "")

                if name == "subject":
                    metadata["subject"] = value
                elif name == "from":
                    metadata["from"] = value
                elif name == "to":
                    metadata["to"] = value
                elif name == "date":
                    metadata["date"] = value
                elif name == "cc":
                    metadata["cc"] = value
                elif name == "bcc":
                    metadata["bcc"] = value
                elif name == "message-id":
                    metadata["message_id"] = value
                elif name == "in-reply-to":
                    metadata["in_reply_to"] = value
                elif name == "references":
                    metadata["references"] = value
                elif name == "delivered-to":
                    metadata["delivered_to"] = value

            if parse_body:
                body = self._extract_body(payload)
                if body:
                    metadata["body"] = body

                metadata["mimeType"] = payload.get("mimeType")

            return metadata
        except Exception as e:
            logging.error(f"Error parsing message: {e!s}")
            logging.error(traceback.format_exc())
            return None

    def _extract_body(self, payload) -> str | None:
        """
        Extract the email body from the payload.
        Handles both multipart and single part messages, including nested multiparts.
        """
        try:
            # For single part text/plain messages
            if payload.get("mimeType") == "text/plain":
                data = payload.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")

            # For single part text/html messages
            if payload.get("mimeType") == "text/html":
                data = payload.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")

            # For multipart messages (both alternative and related)
            if payload.get("mimeType", "").startswith("multipart/"):
                parts = payload.get("parts", [])

                # First try to find a direct text/plain part
                for part in parts:
                    if part.get("mimeType") == "text/plain":
                        data = part.get("body", {}).get("data")
                        if data:
                            return base64.urlsafe_b64decode(data).decode("utf-8")

                # If no direct text/plain, recursively check nested multipart structures
                for part in parts:
                    if part.get("mimeType", "").startswith("multipart/"):
                        nested_body = self._extract_body(part)
                        if nested_body:
                            return nested_body

                # If still no body found, try the first part as fallback
                # Check if 'body' and 'data' exist before accessing
                if parts and "body" in parts[0] and parts[0]["body"] and "data" in parts[0]["body"]:
                    data = parts[0]["body"]["data"]
                    return base64.urlsafe_b64decode(data).decode("utf-8")

            return None  # Return None if no body found after all checks

        except Exception as e:
            logging.error(f"Error extracting body: {e!s}")
            return None

    def get_labels(self) -> list:
        """Lists all labels in the user's mailbox."""
        try:
            results = self.service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])
            return labels
        except Exception as e:
            logging.error(f"An error occurred fetching labels: {e}")
            return []

    def query_emails(self, query=None, max_results=100):
        """
        Query emails from Gmail based on a search query.

        Args:
            query (str, optional): Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')
                                If None, returns all emails
            max_results (int): Maximum number of emails to retrieve (1-500, default: 100)

        Returns:
            list: List of parsed email messages, newest first
        """
        try:
            # Ensure max_results is within API limits

            max_results = min(max(1, max_results), 500)

            # Get the list of messages

            result = (
                self.service.users()
                .messages()
                .list(userId="me", maxResults=max_results, q=query if query else "")
                .execute()
            )

            messages = result.get("messages", [])
            parsed = []

            # Fetch full message details for each message
            for msg in messages:
                txt = self.service.users().messages().get(userId="me", id=msg["id"]).execute()
                parsed_message = self._parse_message(txt=txt, parse_body=False)
                if parsed_message:
                    parsed.append(parsed_message)

            return parsed

        except Exception as e:
            logging.error(f"Error reading emails: {e!s}")
            logging.error(traceback.format_exc())
            return []

    def _extract_attachments_from_parts(self, parts: list, attachments: dict) -> None:
        """
        Recursively extract attachments from message parts.

        This handles nested multipart structures (e.g., multipart/mixed containing
        multipart/alternative) to find all attachments at any nesting level.

        Args:
            parts: List of message parts to scan
            attachments: Dictionary to populate with found attachments (modified in place)
        """
        for part in parts:
            # Check if this part has an attachment
            if "body" in part and "attachmentId" in part["body"]:
                attachment_id = part["body"]["attachmentId"]
                part_id = part["partId"]
                attachment = {
                    "filename": part.get("filename", ""),
                    "mimeType": part.get("mimeType", "application/octet-stream"),
                    "attachmentId": attachment_id,
                    "partId": part_id,
                }
                attachments[part_id] = attachment

            # Recursively check nested parts (for multipart/* types)
            if "parts" in part:
                self._extract_attachments_from_parts(part["parts"], attachments)

    def get_email_by_id_with_attachments(
        self, email_id: str, parse_body: bool = True
    ) -> tuple[dict, dict] | tuple[None, dict]:
        """
        Fetch and parse a complete email message by its ID including attachment IDs.

        Args:
            email_id (str): The Gmail message ID to retrieve
            parse_body (bool): Whether to parse and include the message body (default: True)

        Returns:
            Tuple[dict, dict]: Complete parsed email message including body and dict of attachments
            Tuple[None, dict]: If retrieval or parsing fails, returns None for email and empty dict for attachments
        """
        try:
            # Fetch the complete message by ID
            message = self.service.users().messages().get(userId="me", id=email_id).execute()

            # Parse the message with body included
            parsed_email = self._parse_message(txt=message, parse_body=parse_body)

            if parsed_email is None:
                return None, {}

            attachments = {}
            # Check if 'parts' exists in payload before trying to access it
            if "payload" in message and "parts" in message["payload"]:
                # Recursively extract attachments from all nested parts
                self._extract_attachments_from_parts(message["payload"]["parts"], attachments)
            else:
                # Handle case when there are no parts (single part message)
                logging.info(f"Email {email_id} does not have 'parts' in payload (likely single part message)")
                if (
                    "payload" in message
                    and "body" in message["payload"]
                    and "attachmentId" in message["payload"]["body"]
                ):
                    # Handle potential attachment in single part message
                    attachment_id = message["payload"]["body"]["attachmentId"]
                    attachment = {
                        "filename": message["payload"].get("filename", "attachment"),
                        "mimeType": message["payload"].get("mimeType", "application/octet-stream"),
                        "attachmentId": attachment_id,
                        "partId": "0",
                    }
                    attachments["0"] = attachment

            return parsed_email, attachments

        except Exception as e:
            logging.error(f"Error retrieving email {email_id}: {e!s}")
            logging.error(traceback.format_exc())
            return None, {}

    def create_draft(self, to: str, subject: str, body: str, cc: list[str] | None = None) -> dict | None:
        """
        Create a draft email message.

        Args:
            to (str): Email address of the recipient
            subject (str): Subject line of the email
            body (str): Body content of the email
            cc (list[str], optional): List of email addresses to CC

        Returns:
            dict: Draft message data including the draft ID if successful
            None: If creation fails
        """
        try:
            # Create message body
            message = {
                "to": to,
                "subject": subject,
                "text": body,
            }
            if cc:
                message["cc"] = ",".join(cc)

            # Create the message in MIME format
            mime_message = MIMEText(body)
            mime_message["to"] = to
            mime_message["subject"] = subject
            if cc:
                mime_message["cc"] = ",".join(cc)

            # Encode the message
            raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

            # Create the draft
            draft = self.service.users().drafts().create(userId="me", body={"message": {"raw": raw_message}}).execute()

            return draft

        except Exception as e:
            logging.error(f"Error creating draft: {e!s}")
            logging.error(traceback.format_exc())
            return None

    def delete_draft(self, draft_id: str) -> bool:
        """
        Delete a draft email message.

        Args:
            draft_id (str): The ID of the draft to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            self.service.users().drafts().delete(userId="me", id=draft_id).execute()
            return True

        except Exception as e:
            logging.error(f"Error deleting draft {draft_id}: {e!s}")
            logging.error(traceback.format_exc())
            return False

    def create_reply(
        self,
        original_message: dict,
        reply_body: str,
        send: bool = False,
        cc: list[str] | None = None,
    ) -> dict | None:
        """
        Create a reply to an email message and either send it or save as draft.

        Args:
            original_message (dict): The original message data (as returned by get_email_by_id)
            reply_body (str): Body content of the reply
            send (bool): If True, sends the reply immediately. If False, saves as draft.
            cc (list[str], optional): List of email addresses to CC

        Returns:
            dict: Sent message or draft data if successful
            None: If operation fails
        """
        try:
            to_address = original_message.get("from")
            if not to_address:
                raise ValueError("Could not determine original sender's address")

            subject = original_message.get("subject", "")
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"

            original_date = original_message.get("date", "")
            original_from = original_message.get("from", "")
            original_body = original_message.get("body", "")

            original_body_quoted = original_body.replace("\n", "\n> ") if original_body else "[No message body]"
            full_reply_body = f"{reply_body}\n\nOn {original_date}, {original_from} wrote:\n> {original_body_quoted}"

            mime_message = MIMEText(full_reply_body)
            mime_message["to"] = to_address
            mime_message["subject"] = subject
            if cc:
                mime_message["cc"] = ",".join(cc)

            mime_message["In-Reply-To"] = original_message.get("id", "")
            mime_message["References"] = original_message.get("id", "")

            raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

            message_body = {
                "raw": raw_message,
                "threadId": original_message.get("threadId"),  # Ensure it's added to the same thread
            }

            if send:
                # Send the reply immediately
                result = self.service.users().messages().send(userId="me", body=message_body).execute()
            else:
                # Save as draft
                result = self.service.users().drafts().create(userId="me", body={"message": message_body}).execute()

            return result

        except Exception as e:
            logging.error(f"Error {'sending' if send else 'drafting'} reply: {e!s}")
            logging.error(traceback.format_exc())
            return None

    def get_attachment(self, message_id: str, attachment_id: str) -> dict | None:
        """
        Retrieves a Gmail attachment by its ID.

        Args:
            message_id (str): The ID of the Gmail message containing the attachment
            attachment_id (str): The ID of the attachment to retrieve

        Returns:
            dict: Attachment data including filename and base64-encoded content
            None: If retrieval fails
        """
        try:
            attachment = (
                self.service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
            return {"size": attachment.get("size"), "data": attachment.get("data")}

        except Exception as e:
            logging.error(f"Error retrieving attachment {attachment_id} from message {message_id}: {e!s}")
            logging.error(traceback.format_exc())
            return None
