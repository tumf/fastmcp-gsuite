import json
import logging
from typing import Annotated

from fastmcp import Context
from mcp.types import TextContent

from . import auth_helper
from . import drive as drive_impl
from .common import get_user_id_description

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
        drive = drive_impl.DriveService(drive_service)  # Pass authenticated service
        files_result = drive.list_files(query=query, page_size=limit, order_by=order_by)

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
        drive = drive_impl.DriveService(drive_service)
        file = drive.get_file(file_id=file_id)

        if not file:
            if ctx:
                await ctx.warning(
                    f"File with ID {file_id} not found for user {user_id}"
                )
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
        drive = drive_impl.DriveService(drive_service)
        file_data = drive.download_file(file_id=file_id)

        if not file_data:
            if ctx:
                await ctx.warning(
                    f"File with ID {file_id} could not be downloaded for user {user_id}"
                )
            return [
                TextContent(
                    type="text", text=f"File with ID {file_id} could not be downloaded."
                )
            ]

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
