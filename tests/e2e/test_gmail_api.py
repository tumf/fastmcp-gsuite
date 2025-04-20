import base64
import json
import os
import random
import string
from datetime import datetime

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from mcp_gsuite.gmail import GmailService


class TestGmailAPI:
    def setup_method(self):
        """Set up the test environment"""
        # 環境変数から認証情報を取得
        credentials_json_str = os.environ.get("GSUITE_CREDENTIALS_JSON")
        self.google_email = os.environ.get("GOOGLE_ACCOUNT_EMAIL")
        self.google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

        # 認証情報が設定されていることを確認
        assert credentials_json_str, "GSUITE_CREDENTIALS_JSON環境変数が設定されていません"
        assert self.google_email, "GOOGLE_ACCOUNT_EMAIL環境変数が設定されていません"
        assert self.google_client_id, "GOOGLE_CLIENT_ID環境変数が設定されていません"
        assert self.google_client_secret, "GOOGLE_CLIENT_SECRET環境変数が設定されていません"

        # Base64エンコードされた認証情報をデコード
        try:
            # Base64デコード
            credentials_json_decoded = base64.b64decode(credentials_json_str).decode("utf-8")
            credentials_json = json.loads(credentials_json_decoded)
        except Exception:
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

                    refresh_token_match = re.search(r'refresh_token\\":\\"([^"\\]+)', credentials_json_str)
                    refresh_token = refresh_token_match.group(1) if refresh_token_match else None

                    token_match = re.search(r'token\\":\\"([^"\\]+)', credentials_json_str)
                    token = token_match.group(1) if token_match else None

                    credentials_json = {"refresh_token": refresh_token, "token": token}

        # 認証情報から Credentials オブジェクトを作成
        self.credentials = Credentials(
            token=credentials_json.get("token", credentials_json.get("access_token")),
            refresh_token=credentials_json.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.google_client_id,
            client_secret=self.google_client_secret,
            scopes=["https://mail.google.com/"],
        )

        # トークンがない場合はリフレッシュを試みる
        if not self.credentials.token and self.credentials.refresh_token:
            from google.auth.transport.requests import Request

            self.credentials.refresh(Request())

        # Gmail API サービスを初期化
        gmail_service = build("gmail", "v1", credentials=self.credentials)
        self.gmail = GmailService(gmail_service)

    def _generate_random_string(self, length=10):
        """ランダムな文字列を生成"""
        return "".join(random.choice(string.ascii_letters) for _ in range(length))

    @pytest.mark.e2e
    def test_gmail_draft_creation(self):
        """Gmail APIを使用したドラフト作成のテスト"""
        # テスト用のメール件名と本文を作成
        subject = f"E2E Test: {self._generate_random_string()} - {datetime.now().isoformat()}"
        body = f"This is an automated e2e test sent at {datetime.now().isoformat()}"

        # 自分自身にメールのドラフトを作成
        sent_message = self.gmail.create_draft(to=self.google_email, subject=subject, body=body)

        # ドラフトIDが返されることを確認
        assert sent_message.get("id"), "ドラフトの作成に失敗しました"

        # 少し待機してメールが届くのを待つ
        import time

        time.sleep(2)

        # 作成したドラフトを検索
        messages = self.gmail.query_emails(query=f"subject:{subject}")

        # 検索結果が存在することを確認
        assert messages, f"作成したドラフトが見つかりませんでした: {subject}"

        # 最初のメッセージの詳細を取得
        message_id = messages[0].get("id")
        email_body, attachments = self.gmail.get_email_by_id_with_attachments(message_id)

        # メッセージの内容を確認 (email_bodyがNoneでないことを確認)
        assert email_body is not None, "メールの内容が取得できませんでした"
        assert subject in email_body.get("subject", ""), "メールの件名が一致しません"

        # ドラフトのクリーンアップ
        draft_id = sent_message.get("id")
        self.gmail.delete_draft(draft_id)
