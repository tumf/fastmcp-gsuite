# gmail-attachments Specification

## Purpose
TBD - created by archiving change fix-gmail-attachment-save. Update Purpose after archive.
## Requirements
### Requirement: Stable Attachment Identification

添付ファイルの特定には、API リクエストごとに変化する可能性がある `attachmentId` ではなく、メール内で固定されている `partId` を使用しなければならない（MUST）。

#### Scenario: Attachment identified by partId
- **WHEN** ユーザーが `get_email_details` で添付ファイル情報を取得する
- **THEN** レスポンスには添付ファイルごとに固定の `partId` が含まれる
- **AND** この `partId` を使用して `save_gmail_attachment_to_drive` を呼び出すことで添付ファイルを保存できる

#### Scenario: Current attachmentId used for download
- **WHEN** `save_gmail_attachment_to_drive` が `partId` で添付ファイルを特定する
- **THEN** その時点で API から取得した最新の `attachmentId` を使用してダウンロードを実行する

### Requirement: Nested Attachment Extraction

Gmail メールは `multipart/mixed` や `multipart/related` などのネストされた構造を持つ可能性があり、システムはすべての階層から添付ファイルを抽出しなければならない（MUST）。

#### Scenario: Flat multipart structure
- **WHEN** メールが単一レベルの `multipart/mixed` 構造を持つ
- **THEN** トップレベルの添付ファイルがすべて抽出される

#### Scenario: Nested multipart structure
- **WHEN** メールが `multipart/mixed` > `multipart/alternative` > 添付ファイルのようなネスト構造を持つ
- **THEN** すべての階層から添付ファイルが再帰的に抽出される

#### Scenario: Deeply nested inline attachments
- **WHEN** メールが `multipart/mixed` > `multipart/related` > インライン画像のような構造を持つ
- **THEN** インライン添付ファイルも含めてすべて抽出される

### Requirement: Gmail Attachment to Drive Save

ユーザーは Gmail の添付ファイルを指定した Google Drive フォルダに保存できなければならない（MUST）。

#### Scenario: Save attachment to Drive
- **WHEN** ユーザーが `save_gmail_attachment_to_drive` を `message_id`、`part_id`、`folder_id` を指定して呼び出す
- **THEN** 指定した添付ファイルが Google Drive の指定フォルダに保存される
- **AND** 保存されたファイルの情報（ID、Web View Link）が返される

#### Scenario: Save attachment with rename
- **WHEN** ユーザーが `rename` パラメータを指定して `save_gmail_attachment_to_drive` を呼び出す
- **THEN** 添付ファイルは新しいファイル名で Google Drive に保存される

#### Scenario: Part ID not found
- **WHEN** 指定した `part_id` がメッセージ内に存在しない
- **THEN** エラーメッセージが返され、利用可能な `part_id` の一覧が表示される

### Requirement: Bulk Gmail Attachment to Drive Save

ユーザーは複数の Gmail 添付ファイルを一括で Google Drive に保存できなければならない（MUST）。

#### Scenario: Bulk save attachments
- **WHEN** ユーザーが `bulk_save_gmail_attachments_to_drive` を複数の添付ファイル情報のリストで呼び出す
- **THEN** 各添付ファイルが順番に処理され、Google Drive に保存される
- **AND** 各ファイルの処理結果がリストとして返される

#### Scenario: Bulk save with per-item options
- **WHEN** 各添付ファイル情報に個別の `folder_id` や `rename` が指定されている
- **THEN** 各ファイルは指定されたオプションに従って保存される

#### Scenario: Missing required fields in bulk save
- **WHEN** 添付ファイル情報に `message_id` または `part_id` が欠けている
- **THEN** そのアイテムはエラーとして記録され、他のアイテムの処理は継続される

