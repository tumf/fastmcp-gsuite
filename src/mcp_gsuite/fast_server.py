import json
import logging
from typing import Annotated, Optional, List, Dict, Any
from mcp.types import TextContent

from fastmcp import FastMCP, Context
from . import gmail as gmail_impl # Original implementation
from . import calendar as calendar_impl
from . import auth_helper
from .settings import settings # Import settings to ensure it's loaded

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger.info(f"Using settings: gauth='{settings.absolute_gauth_file}', accounts='{settings.absolute_accounts_file}', creds='{settings.absolute_credentials_dir}'")

mcp = FastMCP("mcp-gsuite-fast", instructions="MCP Server to connect to Google G-Suite using fastmcp.")

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


@mcp.tool(description="Query Gmail emails based on an optional search query. Returns emails in reverse chronological order (newest first).")
async def query_gmail_emails(
    user_id: Annotated[str, get_user_id_description()],
    query: Annotated[Optional[str], "Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')"] = None,
    max_results: Annotated[int, "Maximum number of emails (1-500, default 100)"] = 100,
    ctx: Context | None = None # Optional context
) -> List[TextContent]:
    """Queries Gmail emails for the specified user."""
    try:
        if ctx: await ctx.info(f"Querying emails for {user_id} with query: '{query}'")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service) # Pass authenticated service
        emails = gmail_service.query_emails(query=query, max_results=max_results)
        if not emails:
             if ctx: await ctx.info(f"No emails found for query '{query}' for user {user_id}")
             return [TextContent(type="text", text="No emails found matching the query.")]
        return [TextContent(type="text", text=json.dumps(email, indent=2)) for email in emails]
    except Exception as e:
        logger.error(f"Error in query_gmail_emails for {user_id}: {e}", exc_info=True)
        error_msg = f"Error querying emails: {e}"
        if ctx: await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e








@mcp.tool(description="Get the full details of a specific Gmail email by its ID, including body and attachment metadata.")
async def get_email_details(
    user_id: Annotated[str, get_user_id_description()],
    email_id: Annotated[str, "The unique ID of the Gmail email message."],
    ctx: Context | None = None
) -> List[TextContent]:
    """Retrieves detailed information for a single email, including body and attachments."""
    try:
        if ctx: await ctx.info(f"Fetching details for email ID {email_id} for user {user_id}")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)
        email_details, attachments = gmail_service.get_email_by_id_with_attachments(email_id=email_id)

        if not email_details:
            if ctx: await ctx.warning(f"Email with ID {email_id} not found for user {user_id}")
            return [TextContent(type="text", text=f"Email with ID {email_id} not found.")]

        full_details = {
            "email": email_details,
            "attachments": attachments # Dictionary of attachment metadata keyed by partId
        }

        return [TextContent(type="text", text=json.dumps(full_details, indent=2))]
    except Exception as e:
        logger.error(f"Error in get_email_details for {user_id}, email ID {email_id}: {e}", exc_info=True)
        error_msg = f"Error getting email details: {e}"
        if ctx: await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


@mcp.tool(description="List all available Gmail labels for the user.")
async def get_gmail_labels(
    user_id: Annotated[str, get_user_id_description()],
    ctx: Context | None = None
) -> List[TextContent]:
    """Lists all Gmail labels for the specified user."""
    try:
        if ctx: await ctx.info(f"Fetching labels for user {user_id}")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)
        labels = gmail_service.get_labels()
        if not labels:
            if ctx: await ctx.info(f"No labels found for user {user_id}")
            return [TextContent(type="text", text="No labels found.")]
        return [TextContent(type="text", text=json.dumps(labels, indent=2))]
    except Exception as e:
        logger.error(f"Error in get_gmail_labels for {user_id}: {e}", exc_info=True)
        error_msg = f"Error getting labels: {e}"
        if ctx: await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


