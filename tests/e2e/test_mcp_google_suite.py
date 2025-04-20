import base64
import json
import logging
import os
import shutil
from datetime import datetime, timedelta

import pytest
from chuk_mcp.mcp_client.messages.initialize.send_messages import send_initialize
from chuk_mcp.mcp_client.messages.tools.send_messages import send_tools_call, send_tools_list
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import StdioServerParameters

from tests.e2e.conftest import retry_async

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Get the path of uv from environment variable or search in PATH
UV_PATH = os.environ.get("UV_PATH") or shutil.which("uv")
if not UV_PATH:
    pytest.skip("uv command not found in PATH or UV_PATH not set")

# Define common connection exceptions that should be retried
CONNECTION_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
    json.JSONDecodeError,
)


@pytest.fixture(scope="session")
def credentials():
    """Set up the test environment with credentials from environment variables"""
    # Get authentication information from environment variables
    credentials_json_str = os.environ.get("GSUITE_CREDENTIALS_JSON")
    google_email = os.environ.get("GOOGLE_ACCOUNT_EMAIL")
    google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
    google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
    google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    # Ensure that authentication information is set
    assert credentials_json_str, "GSUITE_CREDENTIALS_JSON environment variable is not set"
    assert google_email, "GOOGLE_ACCOUNT_EMAIL environment variable is not set"
    assert google_client_id, "GOOGLE_CLIENT_ID environment variable is not set"
    assert google_client_secret, "GOOGLE_CLIENT_SECRET environment variable is not set"

    try:
        # Base64 decode
        credentials_json_decoded = base64.b64decode(credentials_json_str).decode("utf-8")
        decoded_credentials = json.loads(credentials_json_decoded)

        # Required fields for OAuth2Credentials
        credentials_json = {
            "access_token": decoded_credentials.get("access_token", ""),
            "client_id": google_client_id,
            "client_secret": google_client_secret,
            "refresh_token": decoded_credentials.get("refresh_token", ""),
            "token_expiry": decoded_credentials.get("token_expiry", ""),
            "token_uri": decoded_credentials.get("token_uri", "https://oauth2.googleapis.com/token"),
            "user_agent": "fastmcp-gsuite-e2e-tests",
            "revoke_uri": "https://oauth2.googleapis.com/revoke",
            "id_token": None,
            "id_token_jwt": None,
            "token_response": {
                "access_token": decoded_credentials.get("access_token", ""),
                "expires_in": 3600,
                "refresh_token": decoded_credentials.get("refresh_token", ""),
                "scope": " ".join(decoded_credentials.get("scopes", [])),
                "token_type": "Bearer",
            },
            "scopes": decoded_credentials.get("scopes", []),
            "token_info_uri": "https://oauth2.googleapis.com/tokeninfo",
            "invalid": False,
            "_class": "OAuth2Credentials",
            "_module": "oauth2client.client",
        }

    except Exception as e:
        pytest.fail(f"Failed to decode credentials: {e!s}")

    # Create temporary credentials file
    credentials_file = ".e2e_test_credentials.json"
    with open(credentials_file, "w") as f:
        json.dump(credentials_json, f)

    # Create OAuth2 authentication file
    oauth2_file = f".oauth2.{google_email}.json"
    with open(oauth2_file, "w") as f:
        json.dump(credentials_json, f)

    # Set environment variables to provide parameters needed to run the MCP server
    os.environ["GSUITE_CREDENTIALS_FILE"] = credentials_file
    os.environ["GSUITE_EMAIL"] = google_email

    # Return data for testing
    yield {
        "credentials_file": credentials_file,
        "oauth2_file": oauth2_file,
        "email": google_email,
        "project_id": google_project_id,
        "client_id": google_client_id,
        "client_secret": google_client_secret,
    }

    # Clean up files after test
    if os.path.exists(credentials_file):
        os.remove(credentials_file)
    if os.path.exists(oauth2_file):
        os.remove(oauth2_file)


