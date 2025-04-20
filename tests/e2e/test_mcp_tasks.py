import base64
import json
import os
import shutil

import pytest
from chuk_mcp.mcp_client.messages.initialize.send_messages import send_initialize
from chuk_mcp.mcp_client.messages.tools.send_messages import send_tools_call, send_tools_list
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import StdioServerParameters

# Get UV path from environment variables or PATH
UV_PATH = os.environ.get("UV_PATH") or shutil.which("uv") or "/Users/tumf/.pyenv/shims/uv"


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
class TestMCPTasks:
    @pytest.mark.e2e
    async def test_list_task_lists(self, credentials):
        """Test for retrieving Google Tasks task list"""
        # Get parent process environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        # Set MCP server parameters
        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Failed to initialize MCP server"

            # Get tool list
            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "No tools found in response"

            # Find Tasks related tools
            tasks_tools = [tool for tool in tools_response["tools"] if "task" in tool["name"].lower()]

            # Skip test if no tasks tools are available
            if not tasks_tools:
                pytest.skip("No Tasks tools found")

            # Find the tool to get task list
            list_tasklists_tool = next(
                (tool for tool in tasks_tools if "list" in tool["name"].lower() and "list" in tool["name"].lower()),
                None,
            )

            # Skip test if task list tool is not available
            if not list_tasklists_tool:
                pytest.skip("Tasks list tool not found")

            # Execute the tool
            result = await send_tools_call(
                read_stream,
                write_stream,
                list_tasklists_tool["name"],
                {"user_id": credentials["email"]},
            )

            # Verify results
            assert result, "Tool execution failed"

            # Check for content in response
            assert "content" in result, "No content in tool response"
            assert len(result["content"]) > 0, "Empty content in response"

            has_tasklists = False
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    response_text = item.get("text")

                    # Handle text responses
                    if "no task lists found" in response_text.lower():
                        print("Warning: No task lists found")
                        return

                    try:
                        tasklists_data = json.loads(response_text)
                        if isinstance(tasklists_data, list) or isinstance(tasklists_data, dict):
                            has_tasklists = True
                            # Display results
                            task_lists = tasklists_data
                            if isinstance(tasklists_data, dict):
                                task_lists = tasklists_data.get("items") or tasklists_data.get("taskLists") or []
                            print(f"Found {len(task_lists)} task lists")
                            break
                    except json.JSONDecodeError:
                        continue

            assert has_tasklists, "No valid task lists found in response"
