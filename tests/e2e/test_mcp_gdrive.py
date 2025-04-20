import base64
import json
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

# uvのパスを環境変数から取得するか、PATHから探す
UV_PATH = (
    os.environ.get("UV_PATH") or shutil.which("uv") or "/Users/tumf/.pyenv/shims/uv"
)


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
class TestMCPGDrive:
    @pytest.mark.e2e
    async def test_gdrive_list_files(self, credentials):
        """GDriveのファイル一覧を取得するテスト"""
        # 親プロセスの環境変数を取得し、必要な変数を追加
        env = os.environ.copy()
        env.update(
            {
                "GSUITE_CREDENTIALS_FILE": credentials["credentials_file"],
                "GSUITE_EMAIL": credentials["email"],
            }
        )

        # MCPサーバーのパラメータを設定
        server_params = StdioServerParameters(
            command=UV_PATH, args=["run", "fastmcp-gsuite"], env=env
        )

        # サーバーに接続
        async with stdio_client(server_params) as (read_stream, write_stream):
            # 初期化
            init_result = await send_initialize(read_stream, write_stream)
            assert init_result, "Failed to initialize MCP server"

            # ツール一覧を取得
            tools_response = await send_tools_list(read_stream, write_stream)
            assert "tools" in tools_response, "No tools found in response"

            # GDrive関連のツールを探す
            gdrive_tools = [
                tool
                for tool in tools_response["tools"]
                if "drive" in tool["name"].lower() or "gdrive" in tool["name"].lower()
            ]

            # GDriveツールがある場合はテストを実行
            if gdrive_tools:
                # ファイル一覧を取得するツールを探す
                list_files_tool = next(
                    (tool for tool in gdrive_tools if "list" in tool["name"].lower()),
                    None,
                )

                if list_files_tool:
                    # ツールを実行
                    tool_params = {"limit": 5}
                    result = await send_tools_call(
                        read_stream, write_stream, list_files_tool["name"], tool_params
                    )

                    # 結果を検証
                    assert result, "Tool execution failed"
                    assert "files" in result, "No files found in response"
                    print(f"Found {len(result['files'])} files in GDrive")
                else:
                    pytest.skip("GDrive list files tool not found")
            else:
                pytest.skip("No GDrive tools found")
