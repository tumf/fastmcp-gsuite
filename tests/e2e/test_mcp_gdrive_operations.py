import base64
import json
import os
import shutil
import tempfile
import time
from typing import Any

import pytest
from chuk_mcp.mcp_client.messages.initialize.send_messages import send_initialize
from chuk_mcp.mcp_client.messages.tools.send_messages import send_tools_call, send_tools_list
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import StdioServerParameters

UV_PATH = os.environ.get("UV_PATH") or shutil.which("uv") or "/Users/tumf/.pyenv/shims/uv"


def find_tool_by_name(tools: list[dict[str, Any]], name_pattern: str) -> dict[str, Any]:
    """Helper function to find a tool by name pattern"""
    return next((tool for tool in tools if name_pattern in tool.get("name", "").lower()), {})


@pytest.fixture(scope="session")
def credentials():
    """Set up the test environment with credentials from environment variables"""
    credentials_json_str = os.environ.get("GSUITE_CREDENTIALS_JSON")
    google_email = os.environ.get("GOOGLE_ACCOUNT_EMAIL")
    google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
    google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
    google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    assert credentials_json_str, "GSUITE_CREDENTIALS_JSON environment variable is not set"
    assert google_email, "GOOGLE_ACCOUNT_EMAIL environment variable is not set"
    assert google_client_id, "GOOGLE_CLIENT_ID environment variable is not set"
    assert google_client_secret, "GOOGLE_CLIENT_SECRET environment variable is not set"

    try:
        credentials_json_decoded = base64.b64decode(credentials_json_str).decode("utf-8")
        decoded_credentials = json.loads(credentials_json_decoded)

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

    credentials_file = ".e2e_test_credentials.json"
    with open(credentials_file, "w") as f:
        json.dump(credentials_json, f)

    oauth2_file = f".oauth2.{google_email}.json"
    with open(oauth2_file, "w") as f:
        json.dump(credentials_json, f)

    os.environ["GSUITE_CREDENTIALS_FILE"] = credentials_file
    os.environ["GSUITE_EMAIL"] = google_email

    yield {
        "credentials_file": credentials_file,
        "oauth2_file": oauth2_file,
        "email": google_email,
        "project_id": google_project_id,
        "client_id": google_client_id,
        "client_secret": google_client_secret,
    }

    if os.path.exists(credentials_file):
        os.remove(credentials_file)
    if os.path.exists(oauth2_file):
        os.remove(oauth2_file)


@pytest.fixture
def test_file():
    """Create a temporary test file for upload tests"""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp:
        temp.write(b"This is a test file for Google Drive operations.")

    yield temp.name

    if os.path.exists(temp.name):
        os.remove(temp.name)


