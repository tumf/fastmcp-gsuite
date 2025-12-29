import json
import logging
from typing import Annotated

from fastmcp import Context
from mcp.types import TextContent

from . import auth_helper
from . import calendar as calendar_impl
from .common import get_user_id_description

logger = logging.getLogger(__name__)


# Calendar related tools
async def list_calendars(
    user_id: Annotated[str, get_user_id_description()], ctx: Context | None = None
) -> list[TextContent]:
    """Lists all calendars accessible by the user."""
    try:
        if ctx:
            await ctx.info(f"Listing calendars for user {user_id}")
        c_service = auth_helper.get_calendar_service(user_id)
        calendar_service = calendar_impl.CalendarService(c_service)
        calendars = calendar_service.list_calendars()
        if not calendars:
            if ctx:
                await ctx.info(f"No calendars found for user {user_id}")
            return [TextContent(type="text", text="No calendars found.")]
        return [TextContent(type="text", text=json.dumps(calendars, indent=2))]
    except Exception as e:
        logger.error(f"Error in list_calendars for {user_id}: {e}", exc_info=True)
        error_msg = f"Error listing calendars: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def list_calendar_events(
    user_id: Annotated[str, get_user_id_description()],
    calendar_id: Annotated[str, "The ID of the calendar to query (use 'primary' for the primary calendar)."],
    start_time: Annotated[str, "Start time in ISO 8601 format (e.g., '2024-04-15T00:00:00Z')."],
    end_time: Annotated[str, "End time in ISO 8601 format (e.g., '2024-04-16T00:00:00Z')."],
    max_results: Annotated[int, "Maximum number of events (1-2500, default 100)"] = 100,
    query: Annotated[str | None, "Optional text query to filter events."] = None,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Lists events from a specified calendar and time range."""
    try:
        if ctx:
            await ctx.info(f"Listing events for {user_id} in calendar {calendar_id} from {start_time} to {end_time}")
        c_service = auth_helper.get_calendar_service(user_id)
        calendar_service = calendar_impl.CalendarService(c_service)
        events = calendar_service.list_events(
            calendar_id=calendar_id,
            start_time=start_time,
            end_time=end_time,
            max_results=max_results,
            query=query,
        )
        if not events:
            if ctx:
                await ctx.info(f"No events found for the specified criteria for user {user_id}")
            return [TextContent(type="text", text="No events found matching the criteria.")]
        return [TextContent(type="text", text=json.dumps(events, indent=2))]
    except Exception as e:
        logger.error(f"Error in list_calendar_events for {user_id}: {e}", exc_info=True)
        error_msg = f"Error listing calendar events: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def create_calendar_event(
    user_id: Annotated[str, get_user_id_description()],
    calendar_id: Annotated[
        str,
        "The ID of the calendar to add the event to (use 'primary' for the primary calendar).",
    ],
    summary: Annotated[str, "The title or summary of the event."],
    start_datetime: Annotated[
        str,
        "Start date/time in ISO 8601 format (e.g., '2024-04-15T10:00:00Z' or '2024-04-15' for all-day).",
    ],
    end_datetime: Annotated[
        str,
        "End date/time in ISO 8601 format (e.g., '2024-04-15T11:00:00Z' or '2024-04-16' for all-day).",
    ],
    description: Annotated[str | None, "Optional description or details for the event."] = None,
    location: Annotated[str | None, "Optional location for the event."] = None,
    attendees: Annotated[list[str] | None, "Optional list of attendee email addresses."] = None,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Creates a new calendar event."""
    try:
        if ctx:
            await ctx.info(f"Creating event '{summary}' for {user_id} in calendar {calendar_id}")
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
            timezone=timezone,
        )

        if not created_event:
            if ctx:
                await ctx.error(f"Failed to create event '{summary}' for user {user_id}")
            raise RuntimeError("Failed to create calendar event.")

        if ctx:
            await ctx.info(f"Successfully created event ID: {created_event.get('id')}")
        return [TextContent(type="text", text=json.dumps(created_event, indent=2))]
    except Exception as e:
        logger.error(f"Error in create_calendar_event for {user_id}: {e}", exc_info=True)
        error_msg = f"Error creating calendar event: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def delete_calendar_event(
    user_id: Annotated[str, get_user_id_description()],
    calendar_id: Annotated[
        str,
        "The ID of the calendar containing the event (use 'primary' for the primary calendar).",
    ],
    event_id: Annotated[str, "The unique ID of the event to delete."],
    ctx: Context | None = None,
) -> list[TextContent]:
    """Deletes a calendar event."""
    try:
        if ctx:
            await ctx.info(f"Deleting event ID {event_id} for {user_id} from calendar {calendar_id}")
        c_service = auth_helper.get_calendar_service(user_id)
        calendar_service = calendar_impl.CalendarService(c_service)
        success = calendar_service.delete_event(event_id=event_id, calendar_id=calendar_id)

        if success:
            if ctx:
                await ctx.info(f"Successfully deleted event ID {event_id}")
            return [TextContent(type="text", text=f"Successfully deleted event ID: {event_id}")]
        else:
            if ctx:
                await ctx.warning(f"Failed to delete event ID {event_id} for user {user_id}")
            return [TextContent(type="text", text=f"Failed to delete event ID: {event_id}")]
    except Exception as e:
        logger.error(f"Error in delete_calendar_event for {user_id}: {e}", exc_info=True)
        error_msg = f"Error deleting calendar event: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


async def update_calendar_event(
    user_id: Annotated[str, get_user_id_description()],
    calendar_id: Annotated[
        str,
        "The ID of the calendar containing the event (use 'primary' for the primary calendar).",
    ],
    event_id: Annotated[str, "The unique ID of the event to update."],
    summary: Annotated[str | None, "New title/summary of the event."] = None,
    start_time: Annotated[
        str | None,
        "New start time in RFC3339 format (e.g., '2024-01-15T09:00:00-05:00').",
    ] = None,
    end_time: Annotated[
        str | None,
        "New end time in RFC3339 format (e.g., '2024-01-15T10:00:00-05:00').",
    ] = None,
    location: Annotated[str | None, "New location of the event."] = None,
    description: Annotated[str | None, "New description of the event."] = None,
    attendees: Annotated[
        list[str] | None,
        "New list of attendee email addresses. This replaces the existing attendees.",
    ] = None,
    timezone: Annotated[
        str | None,
        "Timezone for the event (e.g., 'America/New_York', 'Asia/Tokyo').",
    ] = None,
    ctx: Context | None = None,
) -> list[TextContent]:
    """Updates an existing calendar event. Only provided fields will be updated."""
    try:
        if ctx:
            await ctx.info(f"Updating event ID {event_id} for {user_id} in calendar {calendar_id}")

        c_service = auth_helper.get_calendar_service(user_id)
        calendar_service = calendar_impl.CalendarService(c_service)

        updated_event = calendar_service.update_event(
            event_id=event_id,
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            location=location,
            description=description,
            attendees=attendees,
            timezone=timezone,
            calendar_id=calendar_id,
        )

        if updated_event:
            if ctx:
                await ctx.info(f"Successfully updated event ID {event_id}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps(updated_event, indent=2, ensure_ascii=False),
                )
            ]
        else:
            if ctx:
                await ctx.warning(f"Failed to update event ID {event_id} for user {user_id}")
            return [TextContent(type="text", text=f"Failed to update event ID: {event_id}")]
    except Exception as e:
        logger.error(f"Error in update_calendar_event for {user_id}: {e}", exc_info=True)
        error_msg = f"Error updating calendar event: {e}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
