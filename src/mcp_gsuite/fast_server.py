import logging

from fastmcp import FastMCP

from . import auth_helper
from .calendar_tools import create_calendar_event, delete_calendar_event, list_calendar_events, list_calendars
from .drive_tools import (
    copy_drive_file,
    create_drive_folder,
    delete_drive_file,
    delete_drive_folder,
    download_drive_file,
    get_drive_file,
    list_drive_files,
    list_drive_folders,
    move_drive_file,
    move_drive_folder,
    rename_drive_file,
    rename_drive_folder,
    upload_drive_file,
)
from .gmail_drive_tools import (
    bulk_save_gmail_attachments_to_drive,
    save_gmail_attachment_to_drive,
)
from .gmail_tools import (
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
from .settings import settings  # Import settings to ensure it's loaded

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger.info(
    f"Using settings: gauth='{settings.absolute_gauth_file}', "
    f"accounts='{settings.absolute_accounts_file}', "
    f"creds='{settings.absolute_credentials_dir}'"
)

mcp: FastMCP = FastMCP(
    "mcp-gsuite-fast",
    instructions="MCP Server to connect to Google G-Suite using fastmcp.",
)

_account_info_cache = None


def get_user_id_description() -> str:
    """Generates a description for the user_id parameter based on available accounts."""
    global _account_info_cache
    if _account_info_cache is None:
        try:
            _account_info_cache = auth_helper.get_account_info()
            if not _account_info_cache:
                logger.warning("No accounts found in accounts file. User ID description will be generic.")
                return "The EMAIL of the Google account to use."
        except Exception as e:
            logger.error(f"Failed to load account info for user ID description: {e}")
            return "The EMAIL of the Google account to use (Error loading account list)."

    desc = [f"{acc.email} ({acc.account_type})" for acc in _account_info_cache]
    return f"The EMAIL of the Google account. Choose from: {', '.join(desc)}"


# Register Gmail tools
mcp.tool()(query_gmail_emails)
mcp.tool()(get_email_details)
mcp.tool()(get_gmail_labels)
mcp.tool()(bulk_get_gmail_emails)
mcp.tool()(create_gmail_draft)
mcp.tool()(delete_gmail_draft)
mcp.tool()(create_gmail_reply)
mcp.tool()(get_gmail_attachment)
mcp.tool()(bulk_save_gmail_attachments)

# Register Calendar tools
mcp.tool()(list_calendars)
mcp.tool()(list_calendar_events)
mcp.tool()(create_calendar_event)
mcp.tool()(delete_calendar_event)

# Register Drive tools
mcp.tool()(list_drive_files)
mcp.tool()(get_drive_file)
mcp.tool()(download_drive_file)
mcp.tool()(upload_drive_file)
mcp.tool()(copy_drive_file)
mcp.tool()(delete_drive_file)
mcp.tool()(rename_drive_file)
mcp.tool()(move_drive_file)

# Register Drive folder tools
mcp.tool()(create_drive_folder)
mcp.tool()(list_drive_folders)
mcp.tool()(rename_drive_folder)
mcp.tool()(move_drive_folder)
mcp.tool()(delete_drive_folder)

# Register Gmail to Drive tools
mcp.tool()(save_gmail_attachment_to_drive)
mcp.tool()(bulk_save_gmail_attachments_to_drive)


def run_streamable_http():
    """Run the server in streamable-http mode."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting mcp-gsuite-fast server (streamable-http mode)...")
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        path="/mcp",
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting mcp-gsuite-fast server...")
    mcp.run()  # Runs stdio by default
