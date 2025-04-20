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
class TestMCPGDrive:
    @pytest.mark.e2e
    async def test_gdrive_list_files(self, credentials):
        """Test for retrieving GDrive file list"""
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

            # Find GDrive related tools
            gdrive_tools = [
                tool
                for tool in tools_response["tools"]
                if "drive" in tool["name"].lower() or "gdrive" in tool["name"].lower()
            ]

            # Skip test if no GDrive tools are available
            if not gdrive_tools:
                pytest.skip("No GDrive tools found")

            # Find the tool to get file list
            list_files_tool = next(
                (tool for tool in gdrive_tools if "list" in tool["name"].lower()),
                None,
            )

            # Skip test if GDrive list files tool is not available
            if not list_files_tool:
                pytest.skip("GDrive list files tool not found")

            # Execute the tool
            tool_params = {"limit": 5, "user_id": credentials["email"]}
            result = await send_tools_call(read_stream, write_stream, list_files_tool["name"], tool_params)

            # Verify results
            assert result, "Tool execution failed"

            # Check for content in response
            assert "content" in result, "No content in tool response"
            assert len(result["content"]) > 0, "Empty content in response"

            has_files = False
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    response_text = item.get("text")

                    # Handle text responses
                    if "no files found" in response_text.lower():
                        print("Warning: No files found in GDrive")
                        return

                    try:
                        files_data = json.loads(response_text)
                        if isinstance(files_data, dict) and "files" in files_data:
                            has_files = True
                            print(f"Found {len(files_data['files'])} files in GDrive")
                            break
                    except json.JSONDecodeError:
                        continue

            assert has_files, "No valid files found in response"

    @pytest.mark.e2e
    async def test_gdrive_get_file(self, credentials):
        """Test for retrieving a specific GDrive file by ID"""
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

            # Find GDrive related tools
            gdrive_tools = [
                tool
                for tool in tools_response["tools"]
                if "drive" in tool["name"].lower() or "gdrive" in tool["name"].lower()
            ]

            # Skip test if no GDrive tools are available
            if not gdrive_tools:
                pytest.skip("No GDrive tools found")

            list_files_tool = next(
                (tool for tool in gdrive_tools if "list" in tool["name"].lower()),
                None,
            )
            if not list_files_tool:
                pytest.skip("GDrive list files tool not found")

            # Execute the list files tool to get a file ID
            list_params = {"limit": 1, "user_id": credentials["email"]}
            list_result = await send_tools_call(read_stream, write_stream, list_files_tool["name"], list_params)

            assert list_result, "List files tool execution failed"
            assert "content" in list_result, "No content in list files response"
            assert len(list_result["content"]) > 0, "Empty content in list files response"

            file_id = None
            for item in list_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        files_data = json.loads(item.get("text"))
                        if isinstance(files_data, dict) and "files" in files_data and files_data["files"]:
                            file_id = files_data["files"][0]["id"]
                            break
                    except json.JSONDecodeError:
                        continue

            # Skip test if no file ID was found
            if not file_id:
                pytest.skip("No file ID found to test get_file tool")

            # Find the tool to get file metadata
            get_file_tool = next(
                (
                    tool
                    for tool in gdrive_tools
                    if "get" in tool["name"].lower() and "download" not in tool["name"].lower()
                ),
                None,
            )

            # Skip test if get file tool is not available
            if not get_file_tool:
                pytest.skip("GDrive get file tool not found")

            # Execute the get file tool
            get_params = {"file_id": file_id, "user_id": credentials["email"]}
            result = await send_tools_call(read_stream, write_stream, get_file_tool["name"], get_params)

            # Verify results
            assert result, "Get file tool execution failed"
            assert "content" in result, "No content in get file response"
            assert len(result["content"]) > 0, "Empty content in get file response"

            # Verify file metadata in response
            has_file_metadata = False
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    response_text = item.get("text")

                    if "not found" in response_text.lower():
                        print(f"Warning: File with ID {file_id} not found")
                        return

                    try:
                        file_data = json.loads(response_text)
                        if isinstance(file_data, dict) and "id" in file_data:
                            has_file_metadata = True
                            print(f"Successfully retrieved file: {file_data.get('name', 'Unknown')}")
                            break
                    except json.JSONDecodeError:
                        continue

            assert has_file_metadata, "No valid file metadata found in response"

    @pytest.mark.e2e
    async def test_gdrive_download_file(self, credentials):
        """Test for downloading a GDrive file by ID"""
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

            # Find GDrive related tools
            gdrive_tools = [
                tool
                for tool in tools_response["tools"]
                if "drive" in tool["name"].lower() or "gdrive" in tool["name"].lower()
            ]

            # Skip test if no GDrive tools are available
            if not gdrive_tools:
                pytest.skip("No GDrive tools found")

            list_files_tool = next(
                (tool for tool in gdrive_tools if "list" in tool["name"].lower()),
                None,
            )
            if not list_files_tool:
                pytest.skip("GDrive list files tool not found")

            # Execute the list files tool to get a file ID
            list_params = {"limit": 1, "user_id": credentials["email"]}
            list_result = await send_tools_call(read_stream, write_stream, list_files_tool["name"], list_params)

            assert list_result, "List files tool execution failed"
            assert "content" in list_result, "No content in list files response"
            assert len(list_result["content"]) > 0, "Empty content in list files response"

            file_id = None
            for item in list_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        files_data = json.loads(item.get("text"))
                        if isinstance(files_data, dict) and "files" in files_data and files_data["files"]:
                            file_id = files_data["files"][0]["id"]
                            break
                    except json.JSONDecodeError:
                        continue

            # Skip test if no file ID was found
            if not file_id:
                pytest.skip("No file ID found to test download_file tool")

            # Find the tool to download file
            download_file_tool = next(
                (tool for tool in gdrive_tools if "download" in tool["name"].lower()),
                None,
            )

            # Skip test if download file tool is not available
            if not download_file_tool:
                pytest.skip("GDrive download file tool not found")

            # Execute the download file tool
            download_params = {"file_id": file_id, "user_id": credentials["email"]}
            result = await send_tools_call(read_stream, write_stream, download_file_tool["name"], download_params)

            # Verify results
            assert result, "Download file tool execution failed"
            assert "content" in result, "No content in download file response"
            assert len(result["content"]) > 0, "Empty content in download file response"

            has_file_data = False
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    response_text = item.get("text")

                    if "could not be downloaded" in response_text.lower():
                        print(f"Warning: File with ID {file_id} could not be downloaded")
                        return

                    try:
                        file_data = json.loads(response_text)
                        if isinstance(file_data, dict) and "name" in file_data and "mimeType" in file_data:
                            has_file_data = True
                            print(f"Successfully downloaded file: {file_data.get('name', 'Unknown')}")
                            break
                    except json.JSONDecodeError:
                        continue

            assert has_file_data, "No valid file download data found in response"
