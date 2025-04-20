# scripts/get_refresh_token.py
import argparse
import base64
import json
import logging
import os
import sys
import urllib.parse

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
# Use core google-auth components
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow  # Use base Flow for exchange

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Configuration ---
# Use full scopes again, as minimal didn't help
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/calendar",
]

# Get required environment variables directly, without dotenv
USER_ID = os.environ.get("GOOGLE_ACCOUNT_EMAIL")  # The email to authorize
CREDENTIALS_DIR = os.environ.get(
    "CREDENTIALS_DIR", "./credentials"
)  # Default to ./credentials if not set

# Redirect URI for Out-Of-Band (manual copy/paste) flow
REDIRECT_URI_OOB = "urn:ietf:wg:oauth:2.0:oob"

# --- End Configuration ---


def get_refresh_token_manual_url(client_secret_file):
    """Manually constructs auth URL and uses Flow to exchange code."""

    if not os.path.exists(client_secret_file):
        logging.error(f"Client secrets file path not found at: {client_secret_file}")
        return
    if not USER_ID:
        logging.error("Missing GOOGLE_ACCOUNT_EMAIL environment variable")
        print(
            "Please set the GOOGLE_ACCOUNT_EMAIL environment variable with your Google email address"
        )
        print("Example: export GOOGLE_ACCOUNT_EMAIL=your.email@gmail.com")
        sys.exit(1)

    # Load client secrets data from file
    try:
        with open(client_secret_file, "r") as f:
            client_config_data = json.load(f)
            # Ensure it's the correct type ('installed' key should exist)
            if "installed" not in client_config_data:
                logging.error(
                    f"Client secrets file {client_secret_file} does not appear to be for an 'installed' application."
                )
                return
            client_id = client_config_data["installed"].get("client_id")
            auth_uri = client_config_data["installed"].get("auth_uri")
            if not client_id or not auth_uri:
                logging.error(
                    "Could not find client_id or auth_uri in client secrets file."
                )
                return

    except Exception as e:
        logging.error(
            f"Failed to load or parse client secrets file ({client_secret_file}): {e}"
        )
        return

    # --- Step 1: Manually construct the Authorization URL ---
    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI_OOB,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Force consent screen for refresh token
        "login_hint": USER_ID,
        # 'state': 'some_random_state_string' # Optional: for CSRF protection if needed
    }
    encoded_params = urllib.parse.urlencode(auth_params)
    manual_auth_url = f"{auth_uri}?{encoded_params}"

    print("--- Manual Auth URL Method ---")
    print("Please go to this URL in your browser and authorize access:")
    print(f"\n{manual_auth_url}\n")
    print(f"Make sure you log in as: {USER_ID}")
    print("After authorization, Google will display a code on the page.")
    auth_code = input("Enter the authorization code shown on the page: ").strip()

    # --- Step 2: Exchange the code for tokens using Flow ---
    try:
        # Use the base Flow class for code exchange, configured from the file
        flow = Flow.from_client_secrets_file(
            client_secret_file,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI_OOB,  # Must match the URI used in the auth request
        )

        # Exchange the authorization code for credentials
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials  # google.oauth2.credentials.Credentials object
        logging.info("Successfully exchanged code for tokens.")

        if not credentials.refresh_token:
            logging.warning(
                "NO REFRESH TOKEN obtained. Check settings or previous grants."
            )

        # --- Step 3: Save the credentials ---
        # The credentials object from google-auth is slightly different
        # but gauth.py expects oauth2client format. We need to convert.
        # OR, preferably, update gauth.py/auth_helper.py to use google-auth credentials directly.
        # For now, let's try saving in the google-auth format first to see if exchange works.
        # Note: This might NOT be compatible with the existing gauth.py!

        # Get client_id/secret again for saving (needed by oauth2client format)
        saved_client_id = client_config_data["installed"].get("client_id")
        saved_client_secret = client_config_data["installed"].get("client_secret")
        token_uri = client_config_data["installed"].get("token_uri")

        # Construct data mimicking oauth2client format as best as possible
        credential_data_oauth2client_like = {
            "refresh_token": credentials.refresh_token,  # Might be None
            "token_uri": token_uri,
            "client_id": saved_client_id,
            "client_secret": saved_client_secret,
            "scopes": credentials.scopes,
            "_module": "oauth2client.client",  # Pretend to be oauth2client
            "_class": "OAuth2Credentials",  # Pretend to be oauth2client
            "access_token": credentials.token,
            "token_expiry": (
                credentials.expiry.isoformat() if credentials.expiry else None
            ),
            # google-auth might have other fields like id_token, token_uri
        }

        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        # Save in the format gauth.py expects
        credential_filename = os.path.join(CREDENTIALS_DIR, f".oauth2.{USER_ID}.json")
        with open(credential_filename, "w") as f:
            json.dump(credential_data_oauth2client_like, f, indent=2)
        logging.info(
            f"Credentials saved in potentially compatible format to: {credential_filename}"
        )
        if credentials.refresh_token:
            logging.info("Refresh token was obtained.")
        else:
            logging.warning("Refresh token was NOT obtained.")

        # --- Step 4: Generate environment variables for the user ---
        # Base64 encode credentials data for secure storage in environment variables
        credentials_json_str = json.dumps(credential_data_oauth2client_like)
        credentials_base64 = base64.b64encode(
            credentials_json_str.encode("utf-8")
        ).decode("utf-8")

        # Display only GSUITE_CREDENTIALS_JSON with double quotes
        print("\n" + "=" * 80)
        print("Authentication credentials generated for E2E tests")
        print("=" * 80)
        print(f'GSUITE_CREDENTIALS_JSON="{credentials_base64}"')
        print("=" * 80)
        print(
            "\nSet the environment variable in your testing environment using your preferred method."
        )
        print(
            "Make sure the following environment variables are available during test execution:"
        )
        print("- GSUITE_CREDENTIALS_JSON (shown above)")
        print("- GOOGLE_ACCOUNT_EMAIL")
        print("- GOOGLE_PROJECT_ID")
        print("- GOOGLE_CLIENT_ID")
        print("- GOOGLE_CLIENT_SECRET")
        print(
            "\nFor example, when running E2E tests, ensure these variables are properly set"
        )
        print("according to your chosen environment configuration method.")
        print("=" * 80)

    except Exception as e:
        logging.error(
            f"An error occurred during code exchange or saving: {e}", exc_info=True
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate OAuth2 credentials for Google APIs"
    )
    parser.add_argument(
        "--client-secret",
        "-c",
        required=True,
        help="Path to the client secret JSON file (downloaded from Google Cloud Console)",
    )
    args = parser.parse_args()

    # Check if required environment variable is set
    if not os.environ.get("GOOGLE_ACCOUNT_EMAIL"):
        print("Error: GOOGLE_ACCOUNT_EMAIL environment variable is not set")
        print("Please set your Google account email as an environment variable:")
        print("  export GOOGLE_ACCOUNT_EMAIL=your.email@gmail.com")
        sys.exit(1)

    # Validate client secret file exists
    if not os.path.exists(args.client_secret):
        print(f"Error: Client secret file not found at {args.client_secret}")
        print("Download the client secret JSON file from Google Cloud Console:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Select your project")
        print("3. Navigate to APIs & Services > Credentials")
        print("4. Create or select an OAuth 2.0 Client ID")
        print("5. Download the JSON file")
        sys.exit(1)

    get_refresh_token_manual_url(args.client_secret)
