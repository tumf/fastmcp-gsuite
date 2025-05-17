import json
import logging
from typing import Annotated

from fastmcp import Context
from mcp.types import TextContent
from pydantic import Field

from . import auth_helper
from . import gmail as gmail_impl
from .common import get_user_id_description
from .drive import DriveService

logger = logging.getLogger(__name__)


async def save_gmail_attachment_to_drive(
    user_id: Annotated[str, Field(description=get_user_id_description())],
    message_id: Annotated[str, Field(description="The ID of the Gmail message containing the attachment.")],
    attachment_id: Annotated[str, Field(description="The ID of the attachment to save.")],
    folder_id: Annotated[
        str | None, Field(description="Optional Google Drive folder ID to save to. If not provided, saves to root.")
    ] = None,
    rename: Annotated[
        str | None,
        Field(description="Optional new filename for the attachment. If not provided, uses original filename."),
    ] = None,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Save a Gmail attachment to Google Drive."""
    try:
        if ctx:
            await ctx.info(
                f"Saving attachment ID {attachment_id} from message ID {message_id} to Drive for user {user_id}"
            )

        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)

        d_service = auth_helper.get_drive_service(user_id)
        drive_service = DriveService(d_service)

        email_details, attachments = gmail_service.get_email_by_id_with_attachments(email_id=message_id)

        attachment_metadata = None
        for _part_id, attachment_info in attachments.items():
            if attachment_info.get("attachmentId") == attachment_id:
                attachment_metadata = attachment_info
                break

        if not attachment_metadata:
            error_msg = f"Attachment ID {attachment_id} not found in message {message_id}"
            if ctx:
                await ctx.warning(error_msg)
            return [TextContent(type="text", text=error_msg)]

        attachment_data = gmail_service.get_attachment(message_id=message_id, attachment_id=attachment_id)

        if not attachment_data or not attachment_data.get("data"):
            error_msg = f"Failed to retrieve attachment ID {attachment_id} data from message {message_id}"
            if ctx:
                await ctx.warning(error_msg)
            return [TextContent(type="text", text=error_msg)]

        filename = rename or attachment_metadata.get("filename", "unknown_file")
        mime_type = attachment_metadata.get("mimeType", "application/octet-stream")

        file_result = drive_service.upload_file(
            file_content=attachment_data["data"], file_name=filename, mime_type=mime_type, parent_folder_id=folder_id
        )

        if not file_result:
            error_msg = f"Failed to save attachment {filename} to Google Drive"
            if ctx:
                await ctx.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

        success_msg = (
            f"Successfully saved attachment '{filename}' to Google Drive.\n"
            f"File ID: {file_result.get('id')}\n"
            f"Web View Link: {file_result.get('webViewLink')}"
        )
        if ctx:
            await ctx.info(success_msg)

        return [TextContent(type="text", text=json.dumps(file_result, indent=2))]

    except Exception as e:
        logger.error(f"Error in save_gmail_attachment_to_drive for {user_id}: {e}", exc_info=True)
        error_msg = f"Error saving attachment to Drive: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def bulk_save_gmail_attachments_to_drive(
    user_id: Annotated[str, Field(description=get_user_id_description())],
    attachments: Annotated[
        list[dict],
        Field(
            description=(
                "List of attachment information dictionaries. Each should have message_id, attachment_id, "
                "and optionally folder_id and rename fields."
            )
        ),
    ],
    folder_id: Annotated[
        str | None,
        Field(description="Default Google Drive folder ID to save attachments to if not specified per attachment."),
    ] = None,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Save multiple Gmail attachments to Google Drive in a single request."""
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
                attachment_id = attachment_info.get("attachment_id")

                if not message_id or not attachment_id:
                    error_msg = "Missing required fields in attachment info (message_id, attachment_id)"
                    if ctx:
                        await ctx.error(error_msg)
                    results.append(TextContent(type="text", text=error_msg))
                    continue

                item_folder_id = attachment_info.get("folder_id", folder_id)  # Use per-item folder_id or default
                rename = attachment_info.get("rename")  # Optional rename field

                email_details, attachments_metadata = gmail_service.get_email_by_id_with_attachments(
                    email_id=message_id
                )

                attachment_metadata = None
                for _part_id, att_info in attachments_metadata.items():
                    if att_info.get("attachmentId") == attachment_id:
                        attachment_metadata = att_info
                        break

                if not attachment_metadata:
                    error_msg = f"Attachment ID {attachment_id} not found in message {message_id}"
                    if ctx:
                        await ctx.warning(error_msg)
                    results.append(TextContent(type="text", text=error_msg))
                    continue

                attachment_data = gmail_service.get_attachment(message_id=message_id, attachment_id=attachment_id)

                if not attachment_data or not attachment_data.get("data"):
                    error_msg = f"Failed to retrieve attachment data for ID {attachment_id} from message {message_id}"
                    if ctx:
                        await ctx.warning(error_msg)
                    results.append(TextContent(type="text", text=error_msg))
                    continue

                filename = rename or attachment_metadata.get("filename", "unknown_file")
                mime_type = attachment_metadata.get("mimeType", "application/octet-stream")

                file_result = drive_service.upload_file(
                    file_content=attachment_data["data"],
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

                success_msg = (
                    f"Successfully saved attachment '{filename}' to Google Drive. File ID: {file_result.get('id')}"
                )
                if ctx:
                    await ctx.info(success_msg)

                results.append(TextContent(type="text", text=json.dumps(file_result, indent=2)))

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
