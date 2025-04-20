import logging
import traceback


class DriveService:
    def __init__(self, service):
        if not service:
            raise ValueError("A valid Google API service client must be provided.")
        self.service = service

    def list_files(self, query=None, page_size=100, order_by=None, corpora=None) -> list:
        """
        Lists files in the user's Google Drive.

        Args:
            query (str, optional): Search query for filtering files
            page_size (int): Maximum number of files to return (1-1000, default: 100)
            order_by (str, optional): Sort order for the results (e.g., 'name', 'modifiedTime desc')
            corpora (str, optional): The source of files (user, domain, drive, allDrives)

        Returns:
            list: List of file objects with their metadata
        """
        try:
            page_size = min(max(1, page_size), 1000)

            params = {
                "pageSize": page_size,
                "fields": "files(id, name, mimeType, trashed, parents, modifiedTime, size, webViewLink, iconLink)",
            }

            if query:
                params["q"] = query
            if order_by:
                params["orderBy"] = order_by
            if corpora:
                params["corpora"] = corpora

            result = self.service.files().list(**params).execute()
            files = result.get("files", [])
            return {"files": files}

        except Exception as e:
            logging.error(f"Error listing files: {e!s}")
            logging.error(traceback.format_exc())
            return {"files": []}

    def get_file(self, file_id: str) -> dict | None:
        """
        Get metadata for a specific file by ID.

        Args:
            file_id (str): The ID of the file to retrieve metadata for

        Returns:
            dict: File metadata or None if not found or error occurs
        """
        try:
            file = (
                self.service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, mimeType, trashed, parents, modifiedTime, size, webViewLink, iconLink",
                )
                .execute()
            )
            return file
        except Exception as e:
            logging.error(f"Error getting file {file_id}: {e!s}")
            logging.error(traceback.format_exc())
            return None

    def download_file(self, file_id: str) -> dict | None:
        """
        Download a file's content by ID.

        Args:
            file_id (str): The ID of the file to download

        Returns:
            dict: File data including content or None if download fails
        """
        try:
            file = self.service.files().get(fileId=file_id, fields="name,mimeType").execute()

            request = self.service.files().get_media(fileId=file_id)
            file_content = request.execute()

            return {
                "name": file.get("name"),
                "mimeType": file.get("mimeType"),
                "content": file_content,
            }
        except Exception as e:
            logging.error(f"Error downloading file {file_id}: {e!s}")
            logging.error(traceback.format_exc())
            return None
