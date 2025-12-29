# drive-trash Specification

## Purpose
TBD - created by archiving change add-drive-trash-operations. Update Purpose after archive.
## Requirements
### Requirement: Trash File Operation

The system MUST provide a `trash_drive_file` tool to move files to Google Drive trash.

**Rationale**: Users with edit permissions can trash files even if they cannot permanently delete them.

#### Scenario: Successfully trash a file

**Given** the user has edit permissions on file `abc123`  
**When** they call `trash_drive_file(user_id="user@example.com", file_id="abc123")`  
**Then** the file is moved to trash  
**And** the response includes the file ID and confirmation message  
**And** the file's `trashed` property becomes `true`

#### Scenario: Trash file without permission

**Given** the user has view-only permissions on file `abc123`  
**When** they call `trash_drive_file(user_id="user@example.com", file_id="abc123")`  
**Then** the operation fails  
**And** the response includes the specific error message from the API

#### Scenario: Trash non-existent file

**Given** file `nonexistent` does not exist  
**When** they call `trash_drive_file(user_id="user@example.com", file_id="nonexistent")`  
**Then** the operation fails  
**And** the response indicates the file was not found

---

### Requirement: Trash Folder Operation

The system MUST provide a `trash_drive_folder` tool to move folders to Google Drive trash.

**Rationale**: Consistent behavior between file and folder operations.

#### Scenario: Successfully trash a folder

**Given** the user has edit permissions on folder `folder123`  
**And** the item is a folder (mimeType: `application/vnd.google-apps.folder`)  
**When** they call `trash_drive_folder(user_id="user@example.com", folder_id="folder123")`  
**Then** the folder is moved to trash  
**And** all contents of the folder are also trashed

#### Scenario: Trash item that is not a folder

**Given** item `file123` is a file, not a folder  
**When** they call `trash_drive_folder(user_id="user@example.com", folder_id="file123")`  
**Then** the operation fails  
**And** the response indicates the item is not a folder

---

### Requirement: Untrash File Operation

The system MUST provide an `untrash_drive_file` tool to restore files from trash.

**Rationale**: Users should be able to recover accidentally trashed files.

#### Scenario: Successfully restore a file from trash

**Given** file `abc123` is in the trash  
**And** the user has edit permissions  
**When** they call `untrash_drive_file(user_id="user@example.com", file_id="abc123")`  
**Then** the file is restored from trash  
**And** the file's `trashed` property becomes `false`  
**And** the response includes confirmation message

#### Scenario: Restore file that is not in trash

**Given** file `abc123` is not in the trash  
**When** they call `untrash_drive_file(user_id="user@example.com", file_id="abc123")`  
**Then** the operation succeeds (idempotent)  
**And** the file remains in its current location

---

