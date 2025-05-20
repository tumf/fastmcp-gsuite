"""
HTTP server for OAuth2 authentication following MCP specification.
"""

import base64
import hashlib
import json
import logging
import secrets
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from google_auth_oauthlib.flow import Flow

from .settings import settings

METADATA_ENDPOINT = "/.well-known/oauth-authorization-server"
REDIRECT_URI = "http://localhost:4100/code"
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]

code_verifiers: dict[str, str] = {}


class OAuth2Handler(BaseHTTPRequestHandler):
    """Handler for OAuth2 endpoints."""

    def _send_json_response(self, data: dict[str, Any], status: int = 200) -> None:
        """Send a JSON response with the given status code."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests for metadata discovery and code callback."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == METADATA_ENDPOINT:
            metadata = {
                "issuer": "http://localhost:4100",
                "authorization_endpoint": "https://accounts.google.com/o/oauth2/auth",
                "token_endpoint": "https://oauth2.googleapis.com/token",
                "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "refresh_token"],
                "code_challenge_methods_supported": ["S256"],
                "scopes_supported": SCOPES,
            }
            self._send_json_response(metadata)
            return

        if parsed_path.path == "/code":
            query = parse_qs(parsed_path.query)
            if "code" in query and "state" in query:
                auth_code = query["code"][0]
                state = query["state"][0]

                code_verifier = code_verifiers.get(state)
                if not code_verifier:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Invalid state parameter")
                    return

                try:
                    credentials = exchange_code_with_pkce(auth_code, code_verifier)

                    user_info = get_user_info(credentials)
                    email = user_info.get("email", "")

                    from .gauth import store_credentials_secure

                    store_credentials_secure(credentials, email)

                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"Authentication successful! You can close this window.")

                    code_verifiers.pop(state, None)

                except Exception as e:
                    logging.error(f"Error exchanging code: {e}")
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(f"Authentication error: {e!s}".encode())
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code or state parameter")
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")


def generate_pkce_params() -> tuple[str, str, str]:
    """
    Generate PKCE parameters for OAuth 2.1.

    Returns:
        tuple: (code_verifier, code_challenge, state)
    """
    code_verifier = secrets.token_urlsafe(64)

    code_challenge_digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge_digest).decode().rstrip("=")

    state = secrets.token_urlsafe(32)

    code_verifiers[state] = code_verifier

    return code_verifier, code_challenge, state


def get_authorization_url(email_address: str) -> str:
    """
    Construct an authorization URL with PKCE support.

    Args:
        email_address: User's email address

    Returns:
        str: Authorization URL
    """
    _, code_challenge, state = generate_pkce_params()

    client_config = get_client_config()

    auth_params = {
        "client_id": client_config["web"]["client_id"],
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Force consent screen for refresh token
        "login_hint": email_address,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }

    from urllib.parse import urlencode

    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    auth_url = f"{auth_uri}?{urlencode(auth_params)}"

    return auth_url


def get_client_config() -> dict[str, Any]:
    """
    Get client configuration from the Google auth file.

    Returns:
        Dict: Client configuration
    """
    auth_file = settings.absolute_gauth_file
    with open(auth_file) as f:
        return json.load(f)


def exchange_code_with_pkce(auth_code: str, code_verifier: str) -> Any:
    """
    Exchange authorization code for tokens using PKCE.

    Args:
        auth_code: Authorization code from OAuth callback
        code_verifier: Code verifier for PKCE

    Returns:
        google.oauth2.credentials.Credentials: OAuth credentials
    """
    client_config = get_client_config()

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    flow.fetch_token(
        code=auth_code,
        code_verifier=code_verifier,
    )

    return flow.credentials


def get_user_info(credentials) -> dict[str, Any]:
    """
    Get user information using OAuth credentials.

    Args:
        credentials: OAuth credentials

    Returns:
        Dict: User information
    """
    userinfo_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo"

    response = requests.get(
        userinfo_endpoint,
        headers={"Authorization": f"Bearer {credentials.token}"},
    )

    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Error getting user info: {response.text}")
        raise Exception(f"Failed to get user info: {response.status_code}")


def start_auth_server(port: int = 4100) -> threading.Thread:
    """
    Start the OAuth2 HTTP server in a separate thread.

    Args:
        port: Port to listen on

    Returns:
        threading.Thread: Server thread
    """
    server = HTTPServer(("localhost", port), OAuth2Handler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    logging.info(f"Started OAuth2 server on port {port}")
    return server_thread
