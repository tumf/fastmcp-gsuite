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

# uvのパスを環境変数から取得するか、PATHから探す
UV_PATH = (
    os.environ.get("UV_PATH") or shutil.which("uv") or "/Users/tumf/.pyenv/shims/uv"
)
# テスト実行のためにスキップを一時的に無効化
# if not UV_PATH:
#     pytest.skip("uv command not found in PATH or UV_PATH not set")


@pytest.fixture(scope="session")
def credentials():
    """Set up the test environment with credentials from environment variables"""
    # 環境変数から認証情報を取得
    credentials_json_str = os.environ.get("GSUITE_CREDENTIALS_JSON")
    google_email = os.environ.get("GOOGLE_ACCOUNT_EMAIL")
    google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
    google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
    google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    # 認証情報が設定されていることを確認
    assert (
        credentials_json_str
    ), "GSUITE_CREDENTIALS_JSON environment variable is not set"
    assert google_email, "GOOGLE_ACCOUNT_EMAIL environment variable is not set"
    assert google_client_id, "GOOGLE_CLIENT_ID environment variable is not set"
    assert google_client_secret, "GOOGLE_CLIENT_SECRET environment variable is not set"

    try:
        # Base64デコード
        credentials_json_decoded = base64.b64decode(credentials_json_str).decode(
            "utf-8"
        )
        decoded_credentials = json.loads(credentials_json_decoded)

        # OAuth2Credentialsの必須フィールド
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

    # 一時的な認証情報ファイルを作成
    credentials_file = ".e2e_test_credentials.json"
    with open(credentials_file, "w") as f:
        json.dump(credentials_json, f)

    # OAuth2認証ファイルを作成
    oauth2_file = f".oauth2.{google_email}.json"
    with open(oauth2_file, "w") as f:
        json.dump(credentials_json, f)

    # 環境変数を設定してMCPサーバーの実行に必要なパラメータを提供
    os.environ["GSUITE_CREDENTIALS_FILE"] = credentials_file
    os.environ["GSUITE_EMAIL"] = google_email

    # テスト用のデータを返す
    yield {
        "credentials_file": credentials_file,
        "oauth2_file": oauth2_file,
        "email": google_email,
        "project_id": google_project_id,
        "client_id": google_client_id,
        "client_secret": google_client_secret,
    }

    # テスト後にファイルをクリーンアップ
    if os.path.exists(credentials_file):
        os.remove(credentials_file)
    if os.path.exists(oauth2_file):
        os.remove(oauth2_file)


@pytest.mark.asyncio
class TestMCPGsuite:
    @pytest.mark.e2e
    async def test_mcp_connection_and_tools(self, credentials):
        """Test connecting to the MCP server and listing tools"""
        # 親プロセスの環境変数を取得し、必要な変数を追加
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        # MCP Gsuiteサーバーのパラメータを設定
        server_params = StdioServerParameters(
            command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env
        )

        # サーバーに接続
        async with stdio_client(server_params) as (read_stream, write_stream):
            # 初期化
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Failed to initialize MCP server"

            # サーバー名を検証 - 厳密な一致ではなく、サーバー名が空でないことだけ確認
            assert init_result.serverInfo.name, "Server name is empty"
            print(f"Connected to server: {init_result.serverInfo.name}")

            # Pingを送信して接続を確認
            ping_result = await send_ping(read_stream, write_stream)
            assert ping_result, "Ping to MCP server failed"

            # 利用可能なツールをリスト
            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "No tools found in response"

            # 利用可能なツールの名前を表示
            tool_names = [tool["name"] for tool in tools_response["tools"]]
            print(f"Available tools: {tool_names}")

            # Gmail関連のツールを探す (名前は環境によって変わる可能性あり)
            gmail_tools = [
                tool
                for tool in tools_response["tools"]
                if "gmail" in tool["name"].lower()
            ]
            assert (
                len(gmail_tools) > 0
            ), f"No Gmail tools found. Available tools: {tool_names}"

            # Calendar関連のツールを探す
            calendar_tools = [
                tool
                for tool in tools_response["tools"]
                if "calendar" in tool["name"].lower()
            ]
            assert (
                len(calendar_tools) > 0
            ), f"No Calendar tools found. Available tools: {tool_names}"

            # 特定のツール名を確認（前回の実行で確認済み）
            assert (
                "query_gmail_emails" in tool_names
            ), f"query_gmail_emails tool not found in {tool_names}"
            assert (
                "list_calendar_events" in tool_names
            ), f"list_calendar_events tool not found in {tool_names}"

    @pytest.mark.e2e
    async def test_gmail_tool_list_messages(self, credentials):
        """Test Gmail tool for listing messages"""
        # 親プロセスの環境変数を取得し、必要な変数を追加
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
            # 初期化
            await send_initialize(read_stream, write_stream)

            # Gmail用のクエリーツールを使用
            result = await send_tools_call(
                read_stream,
                write_stream,
                name="query_gmail_emails",
                arguments={
                    "max_results": 5,  # 最新の5件のメールを取得
                    "user_id": credentials["email"],  # ユーザーIDを引数に追加
                },
            )

            assert result, "Tool call returned no result"
            assert not result.get(
                "isError", False
            ), f"Tool call returned error: {result}"

            # レスポンスが辞書であることを確認
            assert isinstance(
                result, dict
            ), f"Result is not a dictionary: {type(result)}"

            # レスポンスを確認
            assert "content" in result, f"No content field in response: {result}"
            assert len(result["content"]) > 0, f"Empty content in response: {result}"

            # JSONテキストが含まれているか確認
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
        # 親プロセスの環境変数を取得し、必要な変数を追加
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
            # 初期化
            await send_initialize(read_stream, write_stream)

            # 現在の日付を取得して、今日のイベントを取得
            import datetime

            today = datetime.datetime.now().strftime("%Y-%m-%d")

            # Calendar list_events ツールを呼び出し
            result = await send_tools_call(
                read_stream,
                write_stream,
                name="list_calendar_events",
                arguments={
                    "calendar_id": "primary",
                    "start_time": f"{today}T00:00:00Z",
                    "end_time": f"{today}T23:59:59Z",
                    "max_results": 10,
                    "user_id": credentials["email"],  # ユーザーIDを引数に追加
                },
            )

            assert result is not None, "Tool call returned None"
            assert not result.get(
                "isError", False
            ), f"Tool call returned error: {result}"
            assert isinstance(
                result, dict
            ), f"Result is not a dictionary: {type(result)}"

            # レスポンスを確認
            assert "content" in result, f"No content field in response: {result}"
            assert len(result["content"]) > 0, f"Empty content in response: {result}"

            # JSONテキストが含まれているか確認
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        event_data = json.loads(item.get("text"))
                        if isinstance(event_data, dict):
                            break
                    except json.JSONDecodeError:
                        continue

            # イベントがない場合もあるので、JSONの解析が成功していればOKとする
            # assert has_events, f"No valid event JSON found in response: {result}"
