# Proposal: Improve Authentication Setup Experience

## Change ID
`improve-auth-setup`

## Status
Implemented

## Overview
Improve the user experience for setting up OAuth2 authentication with Google Workspace by creating an interactive setup command and streamlining the multi-account configuration process.

## Problem Statement

Currently, users must:
1. Manually create `.gauth.json` from Google Cloud Console credentials
2. Manually create `.accounts.json` to define accounts
3. Run a separate Python script (`scripts/get_refresh_token.py`) with environment variables
4. Copy authorization codes from browser
5. Repeat the process for each Google account

This multi-step manual process is error-prone and creates friction for new users. The README warns that "Initial Authentication Required" but doesn't provide a streamlined path.

## Goals

1. **Simplify initial setup**: Reduce manual file creation and environment variable management
2. **Interactive flow**: Guide users through the authentication process with clear prompts
3. **Multi-account support**: Make it easy to add and manage multiple Google accounts
4. **Better UX**: Provide clear feedback and error messages during setup
5. **Maintain compatibility**: Keep existing authentication mechanisms unchanged

## Non-Goals

- Implementing MCP OAuth 2.1 server (remote HTTP transport)
- Changing the underlying Google OAuth2 flow
- Modifying the credential storage format
- Adding automated credential refresh UI

## Proposed Solution

Create a new `uv run fastmcp-gsuite setup` command that:

1. **Guided credential setup**:
   - Prompts for Google OAuth2 client ID and secret
   - Creates `.gauth.json` automatically
   - Validates the credential format

2. **Interactive account addition**:
   - Prompts for account email and type
   - Opens browser for OAuth authorization
   - Handles the token exchange automatically
   - Saves credentials to `.oauth2.{email}.json`
   - Updates `.accounts.json` with new account info

3. **Account management**:
   - List existing accounts
   - Add new accounts
   - Remove accounts (delete credentials and update `.accounts.json`)

## User Experience

### First-time setup:
```bash
$ uv run fastmcp-gsuite setup

Welcome to fastmcp-gsuite setup!

Step 1: Google OAuth2 Client Credentials
----------------------------------------
You need OAuth2 credentials from Google Cloud Console.
See: https://console.cloud.google.com/apis/credentials

Enter your OAuth2 Client ID: <paste-client-id>
Enter your OAuth2 Client Secret: <paste-secret>

✓ Credentials saved to .gauth.json

Step 2: Add Google Account
---------------------------
Enter account email: alice@example.com
Account type (personal/work): personal
Extra info (optional): Primary account

Opening browser for authorization...
✓ Authorization successful!
✓ Credentials saved for alice@example.com

Add another account? (y/n): n

Setup complete! You can now use fastmcp-gsuite.
```

### Adding additional accounts:
```bash
$ uv run fastmcp-gsuite setup --add-account

Current accounts:
  1. alice@example.com (personal)

Adding new account...
Enter account email: bob@company.com
Account type (personal/work): work
Extra info (optional): Work calendar

Opening browser for authorization...
✓ Authorization successful!
✓ Credentials saved for bob@company.com
```

### Listing accounts:
```bash
$ uv run fastmcp-gsuite setup --list

Configured accounts:
  1. alice@example.com (personal) - ✓ Authenticated
  2. bob@company.com (work) - ✓ Authenticated
```

## Technical Approach

1. **Create new module**: `src/mcp_gsuite/setup_cli.py`
2. **Add CLI entry point**: New command in `pyproject.toml` scripts
3. **Reuse existing auth logic**: Leverage `gauth.py` functions
4. **Interactive prompts**: Use Python's `input()` for simplicity (consider `rich` for better UX in future)
5. **Browser automation**: Use `webbrowser.open()` for authorization URL

## Implementation Phases

### Phase 1: Basic Setup Command (MVP)
- Interactive prompts for client credentials
- Single account setup flow
- Create `.gauth.json` and `.accounts.json`
- Browser-based OAuth flow

### Phase 2: Multi-Account Management
- Add `--add-account` flag
- Add `--list` flag
- Add `--remove-account` flag
- Update existing `.accounts.json` safely

### Phase 3: Enhanced UX (Future)
- Validate credentials before saving
- Test API connectivity after setup
- Provide troubleshooting hints
- Optional: Use `rich` library for better terminal UI

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing workflows | High | Keep existing manual setup method documented and working |
| Browser security restrictions | Medium | Provide manual code entry fallback |
| Multiple package managers (uv, pip) | Low | Document both `uv run` and `python -m` invocations |
| Storing secrets in plain text | Medium | Document that `.gauth.json` should be in `.gitignore` |

## Success Metrics

- Setup time reduced from ~15 minutes to ~5 minutes
- Reduction in setup-related issues/questions
- Positive user feedback on setup experience

## Open Questions

1. Should we validate that required Google APIs are enabled during setup?
2. Should we add a `--reset` flag to clear all credentials?
3. Should we support reading client credentials from environment variables as an alternative?
4. Should we add shell completion for the setup command?

## References

- Current setup process: README.md lines 50-110
- Existing auth script: `scripts/get_refresh_token.py`
- Google OAuth2 flow: `src/mcp_gsuite/gauth.py`
