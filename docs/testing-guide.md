# 非同期テスト修正ガイド

現在、テスト実行時に以下の警告が表示されています：

1. `pytest-asyncio` の設定に関する警告
2. 非同期関数（コルーチン）が `await` されていない警告
3. テストケースが値を返していることに関する警告

## 解決済みの修正

`pyproject.toml` に以下の設定を追加して、 `pytest-asyncio` の設定に関する警告を解決しました：

```toml
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "function"
```

また、 `conftest.py` を修正し、 `asyncio` マーカーを登録しました。

## テストファイル修正ガイド

残りの警告を解決するためには、以下の方法でテストファイルを修正する必要があります。特に以下のファイルには非同期関数のテストに関する警告が含まれています：

- `tests/unit/test_calendar_tools.py`
- `tests/unit/test_gmail_tools.py`

### 修正方法1: クラスベースのテストを保持する場合

クラスベースのテスト構造を保持したい場合、各非同期テストメソッドに `@pytest.mark.asyncio` デコレータを追加します：

```python
class TestCalendarTools(unittest.TestCase):
    # ...

    @pytest.mark.asyncio  # デコレータを追加
    @patch("src.mcp_gsuite.calendar_tools.auth_helper.get_calendar_service")
    @patch("src.mcp_gsuite.calendar_tools.calendar_impl.CalendarService")
    async def test_list_calendars_success(self, mock_calendar_service_class, mock_get_calendar_service):
        # テスト実装
        pass
```

### 修正方法2: pytest標準のアプローチに変換する（推奨）

unittest. TestCase は非同期テストに対して完全にサポートされていないため、pytestスタイルのテストに変換することをお勧めします：

```python
import pytest
from unittest.mock import MagicMock, patch

# フィクスチャを使用してセットアップ
@pytest.fixture
def setup_calendar_tools():
    # テスト用のデータや設定を返す
    return {
        "mock_context": MockContext(),
        "test_user_id": "test@example.com",
        # ...
    }

# 個別のテスト関数
@pytest.mark.asyncio
@patch("src.mcp_gsuite.calendar_tools.auth_helper.get_calendar_service")
@patch("src.mcp_gsuite.calendar_tools.calendar_impl.CalendarService")
async def test_list_calendars_success(mock_calendar_service_class, mock_get_gmail_service, setup_calendar_tools):
    setup = setup_calendar_tools
    # テスト実装
    # self.assertEqualの代わりにassertを使用
    assert len(result) == 1
```

## テスト実行

修正後は以下のコマンドでテストを実行し、警告が解決されたことを確認してください：

```bash
make test
```

非同期テストの詳細については、[pytest-asyncio の公式ドキュメント](https://pytest-asyncio.readthedocs.io/en/latest/) を参照してください。
