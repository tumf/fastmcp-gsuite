#!/bin/bash
set -e

# 親ディレクトリに移動
cd "$(dirname "$0")/.."

# アカウントメールが環境変数にセットされているか確認
if [ -z "$GOOGLE_ACCOUNT_EMAIL" ]; then
    echo "環境変数 GOOGLE_ACCOUNT_EMAIL が設定されていません。"
    exit 1
fi

# .accounts.jsonが存在するか確認し、なければ作成
if [ ! -f ".accounts.json" ]; then
    echo '{"accounts": []}' > .accounts.json
fi

# 新しいアカウントJSONオブジェクトを構築
NEW_ACCOUNT=$(cat <<EOF
{
  "email": "$GOOGLE_ACCOUNT_EMAIL",
  "account_type": "gmail",
  "extra_info": ""
}
EOF
)

# 既存のアカウントを更新（同じメールアドレスのアカウントを削除して新しいものを追加）
jq --argjson newAccount "$NEW_ACCOUNT" '.accounts = [.accounts[] | select(.email != $newAccount.email)] + [$newAccount]' .accounts.json > .accounts.json.tmp && mv .accounts.json.tmp .accounts.json

echo "テストアカウント $GOOGLE_ACCOUNT_EMAIL を.accounts.jsonに追加/更新しました。"
echo "Done!"
