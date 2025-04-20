import logging

from fastmcp import FastMCP

from . import auth_helper
from .calendar_tools import (
    create_calendar_event,
    delete_calendar_event,
    list_calendar_events,
    list_calendars,
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

mcp = FastMCP(
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
mcp.tool(
    description="Query Gmail emails based on an optional search query. "
    "Returns emails in reverse chronological order (newest first)."
)(query_gmail_emails)

mcp.tool(
    description="Get the full details of a specific Gmail email by its ID, including body and attachment metadata."
)(get_email_details)

mcp.tool(description="List all available Gmail labels for the user.")(get_gmail_labels)

mcp.tool(
    description="Retrieves multiple Gmail email messages by their IDs in a single request, "
    "including bodies and attachment metadata."
)(bulk_get_gmail_emails)

mcp.tool(description="Create a draft email in Gmail.")(create_gmail_draft)

mcp.tool(description="Delete a draft email from Gmail.")(delete_gmail_draft)

mcp.tool(description="Create a reply to an existing Gmail email message.")(create_gmail_reply)

mcp.tool(description="Retrieve a Gmail attachment by its ID.")(get_gmail_attachment)

mcp.tool(
    description="Save multiple Gmail attachments to disk by their message IDs "
    "and attachment IDs in a single request."
)(bulk_save_gmail_attachments)

# Register Calendar tools
mcp.tool(description="List all calendars the user has access to.")(list_calendars)

mcp.tool(description="List events from a specific calendar within a given time range.")(list_calendar_events)

mcp.tool(description="Create a new event in a specified calendar.")(create_calendar_event)

mcp.tool(description="Delete an event from a calendar.")(delete_calendar_event)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting mcp-gsuite-fast server...")
    mcp.run()  # Runs stdio by default
