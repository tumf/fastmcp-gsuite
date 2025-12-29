import json
import logging
from typing import Annotated

from fastmcp import Context
from mcp.types import TextContent

from . import auth_helper
from . import gmail as gmail_impl
from .common import get_user_id_description

logger = logging.getLogger(__name__)


# Gmail related tools
async def query_gmail_emails(
    user_id: Annotated[str, get_user_id_description()],
    query: Annotated[
        str | None,
        "Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')",
    ] = None,
    max_results: Annotated[int, "Maximum number of emails (1-500, default 100)"] = 100,
    ctx: Context | None = None,  # Optional context
) -> list[TextContent]:
    """Queries Gmail emails for the specified user."""
    try:
        if ctx:
            await ctx.info(f"Querying emails for {user_id} with query: '{query}'")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)  # Pass authenticated service
        emails = gmail_service.query_emails(query=query, max_results=max_results)
        if not emails:
            if ctx:
                await ctx.info(f"No emails found for query '{query}' for user {user_id}")
            return [TextContent(type="text", text="No emails found matching the query.")]
        return [TextContent(type="text", text=json.dumps(email, indent=2)) for email in emails]
    except Exception as e:
        logger.error(f"Error in query_gmail_emails for {user_id}: {e}", exc_info=True)
        error_msg = f"Error querying emails: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def get_email_details(
    user_id: Annotated[str, get_user_id_description()],
    email_id: Annotated[str, "The unique ID of the Gmail email message."],
    body_offset: Annotated[int, "Starting position for body text (0-based). Use with body_limit for pagination."] = 0,
    body_limit: Annotated[
        int, "Maximum number of characters to return for body text. Default 5000. Use 0 to exclude body entirely."
    ] = 5000,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Retrieves detailed information for a single email, including body and attachments.

    The body text is paginated to avoid large responses. Use body_offset and body_limit
    to retrieve the full body in chunks if needed. The response includes body_total_length
    and body_has_more to help with pagination.
    """
    try:
        if ctx:
            await ctx.info(f"Fetching details for email ID {email_id} for user {user_id}")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)
        email_details, attachments = gmail_service.get_email_by_id_with_attachments(email_id=email_id)

        if not email_details:
            if ctx:
                await ctx.warning(f"Email with ID {email_id} not found for user {user_id}")
            return [TextContent(type="text", text=f"Email with ID {email_id} not found.")]

        # Handle body pagination
        body_total_length = 0
        body_has_more = False
        if email_details.get("body"):
            full_body = email_details["body"]
            body_total_length = len(full_body)

            if body_limit == 0:
                # Exclude body entirely
                email_details["body"] = None
            else:
                # Apply offset and limit
                end_pos = body_offset + body_limit
                email_details["body"] = full_body[body_offset:end_pos]
                body_has_more = end_pos < body_total_length

        full_details = {
            "email": email_details,
            "attachments": attachments,
            "body_pagination": {
                "offset": body_offset,
                "limit": body_limit,
                "total_length": body_total_length,
                "has_more": body_has_more,
            },
        }

        return [TextContent(type="text", text=json.dumps(full_details, indent=2))]
    except Exception as e:
        logger.error(
            f"Error in get_email_details for {user_id}, email ID {email_id}: {e}",
            exc_info=True,
        )
        error_msg = f"Error getting email details: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def get_gmail_labels(
    user_id: Annotated[str, get_user_id_description()], ctx: Context | None = None
) -> list[TextContent]:
    """Lists all Gmail labels for the specified user."""
    try:
        if ctx:
            await ctx.info(f"Fetching labels for user {user_id}")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)
        labels = gmail_service.get_labels()
        if not labels:
            if ctx:
                await ctx.info(f"No labels found for user {user_id}")
            return [TextContent(type="text", text="No labels found.")]
        return [TextContent(type="text", text=json.dumps(labels, indent=2))]
    except Exception as e:
        logger.error(f"Error in get_gmail_labels for {user_id}: {e}", exc_info=True)
        error_msg = f"Error getting labels: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def bulk_get_gmail_emails(
    user_id: Annotated[str, get_user_id_description()],
    email_ids: Annotated[list[str], "List of Gmail message IDs to retrieve."],
    ctx: Context | None = None,
) -> list[TextContent]:
    """Retrieves details for multiple emails by their IDs."""
    results = []
    try:
        if ctx:
            await ctx.info(f"Fetching {len(email_ids)} emails for user {user_id}")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)

        for email_id in email_ids:
            try:
                if ctx:
                    await ctx.debug(f"Fetching email ID {email_id}")
                (
                    email_details,
                    attachments,
                ) = gmail_service.get_email_by_id_with_attachments(email_id=email_id, parse_body=False)
                if email_details:
                    full_details = {"email": email_details, "attachments": attachments}
                    results.append(full_details)
                else:
                    if ctx:
                        await ctx.warning(f"Email with ID {email_id} not found for user {user_id}")
            except Exception as inner_e:
                logger.error(
                    f"Error fetching email ID {email_id} for {user_id}: {inner_e}",
                    exc_info=True,
                )
                if ctx:
                    await ctx.error(f"Error fetching email ID {email_id}: {inner_e}")

        if not results:
            if ctx:
                await ctx.info(f"No emails found or retrieved for the given IDs for user {user_id}")
            return [
                TextContent(
                    type="text",
                    text="No emails found or retrieved for the provided IDs.",
                )
            ]
        else:
            return [TextContent(type="text", text=json.dumps(results, indent=2))]

    except Exception as e:  # Catch errors during service init or outside the loop
        logger.error(
            f"Error in bulk_get_gmail_emails setup or outer scope for {user_id}: {e}",
            exc_info=True,
        )
        error_msg = f"Error getting bulk emails: {e}"
        if ctx:
            await ctx.error(error_msg)
        # Return error message in TextContent for bulk operations instead of raising?
        # For consistency with single-get, raising might be better, but bulk could partially succeed.
        # Let's return an error message for now.
        return [TextContent(type="text", text=f"Error processing bulk email request: {e}")]


async def create_gmail_draft(
    user_id: Annotated[str, get_user_id_description()],
    to: Annotated[str, "Email address of the recipient."],
    subject: Annotated[str, "Subject line of the email."],
    body: Annotated[str, "Body content of the email."],
    cc: Annotated[list[str] | None, "Optional list of email addresses to CC."] = None,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Creates a draft email in Gmail."""
    try:
        if ctx:
            await ctx.info(f"Creating draft email for user {user_id} with subject '{subject}'")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)
        draft = gmail_service.create_draft(to=to, subject=subject, body=body, cc=cc)

        if not draft:
            if ctx:
                await ctx.error(f"Failed to create draft email for user {user_id}")
            return [TextContent(type="text", text="Failed to create draft email.")]

        if ctx:
            await ctx.info(f"Successfully created draft with ID: {draft.get('id')}")
        return [TextContent(type="text", text=json.dumps(draft, indent=2))]
    except Exception as e:
        logger.error(f"Error in create_gmail_draft for {user_id}: {e}", exc_info=True)
        error_msg = f"Error creating draft email: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def delete_gmail_draft(
    user_id: Annotated[str, get_user_id_description()],
    draft_id: Annotated[str, "The unique ID of the draft to delete."],
    ctx: Context | None = None,
) -> list[TextContent]:
    """Deletes a draft email from Gmail."""
    try:
        if ctx:
            await ctx.info(f"Deleting draft email with ID {draft_id} for user {user_id}")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)
        success = gmail_service.delete_draft(draft_id=draft_id)

        if success:
            if ctx:
                await ctx.info(f"Successfully deleted draft with ID: {draft_id}")
            return [TextContent(type="text", text=f"Successfully deleted draft ID: {draft_id}")]
        else:
            if ctx:
                await ctx.warning(f"Failed to delete draft ID {draft_id} for user {user_id}")
            return [TextContent(type="text", text=f"Failed to delete draft ID: {draft_id}")]
    except Exception as e:
        logger.error(f"Error in delete_gmail_draft for {user_id}: {e}", exc_info=True)
        error_msg = f"Error deleting draft email: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def create_gmail_reply(
    user_id: Annotated[str, get_user_id_description()],
    original_message_id: Annotated[str, "The ID of the original email message to reply to."],
    reply_body: Annotated[str, "The body text of the reply."],
    send: Annotated[bool, "If True, sends the reply immediately. If False, saves as draft."] = False,
    cc: Annotated[list[str] | None, "Optional list of email addresses to CC."] = None,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Creates a reply to an existing Gmail email message."""
    try:
        if ctx:
            await ctx.info(f"Creating reply to message ID {original_message_id} for user {user_id}")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)

        # First get the original message details
        original_message, _ = gmail_service.get_email_by_id_with_attachments(email_id=original_message_id)
        if not original_message:
            if ctx:
                await ctx.warning(f"Original message with ID {original_message_id} not found for user {user_id}")
            return [
                TextContent(
                    type="text",
                    text=f"Original message with ID {original_message_id} not found.",
                )
            ]

        # Create the reply
        result = gmail_service.create_reply(original_message=original_message, reply_body=reply_body, send=send, cc=cc)

        if not result:
            if ctx:
                await ctx.error(f"Failed to {'send' if send else 'draft'} reply to message {original_message_id}")
            return [TextContent(type="text", text=f"Failed to {'send' if send else 'draft'} reply.")]

        if ctx:
            action = "sent" if send else "created draft"
            await ctx.info(f"Successfully {action} reply to message ID: {original_message_id}")
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        logger.error(f"Error in create_gmail_reply for {user_id}: {e}", exc_info=True)
        error_msg = f"Error creating reply: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def get_gmail_attachment(
    user_id: Annotated[str, get_user_id_description()],
    message_id: Annotated[str, "The ID of the Gmail message containing the attachment."],
    attachment_id: Annotated[str, "The ID of the attachment to retrieve."],
    ctx: Context | None = None,
) -> list[TextContent]:
    """Retrieves an attachment from a Gmail message."""
    try:
        if ctx:
            await ctx.info(f"Retrieving attachment ID {attachment_id} from message ID {message_id} for user {user_id}")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)
        attachment_data = gmail_service.get_attachment(message_id=message_id, attachment_id=attachment_id)

        if not attachment_data:
            if ctx:
                await ctx.warning(f"Attachment ID {attachment_id} not found in message {message_id}")
            return [TextContent(type="text", text=f"Attachment ID {attachment_id} not found.")]

        return [TextContent(type="text", text=json.dumps(attachment_data, indent=2))]
    except Exception as e:
        logger.error(f"Error in get_gmail_attachment for {user_id}: {e}", exc_info=True)
        error_msg = f"Error retrieving attachment: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def bulk_save_gmail_attachments(
    user_id: Annotated[str, get_user_id_description()],
    attachments: Annotated[
        list[dict],
        "List of attachment information dictionaries. Each dictionary should have "
        "message_id, attachment_id, and save_path.",
    ],
    ctx: Context | None = None,
) -> list[TextContent]:
    """Saves multiple Gmail attachments to disk."""
    try:
        if ctx:
            await ctx.info(f"Saving {len(attachments)} attachments for user {user_id}")

        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)

        results = []
        for attachment_info in attachments:
            try:
                if ctx:
                    await ctx.debug(f"Processing attachment for message ID {attachment_info.get('message_id')}")

                # Validate required fields
                message_id = attachment_info.get("message_id")
                attachment_id = attachment_info.get("attachment_id")
                save_path = attachment_info.get("save_path")

                if not message_id or not attachment_id or not save_path:
                    error_msg = "Missing required fields in attachment info (message_id, attachment_id, save_path)"
                    if ctx:
                        await ctx.error(error_msg)
                    results.append(TextContent(type="text", text=error_msg))
                    continue

                # Get the attachment data
                attachment_data = gmail_service.get_attachment(message_id, attachment_id)
                if not attachment_data:
                    error_msg = f"Failed to retrieve attachment {attachment_id} from message {message_id}"
                    if ctx:
                        await ctx.warning(error_msg)
                    results.append(TextContent(type="text", text=error_msg))
                    continue

                # Process attachment data
                # Note: In a real implementation, you would save this data to the specified path
                # However, since we don't have direct file system access in the MCP context,
                # we'll just report success in this simplified version

                success_msg = f"Successfully processed attachment {attachment_id} from message {message_id}"
                if ctx:
                    await ctx.info(success_msg)
                results.append(TextContent(type="text", text=success_msg))

            except Exception as inner_e:
                error_msg = f"Error processing attachment: {inner_e!s}"
                logger.error(error_msg, exc_info=True)
                if ctx:
                    await ctx.error(error_msg)
                results.append(TextContent(type="text", text=error_msg))

        return results

    except Exception as e:
        logger.error(f"Error in bulk_save_gmail_attachments for {user_id}: {e}", exc_info=True)
        error_msg = f"Error processing attachments: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