@mcp.tool(description="Retrieves multiple Gmail email messages by their IDs in a single request, including bodies and attachment metadata.")
async def bulk_get_gmail_emails(
    user_id: Annotated[str, get_user_id_description()],
    email_ids: Annotated[List[str], "List of Gmail message IDs to retrieve."],
    ctx: Context | None = None
) -> List[TextContent]:
    """Retrieves details for multiple emails by their IDs."""
    results = []
    try:
        if ctx: await ctx.info(f"Fetching {len(email_ids)} emails for user {user_id}")
        g_service = auth_helper.get_gmail_service(user_id)
        gmail_service = gmail_impl.GmailService(g_service)

        for email_id in email_ids:
            try:
                if ctx: await ctx.debug(f"Fetching email ID {email_id}")
                email_details, attachments = gmail_service.get_email_by_id_with_attachments(email_id=email_id)
                if email_details:
                    full_details = {
                        "email": email_details,
                        "attachments": attachments
                    }
                    results.append(full_details)
                else:
                    if ctx: await ctx.warning(f"Email with ID {email_id} not found for user {user_id}")
            except Exception as inner_e:
                logger.error(f"Error fetching email ID {email_id} for {user_id}: {inner_e}", exc_info=True)
                if ctx: await ctx.error(f"Error fetching email ID {email_id}: {inner_e}")

        if not results:
            if ctx: await ctx.info(f"No emails found or retrieved for the given IDs for user {user_id}")
            return [TextContent(type="text", text="No emails found or retrieved for the provided IDs.")]
        else:
            return [TextContent(type="text", text=json.dumps(results, indent=2))]

    except Exception as e: # Catch errors during service init or outside the loop
        logger.error(f"Error in bulk_get_gmail_emails setup or outer scope for {user_id}: {e}", exc_info=True)
        error_msg = f"Error getting bulk emails: {e}"
        if ctx: await ctx.error(error_msg)
        # Return error message in TextContent for bulk operations instead of raising?
        # For consistency with single-get, raising might be better, but bulk could partially succeed.
        # Let's return an error message for now.
        return [TextContent(type="text", text=f"Error processing bulk email request: {e}")]


@mcp.tool(description="List all calendars the user has access to.")
async def list_calendars(
    user_id: Annotated[str, get_user_id_description()],
    ctx: Context | None = None
) -> List[TextContent]:
    """Lists all calendars accessible by the user."""
    try:
        if ctx: await ctx.info(f"Listing calendars for user {user_id}")
        c_service = auth_helper.get_calendar_service(user_id)
        calendar_service = calendar_impl.CalendarService(c_service)
        calendars = calendar_service.list_calendars()
        if not calendars:
            if ctx: await ctx.info(f"No calendars found for user {user_id}")
            return [TextContent(type="text", text="No calendars found.")]
        return [TextContent(type="text", text=json.dumps(calendars, indent=2))]
    except Exception as e:
        logger.error(f"Error in list_calendars for {user_id}: {e}", exc_info=True)
        error_msg = f"Error listing calendars: {e}"
        if ctx: await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e

@mcp.tool(description="List events from a specific calendar within a given time range.")
async def list_calendar_events(
    user_id: Annotated[str, get_user_id_description()],
    calendar_id: Annotated[str, "The ID of the calendar to query (use 'primary' for the primary calendar)."],
    start_time: Annotated[str, "Start time in ISO 8601 format (e.g., '2024-04-15T00:00:00Z')."],
    end_time: Annotated[str, "End time in ISO 8601 format (e.g., '2024-04-16T00:00:00Z')."],
    max_results: Annotated[int, "Maximum number of events (1-2500, default 100)"] = 100,
    query: Annotated[Optional[str], "Optional text query to filter events."] = None,
    ctx: Context | None = None
) -> List[TextContent]:
    """Lists events from a specified calendar and time range."""
    try:
        if ctx: await ctx.info(f"Listing events for {user_id} in calendar {calendar_id} from {start_time} to {end_time}")
        c_service = auth_helper.get_calendar_service(user_id)
        calendar_service = calendar_impl.CalendarService(c_service)
        events = calendar_service.list_events(
            calendar_id=calendar_id,
            start_time=start_time,
            end_time=end_time,
            max_results=max_results,
            query=query
        )
        if not events:
            if ctx: await ctx.info(f"No events found for the specified criteria for user {user_id}")
            return [TextContent(type="text", text="No events found matching the criteria.")]
        return [TextContent(type="text", text=json.dumps(events, indent=2))]
    except Exception as e:
        logger.error(f"Error in list_calendar_events for {user_id}: {e}", exc_info=True)
        error_msg = f"Error listing calendar events: {e}"
        if ctx: await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e

