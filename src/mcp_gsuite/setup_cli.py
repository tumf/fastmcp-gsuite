"""Interactive setup CLI for fastmcp-gsuite authentication."""

import argparse
import json
import logging
import os
import sys
import webbrowser

from . import gauth
from .settings import settings

logger = logging.getLogger(__name__)


def setup_client_credentials() -> dict[str, str]:
    """Prompt for Google OAuth2 client credentials and create .gauth.json.

    Returns:
        Dictionary containing client_id and client_secret
    """
    print("\nStep 1: Google OAuth2 Client Credentials")
    print("-" * 50)
    print("You need OAuth2 credentials from Google Cloud Console.")
    print("See: https://console.cloud.google.com/apis/credentials")
    print()
    print("IMPORTANT: Select 'Desktop app' as the application type.")
    print("(You can also paste the client_secrets JSON file content if you prefer)")
    print()

    while True:
        client_id = input("Enter your OAuth2 Client ID: ").strip()
        if client_id:
            break
        print("Error: Client ID cannot be empty. Please try again.")

    while True:
        client_secret = input("Enter your OAuth2 Client Secret: ").strip()
        if client_secret:
            break
        print("Error: Client Secret cannot be empty. Please try again.")

    # Create .gauth.json structure
    # Using "installed" type for desktop/CLI applications (Google Cloud Console standard)
    # Note: oauth2client supports both "web" and "installed" formats
    gauth_data = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    gauth_file = settings.absolute_gauth_file
    with open(gauth_file, "w") as f:
        json.dump(gauth_data, f, indent=2)

    print(f"\n✓ Credentials saved to {gauth_file}")

    return {"client_id": client_id, "client_secret": client_secret}


def collect_account_info(email: str | None = None) -> gauth.AccountInfo:
    """Collect account information from user input.

    Args:
        email: Optional email address (skips email prompt if provided)

    Returns:
        AccountInfo object with email, account_type, and extra_info
    """
    print("\nStep 2: Add Google Account")
    print("-" * 50)

    # Validate email format
    if email:
        if "@" not in email or len(email) <= 3:
            print(f"Error: Invalid email format: {email}")
            raise ValueError(f"Invalid email format: {email}")
        print(f"Email: {email}")
    else:
        while True:
            email = input("Enter account email: ").strip()
            if "@" in email and len(email) > 3:
                break
            print("Error: Invalid email format. Please enter a valid email address.")

    account_type = input("Account type (personal/work): ").strip() or "personal"
    extra_info = input("Extra info (optional): ").strip()

    return gauth.AccountInfo(
        email=email, account_type=account_type, extra_info=extra_info
    )


def authorize_account(account_info: gauth.AccountInfo) -> bool:
    """Guide user through OAuth authorization flow.

    Args:
        account_info: Account information including email

    Returns:
        True if authorization successful, False otherwise
    """
    email = account_info.email
    state = "setup_cli_state"

    try:
        # Generate authorization URL
        auth_url = gauth.get_authorization_url(email, state)

        print("\nOpening browser for authorization...")
        print("If browser doesn't open, visit this URL:")
        print(f"\n{auth_url}\n")

        # Try to open browser
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            logger.warning(f"Could not open browser automatically: {e}")
            print("Please open the URL manually in your browser.")

        # Prompt for authorization code
        auth_code = input("\nEnter the authorization code: ").strip()

        if not auth_code:
            print("Error: Authorization code cannot be empty.")
            return False

        # Exchange code for credentials
        credentials = gauth.get_credentials(auth_code, state)

        # Store credentials
        gauth.store_credentials(credentials, email)

        print("✓ Authorization successful!")
        print(f"✓ Credentials saved for {email}")

        return True

    except gauth.CodeExchangeError as e:
        print("\nError: Authorization failed during code exchange.")
        print("Please try again or check your authorization code.")
        logger.error(f"Code exchange error for {email}: {e}")
        return False
    except gauth.NoRefreshTokenError as e:
        print("\nError: No refresh token received.")
        print("This may happen if you've already authorized this app.")
        print("Try revoking access at https://myaccount.google.com/permissions")
        logger.error(f"No refresh token for {email}: {e}")
        return False
    except Exception as e:
        print(f"\nError: An unexpected error occurred: {e}")
        logger.error(f"Authorization error for {email}: {e}", exc_info=True)
        return False


def save_account_to_file(account_info: gauth.AccountInfo) -> bool:
    """Save account information to .accounts.json.

    Args:
        account_info: Account information to save

    Returns:
        True if successful, False otherwise
    """
    accounts_file = settings.absolute_accounts_file

    try:
        # Read existing accounts if file exists
        if os.path.exists(accounts_file):
            with open(accounts_file) as f:
                data = json.load(f)
                accounts = data.get("accounts", [])
        else:
            accounts = []

        # Check for duplicates
        account_dict = account_info.model_dump()
        for existing in accounts:
            if existing.get("email") == account_info.email:
                print(
                    f"\nAccount {account_info.email} already exists in {accounts_file}"
                )
                overwrite = input("Overwrite? (y/n): ").strip().lower()
                if overwrite == "y":
                    accounts.remove(existing)
                    break
                else:
                    return False

        # Append new account
        accounts.append(account_dict)

        # Write back to file
        with open(accounts_file, "w") as f:
            json.dump({"accounts": accounts}, f, indent=2)

        logger.info(f"Account {account_info.email} saved to {accounts_file}")
        return True

    except Exception as e:
        print(f"\nError: Could not save account to {accounts_file}: {e}")
        logger.error(f"Error saving account: {e}", exc_info=True)
        return False


