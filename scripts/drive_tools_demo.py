"""
Demo script for Google Drive tools in fastmcp-gsuite.

This script demonstrates a complex scenario using the Drive tools:
1. Create 10 dummy files and upload them to Drive
2. List the uploaded files
3. Rename some of the files
4. Create a folder in Drive
5. Move some files to the new folder
6. Remove all dummy files and the folder
"""

import asyncio
import json
import os
import tempfile
import time

from fastmcp import FastMCP

mcp = FastMCP("mcp-gsuite-demo")


async def create_dummy_files(count: int = 10) -> list[str]:
    """Create temporary dummy files and return their paths."""
    temp_dir = tempfile.mkdtemp()
    file_paths = []

    print(f"Creating {count} dummy files in {temp_dir}...")
    for i in range(count):
        file_path = os.path.join(temp_dir, f"dummy_file_{i}.txt")
        with open(file_path, "w") as f:
            f.write(f"This is dummy file {i} created for Drive tools demo.\n")
            f.write(f"Created at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Content: Sample content for file {i}\n")
        file_paths.append(file_path)

    return file_paths


async def upload_files(user_id: str, file_paths: list[str]) -> list[dict]:
    """Upload files to Google Drive and return their metadata."""
    uploaded_files = []

    print(f"Uploading {len(file_paths)} files to Google Drive...")
    for file_path in file_paths:
        print(f"  Uploading {os.path.basename(file_path)}...")
        result = await mcp.call_tool(
            "upload_drive_file",
            {
                "user_id": user_id,
                "file_path": file_path,
            },
        )

        if result and result.get("content"):
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        file_data = json.loads(item.get("text"))
                        uploaded_files.append(file_data)
                        print(f"    Uploaded as '{file_data.get('name')}' with ID: {file_data.get('id')}")
                    except json.JSONDecodeError:
                        print(f"    Failed to parse upload result: {item.get('text')}")

    return uploaded_files


async def list_files(user_id: str, query: str | None = None) -> list[dict]:
    """List files in Google Drive matching the optional query."""
    print(f"Listing Drive files{' with query: ' + query if query else ''}...")

    result = await mcp.call_tool(
        "list_drive_files",
        {
            "user_id": user_id,
            "query": query,
            "limit": 100,
        },
    )

    files = []
    if result and result.get("content"):
        for item in result["content"]:
            if item.get("type") == "text" and item.get("text"):
                try:
                    data = json.loads(item.get("text"))
                    if data.get("files"):
                        files = data.get("files", [])
                        print(f"Found {len(files)} files:")
                        for file in files:
                            print(f"  - {file.get('name')} (ID: {file.get('id')})")
                except json.JSONDecodeError:
                    print(f"Failed to parse list result: {item.get('text')}")

    return files


async def rename_files(user_id: str, files: list[dict], start_index: int, count: int) -> list[dict]:
    """Rename a subset of files and return their updated metadata."""
    renamed_files: list[dict] = []

    if not files or len(files) < start_index + count:
        print("Not enough files to rename")
        return renamed_files

    files_to_rename = files[start_index : start_index + count]
    print(f"Renaming {len(files_to_rename)} files...")

    for file in files_to_rename:
        file_id = file.get("id")
        old_name = file.get("name")
        new_name = f"renamed_{old_name}"

        print(f"  Renaming '{old_name}' to '{new_name}'...")
        result = await mcp.call_tool(
            "rename_drive_file",
            {
                "user_id": user_id,
                "file_id": file_id,
                "new_name": new_name,
            },
        )

        if result and result.get("content"):
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        file_data = json.loads(item.get("text"))
                        renamed_files.append(file_data)
                        print(f"    Renamed successfully to '{file_data.get('name')}'")
                    except json.JSONDecodeError:
                        print(f"    Failed to parse rename result: {item.get('text')}")

    return renamed_files


async def create_folder(user_id: str, folder_name: str) -> dict | None:
    """Create a folder in Google Drive and return its metadata."""
    print(f"Creating folder '{folder_name}'...")

    temp_dir = tempfile.mkdtemp()
    placeholder_path = os.path.join(temp_dir, ".placeholder")
    with open(placeholder_path, "w") as f:
        f.write("")

    result = await mcp.call_tool(
        "upload_drive_file",
        {
            "user_id": user_id,
            "file_path": placeholder_path,
            "mime_type": "application/vnd.google-apps.folder",
            "parent_folder_id": None,
        },
    )

    folder_data = None
    if result and result.get("content"):
        for item in result["content"]:
            if item.get("type") == "text" and item.get("text"):
                try:
                    folder_data = json.loads(item.get("text"))
                    print(f"  Created folder '{folder_data.get('name')}' with ID: {folder_data.get('id')}")
                except json.JSONDecodeError:
                    print(f"  Failed to parse folder creation result: {item.get('text')}")

    os.remove(placeholder_path)
    os.rmdir(temp_dir)

    return folder_data


