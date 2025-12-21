# gmail-drive-integration Specification

## Purpose
TBD - created by archiving change fix-attachment-base64-decode. Update Purpose after archive.
## Requirements
### Requirement: Attachment Data Decoding

The system SHALL decode Gmail attachment data from base64 before saving to Google Drive.

Gmail API returns attachment content as URL-safe base64 encoded strings. Before uploading to Google Drive, the system MUST decode this data to obtain the original binary content.

#### Scenario: PDF attachment saved correctly

- **WHEN** a user saves a Gmail attachment (e.g., PDF) to Google Drive
- **THEN** the system decodes the base64 attachment data before upload
- **AND** the file saved to Drive contains the correct binary content
- **AND** the file opens correctly in Google Drive or when downloaded

#### Scenario: Multiple attachments saved correctly via bulk operation

- **WHEN** a user saves multiple Gmail attachments to Google Drive in bulk
- **THEN** each attachment is decoded from base64 before upload
- **AND** all files saved to Drive contain correct binary content

### Requirement: URL-safe Base64 Handling

The system SHALL use URL-safe base64 decoding for Gmail attachment data.

Gmail API uses URL-safe base64 encoding (RFC 4648), which replaces `+` with `-` and `/` with `_`. The system MUST use the appropriate decoding function (`base64.urlsafe_b64decode`) to handle this encoding.

#### Scenario: URL-safe encoded content decoded correctly

- **WHEN** Gmail returns attachment data with URL-safe base64 encoding
- **THEN** the system uses `base64.urlsafe_b64decode()` to decode the content
- **AND** special characters (`-`, `_`) are correctly interpreted

