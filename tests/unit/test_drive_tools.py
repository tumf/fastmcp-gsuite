import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.mcp_gsuite.drive_tools import (
    create_drive_folder,
    delete_drive_folder,
    download_drive_file,
    get_drive_file,
    list_drive_files,
    list_drive_folders,
    move_drive_folder,
    rename_drive_folder,
    trash_drive_file,
    trash_drive_folder,
    untrash_drive_file,
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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
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

    async def test_create_drive_folder_success(self):
        user_id = "test@example.com"
        folder_name = "Test Folder"
        parent_folder_id = "parent123"

        mock_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.upload_file.return_value = mock_folder

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await create_drive_folder(
                user_id=user_id,
                folder_name=folder_name,
                parent_folder_id=parent_folder_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(json.loads(result[0].text), mock_folder)

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.upload_file.assert_called_once_with(
                file_name=folder_name,
                mime_type="application/vnd.google-apps.folder",
                parent_folder_id=parent_folder_id,
            )
            mock_ctx.info.assert_any_call(f"Creating folder '{folder_name}' for user {user_id}")
            mock_ctx.info.assert_any_call(f"Successfully created folder with ID: {mock_folder.get('id')}")

    async def test_create_drive_folder_failure(self):
        user_id = "test@example.com"
        folder_name = "Test Folder"

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.upload_file.return_value = None

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await create_drive_folder(
                user_id=user_id,
                folder_name=folder_name,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(result[0].text, f"Failed to create folder '{folder_name}'.")

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.upload_file.assert_called_once_with(
                file_name=folder_name,
                mime_type="application/vnd.google-apps.folder",
                parent_folder_id=None,
            )
            mock_ctx.info.assert_called_once_with(f"Creating folder '{folder_name}' for user {user_id}")
            mock_ctx.error.assert_called_once_with(f"Failed to create folder '{folder_name}' for user {user_id}")

    async def test_create_drive_folder_exception(self):
        user_id = "test@example.com"
        folder_name = "Test Folder"

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.upload_file.side_effect = Exception("API Error")

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            with self.assertRaises(RuntimeError) as context:
                await create_drive_folder(
                    user_id=user_id,
                    folder_name=folder_name,
                    ctx=mock_ctx,
                )

            self.assertIn("Error creating folder", str(context.exception))

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.upload_file.assert_called_once()
            mock_ctx.info.assert_called_once_with(f"Creating folder '{folder_name}' for user {user_id}")
            mock_ctx.error.assert_called_once()

    async def test_list_drive_folders_success(self):
        user_id = "test@example.com"
        query = "name contains 'reports'"
        limit = 10

        mock_folders_result = {
            "files": [
                {
                    "id": "folder1",
                    "name": "Reports Folder",
                    "mimeType": "application/vnd.google-apps.folder",
                },
                {
                    "id": "folder2",
                    "name": "Monthly Reports",
                    "mimeType": "application/vnd.google-apps.folder",
                },
            ]
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.list_files.return_value = mock_folders_result

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await list_drive_folders(
                user_id=user_id,
                query=query,
                limit=limit,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(json.loads(result[0].text), mock_folders_result)

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.list_files.assert_called_once_with(
                query=f"mimeType='application/vnd.google-apps.folder' and {query}", page_size=limit
            )
            mock_ctx.info.assert_called_once_with(
                f"Listing folders for {user_id} with query: 'mimeType='application/vnd.google-apps.folder' and {query}'"
            )

    async def test_list_drive_folders_no_results(self):
        user_id = "test@example.com"
        query = "name contains 'nonexistent'"

        mock_folders_result: dict[str, list] = {"files": []}

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.list_files.return_value = mock_folders_result

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await list_drive_folders(
                user_id=user_id,
                query=query,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(result[0].text, "No folders found matching the query.")

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.list_files.assert_called_once_with(
                query=f"mimeType='application/vnd.google-apps.folder' and {query}", page_size=100
            )
            mock_ctx.info.assert_any_call(
                f"Listing folders for {user_id} with query: 'mimeType='application/vnd.google-apps.folder' and {query}'"
            )
            mock_ctx.info.assert_any_call(f"No folders found for query '{query}' for user {user_id}")

    async def test_list_drive_folders_exception(self):
        user_id = "test@example.com"

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.list_files.side_effect = Exception("API Error")

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            with self.assertRaises(RuntimeError) as context:
                await list_drive_folders(
                    user_id=user_id,
                    ctx=mock_ctx,
                )

            self.assertIn("Error listing folders", str(context.exception))

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.list_files.assert_called_once()
            mock_ctx.info.assert_called_once_with(
                f"Listing folders for {user_id} with query: 'mimeType='application/vnd.google-apps.folder''"
            )
            mock_ctx.error.assert_called_once()

    async def test_rename_drive_folder_success(self):
        user_id = "test@example.com"
        folder_id = "folder1"
        new_name = "New Folder Name"

        mock_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_updated_folder = {
            "id": "folder1",
            "name": "New Folder Name",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.return_value = mock_folder
        mock_drive_service.rename_file.return_value = mock_updated_folder

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await rename_drive_folder(
                user_id=user_id,
                folder_id=folder_id,
                new_name=new_name,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(json.loads(result[0].text), mock_updated_folder)

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_called_once_with(file_id=folder_id)
            mock_drive_service.rename_file.assert_called_once_with(file_id=folder_id, new_name=new_name)
            mock_ctx.info.assert_any_call(f"Renaming folder {folder_id} to {new_name} for user {user_id}")
            mock_ctx.info.assert_any_call(f"Successfully renamed folder with ID: {folder_id} to {new_name}")

    async def test_rename_drive_folder_not_a_folder(self):
        user_id = "test@example.com"
        folder_id = "file1"
        new_name = "New Name"

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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await rename_drive_folder(
                user_id=user_id,
                folder_id=folder_id,
                new_name=new_name,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(result[0].text, f"Item with ID {folder_id} is not a folder.")

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_called_once_with(file_id=folder_id)
            mock_ctx.info.assert_called_once_with(f"Renaming folder {folder_id} to {new_name} for user {user_id}")
            mock_ctx.error.assert_called_once_with(f"Item with ID {folder_id} is not a folder.")

    async def test_rename_drive_folder_exception(self):
        user_id = "test@example.com"
        folder_id = "folder1"
        new_name = "New Folder Name"

        mock_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.return_value = mock_folder
        mock_drive_service.rename_file.side_effect = Exception("API Error")

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            with self.assertRaises(RuntimeError) as context:
                await rename_drive_folder(
                    user_id=user_id,
                    folder_id=folder_id,
                    new_name=new_name,
                    ctx=mock_ctx,
                )

            self.assertIn("Error renaming folder", str(context.exception))

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_called_once_with(file_id=folder_id)
            mock_drive_service.rename_file.assert_called_once_with(file_id=folder_id, new_name=new_name)
            mock_ctx.info.assert_called_once_with(f"Renaming folder {folder_id} to {new_name} for user {user_id}")
            mock_ctx.error.assert_called_once()

    async def test_move_drive_folder_success(self):
        user_id = "test@example.com"
        folder_id = "folder1"
        new_parent_id = "folder2"

        mock_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_dest_folder = {
            "id": "folder2",
            "name": "Destination Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_moved_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
            "parents": ["folder2"],
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.side_effect = [mock_folder, mock_dest_folder]
        mock_drive_service.move_file.return_value = mock_moved_folder

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await move_drive_folder(
                user_id=user_id,
                folder_id=folder_id,
                new_parent_id=new_parent_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(json.loads(result[0].text), mock_moved_folder)

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_has_calls(
                [
                    unittest.mock.call(file_id=folder_id),
                    unittest.mock.call(file_id=new_parent_id),
                ]
            )
            mock_drive_service.move_file.assert_called_once_with(
                file_id=folder_id, new_parent_id=new_parent_id, remove_previous_parents=True
            )
            mock_ctx.info.assert_any_call(f"Moving folder {folder_id} to folder {new_parent_id} for user {user_id}")
            mock_ctx.info.assert_any_call(f"Successfully moved folder with ID: {folder_id} to folder {new_parent_id}")

    async def test_move_drive_folder_not_a_folder(self):
        user_id = "test@example.com"
        folder_id = "file1"
        new_parent_id = "folder2"

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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await move_drive_folder(
                user_id=user_id,
                folder_id=folder_id,
                new_parent_id=new_parent_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(result[0].text, f"Item with ID {folder_id} is not a folder.")

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_called_once_with(file_id=folder_id)
            mock_ctx.info.assert_called_once_with(
                f"Moving folder {folder_id} to folder {new_parent_id} for user {user_id}"
            )
            mock_ctx.error.assert_called_once_with(f"Item with ID {folder_id} is not a folder.")

    async def test_move_drive_folder_destination_not_a_folder(self):
        user_id = "test@example.com"
        folder_id = "folder1"
        new_parent_id = "file2"

        mock_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_dest_file = {
            "id": "file2",
            "name": "Destination File",
            "mimeType": "application/pdf",
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.side_effect = [mock_folder, mock_dest_file]

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await move_drive_folder(
                user_id=user_id,
                folder_id=folder_id,
                new_parent_id=new_parent_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(result[0].text, f"Destination with ID {new_parent_id} is not a folder.")

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_has_calls(
                [
                    unittest.mock.call(file_id=folder_id),
                    unittest.mock.call(file_id=new_parent_id),
                ]
            )
            mock_ctx.info.assert_called_once_with(
                f"Moving folder {folder_id} to folder {new_parent_id} for user {user_id}"
            )
            mock_ctx.error.assert_called_once_with(f"Destination with ID {new_parent_id} is not a folder.")

    async def test_move_drive_folder_into_itself(self):
        user_id = "test@example.com"
        folder_id = "folder1"
        new_parent_id = "folder1"

        mock_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.return_value = mock_folder

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await move_drive_folder(
                user_id=user_id,
                folder_id=folder_id,
                new_parent_id=new_parent_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(result[0].text, "Cannot move a folder into itself.")

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_has_calls(
                [
                    unittest.mock.call(file_id=folder_id),
                    unittest.mock.call(file_id=new_parent_id),
                ]
            )
            mock_ctx.info.assert_called_once_with(
                f"Moving folder {folder_id} to folder {new_parent_id} for user {user_id}"
            )
            mock_ctx.error.assert_called_once_with("Cannot move a folder into itself.")

    async def test_move_drive_folder_exception(self):
        user_id = "test@example.com"
        folder_id = "folder1"
        new_parent_id = "folder2"

        mock_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_dest_folder = {
            "id": "folder2",
            "name": "Destination Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.side_effect = [mock_folder, mock_dest_folder]
        mock_drive_service.move_file.side_effect = Exception("API Error")

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            with self.assertRaises(RuntimeError) as context:
                await move_drive_folder(
                    user_id=user_id,
                    folder_id=folder_id,
                    new_parent_id=new_parent_id,
                    ctx=mock_ctx,
                )

            self.assertIn("Error moving folder", str(context.exception))

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_has_calls(
                [
                    unittest.mock.call(file_id=folder_id),
                    unittest.mock.call(file_id=new_parent_id),
                ]
            )
            mock_drive_service.move_file.assert_called_once_with(
                file_id=folder_id, new_parent_id=new_parent_id, remove_previous_parents=True
            )
            mock_ctx.info.assert_called_once_with(
                f"Moving folder {folder_id} to folder {new_parent_id} for user {user_id}"
            )
            mock_ctx.error.assert_called_once()

    async def test_delete_drive_folder_success(self):
        user_id = "test@example.com"
        folder_id = "folder1"

        mock_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.return_value = mock_folder
        mock_drive_service.delete_file.return_value = (True, None)

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await delete_drive_folder(
                user_id=user_id,
                folder_id=folder_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(result[0].text, f"Successfully deleted folder with ID: {folder_id}")

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_called_once_with(file_id=folder_id)
            mock_drive_service.delete_file.assert_called_once_with(file_id=folder_id)
            mock_ctx.info.assert_any_call(f"Deleting folder {folder_id} for user {user_id}")
            mock_ctx.info.assert_any_call(f"Successfully deleted folder with ID: {folder_id}")

    async def test_delete_drive_folder_not_a_folder(self):
        user_id = "test@example.com"
        folder_id = "file1"

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
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await delete_drive_folder(
                user_id=user_id,
                folder_id=folder_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertEqual(result[0].text, f"Item with ID {folder_id} is not a folder.")

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_called_once_with(file_id=folder_id)
            mock_ctx.info.assert_called_once_with(f"Deleting folder {folder_id} for user {user_id}")
            mock_ctx.error.assert_called_once_with(f"Item with ID {folder_id} is not a folder.")

    async def test_delete_drive_folder_failure(self):
        user_id = "test@example.com"
        folder_id = "folder1"

        mock_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.return_value = mock_folder
        mock_drive_service.delete_file.return_value = (False, "Permission denied")

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await delete_drive_folder(
                user_id=user_id,
                folder_id=folder_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertIn("Failed to delete folder with ID:", result[0].text)
            self.assertIn("Permission denied", result[0].text)

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_called_once_with(file_id=folder_id)
            mock_drive_service.delete_file.assert_called_once_with(file_id=folder_id)
            mock_ctx.info.assert_called_once_with(f"Deleting folder {folder_id} for user {user_id}")

    async def test_delete_drive_folder_exception(self):
        user_id = "test@example.com"
        folder_id = "folder1"

        mock_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_ctx = AsyncMock()

        mock_drive_service = MagicMock()
        mock_drive_service.get_file.return_value = mock_folder
        mock_drive_service.delete_file.side_effect = Exception("API Error")

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            with self.assertRaises(RuntimeError) as context:
                await delete_drive_folder(
                    user_id=user_id,
                    folder_id=folder_id,
                    ctx=mock_ctx,
                )

            self.assertIn("Error deleting folder", str(context.exception))

            mock_get_drive_service.assert_called_once_with(user_id)
            mock_drive_service.get_file.assert_called_once_with(file_id=folder_id)
            mock_drive_service.delete_file.assert_called_once_with(file_id=folder_id)
            mock_ctx.info.assert_called_once_with(f"Deleting folder {folder_id} for user {user_id}")
            mock_ctx.error.assert_called_once()


    # Trash file tests
    async def test_trash_drive_file_success(self):
        user_id = "test@example.com"
        file_id = "file1"

        mock_ctx = AsyncMock()
        mock_drive_service = MagicMock()
        mock_drive_service.trash_file.return_value = (True, None)

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await trash_drive_file(
                user_id=user_id,
                file_id=file_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
            self.assertIn("Successfully moved file to trash", result[0].text)
            mock_drive_service.trash_file.assert_called_once_with(file_id=file_id)

    async def test_trash_drive_file_failure(self):
        user_id = "test@example.com"
        file_id = "file1"

        mock_ctx = AsyncMock()
        mock_drive_service = MagicMock()
        mock_drive_service.trash_file.return_value = (False, "Permission denied")

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await trash_drive_file(
                user_id=user_id,
                file_id=file_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertIn("Failed to trash file", result[0].text)
            self.assertIn("Permission denied", result[0].text)

    async def test_trash_drive_folder_success(self):
        user_id = "test@example.com"
        folder_id = "folder1"

        mock_folder = {
            "id": "folder1",
            "name": "Test Folder",
            "mimeType": "application/vnd.google-apps.folder",
        }

        mock_ctx = AsyncMock()
        mock_drive_service = MagicMock()
        mock_drive_service.get_file.return_value = mock_folder
        mock_drive_service.trash_file.return_value = (True, None)

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await trash_drive_folder(
                user_id=user_id,
                folder_id=folder_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertIn("Successfully moved folder to trash", result[0].text)
            mock_drive_service.trash_file.assert_called_once_with(file_id=folder_id)

    async def test_untrash_drive_file_success(self):
        user_id = "test@example.com"
        file_id = "file1"

        mock_ctx = AsyncMock()
        mock_drive_service = MagicMock()
        mock_drive_service.untrash_file.return_value = (True, None)

        with (
            patch("src.mcp_gsuite.drive_tools.auth_helper.get_drive_service") as mock_get_drive_service,
            patch("src.mcp_gsuite.drive_tools.DriveService", return_value=mock_drive_service),
        ):
            mock_get_drive_service.return_value = "mock_service"

            result = await untrash_drive_file(
                user_id=user_id,
                file_id=file_id,
                ctx=mock_ctx,
            )

            self.assertEqual(len(result), 1)
            self.assertIn("Successfully restored file from trash", result[0].text)
            mock_drive_service.untrash_file.assert_called_once_with(file_id=file_id)


if __name__ == "__main__":
    unittest.main()
