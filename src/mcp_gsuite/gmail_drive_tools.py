import base64
import json
import logging
from typing import Annotated

from fastmcp import Context
from mcp.types import TextContent

from . import auth_helper
from . import gmail as gmail_impl
from .common import get_user_id_description
from .drive import DriveService

logger = logging.getLogger(__name__)


async def save_gmail_attachment_to_drive(
    user_id: Annotated[str, get_user_id_description()],
    message_id: Annotated[str, "The ID of the Gmail message containing the attachment."],
    part_id: Annotated[
        str,
        "The part ID of the attachment to save (e.g., '1', '0.1'). "
        "This is more stable than attachment_id and should be preferred.",
    ],
    folder_id: Annotated[
        str | None, "Optional Google Drive folder ID to save to. If not provided, saves to root."
    ] = None,
    rename: Annotated[
        str | None, "Optional new filename for the attachment. If not provided, uses original filename."
    ] = None,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Save a Gmail attachment to Google Drive.

    Uses part_id to identify the attachment, which is stable across API calls.
    The part_id can be found in the attachments dictionary returned by get_email_details.
    """
    try:
        if ctx:
            await ctx.info(
                f"Saving attachment (part_id={part_id}) from message ID {message_id} to Drive for user {user_id}"
            )

        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)

        d_service = auth_helper.get_drive_service(user_id)
        drive_service = DriveService(d_service)

        _, attachments = gmail_service.get_email_by_id_with_attachments(
            email_id=message_id, parse_body=False
        )

        # Find attachment by part_id
        if part_id not in attachments:
            available_parts = list(attachments.keys())
            error_msg = (
                f"Part ID '{part_id}' not found in message {message_id}. " f"Available part IDs: {available_parts}"
            )
            if ctx:
                await ctx.warning(error_msg)
            return [TextContent(type="text", text=error_msg)]

        attachment_metadata = attachments[part_id]
        # Use the current attachmentId from the fresh API response
        current_attachment_id = attachment_metadata.get("attachmentId")

        if not current_attachment_id:
            error_msg = f"No attachmentId found for part_id '{part_id}' in message {message_id}"
            if ctx:
                await ctx.warning(error_msg)
            return [TextContent(type="text", text=error_msg)]

        attachment_data = gmail_service.get_attachment(message_id=message_id, attachment_id=current_attachment_id)

        if not attachment_data or not attachment_data.get("data"):
            error_msg = f"Failed to retrieve attachment data for part_id '{part_id}' from message {message_id}"
            if ctx:
                await ctx.warning(error_msg)
            return [TextContent(type="text", text=error_msg)]

        filename = rename or attachment_metadata.get("filename", "unknown_file")
        mime_type = attachment_metadata.get("mimeType", "application/octet-stream")

        # Decode base64 data - Gmail API returns URL-safe base64 encoded content
        decoded_content = base64.urlsafe_b64decode(attachment_data["data"])

        file_result = drive_service.upload_file(
            file_content=decoded_content, file_name=filename, mime_type=mime_type, parent_folder_id=folder_id
        )

        if not file_result:
            error_msg = f"Failed to save attachment {filename} to Google Drive"
            if ctx:
                await ctx.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

        # Return only essential fields to minimize context consumption
        result = {
            "id": file_result.get("id"),
            "name": file_result.get("name"),
            "md5Checksum": file_result.get("md5Checksum"),
            "webViewLink": file_result.get("webViewLink"),
        }

        if ctx:
            await ctx.info(f"Saved '{filename}' to Drive (ID: {result['id']})")

        return [TextContent(type="text", text=json.dumps(result))]

    except Exception as e:
        logger.error(f"Error in save_gmail_attachment_to_drive for {user_id}: {e}", exc_info=True)
        error_msg = f"Error saving attachment to Drive: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def bulk_save_gmail_attachments_to_drive(
    user_id: Annotated[str, get_user_id_description()],
    attachments: Annotated[
        list[dict],
        "List of attachment information dictionaries. Each should have message_id and part_id, "
        "and optionally folder_id and rename fields. "
        "Example: [{'message_id': 'abc123', 'part_id': '1', 'rename': 'invoice.pdf'}]",
    ],
    folder_id: Annotated[
        str | None, "Default Google Drive folder ID to save attachments to if not specified per attachment."
    ] = None,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Save multiple Gmail attachments to Google Drive in a single request.

    Uses part_id to identify attachments, which is stable across API calls.
    The part_id can be found in the attachments dictionary returned by get_email_details.
    """
    try:
        if ctx:
            await ctx.info(f"Saving {len(attachments)} attachments to Drive for user {user_id}")

        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)

        d_service = auth_helper.get_drive_service(user_id)
        drive_service = DriveService(d_service)

        results = []
        for attachment_info in attachments:
            try:
                message_id = attachment_info.get("message_id")
                part_id = attachment_info.get("part_id")

                if not message_id or not part_id:
                    error_msg = "Missing required fields in attachment info (message_id, part_id)"
                    if ctx:
                        await ctx.error(error_msg)
                    results.append(TextContent(type="text", text=error_msg))
                    continue

                item_folder_id = attachment_info.get("folder_id", folder_id)  # Use per-item folder_id or default
                rename = attachment_info.get("rename")  # Optional rename field

                _, attachments_metadata = gmail_service.get_email_by_id_with_attachments(
                    email_id=message_id, parse_body=False
                )

                # Find attachment by part_id
                if part_id not in attachments_metadata:
                    available_parts = list(attachments_metadata.keys())
                    error_msg = (
                        f"Part ID '{part_id}' not found in message {message_id}. "
                        f"Available part IDs: {available_parts}"
                    )
                    if ctx:
                        await ctx.warning(error_msg)
                    results.append(TextContent(type="text", text=error_msg))
                    continue

                attachment_metadata = attachments_metadata[part_id]
                # Use the current attachmentId from the fresh API response
                current_attachment_id = attachment_metadata.get("attachmentId")

                if not current_attachment_id:
                    error_msg = f"No attachmentId found for part_id '{part_id}' in message {message_id}"
                    if ctx:
                        await ctx.warning(error_msg)
                    results.append(TextContent(type="text", text=error_msg))
                    continue

                attachment_data = gmail_service.get_attachment(
                    message_id=message_id, attachment_id=current_attachment_id
                )

                if not attachment_data or not attachment_data.get("data"):
                    error_msg = f"Failed to retrieve attachment data for part_id '{part_id}' from message {message_id}"
                    if ctx:
                        await ctx.warning(error_msg)
                    results.append(TextContent(type="text", text=error_msg))
                    continue

                filename = rename or attachment_metadata.get("filename", "unknown_file")
                mime_type = attachment_metadata.get("mimeType", "application/octet-stream")

                # Decode base64 data - Gmail API returns URL-safe base64 encoded content
                decoded_content = base64.urlsafe_b64decode(attachment_data["data"])

                file_result = drive_service.upload_file(
                    file_content=decoded_content,
                    file_name=filename,
                    mime_type=mime_type,
                    parent_folder_id=item_folder_id,
                )

                if not file_result:
                    error_msg = f"Failed to save attachment {filename} to Google Drive"
                    if ctx:
                        await ctx.error(error_msg)
                    results.append(TextContent(type="text", text=error_msg))
                    continue

                # Return only essential fields to minimize context consumption
                result = {
                    "id": file_result.get("id"),
                    "name": file_result.get("name"),
                    "md5Checksum": file_result.get("md5Checksum"),
                    "webViewLink": file_result.get("webViewLink"),
                }

                if ctx:
                    await ctx.info(f"Saved '{filename}' to Drive (ID: {result['id']})")

                results.append(TextContent(type="text", text=json.dumps(result)))

            except Exception as inner_e:
                error_msg = f"Error processing attachment: {inner_e!s}"
                logger.error(error_msg, exc_info=True)
                if ctx:
                    await ctx.error(error_msg)
                results.append(TextContent(type="text", text=error_msg))

        return results

    except Exception as e:
        logger.error(f"Error in bulk_save_gmail_attachments_to_drive for {user_id}: {e}", exc_info=True)
        error_msg = f"Error saving attachments to Drive: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
