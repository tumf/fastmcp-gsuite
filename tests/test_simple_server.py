import logging
import os
import shutil

import pytest
from chuk_mcp.mcp_client.messages.initialize.send_messages import \
    send_initialize
from chuk_mcp.mcp_client.messages.tools.send_messages import (send_tools_call,
                                                              send_tools_list)
from chuk_mcp.mcp_client.transport.stdio.stdio_client import stdio_client
from chuk_mcp.mcp_client.transport.stdio.stdio_server_parameters import \
    StdioServerParameters

# デバッグログを有効化
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# uvのパスを環境変数から取得、またはPATHから検索
UV_PATH = os.environ.get("UV_PATH") or shutil.which("uv")
if not UV_PATH:
    pytest.skip("uv command not found in PATH or UV_PATH not set")


class TestSimpleServer:
    """シンプルなMCPサーバーのテスト"""

    def setup_method(self):
        """テスト環境のセットアップ"""
        # 親プロセスの環境変数をコピー
        self.env = os.environ.copy()

    async def _connect_and_initialize(self):
        """MCPサーバーに接続して初期化する"""
        logger.debug(f"Using UV_PATH: {UV_PATH}")

        # StdioServerParametersを使用してサーバーパラメータを設定
        server_params = StdioServerParameters(
            command=UV_PATH,
            args=["run", "python", "-m", "tests.simple_server", "--stdio"],
            env=self.env,
        )

        logger.debug(
            f"Connecting to server with parameters: command={UV_PATH}, args={server_params.args}"
        )
        # サーバーに接続
        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                logger.debug("Connection established, initializing server...")
                # サーバーを初期化
                init_result = await send_initialize(read_stream, write_stream)
                logger.debug(f"Server initialization result: {init_result}")
                assert init_result, "サーバー初期化に失敗しました"

                logger.debug("Server initialized successfully")
                return read_stream, write_stream
        except Exception as e:
            logger.error(f"Error connecting to server: {e}", exc_info=True)
            raise

    @pytest.mark.asyncio
    async def test_hello_world(self):
        """シンプルなhello_worldツールのテスト"""
        read_stream, write_stream = await self._connect_and_initialize()

        # 利用可能なツールの一覧を取得
        logger.debug("Getting tools list...")
        tools_response = await send_tools_list(read_stream, write_stream)

        # ツールリストが返されたことを確認
        assert "tools" in tools_response, "ツールリストが返されませんでした"
        assert len(tools_response["tools"]) > 0, "利用可能なツールがありません"

        # hello_worldツールが含まれているか確認
        hello_tools = [
            tool for tool in tools_response["tools"] if "hello_world" == tool["name"]
        ]
        assert len(hello_tools) > 0, "hello_worldツールが見つかりませんでした"

        # hello_worldツールを呼び出し
        logger.debug("Calling hello_world tool...")
        result = await send_tools_call(
            read_stream,
            write_stream,
            name="hello_world",
            arguments={"name": "Test User"},
        )

        # 結果を確認
        assert "Hello, Test User!" in str(result), "hello_worldツールからの応答が正しくありません"
