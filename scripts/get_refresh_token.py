# scripts/get_refresh_token.py
import argparse
import base64
import json
import logging
import os
import sys
import urllib.parse

# Use core google-auth components
from google_auth_oauthlib.flow import Flow  # Use base Flow for exchange

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Configuration ---
# Use full scopes again, as minimal didn't help
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]

# Get required environment variables directly, without dotenv
USER_ID = os.environ.get("GOOGLE_ACCOUNT_EMAIL")  # The email to authorize
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
CREDENTIALS_DIR = os.environ.get("CREDENTIALS_DIR", "./credentials")  # Default to ./credentials if not set

# Redirect URI for Out-Of-Band (manual copy/paste) flow
REDIRECT_URI_OOB = "urn:ietf:wg:oauth:2.0:oob"

# --- End Configuration ---


def get_refresh_token_manual_url():
    """Manually constructs auth URL and uses Flow to exchange code."""

    if not all([USER_ID, CLIENT_ID, CLIENT_SECRET]):
        missing_vars = []
        if not USER_ID:
            missing_vars.append("GOOGLE_ACCOUNT_EMAIL")
        if not CLIENT_ID:
            missing_vars.append("GOOGLE_CLIENT_ID")
        if not CLIENT_SECRET:
            missing_vars.append("GOOGLE_CLIENT_SECRET")

        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        print(f"Please set the following environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    # --- Step 1: Manually construct the Authorization URL ---
    auth_params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI_OOB,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Force consent screen for refresh token
        "login_hint": USER_ID,
        # 'state': 'some_random_state_string' # Optional: for CSRF protection if needed
    }
    encoded_params = urllib.parse.urlencode(auth_params)
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    manual_auth_url = f"{auth_uri}?{encoded_params}"

    print("--- Manual Auth URL Method ---")
    print("Please go to this URL in your browser and authorize access:")
    print(f"\n{manual_auth_url}\n")
    print(f"Make sure you log in as: {USER_ID}")
    print("After authorization, Google will display a code on the page.")
    auth_code = input("Enter the authorization code shown on the page: ").strip()

    # --- Step 2: Exchange the code for tokens using Flow ---
    try:
        # Create a client config dictionary from environment variables
        client_config = {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI_OOB],
            }
        }

        # Use the Flow class with client config
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI_OOB,  # Must match the URI used in the auth request
        )

        # Exchange the authorization code for credentials
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials  # google.oauth2.credentials.Credentials object
        logging.info("Successfully exchanged code for tokens.")

        if not credentials.refresh_token:
            logging.warning("NO REFRESH TOKEN obtained. Check settings or previous grants.")

        # --- Step 3: Save the credentials ---
        # The credentials object from google-auth is slightly different
        # but gauth.py expects oauth2client format. We need to convert.
        # OR, preferably, update gauth.py/auth_helper.py to use google-auth credentials directly.
        # For now, let's try saving in the google-auth format first to see if exchange works.
        # Note: This might NOT be compatible with the existing gauth.py!

        # Construct data mimicking oauth2client format as best as possible
        credential_data_oauth2client_like = {
            "refresh_token": credentials.refresh_token,  # Might be None
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scopes": credentials.scopes,
            "_module": "oauth2client.client",  # Pretend to be oauth2client
            "_class": "OAuth2Credentials",  # Pretend to be oauth2client
            "access_token": credentials.token,
            "token_expiry": (credentials.expiry.isoformat() if credentials.expiry else None),
            # google-auth might have other fields like id_token, token_uri
        }

        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        # Save in the format gauth.py expects
        credential_filename = os.path.join(CREDENTIALS_DIR, f".oauth2.{USER_ID}.json")
        with open(credential_filename, "w") as f:
            json.dump(credential_data_oauth2client_like, f, indent=2)
        logging.info(f"Credentials saved in potentially compatible format to: {credential_filename}")
        if credentials.refresh_token:
            logging.info("Refresh token was obtained.")
        else:
            logging.warning("Refresh token was NOT obtained.")

        # --- Step 4: Generate environment variables for the user ---
        # Base64 encode credentials data for secure storage in environment variables
        credentials_json_str = json.dumps(credential_data_oauth2client_like)
        credentials_base64 = base64.b64encode(credentials_json_str.encode("utf-8")).decode("utf-8")

        # Display only GSUITE_CREDENTIALS_JSON with double quotes
        print("\n" + "=" * 80)
        print("Authentication credentials generated for E2E tests")
        print("=" * 80)
        print(f'GSUITE_CREDENTIALS_JSON="{credentials_base64}"')
        print("=" * 80)
        print("\nSet the environment variable in your testing environment using your preferred method.")
        print("Make sure the following environment variables are available during test execution:")
        print("- GSUITE_CREDENTIALS_JSON (shown above)")
        print("- GOOGLE_ACCOUNT_EMAIL")
        print("- GOOGLE_PROJECT_ID")
        print("- GOOGLE_CLIENT_ID")
        print("- GOOGLE_CLIENT_SECRET")
        print("\nFor example, when running E2E tests, ensure these variables are properly set")
        print("according to your chosen environment configuration method.")
        print("=" * 80)

    except Exception as e:
        logging.error(f"An error occurred during code exchange or saving: {e}", exc_info=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate OAuth2 credentials for Google APIs")
    args = parser.parse_args()

    # Check if required environment variables are set
    missing_vars = []
    for env_var in ["GOOGLE_ACCOUNT_EMAIL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]:
        if not os.environ.get(env_var):
            missing_vars.append(env_var)

    if missing_vars:
        print(f"Error: The following environment variables are not set: {', '.join(missing_vars)}")
        print("Please set them before running this script.")
        sys.exit(1)

    get_refresh_token_manual_url()
