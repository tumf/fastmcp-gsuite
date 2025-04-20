import json
import logging
import os
from typing import Annotated

from fastmcp import Context
from mcp.types import TextContent

from . import auth_helper
from .common import get_user_id_description
from .drive import DriveService

logger = logging.getLogger(__name__)


async def list_drive_files(
    user_id: Annotated[str, get_user_id_description()],
    query: Annotated[
        str | None,
        "Drive search query (e.g., 'name contains \"report\"', 'mimeType=\"application/pdf\"')",
    ] = None,
    limit: Annotated[int, "Maximum number of files (1-1000, default 100)"] = 100,
    order_by: Annotated[
        str | None,
        "Sort order (e.g., 'name', 'modifiedTime desc') - default is 'modifiedTime desc'",
    ] = None,
    ctx: Context | None = None,  # Optional context
) -> list[TextContent]:
    """Lists files in the user's Google Drive."""
    try:
        if ctx:
            await ctx.info(f"Listing files for {user_id} with query: '{query}'")
        drive_service = auth_helper.get_drive_service(user_id)
        drive_client = DriveService(drive_service)  # Pass authenticated service
        files_result = drive_client.list_files(query=query, page_size=limit, order_by=order_by)

        if not files_result.get("files"):
            if ctx:
                await ctx.info(f"No files found for query '{query}' for user {user_id}")
            return [TextContent(type="text", text="No files found matching the query.")]

        return [TextContent(type="text", text=json.dumps(files_result, indent=2))]
    except Exception as e:
        logger.error(f"Error in list_drive_files for {user_id}: {e}", exc_info=True)
        error_msg = f"Error listing files: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def get_drive_file(
    user_id: Annotated[str, get_user_id_description()],
    file_id: Annotated[str, "The unique ID of the Google Drive file."],
    ctx: Context | None = None,
) -> list[TextContent]:
    """Retrieves metadata for a specific Google Drive file."""
    try:
        if ctx:
            await ctx.info(f"Fetching file ID {file_id} for user {user_id}")
        drive_service = auth_helper.get_drive_service(user_id)
        drive_client = DriveService(drive_service)
        file = drive_client.get_file(file_id=file_id)

        if not file:
            if ctx:
                await ctx.warning(f"File with ID {file_id} not found for user {user_id}")
            return [TextContent(type="text", text=f"File with ID {file_id} not found.")]

        return [TextContent(type="text", text=json.dumps(file, indent=2))]
    except Exception as e:
        logger.error(f"Error in get_drive_file for {user_id}: {e}", exc_info=True)
        error_msg = f"Error getting file details: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def download_drive_file(
    user_id: Annotated[str, get_user_id_description()],
    file_id: Annotated[str, "The unique ID of the Google Drive file to download."],
    ctx: Context | None = None,
) -> list[TextContent]:
    """Downloads the content of a Google Drive file."""
    try:
        if ctx:
            await ctx.info(f"Downloading file ID {file_id} for user {user_id}")
        drive_service = auth_helper.get_drive_service(user_id)
        drive_client = DriveService(drive_service)
        file_data = drive_client.download_file(file_id=file_id)

        if not file_data:
            if ctx:
                await ctx.warning(f"File with ID {file_id} could not be downloaded for user {user_id}")
            return [TextContent(type="text", text=f"File with ID {file_id} could not be downloaded.")]

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "name": file_data.get("name"),
                        "mimeType": file_data.get("mimeType"),
                        "size": (
                            len(file_data.get("content", ""))
                            if isinstance(file_data.get("content"), bytes)
                            else "unknown"
                        ),
                    },
                    indent=2,
                ),
            )
        ]
    except Exception as e:
        logger.error(f"Error in download_drive_file for {user_id}: {e}", exc_info=True)
        error_msg = f"Error downloading file: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def upload_drive_file(
    user_id: Annotated[str, get_user_id_description()],
    file_path: Annotated[str, "Local path to the file to upload."],
    parent_folder_id: Annotated[
        str | None, "ID of the parent folder. If not specified, file will be uploaded to the Drive root."
    ] = None,
    mime_type: Annotated[
        str | None, "MIME type of the file. If not specified, it will be guessed from the file extension."
    ] = None,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Uploads a file to Google Drive."""
    try:
        if ctx:
            await ctx.info(f"Uploading file {file_path} for user {user_id}")

        if not os.path.exists(file_path):
            error_msg = f"File {file_path} does not exist."
            if ctx:
                await ctx.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

        drive_service = auth_helper.get_drive_service(user_id)
        drive_client = DriveService(drive_service)
        uploaded_file = drive_client.upload_file(
            file_path=file_path, parent_folder_id=parent_folder_id, mime_type=mime_type
        )

        if not uploaded_file:
            if ctx:
                await ctx.error(f"Failed to upload file {file_path} for user {user_id}")
            return [TextContent(type="text", text=f"Failed to upload file {file_path}.")]

        if ctx:
            await ctx.info(f"Successfully uploaded file with ID: {uploaded_file.get('id')}")
        return [TextContent(type="text", text=json.dumps(uploaded_file, indent=2))]
    except Exception as e:
        logger.error(f"Error in upload_drive_file for {user_id}: {e}", exc_info=True)
        error_msg = f"Error uploading file: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def copy_drive_file(
    user_id: Annotated[str, get_user_id_description()],
    file_id: Annotated[str, "ID of the file to copy."],
    new_name: Annotated[
        str | None, "New name for the copied file. If not specified, the original name will be used."
    ] = None,
    parent_folder_id: Annotated[
        str | None,
        "ID of the parent folder for the copy. If not specified, the copy will be in the same folder as the original.",
    ] = None,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Creates a copy of a file in Google Drive."""
    try:
        if ctx:
            await ctx.info(f"Copying file {file_id} for user {user_id}")
        drive_service = auth_helper.get_drive_service(user_id)
        drive_client = DriveService(drive_service)
        copied_file = drive_client.copy_file(file_id=file_id, new_name=new_name, parent_folder_id=parent_folder_id)

        if not copied_file:
            if ctx:
                await ctx.error(f"Failed to copy file {file_id} for user {user_id}")
            return [TextContent(type="text", text=f"Failed to copy file with ID {file_id}.")]

        if ctx:
            await ctx.info(f"Successfully copied file with ID: {copied_file.get('id')}")
        return [TextContent(type="text", text=json.dumps(copied_file, indent=2))]
    except Exception as e:
        logger.error(f"Error in copy_drive_file for {user_id}: {e}", exc_info=True)
        error_msg = f"Error copying file: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def delete_drive_file(
    user_id: Annotated[str, get_user_id_description()],
    file_id: Annotated[str, "ID of the file to delete."],
    ctx: Context | None = None,
) -> list[TextContent]:
    """Deletes a file from Google Drive."""
    try:
        if ctx:
            await ctx.info(f"Deleting file {file_id} for user {user_id}")
        drive_service = auth_helper.get_drive_service(user_id)
        drive_client = DriveService(drive_service)
        success = drive_client.delete_file(file_id=file_id)

        if success:
            if ctx:
                await ctx.info(f"Successfully deleted file with ID: {file_id}")
            return [TextContent(type="text", text=f"Successfully deleted file with ID: {file_id}")]
        else:
            if ctx:
                await ctx.warning(f"Failed to delete file {file_id} for user {user_id}")
            return [TextContent(type="text", text=f"Failed to delete file with ID: {file_id}")]
    except Exception as e:
        logger.error(f"Error in delete_drive_file for {user_id}: {e}", exc_info=True)
        error_msg = f"Error deleting file: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def rename_drive_file(
    user_id: Annotated[str, get_user_id_description()],
    file_id: Annotated[str, "ID of the file to rename."],
    new_name: Annotated[str, "New name for the file."],
    ctx: Context | None = None,
) -> list[TextContent]:
    """Renames a file in Google Drive."""
    try:
        if ctx:
            await ctx.info(f"Renaming file {file_id} to {new_name} for user {user_id}")
        drive_service = auth_helper.get_drive_service(user_id)
        drive_client = DriveService(drive_service)
        updated_file = drive_client.rename_file(file_id=file_id, new_name=new_name)

        if not updated_file:
            if ctx:
                await ctx.error(f"Failed to rename file {file_id} for user {user_id}")
            return [TextContent(type="text", text=f"Failed to rename file with ID {file_id}.")]

        if ctx:
            await ctx.info(f"Successfully renamed file with ID: {file_id} to {new_name}")
        return [TextContent(type="text", text=json.dumps(updated_file, indent=2))]
    except Exception as e:
        logger.error(f"Error in rename_drive_file for {user_id}: {e}", exc_info=True)
        error_msg = f"Error renaming file: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def move_drive_file(
    user_id: Annotated[str, get_user_id_description()],
    file_id: Annotated[str, "ID of the file to move."],
    new_parent_id: Annotated[str, "ID of the destination folder."],
    remove_previous_parents: Annotated[
        bool, "Whether to remove the file from its current folders. If False, the file will be in multiple folders."
    ] = True,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Moves a file to a different folder in Google Drive."""
    try:
        if ctx:
            await ctx.info(f"Moving file {file_id} to folder {new_parent_id} for user {user_id}")
        drive_service = auth_helper.get_drive_service(user_id)
        drive_client = DriveService(drive_service)
        moved_file = drive_client.move_file(
            file_id=file_id, new_parent_id=new_parent_id, remove_previous_parents=remove_previous_parents
        )

        if not moved_file:
            if ctx:
                await ctx.error(f"Failed to move file {file_id} for user {user_id}")
            return [TextContent(type="text", text=f"Failed to move file with ID {file_id}.")]

        if ctx:
            await ctx.info(f"Successfully moved file with ID: {file_id} to folder {new_parent_id}")
        return [TextContent(type="text", text=json.dumps(moved_file, indent=2))]
    except Exception as e:
        logger.error(f"Error in move_drive_file for {user_id}: {e}", exc_info=True)
        error_msg = f"Error moving file: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