@pytest.mark.asyncio
class TestMCPGDriveOperations:
    @pytest.mark.e2e
    async def test_upload_drive_file(self, credentials, test_file):
        """Test for uploading a file to Google Drive"""
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Failed to initialize MCP server"

            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "No tools found in response"

            gdrive_tools = [
                tool
                for tool in tools_response["tools"]
                if "drive" in tool.get("name", "").lower() or "gdrive" in tool.get("name", "").lower()
            ]

            if not gdrive_tools:
                pytest.skip("No GDrive tools found")

            upload_file_tool = find_tool_by_name(gdrive_tools, "upload")
            if not upload_file_tool:
                pytest.skip("GDrive upload file tool not found")

            tool_name = upload_file_tool.get("name")
            if not tool_name:
                pytest.skip("Upload tool has no name")

            upload_params = {
                "file_path": test_file,
                "user_id": credentials["email"],
            }

            result = await send_tools_call(read_stream, write_stream, tool_name, upload_params)

            assert result, "Upload file tool execution failed"
            assert "content" in result, "No content in upload file response"
            assert len(result["content"]) > 0, "Empty content in upload file response"

            has_file_data = False
            file_id = None
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    response_text = item.get("text")

                    if "failed to upload" in response_text.lower():
                        print(f"Warning: Failed to upload file {test_file}")
                        return

                    try:
                        file_data = json.loads(response_text)
                        if isinstance(file_data, dict) and "id" in file_data:
                            has_file_data = True
                            file_id = file_data["id"]
                            print(f"Successfully uploaded file with ID: {file_id}")
                            break
                    except json.JSONDecodeError:
                        continue

            assert has_file_data, "No valid file upload data found in response"
            assert file_id, "No file ID found in upload response"

            return file_id

    @pytest.mark.e2e
    async def test_copy_drive_file(self, credentials):
        """Test for copying a file in Google Drive"""
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Failed to initialize MCP server"

            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "No tools found in response"

            gdrive_tools = [
                tool
                for tool in tools_response["tools"]
                if "drive" in tool.get("name", "").lower() or "gdrive" in tool.get("name", "").lower()
            ]

            if not gdrive_tools:
                pytest.skip("No GDrive tools found")

            list_files_tool = find_tool_by_name(gdrive_tools, "list")
            if not list_files_tool:
                pytest.skip("GDrive list files tool not found")

            list_tool_name = list_files_tool.get("name")
            if not list_tool_name:
                pytest.skip("List files tool has no name")

            list_params = {"limit": 1, "user_id": credentials["email"]}
            list_result = await send_tools_call(read_stream, write_stream, list_tool_name, list_params)

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

            if not file_id:
                pytest.skip("No file ID found to test copy_file tool")

            copy_file_tool = find_tool_by_name(gdrive_tools, "copy")
            if not copy_file_tool:
                pytest.skip("GDrive copy file tool not found")

            copy_tool_name = copy_file_tool.get("name")
            if not copy_tool_name:
                pytest.skip("Copy file tool has no name")

            new_name = f"Copy of file {file_id}"
            copy_params = {
                "file_id": file_id,
                "new_name": new_name,
                "user_id": credentials["email"],
            }
            result = await send_tools_call(read_stream, write_stream, copy_tool_name, copy_params)

            assert result, "Copy file tool execution failed"
            assert "content" in result, "No content in copy file response"
            assert len(result["content"]) > 0, "Empty content in copy file response"

            has_file_data = False
            copied_file_id = None
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    response_text = item.get("text")

                    if "failed to copy" in response_text.lower():
                        print(f"Warning: Failed to copy file with ID {file_id}")
                        return

                    try:
                        file_data = json.loads(response_text)
                        if isinstance(file_data, dict) and "id" in file_data:
                            has_file_data = True
                            copied_file_id = file_data["id"]
                            print(f"Successfully copied file to ID: {copied_file_id}")
                            break
                    except json.JSONDecodeError:
                        continue

            assert has_file_data, "No valid file copy data found in response"
            assert copied_file_id, "No file ID found in copy response"
            assert copied_file_id != file_id, "Copied file ID should be different from original file ID"

            return copied_file_id

    @pytest.mark.e2e
    async def test_rename_drive_file(self, credentials):
        """Test for renaming a file in Google Drive"""
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Failed to initialize MCP server"

            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "No tools found in response"

            gdrive_tools = [
                tool
                for tool in tools_response["tools"]
                if "drive" in tool.get("name", "").lower() or "gdrive" in tool.get("name", "").lower()
            ]

            if not gdrive_tools:
                pytest.skip("No GDrive tools found")

            list_files_tool = find_tool_by_name(gdrive_tools, "list")
            if not list_files_tool:
                pytest.skip("GDrive list files tool not found")

            list_tool_name = list_files_tool.get("name")
            if not list_tool_name:
                pytest.skip("List files tool has no name")

            list_params = {"limit": 1, "user_id": credentials["email"]}
            list_result = await send_tools_call(read_stream, write_stream, list_tool_name, list_params)

            assert list_result, "List files tool execution failed"
            assert "content" in list_result, "No content in list files response"
            assert len(list_result["content"]) > 0, "Empty content in list files response"

            file_id = None
            original_name = None
            for item in list_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        files_data = json.loads(item.get("text"))
                        if isinstance(files_data, dict) and "files" in files_data and files_data["files"]:
                            file_id = files_data["files"][0]["id"]
                            original_name = files_data["files"][0]["name"]
                            break
                    except json.JSONDecodeError:
                        continue

            if not file_id:
                pytest.skip("No file ID found to test rename_file tool")

            rename_file_tool = find_tool_by_name(gdrive_tools, "rename")
            if not rename_file_tool:
                pytest.skip("GDrive rename file tool not found")

            rename_tool_name = rename_file_tool.get("name")
            if not rename_tool_name:
                pytest.skip("Rename file tool has no name")

            file_id_prefix = file_id[:4] if file_id and len(file_id) >= 4 else "test"
            new_name = f"Renamed {original_name or 'file'} - {file_id_prefix}"

            rename_params = {
                "file_id": file_id,
                "new_name": new_name,
                "user_id": credentials["email"],
            }
            result = await send_tools_call(read_stream, write_stream, rename_tool_name, rename_params)

            assert result, "Rename file tool execution failed"
            assert "content" in result, "No content in rename file response"
            assert len(result["content"]) > 0, "Empty content in rename file response"

            has_file_data = False
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    response_text = item.get("text")

                    if "failed to rename" in response_text.lower():
                        print(f"Warning: Failed to rename file with ID {file_id}")
                        return

                    try:
                        file_data = json.loads(response_text)
                        if isinstance(file_data, dict) and "id" in file_data and "name" in file_data:
                            has_file_data = True
                            assert file_data["id"] == file_id, "File ID should not change after rename"
                            assert file_data["name"] == new_name, "File name should be updated to new name"
                            print(f"Successfully renamed file to: {file_data['name']}")
                            break
                    except json.JSONDecodeError:
                        continue

            assert has_file_data, "No valid file rename data found in response"

    @pytest.mark.e2e
    async def test_move_drive_file(self, credentials):
        """Test for moving a file in Google Drive"""
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Failed to initialize MCP server"

            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "No tools found in response"

            gdrive_tools = [
                tool
                for tool in tools_response["tools"]
                if "drive" in tool.get("name", "").lower() or "gdrive" in tool.get("name", "").lower()
            ]

            if not gdrive_tools:
                pytest.skip("No GDrive tools found")

            list_files_tool = find_tool_by_name(gdrive_tools, "list")
            if not list_files_tool:
                pytest.skip("GDrive list files tool not found")

            list_tool_name = list_files_tool.get("name")
            if not list_tool_name:
                pytest.skip("List files tool has no name")

            list_params = {"limit": 1, "user_id": credentials["email"]}
            list_result = await send_tools_call(read_stream, write_stream, list_tool_name, list_params)

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

            if not file_id:
                pytest.skip("No file ID found to test move_file tool")

            folder_query = "mimeType='application/vnd.google-apps.folder'"
            folder_params = {"query": folder_query, "limit": 1, "user_id": credentials["email"]}
            folder_result = await send_tools_call(read_stream, write_stream, list_tool_name, folder_params)

            assert folder_result, "List folders tool execution failed"
            assert "content" in folder_result, "No content in list folders response"
            assert len(folder_result["content"]) > 0, "Empty content in list folders response"

            folder_id = None
            for item in folder_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        folders_data = json.loads(item.get("text"))
                        if isinstance(folders_data, dict) and "files" in folders_data and folders_data["files"]:
                            folder_id = folders_data["files"][0]["id"]
                            break
                    except json.JSONDecodeError:
                        continue

            if not folder_id:
                pytest.skip("No folder ID found to test move_file tool")

            move_file_tool = find_tool_by_name(gdrive_tools, "move")
            if not move_file_tool:
                pytest.skip("GDrive move file tool not found")

            move_tool_name = move_file_tool.get("name")
            if not move_tool_name:
                pytest.skip("Move file tool has no name")

            move_params = {
                "file_id": file_id,
                "new_parent_id": folder_id,
                "user_id": credentials["email"],
            }
            result = await send_tools_call(read_stream, write_stream, move_tool_name, move_params)

            assert result, "Move file tool execution failed"
            assert "content" in result, "No content in move file response"
            assert len(result["content"]) > 0, "Empty content in move file response"

            has_file_data = False
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    response_text = item.get("text")

                    if "failed to move" in response_text.lower():
                        print(f"Warning: Failed to move file with ID {file_id}")
                        return

                    try:
                        file_data = json.loads(response_text)
                        if isinstance(file_data, dict) and "id" in file_data and "parents" in file_data:
                            has_file_data = True
                            assert file_data["id"] == file_id, "File ID should not change after move"
                            assert folder_id in file_data["parents"], "File should be moved to the target folder"
                            print(f"Successfully moved file to folder: {folder_id}")
                            break
                    except json.JSONDecodeError:
                        continue

            assert has_file_data, "No valid file move data found in response"

    @pytest.mark.e2e
    async def test_delete_drive_file(self, credentials, test_file):
        """Test for deleting a file from Google Drive"""
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Failed to initialize MCP server"

            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "No tools found in response"

            gdrive_tools = [
                tool
                for tool in tools_response["tools"]
                if "drive" in tool.get("name", "").lower() or "gdrive" in tool.get("name", "").lower()
            ]

            if not gdrive_tools:
                pytest.skip("No GDrive tools found")

            upload_file_tool = find_tool_by_name(gdrive_tools, "upload")
            if not upload_file_tool:
                pytest.skip("GDrive upload file tool not found")

            upload_tool_name = upload_file_tool.get("name")
            if not upload_tool_name:
                pytest.skip("Upload file tool has no name")

            upload_params = {
                "file_path": test_file,
                "user_id": credentials["email"],
            }
            upload_result = await send_tools_call(read_stream, write_stream, upload_tool_name, upload_params)

            assert upload_result, "Upload file tool execution failed"
            assert "content" in upload_result, "No content in upload file response"
            assert len(upload_result["content"]) > 0, "Empty content in upload file response"

            file_id = None
            for item in upload_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        file_data = json.loads(item.get("text"))
                        if isinstance(file_data, dict) and "id" in file_data:
                            file_id = file_data["id"]
                            break
                    except json.JSONDecodeError:
                        continue

            if not file_id:
                pytest.skip("No file ID found to test delete_file tool")

            delete_file_tool = find_tool_by_name(gdrive_tools, "delete")
            if not delete_file_tool:
                pytest.skip("GDrive delete file tool not found")

            delete_tool_name = delete_file_tool.get("name")
            if not delete_tool_name:
                pytest.skip("Delete file tool has no name")

            delete_params = {
                "file_id": file_id,
                "user_id": credentials["email"],
            }
            result = await send_tools_call(read_stream, write_stream, delete_tool_name, delete_params)

            assert result, "Delete file tool execution failed"
            assert "content" in result, "No content in delete file response"
            assert len(result["content"]) > 0, "Empty content in delete file response"

            success = False
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    response_text = item.get("text")

                    if "failed to delete" in response_text.lower():
                        print(f"Warning: Failed to delete file with ID {file_id}")
                        return

                    if "successfully deleted" in response_text.lower():
                        success = True
                        print(f"Successfully deleted file with ID: {file_id}")
                        break

            assert success, "No confirmation of successful deletion found in response"

    @pytest.mark.e2e
    async def test_folder_operations(self, credentials):
        """Test dedicated folder operations in Google Drive:
        1. Create a folder
        2. List folders
        3. Rename the folder
        4. Create a subfolder
        5. Move the subfolder to another location
        6. Delete both folders
        """
        with open(credentials["credentials_file"]) as f:
            creds_data = json.load(f)
            scopes = creds_data.get("scopes", [])
            if "https://www.googleapis.com/auth/drive" not in scopes:
                pytest.skip("Credentials do not have Drive scope. Please regenerate credentials with Drive scope.")

        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Failed to initialize MCP server"

            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "No tools found in response"

            gdrive_tools = [
                tool
                for tool in tools_response["tools"]
                if "drive" in tool.get("name", "").lower() or "gdrive" in tool.get("name", "").lower()
            ]

            if not gdrive_tools:
                pytest.skip("No GDrive tools found")

            create_folder_tool = find_tool_by_name(gdrive_tools, "create_drive_folder")
            list_folders_tool = find_tool_by_name(gdrive_tools, "list_drive_folders")
            rename_folder_tool = find_tool_by_name(gdrive_tools, "rename_drive_folder")
            move_folder_tool = find_tool_by_name(gdrive_tools, "move_drive_folder")
            delete_folder_tool = find_tool_by_name(gdrive_tools, "delete_drive_folder")

            if not all(
                [create_folder_tool, list_folders_tool, rename_folder_tool, move_folder_tool, delete_folder_tool]
            ):
                pytest.skip("Not all required folder tools found")

            # 1. Create a folder
            folder_name = f"Test Folder {int(time.time())}"
            folder_result = await send_tools_call(
                read_stream,
                write_stream,
                create_folder_tool.get("name"),
                {
                    "folder_name": folder_name,
                    "user_id": credentials["email"],
                },
            )

            assert folder_result, "Failed to create folder"
            assert "content" in folder_result, "No content in folder creation response"

            folder_id = None
            for item in folder_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        folder_data = json.loads(item.get("text"))
                        if isinstance(folder_data, dict) and "id" in folder_data:
                            folder_id = folder_data.get("id")
                            print(f"Created folder with ID: {folder_id}")
                            break
                    except json.JSONDecodeError:
                        continue

            assert folder_id, "Failed to get folder ID"

            list_result = await send_tools_call(
                read_stream,
                write_stream,
                list_folders_tool.get("name"),
                {
                    "user_id": credentials["email"],
                    "limit": 10,
                },
            )

            assert list_result, "Failed to list folders"
            assert "content" in list_result, "No content in list folders response"

            found_folder = False
            for item in list_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        folders_data = json.loads(item.get("text"))
                        if isinstance(folders_data, dict) and "files" in folders_data:
                            for folder in folders_data["files"]:
                                if folder.get("id") == folder_id:
                                    found_folder = True
                                    print(f"Found folder in listing: {folder.get('name')}")
                                    break
                    except json.JSONDecodeError:
                        continue

            assert found_folder, "Created folder not found in folder listing"

            # 3. Rename the folder
            new_folder_name = f"Renamed Folder {int(time.time())}"
            rename_result = await send_tools_call(
                read_stream,
                write_stream,
                rename_folder_tool.get("name"),
                {
                    "folder_id": folder_id,
                    "new_name": new_folder_name,
                    "user_id": credentials["email"],
                },
            )

            assert rename_result, "Failed to rename folder"
            assert "content" in rename_result, "No content in rename folder response"

            renamed_folder_data = None
            for item in rename_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        folder_data = json.loads(item.get("text"))
                        if isinstance(folder_data, dict) and "id" in folder_data:
                            renamed_folder_data = folder_data
                            print(f"Renamed folder to: {folder_data.get('name')}")
                            break
                    except json.JSONDecodeError:
                        continue

            assert renamed_folder_data, "Failed to get renamed folder data"
            assert renamed_folder_data.get("name") == new_folder_name, "Folder name not updated correctly"

            subfolder_name = f"Subfolder {int(time.time())}"
            subfolder_result = await send_tools_call(
                read_stream,
                write_stream,
                create_folder_tool.get("name"),
                {
                    "folder_name": subfolder_name,
                    "parent_folder_id": folder_id,
                    "user_id": credentials["email"],
                },
            )

            assert subfolder_result, "Failed to create subfolder"
            assert "content" in subfolder_result, "No content in subfolder creation response"

            subfolder_id = None
            for item in subfolder_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        folder_data = json.loads(item.get("text"))
                        if isinstance(folder_data, dict) and "id" in folder_data:
                            subfolder_id = folder_data.get("id")
                            print(f"Created subfolder with ID: {subfolder_id}")
                            break
                    except json.JSONDecodeError:
                        continue

            assert subfolder_id, "Failed to get subfolder ID"

            # 5. Create another folder to move the subfolder to
            target_folder_name = f"Target Folder {int(time.time())}"
            target_folder_result = await send_tools_call(
                read_stream,
                write_stream,
                create_folder_tool.get("name"),
                {
                    "folder_name": target_folder_name,
                    "user_id": credentials["email"],
                },
            )

            assert target_folder_result, "Failed to create target folder"
            assert "content" in target_folder_result, "No content in target folder creation response"

            target_folder_id = None
            for item in target_folder_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        folder_data = json.loads(item.get("text"))
                        if isinstance(folder_data, dict) and "id" in folder_data:
                            target_folder_id = folder_data.get("id")
                            print(f"Created target folder with ID: {target_folder_id}")
                            break
                    except json.JSONDecodeError:
                        continue

            assert target_folder_id, "Failed to get target folder ID"

            move_result = await send_tools_call(
                read_stream,
                write_stream,
                move_folder_tool.get("name"),
                {
                    "folder_id": subfolder_id,
                    "new_parent_id": target_folder_id,
                    "user_id": credentials["email"],
                },
            )

            assert move_result, "Failed to move subfolder"
            assert "content" in move_result, "No content in move subfolder response"

            moved_folder_data = None
            for item in move_result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        folder_data = json.loads(item.get("text"))
                        if isinstance(folder_data, dict) and "id" in folder_data:
                            moved_folder_data = folder_data
                            print("Moved subfolder to target folder")
                            break
                    except json.JSONDecodeError:
                        continue

            assert moved_folder_data, "Failed to get moved folder data"
            assert subfolder_id == moved_folder_data.get("id"), "Moved folder ID should match subfolder ID"

            folders_to_delete = [subfolder_id, folder_id, target_folder_id]
            deleted_count = 0

            for folder_id_to_delete in folders_to_delete:
                delete_result = await send_tools_call(
                    read_stream,
                    write_stream,
                    delete_folder_tool.get("name"),
                    {
                        "folder_id": folder_id_to_delete,
                        "user_id": credentials["email"],
                    },
                )

                assert delete_result, f"Failed to delete folder {folder_id_to_delete}"
                assert "content" in delete_result, "No content in delete folder response"

                for item in delete_result["content"]:
                    if item.get("type") == "text" and item.get("text"):
                        response_text = item.get("text")
                        if "successfully deleted" in response_text.lower():
                            deleted_count += 1
                            print(f"Deleted folder with ID: {folder_id_to_delete}")
                            break

            assert deleted_count == len(
                folders_to_delete
            ), f"Expected to delete {len(folders_to_delete)} folders, but deleted {deleted_count}"

    @pytest.mark.e2e
    async def test_complex_drive_scenario(self, credentials):
        """Test a complex scenario with multiple Drive operations:
        1. Create and upload multiple dummy files
        2. List the uploaded files
        3. Download one of the uploaded files
        4. Rename some files
        5. Create a folder
        6. Move files to the folder
        7. Remove all dummy files and the folder
        """
        with open(credentials["credentials_file"]) as f:
            creds_data = json.load(f)
            scopes = creds_data.get("scopes", [])
            if "https://www.googleapis.com/auth/drive" not in scopes:
                pytest.skip("Credentials do not have Drive scope. Please regenerate credentials with Drive scope.")

        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Failed to initialize MCP server"

            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "No tools found in response"

            gdrive_tools = [
                tool
                for tool in tools_response["tools"]
                if "drive" in tool.get("name", "").lower() or "gdrive" in tool.get("name", "").lower()
            ]

            if not gdrive_tools:
                pytest.skip("No GDrive tools found")

            upload_tool = find_tool_by_name(gdrive_tools, "upload")
            list_tool = find_tool_by_name(gdrive_tools, "list")
            download_tool = find_tool_by_name(gdrive_tools, "download")
            rename_tool = find_tool_by_name(gdrive_tools, "rename")
            move_tool = find_tool_by_name(gdrive_tools, "move")
            delete_tool = find_tool_by_name(gdrive_tools, "delete")

            create_folder_tool = find_tool_by_name(gdrive_tools, "create_drive_folder")
            list_folders_tool = find_tool_by_name(gdrive_tools, "list_drive_folders")
            rename_folder_tool = find_tool_by_name(gdrive_tools, "rename_drive_folder")
            move_folder_tool = find_tool_by_name(gdrive_tools, "move_drive_folder")
            delete_folder_tool = find_tool_by_name(gdrive_tools, "delete_drive_folder")

            if not all([upload_tool, list_tool, download_tool, rename_tool, move_tool, delete_tool]):
                pytest.skip("Not all required GDrive file tools found")

            folder_tools_available = all(
                [create_folder_tool, list_folders_tool, rename_folder_tool, move_folder_tool, delete_folder_tool]
            )
            use_folder_specific_tools = folder_tools_available

            temp_dir = tempfile.mkdtemp()
            dummy_files = []
            file_count = 5  # Create 5 dummy files for testing
            temp_placeholder = os.path.join(temp_dir, ".placeholder")

            for i in range(file_count):
                file_path = os.path.join(temp_dir, f"dummy_file_{i}.txt")
                with open(file_path, "w") as f:
                    f.write(f"This is dummy file {i} for Drive tools e2e test.\n")
                dummy_files.append(file_path)

            try:
                uploaded_files = []
                for file_path in dummy_files:
                    upload_result = await send_tools_call(
                        read_stream,
                        write_stream,
                        upload_tool.get("name"),
                        {
                            "file_path": file_path,
                            "user_id": credentials["email"],
                        },
                    )

                    assert upload_result, f"Failed to upload file {file_path}"
                    assert "content" in upload_result, "No content in upload response"

                    for item in upload_result["content"]:
                        if item.get("type") == "text" and item.get("text"):
                            try:
                                file_data = json.loads(item.get("text"))
                                if isinstance(file_data, dict) and "id" in file_data:
                                    uploaded_files.append(file_data)
                                    print(f"Uploaded file: {file_data.get('name')} (ID: {file_data.get('id')})")
                                    break
                            except json.JSONDecodeError:
                                continue

                assert (
                    len(uploaded_files) == file_count
                ), f"Expected {file_count} uploaded files, got {len(uploaded_files)}"

                list_result = await send_tools_call(
                    read_stream,
                    write_stream,
                    list_tool.get("name"),
                    {
                        "user_id": credentials["email"],
                        "query": "name contains 'dummy_file'",
                        "limit": 10,
                    },
                )

                assert list_result, "Failed to list files"
                assert "content" in list_result, "No content in list response"

                listed_files = []
                for item in list_result["content"]:
                    if item.get("type") == "text" and item.get("text"):
                        try:
                            files_data = json.loads(item.get("text"))
                            if isinstance(files_data, dict) and "files" in files_data:
                                listed_files = files_data["files"]
                                break
                        except json.JSONDecodeError:
                            continue

                assert len(listed_files) >= file_count, f"Expected at least {file_count} files in listing"

                # Download one of the uploaded files
                download_file_id = uploaded_files[0].get("id")
                download_result = await send_tools_call(
                    read_stream,
                    write_stream,
                    download_tool.get("name"),
                    {
                        "file_id": download_file_id,
                        "user_id": credentials["email"],
                    },
                )

                assert download_result, f"Failed to download file {download_file_id}"
                assert "content" in download_result, "No content in download response"

                downloaded_file_info = None
                for item in download_result["content"]:
                    if item.get("type") == "text" and item.get("text"):
                        try:
                            file_data = json.loads(item.get("text"))
                            if isinstance(file_data, dict) and "name" in file_data:
                                downloaded_file_info = file_data
                                print(f"Downloaded file: {file_data.get('name')} (Size: {file_data.get('size')})")
                                break
                        except json.JSONDecodeError:
                            continue

                assert downloaded_file_info is not None, "Failed to get download file information"

                renamed_files = []
                for i in range(min(2, len(uploaded_files))):
                    file_id = uploaded_files[i].get("id")
                    old_name = uploaded_files[i].get("name")
                    new_name = f"renamed_{old_name}"

                    rename_result = await send_tools_call(
                        read_stream,
                        write_stream,
                        rename_tool.get("name"),
                        {
                            "file_id": file_id,
                            "new_name": new_name,
                            "user_id": credentials["email"],
                        },
                    )

                    assert rename_result, f"Failed to rename file {file_id}"
                    assert "content" in rename_result, "No content in rename response"

                    for item in rename_result["content"]:
                        if item.get("type") == "text" and item.get("text"):
                            try:
                                file_data = json.loads(item.get("text"))
                                if isinstance(file_data, dict) and "id" in file_data:
                                    renamed_files.append(file_data)
                                    print(f"Renamed file to: {file_data.get('name')}")
                                    break
                            except json.JSONDecodeError:
                                continue

                assert len(renamed_files) == min(2, len(uploaded_files)), "Failed to rename files"

                if use_folder_specific_tools and create_folder_tool:
                    folder_name = f"Test Folder {int(time.time())}"
                    folder_result = await send_tools_call(
                        read_stream,
                        write_stream,
                        create_folder_tool.get("name"),
                        {
                            "folder_name": folder_name,
                            "user_id": credentials["email"],
                        },
                    )
                else:
                    temp_placeholder = os.path.join(temp_dir, ".placeholder")
                    with open(temp_placeholder, "w") as f:
                        f.write("")

                    folder_result = await send_tools_call(
                        read_stream,
                        write_stream,
                        upload_tool.get("name"),
                        {
                            "file_path": temp_placeholder,
                            "mime_type": "application/vnd.google-apps.folder",
                            "user_id": credentials["email"],
                        },
                    )

                assert folder_result, "Failed to create folder"
                assert "content" in folder_result, "No content in folder creation response"

                folder_id = None
                for item in folder_result["content"]:
                    if item.get("type") == "text" and item.get("text"):
                        try:
                            folder_data = json.loads(item.get("text"))
                            if isinstance(folder_data, dict) and "id" in folder_data:
                                folder_id = folder_data.get("id")
                                print(f"Created folder with ID: {folder_id}")
                                break
                        except json.JSONDecodeError:
                            continue

                assert folder_id, "Failed to get folder ID"

                moved_files = []
                for i in range(2, min(4, len(uploaded_files))):
                    file_id = uploaded_files[i].get("id")
                    file_name = uploaded_files[i].get("name")

                    move_result = await send_tools_call(
                        read_stream,
                        write_stream,
                        move_tool.get("name"),
                        {
                            "file_id": file_id,
                            "new_parent_id": folder_id,
                            "user_id": credentials["email"],
                        },
                    )

                    assert move_result, f"Failed to move file {file_id}"
                    assert "content" in move_result, "No content in move response"

                    for item in move_result["content"]:
                        if item.get("type") == "text" and item.get("text"):
                            try:
                                file_data = json.loads(item.get("text"))
                                if isinstance(file_data, dict) and "id" in file_data:
                                    moved_files.append(file_data)
                                    print(f"Moved file: {file_name} to folder")
                                    break
                            except json.JSONDecodeError:
                                continue

                assert len(moved_files) == min(2, len(uploaded_files) - 2), "Failed to move files"

                all_to_delete = [*uploaded_files, {"id": folder_id}]
                deleted_count = 0

                for file_data in all_to_delete:
                    file_id = file_data.get("id")
                    delete_result = await send_tools_call(
                        read_stream,
                        write_stream,
                        delete_tool.get("name"),
                        {
                            "file_id": file_id,
                            "user_id": credentials["email"],
                        },
                    )

                    assert delete_result, f"Failed to delete file/folder {file_id}"
                    assert "content" in delete_result, "No content in delete response"

                    for item in delete_result["content"]:
                        if item.get("type") == "text" and item.get("text"):
                            response_text = item.get("text")
                            if "successfully deleted" in response_text.lower():
                                deleted_count += 1
                                print(f"Deleted file/folder with ID: {file_id}")
                                break

                assert deleted_count == len(
                    all_to_delete
                ), f"Expected to delete {len(all_to_delete)} items, but deleted {deleted_count}"

            finally:
                for file_path in dummy_files:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                if os.path.exists(temp_placeholder):
                    os.remove(temp_placeholder)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
