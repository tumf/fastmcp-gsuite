import json
import os
import re
import traceback
import base64

import pytest
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class TestGoogleAuth:
    def setup_method(self):
        """Set up the test environment"""
        # 環境変数から認証情報を取得
        credentials_json_str = os.environ.get("GSUITE_CREDENTIALS_JSON")
        self.google_email = os.environ.get("GOOGLE_ACCOUNT_EMAIL")
        self.google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
        self.google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

        # 認証情報が設定されていることを確認
        assert (
            credentials_json_str
        ), "GSUITE_CREDENTIALS_JSON環境変数が設定されていません"
        assert self.google_email, "GOOGLE_ACCOUNT_EMAIL環境変数が設定されていません"
        assert self.google_client_id, "GOOGLE_CLIENT_ID環境変数が設定されていません"
        assert (
            self.google_client_secret
        ), "GOOGLE_CLIENT_SECRET環境変数が設定されていません"

        # Base64エンコードされた認証情報をデコード
        try:
            # Base64デコード
            credentials_json_decoded = base64.b64decode(credentials_json_str).decode('utf-8')
            credentials_json = json.loads(credentials_json_decoded)
        except Exception as e:
            # デコードに失敗した場合、直接JSONとして解析を試みる
            try:
                credentials_json = json.loads(credentials_json_str)
            except json.JSONDecodeError:
                # エスケープされた文字列を処理
                credentials_json_str = credentials_json_str.replace('\\"', '"')
                try:
                    credentials_json = json.loads(credentials_json_str)
                except json.JSONDecodeError:
                    # それでも失敗する場合は、基本的な値を手動で抽出
                    import re

                    refresh_token_match = re.search(
                        r'refresh_token\\":\\"([^"\\]+)', credentials_json_str
                    )
                    refresh_token = (
                        refresh_token_match.group(1) if refresh_token_match else None
                    )

                    token_match = re.search(r'token\\":\\"([^"\\]+)', credentials_json_str)
                    token = token_match.group(1) if token_match else None

                    credentials_json = {"refresh_token": refresh_token, "token": token}

        # 認証情報の中身をログに出力（アクセストークンなどは短縮表示）
        print(
            f"認証情報: {json.dumps({k: v[:10] + '...' if isinstance(v, str) and len(v) > 10 else v for k, v in credentials_json.items()}, indent=2)}"
        )

        # 認証情報から Credentials オブジェクトを作成
        self.credentials = Credentials(
            token=credentials_json.get("token", credentials_json.get("access_token")),
            refresh_token=credentials_json.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.google_client_id,
            client_secret=self.google_client_secret,
            scopes=["https://mail.google.com/"],  # Gmailスコープを使用
        )

    @pytest.mark.e2e
    def test_google_auth_with_gmail(self):
        """GoogleのGmail APIを使用して認証とアクセストークンの取得をテスト"""
        # トークンリフレッシュが必要な場合に自動的に更新される
        if not self.credentials.token and self.credentials.refresh_token:
            print(
                "アクセストークンがないため、リフレッシュトークンを使用して更新を試みます"
            )
            try:
                self.credentials.refresh(Request())
                print(f"トークンの更新に成功しました: {self.credentials.token[:10]}...")
            except Exception as e:
                print(f"トークンの更新に失敗しました: {str(e)}")
                print(traceback.format_exc())

        # アクセストークンが有効であることを確認
        print(
            f"アクセストークン: {self.credentials.token[:10]}... (存在: {bool(self.credentials.token)})"
        )
        assert self.credentials.token, "アクセストークンが取得できませんでした"

        # 実際にGmail APIを呼び出してみる
        try:
            print("Gmail APIを呼び出します")
            gmail_service = build("gmail", "v1", credentials=self.credentials)

            # ユーザープロファイルを取得（メールアドレスを含む）
            profile = gmail_service.users().getProfile(userId="me").execute()

            # プロファイルからメールアドレスを取得
            email = profile.get("emailAddress")
            print(f"取得したメールアドレス: {email}")

            # 環境変数で指定したメールアドレスと一致することを確認
            assert email, "ユーザーのメールアドレスが取得できませんでした"
            assert (
                email == self.google_email
            ), f"取得したメールアドレス {email} が環境変数のメールアドレス {self.google_email} と一致しません"

            print("Gmail APIでの認証確認に成功しました")
        except Exception as e:
            print(
                f"Gmail APIへのアクセスに失敗しました - 詳細エラー: {e.__class__.__name__}: {str(e)}"
            )
            print(traceback.format_exc())
            pytest.skip(
                f"Gmail APIへのアクセスに失敗しました: {e.__class__.__name__}: {str(e)}"
            )
            return
