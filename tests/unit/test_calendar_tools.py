import json
import unittest
from unittest.mock import MagicMock, patch

from src.mcp_gsuite.calendar_tools import (
    create_calendar_event,
    delete_calendar_event,
    list_calendar_events,
    list_calendars,
    update_calendar_event,
)
from tests.unit.mocks.context_mock import MockContext


class TestCalendarTools(unittest.IsolatedAsyncioTestCase):
    """Test cases for Calendar MCP tools."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_calendar_service = MagicMock()

        self.mock_context = MockContext()

        self.test_user_id = "test@example.com"
        self.test_calendar_id = "primary"
        self.test_event_id = "test_event_123"

        self.sample_calendar = {
            "id": self.test_calendar_id,
            "summary": "Test Calendar",
            "description": "A test calendar",
            "timeZone": "UTC",
        }

        self.sample_event = {
            "id": self.test_event_id,
            "summary": "Test Event",
            "description": "A test event",
            "start": {"dateTime": "2023-01-01T10:00:00Z"},
            "end": {"dateTime": "2023-01-01T11:00:00Z"},
            "location": "Test Location",
        }

    @patch("src.mcp_gsuite.calendar_tools.auth_helper.get_calendar_service")
    @patch("src.mcp_gsuite.calendar_tools.calendar_impl.CalendarService")
    async def test_list_calendars_success(self, mock_calendar_service_class, mock_get_calendar_service):
        """Test successful listing of calendars."""
        mock_service = MagicMock()
        mock_get_calendar_service.return_value = mock_service
        mock_calendar_service_instance = mock_calendar_service_class.return_value
        mock_calendar_service_instance.list_calendars.return_value = [self.sample_calendar]

        result = await list_calendars(
            user_id=self.test_user_id,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(json.loads(result[0].text), [self.sample_calendar])

        mock_get_calendar_service.assert_called_once_with(self.test_user_id)
        mock_calendar_service_class.assert_called_once_with(mock_service)
        mock_calendar_service_instance.list_calendars.assert_called_once()

    @patch("src.mcp_gsuite.calendar_tools.auth_helper.get_calendar_service")
    @patch("src.mcp_gsuite.calendar_tools.calendar_impl.CalendarService")
    async def test_list_calendars_no_results(self, mock_calendar_service_class, mock_get_calendar_service):
        """Test listing of calendars with no results."""
        mock_service = MagicMock()
        mock_get_calendar_service.return_value = mock_service
        mock_calendar_service_instance = mock_calendar_service_class.return_value
        mock_calendar_service_instance.list_calendars.return_value = []

        result = await list_calendars(
            user_id=self.test_user_id,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(result[0].text, "No calendars found.")

        mock_get_calendar_service.assert_called_once_with(self.test_user_id)
        mock_calendar_service_class.assert_called_once_with(mock_service)
        mock_calendar_service_instance.list_calendars.assert_called_once()

    @patch("src.mcp_gsuite.calendar_tools.auth_helper.get_calendar_service")
    @patch("src.mcp_gsuite.calendar_tools.calendar_impl.CalendarService")
    async def test_list_calendar_events_success(self, mock_calendar_service_class, mock_get_calendar_service):
        """Test successful listing of calendar events."""
        mock_service = MagicMock()
        mock_get_calendar_service.return_value = mock_service
        mock_calendar_service_instance = mock_calendar_service_class.return_value
        mock_calendar_service_instance.list_events.return_value = [self.sample_event]

        start_time = "2023-01-01T00:00:00Z"
        end_time = "2023-01-02T00:00:00Z"

        result = await list_calendar_events(
            user_id=self.test_user_id,
            calendar_id=self.test_calendar_id,
            start_time=start_time,
            end_time=end_time,
            max_results=10,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(json.loads(result[0].text), [self.sample_event])

        mock_get_calendar_service.assert_called_once_with(self.test_user_id)
        mock_calendar_service_class.assert_called_once_with(mock_service)
        mock_calendar_service_instance.list_events.assert_called_once_with(
            calendar_id=self.test_calendar_id,
            start_time=start_time,
            end_time=end_time,
            max_results=10,
            query=None,
        )

    @patch("src.mcp_gsuite.calendar_tools.auth_helper.get_calendar_service")
    @patch("src.mcp_gsuite.calendar_tools.calendar_impl.CalendarService")
    async def test_create_calendar_event_success(self, mock_calendar_service_class, mock_get_calendar_service):
        """Test successful creation of calendar event."""
        mock_service = MagicMock()
        mock_get_calendar_service.return_value = mock_service
        mock_calendar_service_instance = mock_calendar_service_class.return_value
        mock_calendar_service_instance.create_event.return_value = self.sample_event

        start_datetime = "2023-01-01T10:00:00Z"
        end_datetime = "2023-01-01T11:00:00Z"

        result = await create_calendar_event(
            user_id=self.test_user_id,
            calendar_id=self.test_calendar_id,
            summary="Test Event",
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            description="Test Description",
            location="Test Location",
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(json.loads(result[0].text), self.sample_event)

        mock_get_calendar_service.assert_called_once_with(self.test_user_id)
        mock_calendar_service_class.assert_called_once_with(mock_service)
        mock_calendar_service_instance.create_event.assert_called_once_with(
            summary="Test Event",
            start_time=start_datetime,
            end_time=end_datetime,
            description="Test Description",
            location="Test Location",
            attendees=None,
            calendar_id=self.test_calendar_id,
            timezone=None,
        )

    @patch("src.mcp_gsuite.calendar_tools.auth_helper.get_calendar_service")
    @patch("src.mcp_gsuite.calendar_tools.calendar_impl.CalendarService")
    async def test_delete_calendar_event_success(self, mock_calendar_service_class, mock_get_calendar_service):
        """Test successful deletion of calendar event."""
        mock_service = MagicMock()
        mock_get_calendar_service.return_value = mock_service
        mock_calendar_service_instance = mock_calendar_service_class.return_value
        mock_calendar_service_instance.delete_event.return_value = True

        result = await delete_calendar_event(
            user_id=self.test_user_id,
            calendar_id=self.test_calendar_id,
            event_id=self.test_event_id,
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(result[0].text, f"Successfully deleted event ID: {self.test_event_id}")

        mock_get_calendar_service.assert_called_once_with(self.test_user_id)
        mock_calendar_service_class.assert_called_once_with(mock_service)
        mock_calendar_service_instance.delete_event.assert_called_once_with(
            event_id=self.test_event_id,
            calendar_id=self.test_calendar_id,
        )

    @patch("src.mcp_gsuite.calendar_tools.auth_helper.get_calendar_service")
    @patch("src.mcp_gsuite.calendar_tools.calendar_impl.CalendarService")
    async def test_list_calendars_error(self, mock_calendar_service_class, mock_get_calendar_service):
        """Test error handling in list_calendars."""
        mock_service = MagicMock()
        mock_get_calendar_service.return_value = mock_service
        mock_calendar_service_instance = mock_calendar_service_class.return_value
        mock_calendar_service_instance.list_calendars.side_effect = Exception("Test error")

        with self.assertRaises(RuntimeError) as context:
            await list_calendars(
                user_id=self.test_user_id,
                ctx=self.mock_context,  # type: ignore
            )
        self.assertTrue("Error listing calendars: Test error" in str(context.exception))
        self.assertEqual(len(self.mock_context.error_messages), 1)
        self.assertTrue("Error listing calendars: Test error" in self.mock_context.error_messages[0])
        mock_get_calendar_service.assert_called_once_with(self.test_user_id)
        mock_calendar_service_class.assert_called_once_with(mock_service)
        mock_calendar_service_instance.list_calendars.assert_called_once()

    @patch("src.mcp_gsuite.calendar_tools.auth_helper.get_calendar_service")
    @patch("src.mcp_gsuite.calendar_tools.calendar_impl.CalendarService")
    async def test_update_calendar_event_success(self, mock_calendar_service_class, mock_get_calendar_service):
        """Test successful update of calendar event."""
        mock_service = MagicMock()
        mock_get_calendar_service.return_value = mock_service
        mock_calendar_service_instance = mock_calendar_service_class.return_value

        updated_event = {
            "id": self.test_event_id,
            "summary": "Updated Event",
            "description": "Updated description",
            "start": {"dateTime": "2023-01-01T10:00:00Z"},
            "end": {"dateTime": "2023-01-01T11:00:00Z"},
            "location": "Updated Location",
        }
        mock_calendar_service_instance.update_event.return_value = updated_event

        result = await update_calendar_event(
            user_id=self.test_user_id,
            calendar_id=self.test_calendar_id,
            event_id=self.test_event_id,
            summary="Updated Event",
            description="Updated description",
            location="Updated Location",
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        result_data = json.loads(result[0].text)
        self.assertEqual(result_data["summary"], "Updated Event")
        self.assertEqual(result_data["description"], "Updated description")
        self.assertEqual(result_data["location"], "Updated Location")

        mock_get_calendar_service.assert_called_once_with(self.test_user_id)
        mock_calendar_service_class.assert_called_once_with(mock_service)
        mock_calendar_service_instance.update_event.assert_called_once_with(
            event_id=self.test_event_id,
            summary="Updated Event",
            start_time=None,
            end_time=None,
            location="Updated Location",
            description="Updated description",
            attendees=None,
            timezone=None,
            calendar_id=self.test_calendar_id,
        )

    @patch("src.mcp_gsuite.calendar_tools.auth_helper.get_calendar_service")
    @patch("src.mcp_gsuite.calendar_tools.calendar_impl.CalendarService")
    async def test_update_calendar_event_failure(self, mock_calendar_service_class, mock_get_calendar_service):
        """Test update calendar event when update fails."""
        mock_service = MagicMock()
        mock_get_calendar_service.return_value = mock_service
        mock_calendar_service_instance = mock_calendar_service_class.return_value
        mock_calendar_service_instance.update_event.return_value = None

        result = await update_calendar_event(
            user_id=self.test_user_id,
            calendar_id=self.test_calendar_id,
            event_id=self.test_event_id,
            summary="Updated Event",
            ctx=self.mock_context,  # type: ignore
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("Failed to update event ID", result[0].text)

    @patch("src.mcp_gsuite.calendar_tools.auth_helper.get_calendar_service")
    @patch("src.mcp_gsuite.calendar_tools.calendar_impl.CalendarService")
    async def test_update_calendar_event_error(self, mock_calendar_service_class, mock_get_calendar_service):
        """Test error handling in update_calendar_event."""
        mock_service = MagicMock()
        mock_get_calendar_service.return_value = mock_service
        mock_calendar_service_instance = mock_calendar_service_class.return_value
        mock_calendar_service_instance.update_event.side_effect = Exception("Test error")

        with self.assertRaises(RuntimeError) as context:
            await update_calendar_event(
                user_id=self.test_user_id,
                calendar_id=self.test_calendar_id,
                event_id=self.test_event_id,
                summary="Updated Event",
                ctx=self.mock_context,  # type: ignore
            )
        self.assertTrue("Error updating calendar event: Test error" in str(context.exception))
        self.assertEqual(len(self.mock_context.error_messages), 1)
        self.assertTrue("Error updating calendar event: Test error" in self.mock_context.error_messages[0])
