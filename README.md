# fastmcp-gsuite MCP server (using fastmcp)

[![codecov](https://codecov.io/gh/tumf/fastmcp-gsuite/branch/main/graph/badge.svg)](https://codecov.io/gh/tumf/fastmcp-gsuite)

MCP server to interact with Google products, rewritten using the `fastmcp` library.

This project is a fork of [mcp-gsuite](https://github.com/MarkusPfundstein/mcp-gsuite).

## Example prompts

Right now, this MCP server supports Gmail and Calendar integration with the following capabilities:

1. General
* Multiple google accounts

2. Gmail
* Get your Gmail user information
* Query emails with flexible search (e.g., unread, from specific senders, date ranges, with attachments)
* Retrieve complete email content by ID
* Create new draft emails with recipients, subject, body and CC options
* Delete draft emails
* Reply to existing emails (can either send immediately or save as draft)
* Retrieve multiple emails at once by their IDs.
* Save multiple attachments from emails to your local system.

3. Calendar
* Manage multiple calendars
* Get calendar events within specified time ranges
* Create calendar events with:
  + Title, start/end times
  + Optional location and description
  + Optional attendees
  + Custom timezone support
  + Notification preferences
* Delete calendar events

Example prompts you can try:

* Retrieve my latest unread messages
* Search my emails from the Scrum Master
* Retrieve all emails from accounting
* Take the email about ABC and summarize it
* Write a nice response to Alice's last email and upload a draft.
* Reply to Bob's email with a Thank you note. Store it as draft

* What do I have on my agenda tomorrow?
* Check my private account's Family agenda for next week
* I need to plan an event with Tim for 2hrs next week. Suggest some time slots.

## Quickstart

### Install

#### Quick Setup (Recommended)

The easiest way to set up authentication is using the interactive setup command:

```bash
# Install the package
pip install fastmcp-gsuite
# or with uv
uv pip install fastmcp-gsuite

# Run interactive setup
uv run fastmcp-gsuite-setup
```

**Prerequisites:**
- Create OAuth2 credentials in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
  - Select "Desktop app" as application type
  - Enable Gmail API, Google Calendar API, and Google Drive API

The setup wizard will guide you through:
1. Entering your Google OAuth2 Client ID and Client Secret
2. Authorizing your Google account(s) in browser
3. Copying the authorization code from browser back to terminal
4. Automatically creating all necessary configuration files

**Additional Commands:**
```bash
# Add another Google account
uv run fastmcp-gsuite-setup --add-account

# List configured accounts
uv run fastmcp-gsuite-setup --list

# Remove an account
uv run fastmcp-gsuite-setup --remove-account user@example.com
```

#### Manual Setup (Advanced)

<details>
  <summary>Click to expand manual setup instructions</summary>

Google Workspace (G Suite) APIs require OAuth2 authorization. Follow these steps to set up authentication manually:

1. Create OAuth2 Credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API, Google Calendar API, and Google Drive API for your project
   - Go to "Credentials" → "Create Credentials" → "OAuth client ID"
   - Select "Desktop app" as the application type
   - Configure the OAuth consent screen with required information
   - **Note**: For desktop/CLI applications, the redirect URI `urn:ietf:wg:oauth:2.0:oob` will be used automatically

2. Required OAuth2 Scopes:

```json
   [
     "openid",
     "https://mail.google.com/",
     "https://www.googleapis.com/auth/calendar",
     "https://www.googleapis.com/auth/drive",
     "https://www.googleapis.com/auth/userinfo.email"
   ]
```

3. Create a `.gauth.json` in your working directory:

```json
{
    "installed": {
        "client_id": "$your_client_id",
        "client_secret": "$your_client_secret",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
}
```

**Note**: 
- Use `"installed"` for Desktop app credentials (recommended)
- Alternatively, `"web"` format also works with this library
- `urn:ietf:wg:oauth:2.0:oob` is the Out-of-Band (OOB) redirect URI
- Google will display the authorization code in the browser for you to copy and paste

4. Create a `.accounts.json` file with account information:

```json
{
    "accounts": [
        {
            "email": "alice@bob.com",
            "account_type": "personal",
            "extra_info": "Additional info that you want to tell Claude: E.g. 'Contains Family Calendar'"
        }
    ]
}
```

You can specify multiple accounts. Make sure they have access in your Google Auth app. The `extra_info` field is especially interesting as you can add info here that you want to tell the AI about the account (e.g. whether it has a specific agenda).

5. Run the authentication script to generate credentials:

```bash
# Set environment variables
export GOOGLE_ACCOUNT_EMAIL="your-email@example.com"
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"

# Run the script
uv run python scripts/get_refresh_token.py
```

This will open a browser for authorization and create `.oauth2.{email}.json` credential files.

</details>

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`

On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>

```json
{
  "mcpServers": {
    "gsuite": {
      "command": "uv",
      "args": [
        "--directory",
        "<dir_to>/fastmcp-gsuite",
        "run",
        "fastmcp-gsuite"
      ]
    }
  }
}
```

Note: Configuration is now primarily handled via environment variables or a `.env` file in the working directory, using `pydantic-settings` . See the Configuration Options section below.

```json
{
  "mcpServers": {
    "fastmcp-gsuite": {
      "command": "uv",
      "args": [
        "--directory",
        "<dir_to>/fastmcp-gsuite",
        "run",
        "fastmcp-gsuite" # Use the new entry point
        # Configuration via .env or environment variables is preferred now
      ]
    }
  }
}
```

</details>

<details>
  <summary>Published Servers Configuration</summary>

```json
{
  "mcpServers": {
    "fastmcp-gsuite": {
      "command": "uvx",
      "args": [
        "fastmcp-gsuite" # Use the new entry point
        # Configuration via .env or environment variables is preferred now
      ]
    }
  }
}
```

</details>

### Configuration Options (via `.env` file or Environment Variables)

Configuration is now managed using `pydantic-settings` . Create a `.env` file in the directory where you run the server, or set environment variables:

* `GAUTH_FILE`: Path to the `.gauth.json` file containing OAuth2 client configuration. Default: `./.gauth.json`
* `ACCOUNTS_FILE`: Path to the `.accounts.json` file containing Google account information. Default: `./.accounts.json`
* `CREDENTIALS_DIR`: Directory to store the generated `.oauth2.{email}.json` credential files. Default: `.` (current directory)

Example `.env` file:

```dotenv
GAUTH_FILE=/path/to/your/.gauth.json
ACCOUNTS_FILE=/path/to/your/.accounts.json
CREDENTIALS_DIR=/path/to/your/credentials
```

This allows for flexible configuration without command-line arguments when running the server.

### Troubleshooting Setup

**Problem: "No refresh token received"**
- **Cause**: You may have already authorized the app previously
- **Solution**: Go to https://myaccount.google.com/permissions and revoke access, then try setup again

**Problem: "Browser doesn't open automatically"**
- **Solution**: Copy the authorization URL displayed in the terminal and open it manually in your browser

**Problem: "Redirect URI mismatch" error**
- **Cause**: Google Cloud Console has wrong redirect URI configured
- **Solution**: In Google Cloud Console, ensure your OAuth client is configured as "Desktop app" type. Desktop apps automatically use `urn:ietf:wg:oauth:2.0:oob` as the redirect URI

**Problem: "Permission denied when creating .gauth.json"**
- **Cause**: Insufficient write permissions in current directory
- **Solution**: Run setup in a directory where you have write permissions, or use `GAUTH_FILE` environment variable to specify a different location

**Problem: "Account already exists" when adding account**
- **Solution**: Use `--remove-account` to remove the old account first, or choose to overwrite when prompted

**Problem: Setup works but MCP server can't find credentials**
- **Solution**: Ensure you're running the MCP server from the same directory where you ran setup, or set `GAUTH_FILE`, `ACCOUNTS_FILE`, and `CREDENTIALS_DIR` environment variables to point to the correct locations

For more help, see the [GitHub Issues](https://github.com/tumf/fastmcp-gsuite/issues).

## Development

### Building and Publishing

To prepare the package for distribution:

1. Sync dependencies and update lockfile:

```bash
uv sync
```

2. Build package distributions:

```bash
uv build
```

This will create source and wheel distributions in the `dist/` directory.

3. Publish to PyPI:

```bash
uv publish
```

Note: You'll need to set PyPI credentials via environment variables or command flags:
* Token: `--token` or `UV_PUBLISH_TOKEN`
* Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Automatic PyPI Publishing with Tag Push

This project is configured to automatically publish to PyPI when a tag is pushed to the repository. The publishing process is handled by a GitHub Actions workflow.

To publish a new version:

1. Update the version in `pyproject.toml`
2. Commit the changes
3. Tag the commit with a version tag (e.g., `v0.4.2`)
4. Push the tag to GitHub

```bash
# Example workflow to release a new version
git add pyproject.toml
git commit -m "Bump version to 0.4.2"
git tag -a v0.4.2 -m "Version 0.4.2"
git push && git push --tags
```

The GitHub Actions workflow will automatically build and publish the package to PyPI. Make sure to set the following secrets in your GitHub repository:

* `PYPI_API_TOKEN`: Your PyPI API token

You can also use the version bumping commands in the Makefile:

```bash
# Bump patch version (0.4.1 -> 0.4.2)
make bump-patch

# Bump minor version (0.4.1 -> 0.5.0)
make bump-minor

# Bump major version (0.4.1 -> 1.0.0)
make bump-major
```

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

You can launch the MCP Inspector via [ `npm` ](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/fastmcp-gsuite run fastmcp-gsuite
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

You can also watch the server logs with this command:

```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp-server-fastmcp-gsuite.log # Log filename might change based on the server name
```

## E2E Testing

### Standard E2E Tests

To run the standard E2E tests, you need to set up the necessary environment variables with valid Google credentials:

```bash
# Make sure valid Google credentials are set in your environment variables
dotenvx run -f .env.local -- uv run make e2e-tests
```

These tests use the Google API libraries directly to authenticate and test the functionality.

### MCP-Based E2E Tests

There are also MCP-based E2E tests that test the functionality through the MCP protocol, simulating how Claude or other clients would interact with the MCP server:

```bash
# Specify the environment file containing your Google credentials
make mcp-e2e-tests ENV_FILE=.env.local
```

This will run tests that:
1. Start the MCP G-Suite server
2. Connect to it using the chuk-mcp client
3. Test various tools like Gmail message listing and Calendar event retrieval

The environment file should contain the following variables:
- `GSUITE_CREDENTIALS_JSON` - Base64 encoded JSON credentials
- `GOOGLE_ACCOUNT_EMAIL` - Your Google account email
- `GOOGLE_PROJECT_ID` - Your Google Cloud project ID
- `GOOGLE_CLIENT_ID` - Your OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Your OAuth client secret

Both types of E2E tests are excluded from CI pipelines and should only be run locally with valid credentials.

### E2E Test Execution Guide

This project implements end-to-end (E2E) tests using real Google accounts. You can run the E2E tests using the following steps.

#### Prerequisites

To run E2E tests, you need:

1. A `.env.local` file with the following environment variables:
   - `GSUITE_CREDENTIALS_JSON` : Base64 encoded Google credentials
   - `GOOGLE_ACCOUNT_EMAIL` : Google account email for testing
   - `GOOGLE_PROJECT_ID` : Google project ID
   - `GOOGLE_CLIENT_ID` : Google client ID
   - `GOOGLE_CLIENT_SECRET` : Google client secret

2. E2E test dependencies installed:

```bash
uv pip install -e ".[e2e]"
```

#### Test Execution Commands

- Run all E2E tests:

```bash
dotenvx run -f .env.local -- uv run make mcp-all-e2e-tests
```

- Run tests for individual services:

```bash
# Gmail tests
dotenvx run -f .env.local -- uv run make mcp-e2e-tests

# Google Calendar tests
dotenvx run -f .env.local -- uv run make mcp-google-e2e-tests

# Google Drive tests
dotenvx run -f .env.local -- uv run make mcp-gdrive-e2e-tests

# Google Tasks tests
dotenvx run -f .env.local -- uv run make mcp-tasks-e2e-tests

# Google Contacts tests
dotenvx run -f .env.local -- uv run make mcp-contacts-e2e-tests
```

#### Important Notes

- E2E tests access real Google accounts, so be careful not to affect production environments
- E2E tests are automatically skipped in CI environments
- Temporary authentication files are created during test execution but are automatically deleted afterward

## License

# Test push hook

# Test push hook
