import logging
from typing import Annotated, List

from fastmcp import Context, FastMCP
from mcp.types import TextContent

# ロギングの設定
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# シンプルなMCPサーバーの作成
mcp = FastMCP(
    "simple-test-server",
    instructions="Simple MCP Server for testing connection issues.",
)


@mcp.tool(description="A simple test tool that returns a greeting.")
async def hello_world(
    name: Annotated[str, "Your name"],
    ctx: Context | None = None,
) -> List[TextContent]:
    """A simple test tool that returns a greeting."""
    logger.debug(f"hello_world called with name: {name}")
    if ctx:
        await ctx.info(f"Greeting {name}")
    return [TextContent(type="text", text=f"Hello, {name}!")]


if __name__ == "__main__":
    logger.info("Starting simple test server...")
    import sys

    if "--stdio" in sys.argv:
        logger.info("Running in stdio mode...")
        mcp.run(stdio=True)
    else:
        mcp.run()
