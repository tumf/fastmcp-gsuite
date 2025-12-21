import unittest
from unittest.mock import MagicMock

from src.mcp_gsuite.drive import DriveService


class TestDriveService(unittest.TestCase):
    def setUp(self):
        self.mock_service = MagicMock()

        self.mock_files_list = MagicMock()
        self.mock_files = MagicMock()
        self.mock_files.list.return_value = self.mock_files_list

        self.mock_files_get = MagicMock()
        self.mock_files.get.return_value = self.mock_files_get

        self.mock_files_get_media = MagicMock()
        self.mock_files.get_media.return_value = self.mock_files_get_media

        self.mock_service.files.return_value = self.mock_files

        self.drive_service = DriveService(self.mock_service)

    def test_init_with_valid_service(self):
        drive_service = DriveService(self.mock_service)
        self.assertEqual(drive_service.service, self.mock_service)

    def test_init_with_invalid_service(self):
        with self.assertRaises(ValueError):
            DriveService(None)

    def test_list_files(self):
        mock_response = {
            "files": [
                {
                    "id": "file1",
                    "name": "File 1",
                    "mimeType": "application/pdf",
                    "modifiedTime": "2023-01-01T12:00:00.000Z",
                },
                {
                    "id": "file2",
                    "name": "File 2",
                    "mimeType": "text/plain",
                    "modifiedTime": "2023-01-02T12:00:00.000Z",
                },
            ]
        }
        self.mock_files_list.execute.return_value = mock_response

        result = self.drive_service.list_files(query="name contains 'test'", page_size=10, order_by="name")

        self.assertEqual(result, {"files": mock_response["files"]})

        self.mock_service.files.assert_called_once()
        from src.mcp_gsuite.drive import FILE_LIST_FIELDS

        self.mock_files.list.assert_called_once_with(
            pageSize=10,
            fields=FILE_LIST_FIELDS,
            q="name contains 'test'",
            orderBy="name",
        )
        self.mock_files_list.execute.assert_called_once()

    def test_list_files_exception(self):
        self.mock_files_list.execute.side_effect = Exception("API Error")

        result = self.drive_service.list_files()

        self.assertEqual(result, {"files": []})

    def test_get_file(self):
        mock_response = {
            "id": "file1",
            "name": "File 1",
            "mimeType": "application/pdf",
            "modifiedTime": "2023-01-01T12:00:00.000Z",
        }
        self.mock_files_get.execute.return_value = mock_response

        result = self.drive_service.get_file(file_id="file1")

        self.assertEqual(result, mock_response)

        self.mock_service.files.assert_called_once()
        from src.mcp_gsuite.drive import FILE_FIELDS

        self.mock_files.get.assert_called_once_with(
            fileId="file1",
            fields=FILE_FIELDS,
        )
        self.mock_files_get.execute.assert_called_once()

    def test_get_file_exception(self):
        self.mock_files_get.execute.side_effect = Exception("API Error")

        result = self.drive_service.get_file(file_id="file1")

        self.assertIsNone(result)

    def test_download_file(self):
        mock_file_info = {
            "name": "File 1",
            "mimeType": "application/pdf",
        }
        mock_file_content = b"file content"

        self.mock_files_get.execute.return_value = mock_file_info
        self.mock_files_get_media.execute.return_value = mock_file_content

        result = self.drive_service.download_file(file_id="file1")

        self.assertEqual(
            result,
            {
                "name": "File 1",
                "mimeType": "application/pdf",
                "content": mock_file_content,
            },
        )

        self.assertEqual(self.mock_service.files.call_count, 2)
        self.mock_files.get.assert_called_once_with(fileId="file1", fields="name,mimeType")
        self.mock_files.get_media.assert_called_once_with(fileId="file1")
        self.mock_files_get.execute.assert_called_once()
        self.mock_files_get_media.execute.assert_called_once()

    def test_download_file_exception(self):
        self.mock_files_get.execute.side_effect = Exception("API Error")

        result = self.drive_service.download_file(file_id="file1")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