def list_accounts() -> None:
    """List all configured accounts with their authentication status."""
    accounts_file = settings.absolute_accounts_file

    if not os.path.exists(accounts_file):
        print("\nNo accounts configured.")
        return

    try:
        with open(accounts_file) as f:
            data = json.load(f)
            accounts = data.get("accounts", [])

        if not accounts:
            print("\nNo accounts configured.")
            return

        print("\nConfigured accounts:")
        for i, acc in enumerate(accounts, 1):
            email = acc.get("email", "unknown")
            acc_type = acc.get("account_type", "unknown")

            # Check if credentials exist
            cred_file = os.path.join(
                settings.absolute_credentials_dir, f".oauth2.{email}.json"
            )
            status = (
                "✓ Authenticated"
                if os.path.exists(cred_file)
                else "✗ Missing credentials"
            )

            print(f"  {i}. {email} ({acc_type}) - {status}")

    except Exception as e:
        print(f"\nError reading accounts: {e}")
        logger.error(f"Error listing accounts: {e}", exc_info=True)


def remove_account(email: str) -> bool:
    """Remove an account and its credentials.

    Args:
        email: Email address of account to remove

    Returns:
        True if successful, False otherwise
    """
    accounts_file = settings.absolute_accounts_file

    if not os.path.exists(accounts_file):
        print(f"\nError: No accounts file found at {accounts_file}")
        return False

    try:
        # Read existing accounts
        with open(accounts_file) as f:
            data = json.load(f)
            accounts = data.get("accounts", [])

        # Find account
        found = False
        for acc in accounts:
            if acc.get("email") == email:
                found = True
                break

        if not found:
            print(f"\nError: Account not found: {email}")
            return False

        # Confirm removal
        confirm = input(f"\nRemove {email}? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return False

        # Remove from accounts list
        accounts = [acc for acc in accounts if acc.get("email") != email]

        # Write back
        with open(accounts_file, "w") as f:
            json.dump({"accounts": accounts}, f, indent=2)

        # Delete credential file
        cred_file = os.path.join(
            settings.absolute_credentials_dir, f".oauth2.{email}.json"
        )
        if os.path.exists(cred_file):
            os.remove(cred_file)

        print(f"✓ Account {email} removed")
        return True

    except Exception as e:
        print(f"\nError removing account: {e}")
        logger.error(f"Error removing account {email}: {e}", exc_info=True)
        return False


def run_setup(add_account: bool = False, email: str | None = None) -> int:
    """Run the interactive setup flow.

    Args:
        add_account: If True, skip client credentials and only add account
        email: Optional email address to use (skips email prompt)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    print("\nWelcome to fastmcp-gsuite setup!")

    # Check if .gauth.json exists
    gauth_file = settings.absolute_gauth_file
    gauth_exists = os.path.exists(gauth_file)

    if not add_account and not gauth_exists:
        # First-time setup: need client credentials
        try:
            setup_client_credentials()
        except KeyboardInterrupt:
            print("\n\nSetup cancelled.")
            return 130
        except Exception as e:
            print(f"\nError during client credentials setup: {e}")
            return 1
    elif gauth_exists:
        if not add_account:
            print(f"\nUsing existing client credentials from {gauth_file}")
    else:
        print(f"\nError: Client credentials not found at {gauth_file}")
        print("Please run setup without --add-account first.")
        return 1

    # Account setup loop
    while True:
        try:
            # Collect account info
            account_info = collect_account_info(email=email)

            # Authorize account
            if authorize_account(account_info):
                # Save to accounts.json
                if save_account_to_file(account_info):
                    print()
                else:
                    print(
                        "\nWarning: Account authorized but not saved to accounts file."
                    )
            else:
                print("\nAuthorization failed. Please try again.")
                retry = input("Retry? (y/n): ").strip().lower()
                if retry != "y":
                    break
                continue

            # Ask if user wants to add another account
            if not add_account:
                another = input("\nAdd another account? (y/n): ").strip().lower()
                if another != "y":
                    break
            else:
                # In add-account mode, only add one account
                break

        except KeyboardInterrupt:
            print("\n\nSetup cancelled.")
            return 130
        except Exception as e:
            print(f"\nError during account setup: {e}")
            logger.error(f"Account setup error: {e}", exc_info=True)
            return 1

    print("\nSetup complete! You can now use fastmcp-gsuite.")
    print("Run: uv run python -m mcp_gsuite.fast_server")
    return 0


def main() -> int:
    """Main entry point for setup CLI."""
    parser = argparse.ArgumentParser(
        description="Interactive setup for fastmcp-gsuite authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First-time setup
  uv run fastmcp-gsuite-setup

  # Add another account (interactive)
  uv run fastmcp-gsuite-setup --add-account

  # Add account with email specified
  uv run fastmcp-gsuite-setup --add-account user@example.com

  # List configured accounts
  uv run fastmcp-gsuite-setup --list

  # Remove an account
  uv run fastmcp-gsuite-setup --remove-account user@example.com
""",
    )

    parser.add_argument(
        "--add-account",
        nargs="?",
        const=True,
        default=False,
        metavar="EMAIL",
        help="Add a new account (optionally specify email address)",
    )

    parser.add_argument(
        "--list", action="store_true", help="List all configured accounts"
    )

    parser.add_argument(
        "--remove-account", metavar="EMAIL", help="Remove an account by email address"
    )

    args = parser.parse_args()

    # Handle different modes
    if args.list:
        list_accounts()
        return 0

    if args.remove_account:
        return 0 if remove_account(args.remove_account) else 1

    # Determine email if provided via --add-account
    email = None
    add_account_mode = False
    if args.add_account is True:
        add_account_mode = True
    elif args.add_account:
        add_account_mode = True
        email = args.add_account

    # Run setup (either full setup or add-account)
    return run_setup(add_account=add_account_mode, email=email)


if __name__ == "__main__":
    sys.exit(main())
