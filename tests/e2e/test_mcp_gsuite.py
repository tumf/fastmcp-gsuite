import datetime
import json
import os
import shutil

import pytest
from chuk_mcp.mcp_client.messages.initialize.send_messages import send_initialize
from chuk_mcp.mcp_client.messages.ping.send_messages import send_ping
from chuk_mcp.mcp_client.messages.tools.send_messages import send_tools_call, send_tools_list
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import StdioServerParameters

# Get UV path from environment variables or PATH
UV_PATH = os.environ.get("UV_PATH") or shutil.which("uv") or "/Users/tumf/.pyenv/shims/uv"
# Temporarily disable skipping for test execution
# if not UV_PATH:
#     pytest.skip("uv command not found in PATH or UV_PATH not set")


@pytest.mark.asyncio
class TestMCPGsuite:
    @pytest.mark.e2e
    async def test_mcp_connection_and_tools(self, oauth_token):
        """Test connecting to the MCP server and listing tools"""
        # Get parent process environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": oauth_token["credentials_file"],
                "GSUITE_EMAIL": oauth_token["email"],
            }
        )

        # Set MCP Gsuite server parameters
        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

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
            gmail_tools = [tool for tool in tools_response["tools"] if "gmail" in tool["name"].lower()]
            assert len(gmail_tools) > 0, f"No Gmail tools found. Available tools: {tool_names}"

            # Find Calendar related tools
            calendar_tools = [tool for tool in tools_response["tools"] if "calendar" in tool["name"].lower()]
            assert len(calendar_tools) > 0, f"No Calendar tools found. Available tools: {tool_names}"

            # Verify specific tool names (confirmed in previous executions)
            assert "query_gmail_emails" in tool_names, f"query_gmail_emails tool not found in {tool_names}"
            assert "list_calendar_events" in tool_names, f"list_calendar_events tool not found in {tool_names}"

    @pytest.mark.e2e
    async def test_gmail_tool_list_messages(self, oauth_token):
        """Test Gmail tool for listing messages"""
        # Get parent process environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": oauth_token["credentials_file"],
                "GSUITE_EMAIL": oauth_token["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

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
                    "user_id": oauth_token["email"],  # Add user ID as argument
                },
            )

            assert result, "Tool call returned no result"
            assert not result.get("isError", False), f"Tool call returned error: {result}"

            # Verify that the response is a dictionary
            assert isinstance(result, dict), f"Result is not a dictionary: {type(result)}"

            # Verify response
            assert "content" in result, f"No content field in response: {result}"
            assert len(result["content"]) > 0, f"Empty content in response: {result}"

            # Print response for debugging
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    print(f"Response text: {item.get('text')[:100]}...")  # Print first 100 chars

            # Check if we have a valid response (individual JSON objects or "No emails found" message)
            is_valid_response = False
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    text = item.get("text")
                    # Try parsing as JSON
                    try:
                        # Check for individual JSON objects with email data
                        if '"id"' in text and '"threadId"' in text:
                            is_valid_response = True
                            break
                        # Check for JSON array
                        data = json.loads(text)
                        if isinstance(data, list) or "id" in data:
                            is_valid_response = True
                            break
                    except json.JSONDecodeError:
                        # Check if it contains a known response message
                        if "No emails found" in text:
                            is_valid_response = True
                            break

            assert is_valid_response, "No valid response found"

    @pytest.mark.e2e
    async def test_calendar_tool_list_events(self, oauth_token):
        """Test Calendar tool for listing events"""
        # Get parent process environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": oauth_token["credentials_file"],
                "GSUITE_EMAIL": oauth_token["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            await send_initialize(read_stream, write_stream)

            # Get current date and time
            import datetime

            now = datetime.datetime.now(datetime.UTC)
            start_time = now.isoformat()
            end_time = (now + datetime.timedelta(days=7)).isoformat()

            # Use Calendar list events tool (correct parameter names)
            result = await send_tools_call(
                read_stream,
                write_stream,
                name="list_calendar_events",
                arguments={
                    "calendar_id": "primary",
                    "start_time": start_time,
                    "end_time": end_time,
                    "max_results": 5,
                    "user_id": oauth_token["email"],  # Add user ID as argument
                },
            )

            assert result, "Tool call returned no result"
            assert not result.get("isError", False), f"Tool call returned error: {result}"

            # Verify that the response is a dictionary
            assert isinstance(result, dict), f"Result is not a dictionary: {type(result)}"

            # Verify response
            assert "content" in result, f"No content field in response: {result}"
            assert len(result["content"]) > 0, f"Empty content in response: {result}"

    @pytest.mark.e2e
    async def test_gmail_create_draft(self, oauth_token):
        """Test Gmail tool for creating a draft message"""
        # Get parent process environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": oauth_token["credentials_file"],
                "GSUITE_EMAIL": oauth_token["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            await send_initialize(read_stream, write_stream)

            # Create a draft message
            result = await send_tools_call(
                read_stream,
                write_stream,
                name="create_gmail_draft",
                arguments={
                    "user_id": oauth_token["email"],
                    "to": oauth_token["email"],  # Send to self for testing
                    "subject": "E2E Test Draft - " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "body": "This is a test draft message created during E2E testing.",
                },
            )

            assert result, "Tool call returned no result"
            assert not result.get("isError", False), f"Tool call returned error: {result}"

            # Verify that the response is a dictionary
            assert isinstance(result, dict), f"Result is not a dictionary: {type(result)}"

            # Verify response content
            assert "content" in result, f"No content field in response: {result}"
            assert len(result["content"]) > 0, f"Empty content in response: {result}"

            # Extract the draft ID for later use or cleanup
            draft_id = None
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        data = json.loads(item["text"])
                        if isinstance(data, dict) and "id" in data:
                            draft_id = data["id"]
                            break
                    except json.JSONDecodeError:
                        continue

            assert draft_id, "Could not extract draft ID from response"
            print(f"Created draft with ID: {draft_id}")

            # Store the draft ID in environment variable for other tests to use or clean up
            os.environ["E2E_TEST_DRAFT_ID"] = draft_id

    @pytest.mark.e2e
    async def test_gmail_delete_draft(self, oauth_token):
        """Test Gmail tool for deleting a draft message"""
        # Check if we have a draft ID from previous test
        draft_id = os.environ.get("E2E_TEST_DRAFT_ID")
        if not draft_id:
            pytest.skip("No draft ID available for delete test")

        # Get parent process environment variables and add necessary variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": oauth_token["credentials_file"],
                "GSUITE_EMAIL": oauth_token["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            await send_initialize(read_stream, write_stream)

            # Delete the draft message
            result = await send_tools_call(
                read_stream,
                write_stream,
                name="delete_gmail_draft",
                arguments={
                    "user_id": oauth_token["email"],
                    "draft_id": draft_id,
                },
            )

            assert result, "Tool call returned no result"
            assert not result.get("isError", False), f"Tool call returned error: {result}"

            # Verify that the response is a dictionary
            assert isinstance(result, dict), f"Result is not a dictionary: {type(result)}"

            # Success should be indicated in the response
            success = False
            for item in result.get("content", []):
                if item.get("type") == "text" and "success" in item.get("text", "").lower():
                    success = True
                    break

            assert success, "Draft deletion success confirmation not found in response"
            print(f"Successfully deleted draft with ID: {draft_id}")

            # Clean up environment variable
            if "E2E_TEST_DRAFT_ID" in os.environ:
                del os.environ["E2E_TEST_DRAFT_ID"]

    @pytest.mark.e2e
    async def test_gmail_reply(self, oauth_token):
        """Test Gmail tool for replying to a message"""
        # Get parent process environment variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": oauth_token["credentials_file"],
                "GSUITE_EMAIL": oauth_token["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            await send_initialize(read_stream, write_stream)

            # First, get a message to reply to
            list_result = await send_tools_call(
                read_stream,
                write_stream,
                name="query_gmail_emails",
                arguments={
                    "max_results": 5,
                    "user_id": oauth_token["email"],
                },
            )

            assert list_result, "Tool call to list messages returned no result"
            assert not list_result.get("isError", False), f"Tool call to list messages returned error: {list_result}"

            # Extract a message ID to reply to
            message_id = None
            thread_id = None
            for item in list_result.get("content", []):
                if item.get("type") == "text" and item.get("text"):
                    try:
                        data = json.loads(item["text"])
                        if isinstance(data, list) and len(data) > 0:
                            # Get the first message ID from the list
                            message_id = data[0].get("id")
                            thread_id = data[0].get("threadId")
                            break
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

            if not message_id or not thread_id:
                pytest.skip("No message found to reply to")

            # Create a reply as draft
            reply_result = await send_tools_call(
                read_stream,
                write_stream,
                name="reply_to_gmail_message",
                arguments={
                    "user_id": oauth_token["email"],
                    "message_id": message_id,
                    "thread_id": thread_id,
                    "body": f"This is an E2E test reply - {datetime.datetime.now().isoformat()}",
                    "as_draft": True,
                },
            )

            assert reply_result, "Tool call to reply returned no result"
            assert not reply_result.get("isError", False), f"Tool call to reply returned error: {reply_result}"

            # Extract the draft ID for cleanup
            draft_id = None
            for item in reply_result.get("content", []):
                if item.get("type") == "text" and item.get("text"):
                    # Look for a JSON structure or a line containing a draft ID
                    try:
                        data = json.loads(item["text"])
                        if isinstance(data, dict) and data.get("id"):
                            draft_id = data.get("id")
                            break
                    except json.JSONDecodeError:
                        # Try to find it in text output
                        text = item["text"]
                        if '"id":' in text:
                            try:
                                # Extract the id if it's in a partial JSON string
                                import re

                                match = re.search(r'"id":\s*"([^"]+)"', text)
                                if match:
                                    draft_id = match.group(1)
                                    break
                            except Exception:
                                continue

            # If we found a draft ID, clean it up
            if draft_id:
                print(f"Created reply draft with ID: {draft_id}")
                # Store for cleanup
                os.environ["E2E_TEST_REPLY_DRAFT_ID"] = draft_id

                # Delete the draft
                delete_result = await send_tools_call(
                    read_stream,
                    write_stream,
                    name="delete_gmail_draft",
                    arguments={
                        "user_id": oauth_token["email"],
                        "draft_id": draft_id,
                    },
                )
                assert delete_result, "Tool call to delete reply draft returned no result"
                assert not delete_result.get("isError", False), f"Error deleting reply draft: {delete_result}"
                print(f"Successfully deleted reply draft with ID: {draft_id}")
                # Clear environment variable
                if "E2E_TEST_REPLY_DRAFT_ID" in os.environ:
                    del os.environ["E2E_TEST_REPLY_DRAFT_ID"]

    @pytest.mark.e2e
    async def test_gmail_get_attachment(self, oauth_token):
        """Test Gmail tool for getting message attachments"""
        # Get parent process environment variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": oauth_token["credentials_file"],
                "GSUITE_EMAIL": oauth_token["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            await send_initialize(read_stream, write_stream)

            # First, query for messages with attachments
            list_result = await send_tools_call(
                read_stream,
                write_stream,
                name="query_gmail_emails",
                arguments={
                    "max_results": 20,
                    "query": "has:attachment",  # Search for messages with attachments
                    "user_id": oauth_token["email"],
                },
            )

            assert list_result, "Tool call to list messages returned no result"
            assert not list_result.get("isError", False), f"Tool call to list messages returned error: {list_result}"

            # Extract a message ID that has attachments
            message_id = None
            for item in list_result.get("content", []):
                if item.get("type") == "text" and item.get("text"):
                    try:
                        data = json.loads(item["text"])
                        if isinstance(data, list) and len(data) > 0:
                            # Get the first message ID from the list
                            message_id = data[0].get("id")
                            break
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

            if not message_id:
                pytest.skip("No message with attachments found")

            # Get the message details to find attachment IDs
            message_result = await send_tools_call(
                read_stream,
                write_stream,
                name="get_gmail_message",
                arguments={
                    "user_id": oauth_token["email"],
                    "message_id": message_id,
                },
            )

            assert message_result, "Tool call to get message details returned no result"
            assert not message_result.get(
                "isError", False
            ), f"Tool call to get message details returned error: {message_result}"

            # Extract attachment ID
            attachment_id = None
            for item in message_result.get("content", []):
                if item.get("type") == "text" and item.get("text"):
                    try:
                        text = item["text"]
                        # Try to parse as JSON first
                        try:
                            data = json.loads(text)
                            # Look for attachments in payload parts
                            if isinstance(data, dict) and "payload" in data:
                                parts = data["payload"].get("parts", [])
                                for part in parts:
                                    if part.get("filename") and part.get("body", {}).get("attachmentId"):
                                        attachment_id = part["body"]["attachmentId"]
                                        print(f"Found attachment: {part['filename']} with ID: {attachment_id}")
                                        break
                        except json.JSONDecodeError:
                            # If not JSON, try to find attachment ID in text
                            import re

                            match = re.search(r'"attachmentId":\s*"([^"]+)"', text)
                            if match:
                                attachment_id = match.group(1)
                                print(f"Found attachment ID in text: {attachment_id}")
                                break
                    except Exception:
                        continue

            if not attachment_id:
                pytest.skip("No attachment ID found in the message")

            # Get the attachment
            attachment_result = await send_tools_call(
                read_stream,
                write_stream,
                name="get_gmail_attachment",
                arguments={
                    "user_id": oauth_token["email"],
                    "message_id": message_id,
                    "attachment_id": attachment_id,
                },
            )

            assert attachment_result, "Tool call to get attachment returned no result"
            assert not attachment_result.get(
                "isError", False
            ), f"Tool call to get attachment returned error: {attachment_result}"

            # Verify response contains the attachment data
            has_attachment_data = False
            for item in attachment_result.get("content", []):
                if item.get("type") == "text" and item.get("text"):
                    # Check if there's attachment data in the response
                    if "data" in item["text"] or "filename" in item["text"]:
                        has_attachment_data = True
                        break

            assert has_attachment_data, "No attachment data found in response"

    @pytest.mark.e2e
    async def test_bulk_save_gmail_attachments(self, oauth_token):
        """Test tool for saving multiple Gmail attachments"""
        # Get parent process environment variables
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": oauth_token["credentials_file"],
                "GSUITE_EMAIL": oauth_token["email"],
            }
        )

        server_params = StdioServerParameters(command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env)

        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize
            await send_initialize(read_stream, write_stream)

            # First, query for messages with attachments
            list_result = await send_tools_call(
                read_stream,
                write_stream,
                name="query_gmail_emails",
                arguments={
                    "max_results": 5,
                    "query": "has:attachment",  # Search for messages with attachments
                    "user_id": oauth_token["email"],
                },
            )

            assert list_result, "Tool call to list messages returned no result"
            assert not list_result.get("isError", False), f"Tool call to list messages returned error: {list_result}"

            # Extract message IDs that may have attachments
            message_ids = []
            for item in list_result.get("content", []):
                if item.get("type") == "text" and item.get("text"):
                    try:
                        data = json.loads(item["text"])
                        if isinstance(data, list) and len(data) > 0:
                            # Get message IDs from the list
                            message_ids = [msg.get("id") for msg in data[:2]]  # Limit to first 2
                            break
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

            if not message_ids:
                pytest.skip("No messages with attachments found")

            # Create temp directory for saving attachments
            temp_dir = os.path.join(os.getcwd(), ".tmp", "e2e-test-attachments")
            os.makedirs(temp_dir, exist_ok=True)
            print(f"Created temp directory for attachments: {temp_dir}")

            # Use bulk save tool
            save_result = await send_tools_call(
                read_stream,
                write_stream,
                name="save_gmail_attachments",
                arguments={
                    "user_id": oauth_token["email"],
                    "message_ids": message_ids,
                    "output_dir": temp_dir,
                    "create_subfolders": True,
                },
            )

            assert save_result, "Tool call to save attachments returned no result"

            # Depending on whether there are actually attachments, we might get success or failure
            if not save_result.get("isError", False):
                # Check if any files were saved
                has_files = False
                for item in save_result.get("content", []):
                    if item.get("type") == "text" and item.get("text"):
                        if "saved" in item["text"].lower() and "attachment" in item["text"].lower():
                            has_files = True
                            break

                if has_files:
                    print("Successfully saved attachments")
                else:
                    print("No attachments were found in the messages")
            else:
                # It's not an error if there are no attachments to save
                print(f"Warning: {save_result.get('error', 'Unknown error')}")

            # Clean up temp directory
            import shutil

            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                print(f"Error cleaning up temp directory: {e!s}")
                # Don't fail the test because of cleanup issues
