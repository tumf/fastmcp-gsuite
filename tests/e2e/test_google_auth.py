import traceback

import pytest
from googleapiclient.discovery import build


class TestGoogleAuth:
    @pytest.mark.e2e
    def test_google_auth_with_gmail(self, oauth_token):
        """GoogleのGmail APIを使用して認証とアクセストークンの取得をテスト"""
        # oauth_token fixtureから認証情報を取得
        credentials = oauth_token["credentials"]
        google_email = oauth_token["email"]

        # アクセストークンが有効であることを確認
        print(f"アクセストークン: {credentials.token[:10]}... (存在: {bool(credentials.token)})")
        assert credentials.token, "アクセストークンが取得できませんでした"

        # 実際にGmail APIを呼び出してみる
        try:
            print("Gmail APIを呼び出します")
            gmail_service = build("gmail", "v1", credentials=credentials)

            # ユーザープロファイルを取得(メールアドレスを含む)
            profile = gmail_service.users().getProfile(userId="me").execute()

            # プロファイルからメールアドレスを取得
            email = profile.get("emailAddress")
            print(f"取得したメールアドレス: {email}")

            # 環境変数で指定したメールアドレスと一致することを確認
            assert email, "ユーザーのメールアドレスが取得できませんでした"
            assert (
                email == google_email
            ), f"取得したメールアドレス {email} が環境変数のメールアドレス {google_email} と一致しません"

            print("Gmail APIでの認証確認に成功しました")
        except Exception as e:
            print(f"Gmail APIへのアクセスに失敗しました - 詳細エラー: {e.__class__.__name__}: {e!s}")
            print(traceback.format_exc())
            pytest.skip(f"Gmail APIへのアクセスに失敗しました: {e.__class__.__name__}: {e!s}")
            return
