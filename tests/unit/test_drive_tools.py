import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.mcp_gsuite.drive_tools import (
    download_drive_file,
    get_drive_file,
    list_drive_files,
)


class TestDriveTools(unittest.IsolatedAsyncioTestCase):
    async def test_list_drive_files_success(self):
        user_id = "test@example.com"
        query = "name contains 'report'"
        limit = 10
        order_by = "name"

        mock_files_result = {
            "files": [
                {
                    "id": "file1",
                    "name": "Report 1",
                    "mimeType": "application/pdf",
                },
                {
                    "id": "file2",
                    "name": "Report 2",
                    "mimeType": "text/plain",
                },
            ]
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.list_files.return_value = mock_files_result

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.drive_impl.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await list_drive_files(
                user_id=user_id,
                query=query,
                limit=limit,
                order_by=order_by,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(json.loads(result[0].text), mock_files_result)

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.list_files.assert_called_once_with(query=query, page_size=limit, order_by=order_by)
            mock_ctx.info.assert_called_once_with(f"Listing files for {user_id} with query: '{query}'")

    async def test_list_drive_files_no_results(self):
        user_id = "test@example.com"
        query = "name contains 'nonexistent'"

        mock_files_result: dict[str, list] = {"files": []}

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.list_files.return_value = mock_files_result

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.drive_impl.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await list_drive_files(
                user_id=user_id,
                query=query,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(result[0].text, "No files found matching the query.")

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.list_files.assert_called_once_with(query=query, page_size=100, order_by=None)
            mock_ctx.info.assert_any_call(f"Listing files for {user_id} with query: '{query}'")
            mock_ctx.info.assert_any_call(f"No files found for query '{query}' for user {user_id}")

    async def test_list_drive_files_exception(self):
        user_id = "test@example.com"

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.list_files.side_effect = Exception("API Error")

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.drive_impl.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            with self.assertRaises(RuntimeError) as context:
                await list_drive_files(
                    user_id=user_id,
                    ctx=mock_ctx,
                )

            self.assertIn("Error listing files", str(context.exception))

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.list_files.assert_called_once()
            mock_ctx.info.assert_called_once_with(f"Listing files for {user_id} with query: 'None'")
            mock_ctx.error.assert_called_once()

    async def test_get_drive_file_success(self):
        user_id = "test@example.com"
        file_id = "file1"

        mock_file = {
            "id": "file1",
            "name": "Test File",
            "mimeType": "application/pdf",
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.return_value = mock_file

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.drive_impl.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await get_drive_file(
                user_id=user_id,
                file_id=file_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(json.loads(result[0].text), mock_file)

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_called_once_with(file_id=file_id)
            mock_ctx.info.assert_called_once_with(f"Fetching file ID {file_id} for user {user_id}")

    async def test_get_drive_file_not_found(self):
        user_id = "test@example.com"
        file_id = "nonexistent"

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.return_value = None

        mock_ctx = AsyncMock()

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.drive_impl.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await get_drive_file(
                user_id=user_id,
                file_id=file_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(result[0].text, f"File with ID {file_id} not found.")

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_called_once_with(file_id=file_id)
            mock_ctx.info.assert_called_once_with(f"Fetching file ID {file_id} for user {user_id}")
            mock_ctx.warning.assert_called_once_with(f"File with ID {file_id} not found for user {user_id}")

    async def test_get_drive_file_exception(self):
        user_id = "test@example.com"
        file_id = "file1"

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.side_effect = Exception("API Error")

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.drive_impl.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            with self.assertRaises(RuntimeError) as context:
                await get_drive_file(
                    user_id=user_id,
                    file_id=file_id,
                    ctx=mock_ctx,
                )

            self.assertIn("Error getting file details", str(context.exception))

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_called_once_with(file_id=file_id)
            mock_ctx.info.assert_called_once_with(f"Fetching file ID {file_id} for user {user_id}")
            mock_ctx.error.assert_called_once()

    async def test_download_drive_file_success(self):
        user_id = "test@example.com"
        file_id = "file1"

        mock_file_data = {
            "name": "Test File",
            "mimeType": "application/pdf",
            "content": b"file content",
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.download_file.return_value = mock_file_data

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.drive_impl.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await download_drive_file(
                user_id=user_id,
                file_id=file_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            expected_result = {
                "name": "Test File",
                "mimeType": "application/pdf",
                "size": len(mock_file_data["content"]),
            }
            self.assertEqual(json.loads(result[0].text), expected_result)

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.download_file.assert_called_once_with(file_id=file_id)
            mock_ctx.info.assert_called_once_with(f"Downloading file ID {file_id} for user {user_id}")

    async def test_download_drive_file_not_found(self):
        user_id = "test@example.com"
        file_id = "nonexistent"

        mock_drive_service = MagicMock()
        mock_drive_service.download_file.return_value = None

        mock_ctx = AsyncMock()

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.drive_impl.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await download_drive_file(
                user_id=user_id,
                file_id=file_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(result[0].text, f"File with ID {file_id} could not be downloaded.")

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.download_file.assert_called_once_with(file_id=file_id)
            mock_ctx.info.assert_called_once_with(f"Downloading file ID {file_id} for user {user_id}")
            mock_ctx.warning.assert_called_once_with(
                f"File with ID {file_id} could not be downloaded for user {user_id}"
            )

    async def test_download_drive_file_exception(self):
        user_id = "test@example.com"
        file_id = "file1"

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.download_file.side_effect = Exception("API Error")

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.drive_impl.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            with self.assertRaises(RuntimeError) as context:
                await download_drive_file(
                    user_id=user_id,
                    file_id=file_id,
                    ctx=mock_ctx,
                )

            self.assertIn("Error downloading file", str(context.exception))

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.download_file.assert_called_once_with(file_id=file_id)
            mock_ctx.info.assert_called_once_with(f"Downloading file ID {file_id} for user {user_id}")
            mock_ctx.error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
