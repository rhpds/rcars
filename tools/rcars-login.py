#!/usr/bin/env python3
"""RCARS API login helper — authenticates via OpenShift OAuth and obtains an API key.

Usage:
    python rcars-login.py --server URL --oauth-server URL
    python rcars-login.py token     # print current key
    python rcars-login.py status    # show expiry and user

Zero external dependencies — stdlib only.
"""

import argparse
import http.server
import json
import os
import secrets
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

CREDENTIALS_DIR = Path.home() / ".config" / "rcars"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"

# The implicit grant puts the access_token in the URL fragment (#access_token=...).
# Browsers never send fragments to the server, so we serve a tiny HTML page
# with JS that reads the fragment and redirects it as a query parameter.
CALLBACK_HTML = b"""<!DOCTYPE html><html><body>
<h2>Completing login...</h2>
<script>
var h = window.location.hash.substring(1);
var p = new URLSearchParams(h);
var t = p.get("access_token");
var s = p.get("state");
if (t && s) {
    window.location = "/complete?access_token=" + encodeURIComponent(t) + "&state=" + encodeURIComponent(s);
} else {
    document.body.innerHTML = "<h2>Login failed</h2><p>No access token received.</p>";
}
</script>
</body></html>"""


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
        print("Error: --oauth-server is required")
        sys.exit(1)

    oauth_state = secrets.token_hex(32)
    received_token = {"access_token": None}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)

            if parsed.path == "/callback":
                # First hit: browser arrives with fragment. Serve JS to extract it.
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(CALLBACK_HTML)
                return

            if parsed.path == "/complete":
                # Second hit: JS redirected with access_token as query param.
                params = urllib.parse.parse_qs(parsed.query)
                token = params.get("access_token", [None])[0]
                state = params.get("state", [None])[0]
                if token and state == oauth_state:
                    received_token["access_token"] = token
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h2>Login successful!</h2>"
                                     b"<p>You can close this tab.</p></body></html>")
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h2>Login failed</h2>"
                                     b"<p>Invalid state or no access token received.</p></body></html>")
                return

            self.send_response(404)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), CallbackHandler)
    port = httpd.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    authorize_url = (
        f"{oauth_server}/oauth/authorize?"
        f"client_id={args.client_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"response_type=token&"
        f"state={oauth_state}"
    )

    print("Opening browser for login...")
    print(f"If browser doesn't open, visit:\n  {authorize_url}")
    webbrowser.open(authorize_url)

    httpd.timeout = 120
    deadline = time.time() + 120
    while not received_token["access_token"] and time.time() < deadline:
        httpd.handle_request()
    httpd.server_close()

    if not received_token["access_token"]:
        print("Error: no access token received")
        sys.exit(1)

    # Exchange the OAuth access token for an RCARS API key
    token_url = f"{server}/api/v1/auth/token"
    payload = json.dumps({"access_token": received_token["access_token"]}).encode()

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
        print(f"Error: {e.code} - {body}")
        sys.exit(1)

    _save_credentials({
        "server": server,
        "api_key": data["api_key"],
        "expires_at": data["expires_at"],
        "user": data["user"],
    })

    print(f"\nLogged in as {data['user']}")
    print(f"Key expires: {data['expires_at']}")
    print(f"Credentials saved to {CREDENTIALS_FILE}")
    print(f"\nUsage:")
    print(f"  curl -H \"X-API-Key: $(python3 {sys.argv[0]} token)\" {server}/api/v1/catalog/items")


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


def cmd_logout(args):
    creds = _load_credentials()
    if not creds:
        print("Not logged in.")
        return

    server = creds.get("server", "").rstrip("/")
    api_key = creds.get("api_key")

    if server and api_key:
        try:
            # List keys to find ours, then revoke it
            list_url = f"{server}/api/v1/auth/keys"
            req = urllib.request.Request(
                list_url,
                headers={"X-API-Key": api_key},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                keys = json.loads(resp.read())
            key_prefix = api_key[:8]
            for k in keys:
                if k.get("key_prefix") == key_prefix:
                    revoke_url = f"{server}/api/v1/auth/keys/{k['id']}"
                    revoke_req = urllib.request.Request(
                        revoke_url,
                        headers={"X-API-Key": api_key},
                        method="DELETE",
                    )
                    urllib.request.urlopen(revoke_req, timeout=10)
                    print(f"Revoked API key on server.")
                    break
        except Exception as e:
            print(f"Warning: could not revoke key on server: {e}", file=sys.stderr)

    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
        print(f"Removed {CREDENTIALS_FILE}")
    print("Logged out.")


def main():
    parser = argparse.ArgumentParser(description="RCARS API login helper")
    sub = parser.add_subparsers(dest="command")

    login_p = sub.add_parser("login", help="Authenticate and obtain an API key")
    login_p.add_argument("--server", required=True, help="RCARS API server URL")
    login_p.add_argument("--oauth-server", required=True, help="OAuth server URL")
    login_p.add_argument("--client-id", default="rcars-api", help="OAuth client ID (default: rcars-api)")

    sub.add_parser("token", help="Print current API key")
    sub.add_parser("status", help="Show login status")
    sub.add_parser("logout", help="Revoke API key and remove local credentials")

    parser.add_argument("--server", dest="top_server", help=argparse.SUPPRESS)
    parser.add_argument("--oauth-server", dest="top_oauth_server", help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.command == "login":
        cmd_login(args)
    elif args.command == "token":
        cmd_token(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "logout":
        cmd_logout(args)
    elif args.top_server:
        args.server = args.top_server
        args.oauth_server = args.top_oauth_server
        cmd_login(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
