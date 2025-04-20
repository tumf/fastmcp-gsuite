import logging
import os
import shutil

import pytest
from chuk_mcp.mcp_client.messages.initialize.send_messages import send_initialize
from chuk_mcp.mcp_client.messages.tools.send_messages import (
    send_tools_call,
    send_tools_list,
)
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import (
    StdioServerParameters,
)

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get UV path from environment variables or search in PATH
UV_PATH = os.environ.get("UV_PATH") or shutil.which("uv")
if not UV_PATH:
    pytest.skip("uv command not found in PATH or UV_PATH not set")


class TestSimpleServer:
    """Test for simple MCP server"""

    def setup_method(self):
        """Set up test environment"""
        # Copy parent process environment variables
        self.env = os.environ.copy()

    async def _connect_and_initialize(self):
        """Connect to and initialize the MCP server"""
        logger.debug(f"Using UV_PATH: {UV_PATH}")

        # Set up server parameters using StdioServerParameters
        server_params = StdioServerParameters(
            command=UV_PATH,
            args=["run", "python", "-m", "tests.simple_server", "--stdio"],
            env=self.env,
        )

        logger.debug(
            f"Connecting to server with parameters: command={UV_PATH}, args={server_params.args}"
        )
        # Connect to the server
        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                logger.debug("Connection established, initializing server...")
                # Initialize the server
                init_result = await send_initialize(read_stream, write_stream)
                logger.debug(f"Server initialization result: {init_result}")
                assert init_result, "Failed to initialize server"

                logger.debug("Server initialized successfully")
                return read_stream, write_stream
        except Exception as e:
            logger.error(f"Error connecting to server: {e}", exc_info=True)
            raise

    @pytest.mark.asyncio
    async def test_hello_world(self):
        """Test the simple hello_world tool"""
        read_stream, write_stream = await self._connect_and_initialize()

        # Get list of available tools
        logger.debug("Getting tools list...")
        tools_response = await send_tools_list(read_stream, write_stream)

        # Verify that tool list was returned
        assert "tools" in tools_response, "Tool list was not returned"
        assert len(tools_response["tools"]) > 0, "No tools available"

        # Check if hello_world tool is included
        hello_tools = [
            tool for tool in tools_response["tools"] if "hello_world" == tool["name"]
        ]
        assert len(hello_tools) > 0, "hello_world tool not found"

        # Call hello_world tool
        logger.debug("Calling hello_world tool...")
        result = await send_tools_call(
            read_stream,
            write_stream,
            name="hello_world",
            arguments={"name": "Test User"},
        )

        # Verify result
        assert "Hello, Test User!" in str(
            result
        ), "Response from hello_world tool is incorrect"
