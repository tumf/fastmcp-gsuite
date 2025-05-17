import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


@pytest.mark.asyncio
async def test_mcp_server_list_tools():
    """MCPサーバのtool一覧取得のE2Eテスト"""
    url = "http://localhost:8000/mcp/"
    headers = {}  # 認証が必要な場合はここにAPIキー等を追加
    async with streamablehttp_client(url, headers=headers) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tool_list = await session.list_tools()
            assert hasattr(tool_list, "tools")
            assert isinstance(tool_list.tools, list)
            assert any("gmail" in getattr(tool, "name", "").lower() for tool in tool_list.tools)
            print([getattr(tool, "name", None) for tool in tool_list.tools])
