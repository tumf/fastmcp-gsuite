import base64
import hashlib
import json
import logging
import os
import secrets

import pydantic
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

# import argparse # Replaced by settings
from .settings import settings

# def get_gauth_file() -> str: # Replaced by settings
#     parser = argparse.ArgumentParser()
#     parser.add_argument(
#         "--gauth-file",
#         type=str,
#         default="./.gauth.json",
#         help="Path to client secrets file",
#     )
#     args, _ = parser.parse_known_args()
#     return args.gauth_file


CLIENTSECRETS_LOCATION = settings.absolute_gauth_file

REDIRECT_URI = "http://localhost:4100/code"
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]


class AccountInfo(pydantic.BaseModel):
    email: str
    account_type: str
    extra_info: str

    def __init__(self, email: str, account_type: str, extra_info: str = ""):
        super().__init__(email=email, account_type=account_type, extra_info=extra_info)

    def to_description(self):
        return f"""Account for email: {self.email} of type: {self.account_type}. Extra info for: {self.extra_info}"""


# def get_accounts_file() -> str: # Replaced by settings
#     parser = argparse.ArgumentParser()
#     parser.add_argument(
#         "--accounts-file",
#         type=str,
#         default="./.accounts.json",
#         help="Path to accounts configuration file",
#     )
#     args, _ = parser.parse_known_args()
#     return args.accounts_file


def get_account_info() -> list[AccountInfo]:
    accounts_file = settings.absolute_accounts_file
    if not os.path.exists(accounts_file):
        logging.error(f"Accounts file not found at: {accounts_file}")
        return []
    with open(accounts_file) as f:
        data = json.load(f)
        accounts = data.get("accounts", [])
        return [AccountInfo.model_validate(acc) for acc in accounts]


class GetCredentialsError(Exception):
    """Error raised when an error occurred while retrieving credentials.

    Attributes:
      authorization_url: Authorization URL to redirect the user to in order to
                         request offline access.
    """

    def __init__(self, authorization_url):
        """Construct a GetCredentialsError."""
        self.authorization_url = authorization_url


class CodeExchangeError(GetCredentialsError):
    """Error raised when a code exchange has failed."""


class NoRefreshTokenError(GetCredentialsError):
    """Error raised when no refresh token has been found."""


class NoUserIdError(Exception):
    """Error raised when no user ID could be retrieved."""


# def get_credentials_dir() -> str: # Replaced by settings
#     parser = argparse.ArgumentParser()
#     parser.add_argument(
#         "--credentials-dir",
#         type=str,
#         default=".",
#         help="Directory to store OAuth2 credentials",
#     )
#     args, _ = parser.parse_known_args()
#     return args.credentials_dir


def _get_credential_filename(user_id: str) -> str:
    creds_dir = settings.absolute_credentials_dir
    return os.path.join(creds_dir, f".oauth2.{user_id}.json")


def get_stored_credentials(user_id: str) -> Credentials | None:
    """Retrieved stored credentials for the provided user ID.

    Args:
    user_id: User's ID.
    Returns:
    Stored google.oauth2.credentials.Credentials if found, None otherwise.
    """
    try:
        cred_file_path = _get_credential_filename(user_id=user_id)
        if not os.path.exists(cred_file_path):
            logging.warning(f"No stored Oauth2 credentials yet at path: {cred_file_path}")
            return None

        with open(cred_file_path) as f:
            cred_data = json.load(f)
            return Credentials(
                token=cred_data.get("token"),
                refresh_token=cred_data.get("refresh_token"),
                token_uri=cred_data.get("token_uri"),
                client_id=cred_data.get("client_id"),
                client_secret=cred_data.get("client_secret"),
                scopes=cred_data.get("scopes"),
            )
    except Exception as e:
        logging.error(e)
        return None


def store_credentials(credentials: Credentials, user_id: str):
    """Store OAuth 2.0 credentials in the specified directory."""
    cred_file_path = _get_credential_filename(user_id=user_id)
    os.makedirs(os.path.dirname(cred_file_path), exist_ok=True)

    cred_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    with open(cred_file_path, "w") as f:
        json.dump(cred_data, f, indent=2)


def store_credentials_secure(credentials: Credentials, user_id: str):
    """
    Store OAuth 2.0 credentials securely.

    Args:
        credentials: OAuth 2.0 credentials from google.oauth2.credentials.Credentials
        user_id: User ID (email)
    """
    cred_file_path = _get_credential_filename(user_id=user_id)
    os.makedirs(os.path.dirname(cred_file_path), exist_ok=True)

    cred_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    with open(cred_file_path, "w") as f:
        json.dump(cred_data, f, indent=2)

    cred_json = json.dumps(cred_data)
    cred_b64 = base64.b64encode(cred_json.encode()).decode()

    # Log a message about the secure storage (but don't log the actual credentials)
    logging.info(f"Securely stored credentials for {user_id}")

    return cred_b64


