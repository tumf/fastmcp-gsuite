# setup-cli Specification

## Purpose
TBD - created by archiving change improve-auth-setup. Update Purpose after archive.
## Requirements
### Requirement: CLI Entry Point

The package MUST provide a `setup` command accessible via `uv run fastmcp-gsuite setup` or `python -m mcp_gsuite.setup_cli`.

**Rationale**: Provides a discoverable, standardized entry point for setup.

#### Scenario: User runs setup command

**Given** the user has installed fastmcp-gsuite  
**When** they run `uv run fastmcp-gsuite setup`  
**Then** the interactive setup process begins  
**And** the command displays a welcome message

#### Scenario: User requests help

**Given** the user wants to see available options  
**When** they run `uv run fastmcp-gsuite setup --help`  
**Then** the command displays usage information  
**And** lists all available flags (`--add-account`, `--list`, `--remove-account`)

---

### Requirement: Client Credentials Configuration

The setup command MUST interactively prompt for Google OAuth2 client credentials and create `.gauth.json`.

**Rationale**: Eliminates manual JSON file creation and reduces setup errors.

#### Scenario: First-time client credentials setup

**Given** no `.gauth.json` file exists  
**When** the user runs the setup command  
**Then** the system prompts for OAuth2 Client ID  
**And** prompts for OAuth2 Client Secret  
**And** creates `.gauth.json` with the structure:
```json
{
  "web": {
    "client_id": "<provided-id>",
    "client_secret": "<provided-secret>",
    "redirect_uris": ["http://localhost:4100/code"],
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token"
  }
}
```

#### Scenario: Client credentials already exist

**Given** `.gauth.json` already exists  
**When** the user runs the setup command  
**Then** the system displays "Using existing .gauth.json"  
**And** skips client credentials prompts  
**And** proceeds to account setup

#### Scenario: Invalid client credentials provided

**Given** the user enters empty client ID or secret  
**When** the system validates the input  
**Then** it displays an error message  
**And** re-prompts for the empty field

---

### Requirement: Account Information Collection

The setup command MUST collect account metadata (email, type, extra info) for each Google account.

**Rationale**: Provides context for multi-account selection in MCP tools.

#### Scenario: Collecting account information

**Given** client credentials are configured  
**When** adding a new account  
**Then** the system prompts for account email  
**And** prompts for account type (personal/work)  
**And** prompts for optional extra info  
**And** validates email format (contains @)

#### Scenario: Invalid email format

**Given** the user enters an invalid email (no @ symbol)  
**When** the system validates the email  
**Then** it displays "Invalid email format"  
**And** re-prompts for email address

---

### Requirement: OAuth Authorization Flow

The setup command MUST guide users through Google OAuth authorization and store credentials securely.

**Rationale**: Automates the most complex part of setup.

#### Scenario: Successful authorization flow

**Given** account information has been collected  
**When** starting the authorization flow  
**Then** the system generates an authorization URL  
**And** opens the URL in the default browser  
**And** displays "Opening browser for authorization..."  
**And** prompts "Enter the authorization code:"  
**When** the user enters the code  
**Then** the system exchanges the code for credentials  
**And** saves credentials to `.oauth2.{email}.json`  
**And** displays "✓ Authorization successful!"

#### Scenario: Authorization code exchange fails

**Given** the user enters an invalid authorization code  
**When** the system attempts token exchange  
**Then** it displays "Authorization failed: <error-message>"  
**And** prompts the user to try again or exit

#### Scenario: Browser fails to open

**Given** the browser cannot be opened automatically  
**When** the authorization flow starts  
**Then** the system displays the URL as text  
**And** instructs the user to open it manually  
**And** continues with code prompt

---

### Requirement: Accounts Registry Management

The setup command MUST maintain `.accounts.json` as the authoritative registry of configured accounts.

**Rationale**: Enables multi-account support with metadata.

#### Scenario: Creating accounts.json for first account

**Given** no `.accounts.json` exists  
**When** the first account is successfully authorized  
**Then** the system creates `.accounts.json` with:
```json
{
  "accounts": [
    {
      "email": "user@example.com",
      "account_type": "personal",
      "extra_info": "Primary account"
    }
  ]
}
```

#### Scenario: Adding account to existing accounts.json

**Given** `.accounts.json` exists with one account  
**When** a second account is successfully authorized  
**Then** the system appends to the accounts array  
**And** preserves existing accounts  
**And** writes formatted JSON with 2-space indentation

#### Scenario: Preventing duplicate accounts

**Given** an account with email `user@example.com` already exists  
**When** attempting to add the same email again  
**Then** the system displays "Account already exists"  
**And** prompts whether to re-authorize (overwrite credentials)