@mcp.tool(description="Create a new event in a specified calendar.")
async def create_calendar_event(
    user_id: Annotated[str, get_user_id_description()],
    calendar_id: Annotated[str, "The ID of the calendar to add the event to (use 'primary' for the primary calendar)."],
    summary: Annotated[str, "The title or summary of the event."],
    start_datetime: Annotated[str, "Start date/time in ISO 8601 format (e.g., '2024-04-15T10:00:00Z' or '2024-04-15' for all-day)."],
    end_datetime: Annotated[str, "End date/time in ISO 8601 format (e.g., '2024-04-15T11:00:00Z' or '2024-04-16' for all-day)."],
    description: Annotated[Optional[str], "Optional description or details for the event."] = None,
    location: Annotated[Optional[str], "Optional location for the event."] = None,
    attendees: Annotated[Optional[List[str]], "Optional list of attendee email addresses."] = None,
    ctx: Context | None = None
) -> List[TextContent]:
    """Creates a new calendar event."""
    try:
        if ctx: await ctx.info(f"Creating event '{summary}' for {user_id} in calendar {calendar_id}")
        c_service = auth_helper.get_calendar_service(user_id)
        calendar_service = calendar_impl.CalendarService(c_service)

        # Extract date/time values properly depending on whether it's an all-day event or timed event
        start_time = start_datetime
        end_time = end_datetime
        timezone = None  # Default timezone will be handled by the calendar service

        created_event = calendar_service.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            attendees=attendees,
            calendar_id=calendar_id,
            timezone=timezone
        )
        
        if not created_event:
            if ctx: await ctx.error(f"Failed to create event '{summary}' for user {user_id}")
            raise RuntimeError("Failed to create calendar event.")

        if ctx: await ctx.info(f"Successfully created event ID: {created_event.get('id')}")
        return [TextContent(type="text", text=json.dumps(created_event, indent=2))]
    except Exception as e:
        logger.error(f"Error in create_calendar_event for {user_id}: {e}", exc_info=True)
        error_msg = f"Error creating calendar event: {e}"
        if ctx: await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e

@mcp.tool(description="Delete an event from a calendar.")
async def delete_calendar_event(
    user_id: Annotated[str, get_user_id_description()],
    calendar_id: Annotated[str, "The ID of the calendar containing the event (use 'primary' for the primary calendar)."],
    event_id: Annotated[str, "The unique ID of the event to delete."],
    ctx: Context | None = None
) -> List[TextContent]:
    """Deletes a calendar event."""
    try:
        if ctx: await ctx.info(f"Deleting event ID {event_id} for {user_id} from calendar {calendar_id}")
        c_service = auth_helper.get_calendar_service(user_id)
        calendar_service = calendar_impl.CalendarService(c_service)
        success = calendar_service.delete_event(
            event_id=event_id,
            calendar_id=calendar_id
        )
        
        if success:
            if ctx: await ctx.info(f"Successfully deleted event ID {event_id}")
            return [TextContent(type="text", text=f"Successfully deleted event ID: {event_id}")]
        else:
            if ctx: await ctx.warning(f"Failed to delete event ID {event_id} for user {user_id}")
            return [TextContent(type="text", text=f"Failed to delete event ID: {event_id}")]
    except Exception as e:
        logger.error(f"Error in delete_calendar_event for {user_id}: {e}", exc_info=True)
        error_msg = f"Error deleting calendar event: {e}"
        if ctx: await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e










if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Starting mcp-gsuite-fast server...")
    mcp.run() # Runs stdio by default