async def move_files_to_folder(
    user_id: str, files: list[dict], folder_id: str, start_index: int, count: int
) -> list[dict]:
    """Move a subset of files to a folder and return their updated metadata."""
    moved_files: list[dict] = []

    if not files or len(files) < start_index + count:
        print("Not enough files to move")
        return moved_files

    files_to_move = files[start_index : start_index + count]
    print(f"Moving {len(files_to_move)} files to folder with ID {folder_id}...")

    for file in files_to_move:
        file_id = file.get("id")
        file_name = file.get("name")

        print(f"  Moving '{file_name}'...")
        result = await mcp.call_tool(
            "move_drive_file",
            {
                "user_id": user_id,
                "file_id": file_id,
                "new_parent_id": folder_id,
                "remove_previous_parents": True,
            },
        )

        if result and result.get("content"):
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        file_data = json.loads(item.get("text"))
                        moved_files.append(file_data)
                        print("    Moved successfully")
                    except json.JSONDecodeError:
                        print(f"    Failed to parse move result: {item.get('text')}")

    return moved_files


async def delete_files(user_id: str, files: list[dict]) -> int:
    """Delete files from Google Drive and return the count of successfully deleted files."""
    deleted_count = 0

    print(f"Deleting {len(files)} files...")
    for file in files:
        file_id = file.get("id")
        file_name = file.get("name")

        print(f"  Deleting '{file_name}'...")
        result = await mcp.call_tool(
            "delete_drive_file",
            {
                "user_id": user_id,
                "file_id": file_id,
            },
        )

        success = False
        if result and result.get("content"):
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    response_text = item.get("text")
                    if "successfully deleted" in response_text.lower():
                        success = True
                        deleted_count += 1
                        print("    Deleted successfully")
                    else:
                        print(f"    Failed to delete: {response_text}")

        if not success:
            print(f"    Failed to delete file {file_id}")

    return deleted_count


async def copy_files(user_id: str, files: list[dict], start_index: int, count: int) -> list[dict]:
    """Copy a subset of files and return their metadata."""
    copied_files: list[dict] = []

    if not files or len(files) < start_index + count:
        print("Not enough files to copy")
        return copied_files

    files_to_copy = files[start_index : start_index + count]
    print(f"Copying {len(files_to_copy)} files...")

    for file in files_to_copy:
        file_id = file.get("id")
        file_name = file.get("name")
        new_name = f"copy_of_{file_name}"

        print(f"  Copying '{file_name}' to '{new_name}'...")
        result = await mcp.call_tool(
            "copy_drive_file",
            {
                "user_id": user_id,
                "file_id": file_id,
                "new_name": new_name,
            },
        )

        if result and result.get("content"):
            for item in result["content"]:
                if item.get("type") == "text" and item.get("text"):
                    try:
                        file_data = json.loads(item.get("text"))
                        copied_files.append(file_data)
                        print(f"    Copied successfully as '{file_data.get('name')}'")
                    except json.JSONDecodeError:
                        print(f"    Failed to parse copy result: {item.get('text')}")

    return copied_files


async def run_demo(user_id: str):
    """Run the complete Drive tools demo scenario."""
    print("\n=== Google Drive Tools Demo ===\n")

    dummy_files = await create_dummy_files(10)
    uploaded_files = await upload_files(user_id, dummy_files)

    if not uploaded_files:
        print("Failed to upload files. Exiting demo.")
        return

    for file_path in dummy_files:
        os.remove(file_path)
    os.rmdir(os.path.dirname(dummy_files[0]))

    all_files = await list_files(user_id)

    our_files = [f for f in all_files if f.get("name", "").startswith("dummy_file_")]

    await rename_files(user_id, our_files, 0, 3)
    print("Renamed first 3 files successfully")

    folder = await create_folder(user_id, "demo_folder")

    if not folder:
        print("Failed to create folder. Skipping move step.")
    else:
        folder_id = folder.get("id")
        if folder_id:
            await move_files_to_folder(user_id, our_files, folder_id, 3, 3)
            print("Moved files 3-5 to folder successfully")

    copied_files = await copy_files(user_id, our_files, 6, 2)
    print(f"Created {len(copied_files)} copies of files")

    print("\nFinal state of files:")
    await list_files(user_id)

    all_to_delete = uploaded_files + copied_files
    if folder:
        all_to_delete.append(folder)

    deleted_count = await delete_files(user_id, all_to_delete)
    print(f"\nDeleted {deleted_count} out of {len(all_to_delete)} files/folders")

    print("\n=== Demo Complete ===")


async def main():
    """Main entry point for the demo script."""
    user_id = os.environ.get("GSUITE_EMAIL")
    if not user_id:
        user_id = input("Enter your Google account email: ")

    await run_demo(user_id)


if __name__ == "__main__":
    asyncio.run(main())