---

### Requirement: Multi-Account Addition

The setup command MUST support adding additional accounts via `--add-account` flag.

**Rationale**: Simplifies adding multiple Google accounts.

#### Scenario: Adding account with existing client credentials

**Given** `.gauth.json` exists  
**And** one account is already configured  
**When** the user runs `uv run fastmcp-gsuite setup --add-account`  
**Then** the system skips client credentials prompts  
**And** proceeds directly to account information collection  
**And** runs the authorization flow  
**And** appends to `.accounts.json`

#### Scenario: Adding account without client credentials

**Given** `.gauth.json` does not exist  
**When** the user runs `uv run fastmcp-gsuite setup --add-account`  
**Then** the system displays "Client credentials not found"  
**And** prompts for client credentials first  
**And** then proceeds with account addition

---

### Requirement: Account Listing

The setup command MUST support listing configured accounts via `--list` flag.

**Rationale**: Provides visibility into configured accounts and authentication status.

#### Scenario: Listing accounts with credentials

**Given** two accounts exist in `.accounts.json`  
**And** both have corresponding `.oauth2.{email}.json` files  
**When** the user runs `uv run fastmcp-gsuite setup --list`  
**Then** the system displays:
```
Configured accounts:
  1. alice@example.com (personal) - ✓ Authenticated
  2. bob@company.com (work) - ✓ Authenticated
```

#### Scenario: Listing accounts with missing credentials

**Given** one account exists in `.accounts.json`  
**And** no `.oauth2.{email}.json` file exists  
**When** the user runs `uv run fastmcp-gsuite setup --list`  
**Then** the system displays:
```
Configured accounts:
  1. alice@example.com (personal) - ✗ Missing credentials
```

#### Scenario: No accounts configured

**Given** no `.accounts.json` exists  
**When** the user runs `uv run fastmcp-gsuite setup --list`  
**Then** the system displays "No accounts configured"  
**And** exits with status code 0

---

### Requirement: Account Removal

The setup command MUST support removing accounts via `--remove-account <email>` flag.

**Rationale**: Allows users to clean up unused accounts.

#### Scenario: Removing an existing account

**Given** account `alice@example.com` exists in `.accounts.json`  
**And** `.oauth2.alice@example.com.json` exists  
**When** the user runs `uv run fastmcp-gsuite setup --remove-account alice@example.com`  
**Then** the system prompts "Remove alice@example.com? (y/n):"  
**When** the user confirms with "y"  
**Then** the system removes the account from `.accounts.json`  
**And** deletes `.oauth2.alice@example.com.json`  
**And** displays "✓ Account removed"

#### Scenario: Canceling account removal

**Given** an account exists  
**When** the user runs remove-account command  
**And** responds "n" to the confirmation prompt  
**Then** the system displays "Cancelled"  
**And** does not modify any files

#### Scenario: Removing non-existent account

**Given** account `nobody@example.com` does not exist  
**When** the user runs `uv run fastmcp-gsuite setup --remove-account nobody@example.com`  
**Then** the system displays "Account not found: nobody@example.com"  
**And** exits with status code 1

---

### Requirement: Error Handling and User Feedback

The setup command MUST provide clear error messages and feedback throughout the process.

**Rationale**: Improves troubleshooting and user confidence.

#### Scenario: Handling file permission errors

**Given** the current directory is read-only  
**When** attempting to create `.gauth.json`  
**Then** the system displays "Permission denied: Cannot write to .gauth.json"  
**And** suggests checking directory permissions  
**And** exits with status code 1

#### Scenario: Handling network errors during authorization

**Given** network connectivity fails during OAuth exchange  
**When** the token exchange is attempted  
**Then** the system displays "Network error: <details>"  
**And** suggests checking internet connection  
**And** offers to retry

#### Scenario: Success feedback

**Given** all setup steps complete successfully  
**When** the setup finishes  
**Then** the system displays:
```
Setup complete! You can now use fastmcp-gsuite.
Run: uv run fastmcp-gsuite
```

---

### Requirement: Backward Compatibility

The setup command MUST NOT break existing manual setup workflows.

**Rationale**: Users who have already set up authentication should not be affected.

#### Scenario: Existing manual setup still works

**Given** a user has manually created `.gauth.json`, `.accounts.json`, and credential files  
**When** they run the MCP server  
**Then** the server loads and uses existing credentials  
**And** no migration or conversion is required

#### Scenario: Mixing manual and CLI setup

**Given** a user manually created `.gauth.json`  
**When** they run `uv run fastmcp-gsuite setup --add-account`  
**Then** the CLI detects and uses the existing `.gauth.json`  
**And** adds the new account without modifying client credentials

---

