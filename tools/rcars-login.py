#!/usr/bin/env python3
"""RCARS API login helper — authenticates via OpenShift OAuth and obtains an API key.

Usage:
    python rcars-login.py --server https://rcars-api.apps.example.com
    python rcars-login.py token     # print current key
    python rcars-login.py status    # show expiry and user

Zero external dependencies — stdlib only.
"""

import argparse
import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

CREDENTIALS_DIR = Path.home() / ".config" / "rcars"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"


def _generate_pkce():
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def _load_credentials():
    if CREDENTIALS_FILE.exists():
        return json.loads(CREDENTIALS_FILE.read_text())
    return None


def _save_credentials(data):
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(data, indent=2))
    os.chmod(CREDENTIALS_FILE, 0o600)


def cmd_login(args):
    server = args.server.rstrip("/")
    oauth_server = args.oauth_server

    if not oauth_server:
        print("Error: --oauth-server is required (e.g., https://oauth-openshift.apps.example.com)")
        sys.exit(1)

    verifier, challenge = _generate_pkce()
    oauth_state = secrets.token_hex(32)
    received_code = {"code": None}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            returned_state = params.get("state", [None])[0]
            if returned_state != oauth_state:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h2>Login failed</h2>"
                                 b"<p>State mismatch — possible CSRF attack.</p></body></html>")
                return
            received_code["code"] = params.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Login successful!</h2>"
                             b"<p>You can close this tab.</p></body></html>")

        def log_message(self, format, *args):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), CallbackHandler)
    port = httpd.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    authorize_url = (
        f"{oauth_server}/oauth/authorize?"
        f"client_id=rcars-api&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"response_type=code&"
        f"code_challenge={challenge}&"
        f"code_challenge_method=S256&"
        f"state={oauth_state}"
    )

    print(f"Opening browser for login...")
    print(f"If browser doesn't open, visit: {authorize_url}")
    webbrowser.open(authorize_url)

    # Wait for callback
    httpd.timeout = 120
    while not received_code["code"]:
        httpd.handle_request()
    httpd.server_close()

    if not received_code["code"]:
        print("Error: no authorization code received (state mismatch or timeout)")
        sys.exit(1)

    # Exchange code for API key
    token_url = f"{server}/api/v1/auth/token"
    payload = json.dumps({
        "code": received_code["code"],
        "code_verifier": verifier,
        "redirect_uri": redirect_uri,
    }).encode()

    req = urllib.request.Request(
        token_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Error: {e.code} — {body}")
        sys.exit(1)

    _save_credentials({
        "server": server,
        "api_key": data["api_key"],
        "expires_at": data["expires_at"],
        "user": data["user"],
    })

    print(f"Logged in as {data['user']}")
    print(f"Key expires: {data['expires_at']}")
    print(f"Credentials saved to {CREDENTIALS_FILE}")


def cmd_token(args):
    creds = _load_credentials()
    if not creds:
        print("Not logged in. Run: python rcars-login.py --server URL --oauth-server URL", file=sys.stderr)
        sys.exit(1)
    print(creds["api_key"])


def cmd_status(args):
    creds = _load_credentials()
    if not creds:
        print("Not logged in.")
        sys.exit(1)
    print(f"Server:  {creds['server']}")
    print(f"User:    {creds['user']}")
    print(f"Expires: {creds['expires_at']}")


def main():
    parser = argparse.ArgumentParser(description="RCARS API login helper")
    sub = parser.add_subparsers(dest="command")

    login_p = sub.add_parser("login", help="Authenticate and obtain an API key")
    login_p.add_argument("--server", required=True, help="RCARS API server URL")
    login_p.add_argument("--oauth-server", required=True, help="OpenShift OAuth server URL")

    sub.add_parser("token", help="Print current API key")
    sub.add_parser("status", help="Show login status")

    # Default to login if --server is provided as a top-level arg
    parser.add_argument("--server", dest="top_server", help=argparse.SUPPRESS)
    parser.add_argument("--oauth-server", dest="top_oauth_server", help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.command == "login":
        cmd_login(args)
    elif args.command == "token":
        cmd_token(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.top_server:
        # Allow: python rcars-login.py --server URL --oauth-server URL
        args.server = args.top_server
        args.oauth_server = args.top_oauth_server
        cmd_login(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