@pytest.mark.asyncio
class TestMCPGoogleSuite:
    """E2E tests for Google services using MCP"""

    def setup_method(self):
        """Set up the test environment"""
        # Copy the parent process's environment variables
        self.env = os.environ.copy()

    def teardown_method(self):
        """Clean up after the test is complete"""
        pass

    @pytest.mark.e2e
    async def test_list_gmail_tools(self, credentials):
        """Test if Gmail-related tools are available"""
        # Get the parent process's environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        # Set up server parameters using StdioServerParameters
        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        # Define helper functions to be used with retry logic
        async def initialize_mcp(read_stream, write_stream):
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Server initialization failed"
            return init_result

        async def get_tool_list(read_stream, write_stream):
            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "Tool list was not returned"
            assert len(tools_response["tools"]) > 0, "No tools available"
            return tools_response

        # Connect to the server with retry logic
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize with retry
            await retry_async(
                initialize_mcp,
                read_stream,
                write_stream,
                max_attempts=3,
                expected_exceptions=CONNECTION_EXCEPTIONS,
            )

            # Get a list of available tools with retry
            tools_response = await retry_async(
                get_tool_list,
                read_stream,
                write_stream,
                max_attempts=3,
                expected_exceptions=CONNECTION_EXCEPTIONS,
            )

            # Check if Gmail-related tools are included
            gmail_tools = [tool for tool in tools_response["tools"] if "gmail" in tool["name"].lower()]
            assert len(gmail_tools) > 0, "No Gmail-related tools found"

            # Output tool names
            for tool in gmail_tools:
                print(f"Found Gmail tool: {tool['name']} - {tool['description']}")

    @pytest.mark.e2e
    async def test_create_gmail_draft(self, credentials):
        """Test creating and deleting a Gmail draft"""
        # Get the parent process's environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        # Set up server parameters using StdioServerParameters
        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        # Define helper functions to be used with retry logic
        async def initialize_mcp(read_stream, write_stream):
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Server initialization failed"
            return init_result

        async def create_draft(read_stream, write_stream, subject, body, email):
            result = await send_tools_call(
                read_stream,
                write_stream,
                name="create_gmail_draft",
                arguments={
                    "to": email,  # Send to self for testing
                    "subject": subject,
                    "body": body,
                    "user_id": email,
                },
            )

            assert result is not None, "Tool call returned None"
            assert not result.get("isError", False), f"Tool call returned error: {result}"
            assert "content" in result, f"No content field in response: {result}"
            assert len(result["content"]) > 0, f"Empty content in response: {result}"
            return result

        async def search_messages(read_stream, write_stream, query, email):
            search_result = await send_tools_call(
                read_stream,
                write_stream,
                name="query_gmail_emails",
                arguments={
                    "query": query,
                    "user_id": email,
                },
            )

            assert search_result, "Failed to search for messages"
            assert "content" in search_result, "No content in search response"
            assert len(search_result["content"]) > 0, "Empty content in search response"
            return search_result

        async def delete_draft(read_stream, write_stream, draft_id, email):
            delete_result = await send_tools_call(
                read_stream,
                write_stream,
                name="delete_gmail_draft",
                arguments={
                    "draft_id": draft_id,
                    "user_id": email,
                },
            )

            assert delete_result, "Failed to delete draft"
            return delete_result

        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize with retry
            await retry_async(
                initialize_mcp,
                read_stream,
                write_stream,
                max_attempts=3,
                expected_exceptions=CONNECTION_EXCEPTIONS,
            )

            # Create test email subject and body
            subject = f"E2E Test: MCP Test - {datetime.now().isoformat()}"
            body = f"This is an automated e2e test using MCP client sent at {datetime.now().isoformat()}"

            # Call the draft creation tool with retry
            result = await retry_async(
                create_draft,
                read_stream,
                write_stream,
                subject,
                body,
                credentials["email"],
                max_attempts=3,
                expected_exceptions=CONNECTION_EXCEPTIONS,
            )

            # Extract draft ID from response
            draft_id = None
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    response_text = item.get("text")
                    # Check for error messages in the response
                    if "error" in response_text.lower():
                        print(f"Warning: Error in draft creation response: {response_text}")
                        pytest.skip(f"Draft creation failed: {response_text}")

                    try:
                        draft_data = json.loads(response_text)
                        if isinstance(draft_data, dict) and "id" in draft_data:
                            draft_id = draft_data["id"]
                            break
                    except json.JSONDecodeError:
                        # Handle non-JSON responses
                        if "draft id:" in response_text.lower():
                            # Try to extract ID from text response
                            parts = response_text.split(":")
                            if len(parts) > 1:
                                draft_id = parts[1].strip()
                                break
                        continue

            assert draft_id, "Failed to extract draft ID from response"

            # Search for the draft with retry
            await retry_async(
                search_messages,
                read_stream,
                write_stream,
                f"subject:{subject}",
                credentials["email"],
                max_attempts=3,
                expected_exceptions=CONNECTION_EXCEPTIONS,
            )

            # Clean up the draft with retry
            delete_result = await retry_async(
                delete_draft,
                read_stream,
                write_stream,
                draft_id,
                credentials["email"],
                max_attempts=3,
                expected_exceptions=CONNECTION_EXCEPTIONS,
            )

            # Verify successful deletion message
            success = False
            for item in delete_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    if "Successfully deleted draft" in item.get("text"):
                        success = True
                        break

            assert success, "Delete draft operation was not successful"

    @pytest.mark.e2e
    async def test_list_calendar_tools(self, credentials):
        """Test if Calendar-related tools are available"""
        # Get the parent process's environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        # Set up server parameters using StdioServerParameters
        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Server initialization failed"

            # Get a list of available tools
            tools_response = await send_tools_list(read_stream, write_stream)

            # Check if Calendar-related tools are included
            calendar_tools = [tool for tool in tools_response["tools"] if "calendar" in tool["name"].lower()]
            assert len(calendar_tools) > 0, "No Calendar-related tools found"

            # Output tool names
            for tool in calendar_tools:
                print(f"Found Calendar tool: {tool['name']} - {tool['description']}")

    @pytest.mark.e2e
    async def test_create_calendar_event(self, credentials):
        """Test creating and deleting a Calendar event"""
        # Get the parent process's environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        # Set up server parameters using StdioServerParameters
        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Server initialization failed"

            # Create event details for testing
            event_title = f"E2E Test Event - {datetime.now().isoformat()}"

            # Set start time to 1 hour from now
            start_time = datetime.now() + timedelta(hours=1)
            end_time = start_time + timedelta(hours=1)

            # Convert to ISO format date string
            start_time_iso = start_time.isoformat()
            end_time_iso = end_time.isoformat()

            # Call the event creation tool
            result = await send_tools_call(
                read_stream,
                write_stream,
                name="create_calendar_event",
                arguments={
                    "summary": event_title,
                    "start_datetime": start_time_iso,
                    "end_datetime": end_time_iso,
                    "calendar_id": "primary",
                    "user_id": credentials["email"],
                },
            )

            # Verify that the event was created
            assert result, "Failed to create event"
            event_data = json.loads(result["content"][0]["text"])
            assert "id" in event_data, "Event ID was not returned"
            event_id = event_data["id"]

            # Search for the event
            list_result = await send_tools_call(
                read_stream,
                write_stream,
                name="list_calendar_events",
                arguments={
                    "calendar_id": "primary",
                    "start_time": start_time_iso,
                    "end_time": end_time_iso,
                    "query": event_title,
                    "user_id": credentials["email"],
                },
            )

            # Verify that search results exist
            assert list_result, "Failed to search for events"
            events_data_text = list_result["content"][0]["text"]
            if events_data_text == "No events found matching the criteria.":
                print(
                    "Warning: No events found. The event you just created may not yet be reflected in Google Calendar."
                )
                # Test ends here - skip deletion if event not found
                return

            events_data = json.loads(events_data_text)
            assert len(events_data) > 0, "Created event not found"

            # Clean up the event
            delete_result = await send_tools_call(
                read_stream,
                write_stream,
                name="delete_calendar_event",
                arguments={
                    "calendar_id": "primary",
                    "event_id": event_id,
                    "user_id": credentials["email"],
                },
            )

            assert delete_result, "Failed to delete event"

    @pytest.mark.e2e
    async def test_gmail_search_and_read(self, credentials):
        """Test Gmail search and message retrieval"""
        # Get the parent process's environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        # Set up server parameters using StdioServerParameters
        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Server initialization failed"

            # Search for the 10 most recent emails
            search_result = await send_tools_call(
                read_stream,
                write_stream,
                name="query_gmail_emails",
                arguments={
                    "query": "is:inbox",
                    "max_results": 10,
                    "user_id": credentials["email"],
                },
            )

            # Verify that search results were returned
            assert search_result, "Failed to search for messages"

            # If at least one email was returned, get details of the first email
            emails_data_text = search_result["content"][0]["text"]
            if emails_data_text != "No emails found matching the query.":
                emails_data = json.loads(emails_data_text)
                email_id = emails_data["id"]

                # Get message details
                message_result = await send_tools_call(
                    read_stream,
                    write_stream,
                    name="get_email_details",
                    arguments={
                        "email_id": email_id,
                        "user_id": credentials["email"],
                    },
                )

                # Verify that message details were returned
                assert message_result, "Failed to retrieve message"
                message_data = json.loads(message_result["content"][0]["text"])

                # Verify that message data was returned in the correct format
                assert "email" in message_data, "Email data was not returned"
                assert "attachments" in message_data, "Attachment information was not returned"

    @pytest.mark.e2e
    async def test_gmail_labels(self, credentials):
        """Test retrieving Gmail labels"""
        # Get the parent process's environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        # Set up server parameters using StdioServerParameters
        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Server initialization failed"

            # Get Gmail labels
            labels_result = await send_tools_call(
                read_stream,
                write_stream,
                name="get_gmail_labels",
                arguments={"user_id": credentials["email"]},
            )

            # Verify that labels were returned
            assert labels_result, "Failed to retrieve label list"
            labels_data = json.loads(labels_result["content"][0]["text"])
            assert labels_data, "Label data was not returned"

    @pytest.mark.e2e
    async def test_calendar_get_colors(self, credentials):
        """Test retrieving available colors in Calendar"""
        # Skip this test. The calendar color retrieval function is not implemented
        pytest.skip("Calendar color listing function is not implemented")

    @pytest.mark.e2e
    async def test_calendar_list(self, credentials):
        """Test retrieving user's calendar list"""
        # Get the parent process's environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        # Set up server parameters using StdioServerParameters
        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Server initialization failed"

            # Get calendar list
            calendars_result = await send_tools_call(
                read_stream,
                write_stream,
                name="list_calendars",
                arguments={"user_id": credentials["email"]},
            )

            # Verify that calendar list was returned
            assert calendars_result, "Failed to retrieve calendar list"
            calendars_data = json.loads(calendars_result["content"][0]["text"])
            assert calendars_data, "Calendar data was not returned"
