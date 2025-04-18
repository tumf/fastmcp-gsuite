# mcp-gsuite MCP server (using fastmcp)

[![smithery badge](https://smithery.ai/badge/mcp-gsuite)](https://smithery.ai/server/mcp-gsuite)
MCP server to interact with Google products, rewritten using the `fastmcp` library.

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

### Installing via Smithery

To install mcp-gsuite for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-gsuite) (Note: Smithery integration might need updates for the `fastmcp` version):

```bash
npx -y @smithery/cli install mcp-gsuite --client claude
```

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

You can specifiy multiple accounts. Make sure they have access in your Google Auth app. The `extra_info` field is especially interesting as you can add info here that you want to tell the AI about the account (e.g. whether it has a specific agenda)

Note: **Initial Authentication Required:** Before running the server for the first time with a new account, you need to perform an initial OAuth2 authentication. This server does not yet include a built-in command for this. You may need to adapt the authentication logic from the previous version or use a separate script to generate the initial `.oauth2.{email}.json` credential file by completing the Google OAuth flow (which involves opening a browser, logging in, and granting permissions). Once the credential file exists, the server will use it and attempt to refresh the token automatically when needed.

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`

On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  

```json
{
  "mcpServers": {
    "mcp-gsuite": {
      "command": "uv",
      "args": [
        "--directory",
        "<dir_to>/mcp-gsuite",
        "run",
        "mcp-gsuite-fast" # Use the new entry point
      ]
    }
  }
}
```


Note: Configuration is now primarily handled via environment variables or a `.env` file in the working directory, using `pydantic-settings`. See the Configuration Options section below.

```json
{
  "mcpServers": {
    "mcp-gsuite": {
      "command": "uv",
      "args": [
        "--directory",
        "<dir_to>/mcp-gsuite",
        "run",
        "mcp-gsuite-fast" # Use the new entry point
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
    "mcp-gsuite": {
      "command": "uvx",
      "args": [
        "mcp-gsuite-fast" # Use the new entry point
        # Configuration via .env or environment variables is preferred now
      ]
    }
  }
}
```

</details>

### Configuration Options (via `.env` file or Environment Variables)

Configuration is now managed using `pydantic-settings`. Create a `.env` file in the directory where you run the server, or set environment variables:

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
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-gsuite run mcp-gsuite-fast
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

You can also watch the server logs with this command:

```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp-server-mcp-gsuite-fast.log # Log filename might change based on the server name
```
