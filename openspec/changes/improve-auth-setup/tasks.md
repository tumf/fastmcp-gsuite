# Tasks: Improve Authentication Setup Experience

## Phase 1: Basic Setup Command (MVP)

### 1. Create setup CLI module structure
- [x] Create `src/mcp_gsuite/setup_cli.py` with main entry point
- [x] Add `setup` command to `pyproject.toml` scripts section
- [x] Add basic argparse for command-line arguments (`--add-account`, `--list`, `--remove-account`)
- **Validation**: `uv run fastmcp-gsuite-setup --help` displays usage ✓

### 2. Implement client credentials setup
- [x] Add function `setup_client_credentials()` to prompt for client ID/secret
- [x] Validate input format (basic non-empty check)
- [x] Create `.gauth.json` with proper structure
- [x] Handle case where `.gauth.json` already exists (prompt to overwrite)
- **Validation**: Run command, verify `.gauth.json` is created with correct JSON structure ✓

### 3. Implement account information collection
- [x] Add function `collect_account_info()` to prompt for email, type, extra info
- [x] Validate email format (basic regex check)
- [x] Support account type selection (personal/work or free-form)
- **Validation**: Function returns valid `AccountInfo` object ✓

### 4. Implement OAuth authorization flow
- [x] Add function `authorize_account(email, client_credentials)` 
- [x] Generate authorization URL using existing `gauth.get_authorization_url()`
- [x] Open browser with `webbrowser.open()`
- [x] Prompt for authorization code
- [x] Exchange code for credentials using existing `gauth.get_credentials()`
- [x] Save credentials to `.oauth2.{email}.json` using `gauth.store_credentials()`
- **Validation**: Complete flow manually, verify credential file created ✓

### 5. Implement accounts.json management
- [x] Add function `save_account_to_file(account_info)` 
- [x] Read existing `.accounts.json` if present
- [x] Append new account (avoid duplicates by email)
- [x] Write updated JSON with proper formatting
- **Validation**: Run setup, verify `.accounts.json` contains correct account list ✓

### 6. Implement main setup flow
- [x] Integrate all steps into `main()` function
- [x] Add error handling for each step
- [x] Provide clear success/failure messages
- [x] Add option to skip client credentials if `.gauth.json` exists
- **Validation**: Complete end-to-end setup for one account ✓

### 7. Add documentation
- [x] Update README.md with new setup command
- [x] Add troubleshooting section for common errors
- [x] Document fallback to manual setup method
- [x] Add examples for different scenarios
- **Validation**: Follow README instructions to complete setup ✓

### 8. Add tests
- [x] Unit tests for `collect_account_info()` validation
- [x] Unit tests for `.accounts.json` file management
- [x] Unit tests for `.gauth.json` creation
- [x] Mock tests for authorization flow
- **Validation**: `make test` passes with new tests ✓

## Phase 2: Multi-Account Management

### 9. Implement --add-account flag
- [x] Add argparse argument `--add-account`
- [x] Skip client credentials step if `.gauth.json` exists
- [x] Run only account addition flow
- [x] Append to existing `.accounts.json`
- **Validation**: Add second account, verify both in `.accounts.json` ✓

### 10. Implement --list flag
- [x] Add argparse argument `--list`
- [x] Read `.accounts.json` and display accounts
- [x] Check for credential file existence for each account
- [x] Show authentication status (✓ Authenticated / ✗ Missing credentials)
- **Validation**: List command shows all accounts with correct status ✓

### 11. Implement --remove-account flag
- [x] Add argparse argument `--remove-account <email>`
- [x] Prompt for confirmation
- [x] Remove account from `.accounts.json`
- [x] Delete `.oauth2.{email}.json` file
- [x] Handle case where account doesn't exist
- **Validation**: Remove account, verify files deleted and JSON updated ✓

### 12. Add account management tests
- [x] Test adding multiple accounts
- [x] Test removing accounts
- [x] Test listing accounts
- [x] Test duplicate email handling
- **Validation**: All account management tests pass ✓

## Phase 3: Enhanced UX (Future - Optional)

### 13. Add credential validation
- [ ] Test OAuth credentials before saving
- [ ] Make test API call to verify scopes
- [ ] Provide helpful error messages for common issues
- **Validation**: Invalid credentials rejected with clear error

### 14. Improve terminal UI
- [ ] Consider adding `rich` library for better formatting
- [ ] Add progress indicators for long operations
- [ ] Add colored output for success/error messages
- **Validation**: Setup looks professional in terminal

### 15. Add environment variable support
- [ ] Support `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` env vars
- [ ] Use env vars as defaults if present
- [ ] Document env var usage
- **Validation**: Setup works with env vars set

## Dependencies

- Tasks 1-6 must be completed sequentially (each builds on previous)
- Task 7 (documentation) can be done in parallel after task 6
- Task 8 (tests) should follow task 6
- Phase 2 tasks require Phase 1 completion
- Phase 3 tasks are independent enhancements

## Estimated Effort

- Phase 1 (MVP): 1-2 days
- Phase 2 (Multi-account): 0.5-1 day  
- Phase 3 (Enhanced UX): 0.5-1 day (optional)

Total: 2-4 days depending on scope
