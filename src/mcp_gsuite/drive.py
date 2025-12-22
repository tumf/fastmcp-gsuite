import io
import logging
import mimetypes
import os
import traceback

from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

# Common fields for Drive API responses
FILE_FIELDS = "id, name, mimeType, md5Checksum, trashed, parents, modifiedTime, size, webViewLink, iconLink"
FILE_LIST_FIELDS = f"files({FILE_FIELDS})"


class DriveService:
    def __init__(self, service):
        if not service:
            raise ValueError("A valid Google API service client must be provided.")
        self.service = service

    def list_files(self, query=None, page_size=100, order_by=None, corpora=None) -> dict:
        """
        Lists files in the user's Google Drive.

        Args:
            query (str, optional): Search query for filtering files
            page_size (int): Maximum number of files to return (1-1000, default: 100)
            order_by (str, optional): Sort order for the results (e.g., 'name', 'modifiedTime desc')
            corpora (str, optional): The source of files (user, domain, drive, allDrives)

        Returns:
            dict: Dictionary containing list of file objects with their metadata
        """
        try:
            page_size = min(max(1, page_size), 1000)

            params = {
                "pageSize": page_size,
                "fields": FILE_LIST_FIELDS,
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
                    fields=FILE_FIELDS,
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

    def upload_file(
        self, file_path=None, file_content=None, file_name=None, mime_type=None, parent_folder_id=None
    ) -> dict | None:
        """
        Upload a file to Google Drive or create a folder.

        Args:
            file_path (str, optional): Path to the file to upload
            file_content (bytes, optional): Content of the file to upload
            file_name (str, optional): Name of the file (required if file_content is provided)
            mime_type (str, optional): MIME type of the file
            parent_folder_id (str, optional): ID of the parent folder

        Returns:
            dict: Metadata of the uploaded file or None if upload fails

        Note:
            - Either file_path or (file_content and file_name) must be provided
            - For folder creation, set mime_type to "application/vnd.google-apps.folder"
        """
        try:
            if mime_type == "application/vnd.google-apps.folder":
                folder_name = file_name
                if file_path and not folder_name:
                    folder_name = os.path.basename(file_path)
                if not folder_name:
                    folder_name = "New Folder"

                folder_metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}

                if parent_folder_id:
                    folder_metadata["parents"] = [parent_folder_id]

                folder = (
                    self.service.files()
                    .create(
                        body=folder_metadata,
                        fields="id, name, mimeType, trashed, parents, modifiedTime, webViewLink, iconLink",
                    )
                    .execute()
                )

                return folder

            if not file_path and not (file_content and file_name):
                raise ValueError("Either file_path or (file_content and file_name) must be provided")

            file_metadata = {}

            if file_path:
                file_metadata["name"] = os.path.basename(file_path)
            else:
                file_metadata["name"] = file_name

            if parent_folder_id:
                file_metadata["parents"] = [parent_folder_id]

            if not mime_type and file_path:
                guessed_mime_type, _ = mimetypes.guess_type(file_path)
                mime_type = guessed_mime_type or "application/octet-stream"

            if file_path:
                media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            else:
                if not isinstance(file_content, bytes):
                    file_content = bytes(file_content, "utf-8") if isinstance(file_content, str) else b""
                media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=mime_type, resumable=True)

            uploaded_file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields=FILE_FIELDS,
                )
                .execute()
            )

            return uploaded_file
        except Exception as e:
            logging.error(f"Error uploading file: {e!s}")
            logging.error(traceback.format_exc())
            return None

    def copy_file(self, file_id: str, new_name=None, parent_folder_id=None) -> dict | None:
        """
        Create a copy of a file in Google Drive.

        Args:
            file_id (str): ID of the file to copy
            new_name (str, optional): New name for the copied file
            parent_folder_id (str, optional): ID of the parent folder for the copy

        Returns:
            dict: Metadata of the copied file or None if copy fails
        """
        try:
            body = {}
            if new_name:
                body["name"] = new_name

            if parent_folder_id:
                body["parents"] = [parent_folder_id]

            copied_file = (
                self.service.files()
                .copy(
                    fileId=file_id,
                    body=body,
                    fields=FILE_FIELDS,
                )
                .execute()
            )

            return copied_file
        except Exception as e:
            logging.error(f"Error copying file {file_id}: {e!s}")
            logging.error(traceback.format_exc())
            return None

    def delete_file(self, file_id: str) -> tuple[bool, str | None]:
        """
        Delete a file from Google Drive.

        Args:
            file_id (str): ID of the file to delete

        Returns:
            tuple[bool, str | None]: (success, error_message)
                - (True, None) if deletion was successful
                - (False, error_message) if deletion failed
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True, None
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error deleting file {file_id}: {error_msg}")
            logging.error(traceback.format_exc())
            return False, error_msg

    def trash_file(self, file_id: str) -> tuple[bool, str | None]:
        """
        Move a file to Google Drive trash (soft delete).

        Args:
            file_id (str): ID of the file to trash

        Returns:
            tuple[bool, str | None]: (success, error_message)
                - (True, None) if trashing was successful
                - (False, error_message) if trashing failed
        """
        try:
            self.service.files().update(
                fileId=file_id,
                body={"trashed": True},
                fields=FILE_FIELDS,
            ).execute()
            return True, None
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error trashing file {file_id}: {error_msg}")
            logging.error(traceback.format_exc())
            return False, error_msg

    def untrash_file(self, file_id: str) -> tuple[bool, str | None]:
        """
        Restore a file from Google Drive trash.

        Args:
            file_id (str): ID of the file to restore

        Returns:
            tuple[bool, str | None]: (success, error_message)
                - (True, None) if restoring was successful
                - (False, error_message) if restoring failed
        """
        try:
            self.service.files().update(
                fileId=file_id,
                body={"trashed": False},
                fields=FILE_FIELDS,
            ).execute()
            return True, None
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error restoring file {file_id}: {error_msg}")
            logging.error(traceback.format_exc())
            return False, error_msg

    def rename_file(self, file_id: str, new_name: str) -> dict | None:
        """
        Rename a file in Google Drive.

        Args:
            file_id (str): ID of the file to rename
            new_name (str): New name for the file

        Returns:
            dict: Updated file metadata or None if rename fails
        """
        try:
            file_metadata = {"name": new_name}

            updated_file = (
                self.service.files()
                .update(
                    fileId=file_id,
                    body=file_metadata,
                    fields=FILE_FIELDS,
                )
                .execute()
            )

            return updated_file
        except Exception as e:
            logging.error(f"Error renaming file {file_id}: {e!s}")
            logging.error(traceback.format_exc())
            return None

    def move_file(self, file_id: str, new_parent_id: str, remove_previous_parents=True) -> dict | None:
        """
        Move a file to a different folder in Google Drive.

        Args:
            file_id (str): ID of the file to move
            new_parent_id (str): ID of the destination folder
            remove_previous_parents (bool): Whether to remove the file from its current folders

        Returns:
            dict: Updated file metadata or None if move fails
        """
        try:
            previous_parents = ""
            if remove_previous_parents:
                file = self.service.files().get(fileId=file_id, fields="parents").execute()
                previous_parents = ",".join(file.get("parents", []))

            updated_file = (
                self.service.files()
                .update(
                    fileId=file_id,
                    addParents=new_parent_id,
                    removeParents=previous_parents if remove_previous_parents else None,
                    fields=FILE_FIELDS,
                )
                .execute()
            )

            return updated_file
        except Exception as e:
            logging.error(f"Error moving file {file_id}: {e!s}")
            logging.error(traceback.format_exc())
            return None
