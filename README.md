# fastmcp-gsuite MCP server (using fastmcp)

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

#### Oauth 2

Google Workspace (G Suite) APIs require OAuth2 authorization. Follow these steps to set up authentication:

1. Create OAuth2 Credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API and Google Calendar API for your project
   - Go to "Credentials" → "Create Credentials" → "OAuth client ID"
   - Select "Desktop app" or "Web application" as the application type
   - Configure the OAuth consent screen with required information
   - Add authorized redirect URIs (include `http://localhost:4100/code` for local development)

2. Required OAuth2 Scopes:

```json
   [
     "openid",
     "https://mail.google.com/",
     "https://www.googleapis.com/auth/calendar",
     "https://www.googleapis.com/auth/userinfo.email"
   ]
```

3. Then create a `.gauth.json` in your working directory with client

```json
{
    "web": {
        "client_id": "$your_client_id",
        "client_secret": "$your_client_secret",
        "redirect_uris": ["http://localhost:4100/code"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
}
```

4. Create a `.accounts.json` file with account information

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

You can specify multiple accounts. Make sure they have access in your Google Auth app. The `extra_info` field is especially interesting as you can add info here that you want to tell the AI about the account (e.g. whether it has a specific agenda)

Note: **Initial Authentication Required:** Before running the server for the first time with a new account, you need to perform an initial OAuth2 authentication. This server does not yet include a built-in command for this. You may need to adapt the authentication logic from the previous version or use a separate script to generate the initial `.oauth2.{email}.json` credential file by completing the Google OAuth flow (which involves opening a browser, logging in, and granting permissions). Once the credential file exists, the server will use it and attempt to refresh the token automatically when needed.

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