def exchange_code(authorization_code, code_verifier=None):
    """Exchange an authorization code for OAuth 2.0 credentials with PKCE.

    Args:
        authorization_code: Authorization code to exchange for OAuth 2.0 credentials
        code_verifier: PKCE code verifier (if available)

    Returns:
        google.oauth2.credentials.Credentials instance

    Raises:
        CodeExchangeError: an error occurred
    """
    try:
        with open(CLIENTSECRETS_LOCATION) as f:
            client_config = json.load(f)

        flow = Flow.from_client_config(
            client_config=client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        # Exchange authorization code for credentials
        kwargs = {"code": authorization_code}
        if code_verifier:
            kwargs["code_verifier"] = code_verifier

        flow.fetch_token(**kwargs)
        return flow.credentials
    except Exception as error:
        logging.error("An error occurred: %s", error)
        raise CodeExchangeError(None) from error


def get_user_info(credentials):
    """Send a request to the UserInfo API to retrieve the user's information.

    Args:
    credentials: google.oauth2.credentials.Credentials instance to authorize the
                    request.
    Returns:
    User information as a dict.
    """
    userinfo_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo"
    response = requests.get(
        userinfo_endpoint,
        headers={"Authorization": f"Bearer {credentials.token}"},
    )

    if response.status_code == 200:
        user_info = response.json()
        if user_info and user_info.get("sub"):  # OAuth 2.0 uses 'sub' as the ID
            return user_info
    else:
        logging.error(f"Error getting user info: {response.text}")

    raise NoUserIdError()


def get_authorization_url(email_address, state=None):
    """Retrieve the authorization URL.

    Args:
    email_address: User's e-mail address.
    state: State for the authorization URL. Optional.
    Returns:
    Authorization URL to redirect the user to.
    """
    with open(CLIENTSECRETS_LOCATION) as f:
        client_config = json.load(f)

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    kwargs = {
        "access_type": "offline",
        "prompt": "consent",
        "login_hint": email_address,
        "include_granted_scopes": "true",
    }

    if state:
        kwargs["state"] = state

    auth_url, _ = flow.authorization_url(**kwargs)
    return auth_url


def generate_pkce_params():
    """
    Generate PKCE parameters for OAuth 2.1.

    Returns:
        tuple: (code_verifier, code_challenge, state)
    """

    code_verifier = secrets.token_urlsafe(64)

    code_challenge_digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge_digest).decode().rstrip("=")

    state = secrets.token_urlsafe(32)

    return code_verifier, code_challenge, state


def get_authorization_url_with_pkce(email_address):
    """
    Retrieve the authorization URL with PKCE support.

    Args:
        email_address: User's e-mail address

    Returns:
        Tuple of (authorization_url, code_verifier, state)
    """
    code_verifier, code_challenge, state = generate_pkce_params()

    with open(CLIENTSECRETS_LOCATION) as f:
        client_config = json.load(f)

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    flow.authorization_url_kwargs.update(
        {
            "access_type": "offline",
            "approval_prompt": "force",
            "login_hint": email_address,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )

    auth_url, _ = flow.authorization_url()
    return auth_url, code_verifier, state


def get_credentials(authorization_code, state, code_verifier=None):
    """Retrieve credentials using the provided authorization code.

    This function exchanges the authorization code for an access token and queries
    the UserInfo API to retrieve the user's e-mail address.
    If a refresh token has been retrieved along with an access token, it is stored
    in the application database using the user's e-mail address as key.
    If no refresh token has been retrieved, the function checks in the application
    database for one and returns it if found or raises a NoRefreshTokenError
    with the authorization URL to redirect the user to.

    Args:
    authorization_code: Authorization code to use to retrieve an access token.
    state: State to set to the authorization URL in case of error.
    code_verifier: PKCE code verifier (if available)
    Returns:
    google.oauth2.credentials.Credentials instance containing an access and
    refresh token.
    Raises:
    CodeExchangeError: Could not exchange the authorization code.
    NoRefreshTokenError: No refresh token could be retrieved from the
                                available sources.
    """
    email_address = ""
    try:
        credentials = exchange_code(authorization_code, code_verifier)
        user_info = get_user_info(credentials)

        email_address = user_info.get("email")

        logging.debug(f"user_info: {json.dumps(user_info)}")

        if credentials.refresh_token is not None:
            store_credentials(credentials, user_id=email_address)
            return credentials
        else:
            credentials = get_stored_credentials(user_id=email_address)
            if credentials and credentials.refresh_token is not None:
                return credentials
    except CodeExchangeError as error:
        logging.error("An error occurred during code exchange.")
        # If none is available, redirect the user to the authorization URL.
        error.authorization_url = get_authorization_url(email_address, state)
        raise error
    except NoUserIdError:
        logging.error("No user ID could be retrieved.")

    # No refresh token has been retrieved.
    authorization_url = get_authorization_url(email_address, state)
    raise NoRefreshTokenError(authorization_url)
