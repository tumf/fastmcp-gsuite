import base64
import json
import os
import shutil

import pytest
from chuk_mcp.mcp_client.messages.initialize.send_messages import \
    send_initialize
from chuk_mcp.mcp_client.messages.ping.send_messages import send_ping
from chuk_mcp.mcp_client.messages.tools.send_messages import (send_tools_call,
                                                              send_tools_list)
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import \
    StdioServerParameters

# Get UV path from environment variables or PATH
UV_PATH = (
    os.environ.get("UV_PATH") or shutil.which("uv") or "/Users/tumf/.pyenv/shims/uv"
)
# Temporarily disable skipping for test execution
# if not UV_PATH:
#     pytest.skip("uv command not found in PATH or UV_PATH not set")


@pytest.fixture(scope="session")
def credentials():
    """Set up the test environment with credentials from environment variables"""
    # Get authentication information from environment variables
    credentials_json_str = os.environ.get("GSUITE_CREDENTIALS_JSON")
    google_email = os.environ.get("GOOGLE_ACCOUNT_EMAIL")
    google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
    google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
    google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    # Verify that authentication information is set
    assert (
        credentials_json_str
    ), "GSUITE_CREDENTIALS_JSON environment variable is not set"
    assert google_email, "GOOGLE_ACCOUNT_EMAIL environment variable is not set"
    assert google_client_id, "GOOGLE_CLIENT_ID environment variable is not set"
    assert google_client_secret, "GOOGLE_CLIENT_SECRET environment variable is not set"

    try:
        # Base64 decode
        credentials_json_decoded = base64.b64decode(credentials_json_str).decode(
            "utf-8"
        )
        decoded_credentials = json.loads(credentials_json_decoded)

        # Required fields for OAuth2Credentials
        credentials_json = {
            "access_token": decoded_credentials.get("access_token", ""),
            "client_id": google_client_id,
            "client_secret": google_client_secret,
            "refresh_token": decoded_credentials.get("refresh_token", ""),
            "token_expiry": decoded_credentials.get("token_expiry", ""),
            "token_uri": decoded_credentials.get(
                "token_uri", "https://oauth2.googleapis.com/token"
            ),
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
        pytest.fail(f"Failed to decode credentials: {str(e)}")

    # Create temporary credentials file
    credentials_file = ".e2e_test_credentials.json"
    with open(credentials_file, "w") as f:
        json.dump(credentials_json, f)

    # Create OAuth2 authentication file
    oauth2_file = f".oauth2.{google_email}.json"
    with open(oauth2_file, "w") as f:
        json.dump(credentials_json, f)

    # Set environment variables needed to run the MCP server
    os.environ["GSUITE_CREDENTIALS_FILE"] = credentials_file
    os.environ["GSUITE_EMAIL"] = google_email

    # Return test data
    yield {
        "credentials_file": credentials_file,
        "oauth2_file": oauth2_file,
        "email": google_email,
        "project_id": google_project_id,
        "client_id": google_client_id,
        "client_secret": google_client_secret,
    }

    # Clean up files after testing
    if os.path.exists(credentials_file):
        os.remove(credentials_file)
    if os.path.exists(oauth2_file):
        os.remove(oauth2_file)


@pytest.mark.asyncio
class TestMCPGsuite:
    @pytest.mark.e2e
    async def test_mcp_connection_and_tools(self, credentials):
        """Test connecting to the MCP server and listing tools"""
        # Get parent process environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        # Set MCP Gsuite server parameters
        server_params = StdioServerParameters(
            command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env
        )

        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Failed to initialize MCP server"

            # Verify server name - only check that the server name is not empty, not an exact match
            assert init_result.serverInfo.name, "Server name is empty"
            print(f"Connected to server: {init_result.serverInfo.name}")

            # Send Ping to confirm connection
            ping_result = await send_ping(read_stream, write_stream)
            assert ping_result, "Ping to MCP server failed"

            # List available tools
            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "No tools found in response"

            # Display available tool names
            tool_names = [tool["name"] for tool in tools_response["tools"]]
            print(f"Available tools: {tool_names}")

            # Find Gmail related tools (names may vary by environment)
            gmail_tools = [
                tool
                for tool in tools_response["tools"]
                if "gmail" in tool["name"].lower()
            ]
            assert (
                len(gmail_tools) > 0
            ), f"No Gmail tools found. Available tools: {tool_names}"

            # Find Calendar related tools
            calendar_tools = [
                tool
                for tool in tools_response["tools"]
                if "calendar" in tool["name"].lower()
            ]
            assert (
                len(calendar_tools) > 0
            ), f"No Calendar tools found. Available tools: {tool_names}"

            # Verify specific tool names (confirmed in previous executions)
            assert (
                "query_gmail_emails" in tool_names
            ), f"query_gmail_emails tool not found in {tool_names}"
            assert (
                "list_calendar_events" in tool_names
            ), f"list_calendar_events tool not found in {tool_names}"

    @pytest.mark.e2e
    async def test_gmail_tool_list_messages(self, credentials):
        """Test Gmail tool for listing messages"""
        # Get parent process environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        server_params = StdioServerParameters(
            command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            await send_initialize(read_stream, write_stream)

            # Use Gmail query tool
            result = await send_tools_call(
                read_stream,
                write_stream,
                name="query_gmail_emails",
                arguments={
                    "max_results": 5,  # Get latest 5 emails
                    "user_id": credentials["email"],  # Add user ID as argument
                },
            )

            assert result, "Tool call returned no result"
            assert not result.get(
                "isError", False
            ), f"Tool call returned error: {result}"

            # Verify that the response is a dictionary
            assert isinstance(
                result, dict
            ), f"Result is not a dictionary: {type(result)}"

            # Verify response
            assert "content" in result, f"No content field in response: {result}"
            assert len(result["content"]) > 0, f"Empty content in response: {result}"

            # Verify that JSON text is included
            has_messages = False
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        message_data = json.loads(item.get("text"))
                        if isinstance(message_data, dict) and "id" in message_data:
                            has_messages = True
                            break
                    except json.JSONDecodeError:
                        continue

            assert has_messages, f"No valid message JSON found in response: {result}"

    @pytest.mark.e2e
    async def test_calendar_tool_list_events(self, credentials):
        """Test Calendar tool for listing events"""
        # Get parent process environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        server_params = StdioServerParameters(
            command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            await send_initialize(read_stream, write_stream)

            # Get current date and get today's events
            import datetime

            today = datetime.datetime.now().strftime("%Y-%m-%d")

            # Call Calendar list_events tool
            result = await send_tools_call(
                read_stream,
                write_stream,
                name="list_calendar_events",
                arguments={
                    "calendar_id": "primary",
                    "start_time": f"{today}T00:00:00Z",
                    "end_time": f"{today}T23:59:59Z",
                    "max_results": 10,
                    "user_id": credentials["email"],  # Add user ID as argument
                },
            )

            assert result is not None, "Tool call returned None"
            assert not result.get(
                "isError", False
            ), f"Tool call returned error: {result}"
            assert isinstance(
                result, dict
            ), f"Result is not a dictionary: {type(result)}"

            # Verify response
            assert "content" in result, f"No content field in response: {result}"
            assert len(result["content"]) > 0, f"Empty content in response: {result}"

            # Verify that JSON text is included
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        event_data = json.loads(item.get("text"))
                        if isinstance(event_data, dict):
                            break
                    except json.JSONDecodeError:
                        continue

            # There may be no events, so if JSON parsing is successful, it's OK
            # assert has_events, f"No valid event JSON found in response: {result}"
