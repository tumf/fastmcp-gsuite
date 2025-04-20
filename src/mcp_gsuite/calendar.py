import logging
import traceback
from datetime import datetime

import pytz


class CalendarService:
    def __init__(self, service):
        # credentials = gauth.get_stored_credentials(user_id=user_id) # Handled by auth_helper
        # if not credentials:
        #     raise RuntimeError("No Oauth2 credentials stored")
        # self.service = build('calendar', 'v3', credentials=credentials) # Service is now passed in
        if not service:
            raise ValueError("A valid Google API service client must be provided.")
        self.service = service

    def list_calendars(self) -> list:
        """
        Lists all calendars accessible by the user.

        Returns:
            list: List of calendar objects with their metadata
        """
        try:
            calendar_list = self.service.calendarList().list().execute()

            calendars = []

            for calendar in calendar_list.get("items", []):
                if calendar.get("kind") == "calendar#calendarListEntry":
                    calendars.append(
                        {
                            "id": calendar.get("id"),
                            "summary": calendar.get("summary"),
                            "primary": calendar.get("primary", False),
                            "time_zone": calendar.get("timeZone"),
                            "etag": calendar.get("etag"),
                            "access_role": calendar.get("accessRole"),
                        }
                    )

            return calendars

        except Exception as e:
            logging.error(f"Error retrieving calendars: {e!s}")
            logging.error(traceback.format_exc())
            return []

    def list_events(
        self,
        calendar_id: str = "primary",
        start_time: str | None = None,
        end_time: str | None = None,
        max_results: int = 100,
        query: str | None = None,
    ) -> list:
        """
        Lists events on the specified calendar within a given time range.

        Args:
            calendar_id: Calendar identifier. Use 'primary' for the primary calendar.
            start_time: Start time in ISO 8601 format (RFC3339). If None, defaults to now.
            end_time: End time in ISO 8601 format (RFC3339). Optional.
            max_results: Maximum number of events to return.
            query: Free text search query.

        Returns:
            A list of event resources.
        """
        try:
            now = datetime.now(pytz.utc).isoformat()
            time_min = start_time or now

            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=end_time,
                    maxResults=min(max(1, max_results), 2500),  # Ensure within bounds
                    singleEvents=True,
                    orderBy="startTime",
                    q=query,
                )
                .execute()
            )
            events = events_result.get("items", [])
            return events
        except Exception as e:
            logging.error(f"An error occurred listing events: {e}")
            return []

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        location: str | None = None,
        description: str | None = None,
        attendees: list | None = None,
        send_notifications: bool = True,
        timezone: str | None = None,
        calendar_id: str = "primary",
    ) -> dict | None:
        """
        Create a new calendar event.

        Args:
            summary (str): Title of the event
            start_time (str): Start time in RFC3339 format
            end_time (str): End time in RFC3339 format
            location (str, optional): Location of the event
            description (str, optional): Description of the event
            attendees (list, optional): List of attendee email addresses
            send_notifications (bool): Whether to send notifications to attendees
            timezone (str, optional): Timezone for the event (e.g. 'America/New_York')

        Returns:
            dict: Created event data or None if creation fails
        """
        try:
            # Prepare event data
            event = {
                "summary": summary,
                "start": {
                    "dateTime": start_time,
                    "timeZone": timezone or "UTC",
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": timezone or "UTC",
                },
            }

            # Add optional fields if provided
            if location:
                event["location"] = location
            if description:
                event["description"] = description
            if attendees:
                # Type annotation to clarify the expected structure
                event["attendees"] = [{"email": email} for email in attendees]  # type: ignore

            # Create the event
            created_event = (
                self.service.events()
                .insert(
                    calendarId=calendar_id,
                    body=event,
                    sendNotifications=send_notifications,
                )
                .execute()
            )

            return created_event

        except Exception as e:
            logging.error(f"Error creating calendar event: {e!s}")
            logging.error(traceback.format_exc())
            return None

    def delete_event(
        self,
        event_id: str,
        send_notifications: bool = True,
        calendar_id: str = "primary",
    ) -> bool:
        """
        Delete a calendar event by its ID.

        Args:
            event_id (str): The ID of the event to delete
            send_notifications (bool): Whether to send cancellation notifications to attendees

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendNotifications=send_notifications,
            ).execute()
            return True

        except Exception as e:
            logging.error(f"Error deleting calendar event {event_id}: {e!s}")
            logging.error(traceback.format_exc())
            return False
