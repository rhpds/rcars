#!/usr/bin/env bash
# rcars-login.sh — Get an RCARS API key via OpenShift OAuth (PKCE flow)
#
# Usage:
#   ./rcars-login.sh --server URL --oauth-server URL
#   ./rcars-login.sh --server URL --oauth-server URL --no-server  # manual mode (no local server)
#   ./rcars-login.sh token    # print saved key
#   ./rcars-login.sh status   # show expiry and user
#
# Requirements: curl, openssl, python3 (stdlib only — for JSON parsing and the
#   local callback server). python3 is available on every macOS and Linux system.
#
# Credentials saved to ~/.config/rcars/credentials.json (mode 600).

set -euo pipefail

CREDS_DIR="${HOME}/.config/rcars"
CREDS_FILE="${CREDS_DIR}/credentials.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

urlencode() { python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$1"; }
json_get()  { python3 -c "import json,sys; print(json.loads(sys.argv[1])[sys.argv[2]])" "$1" "$2"; }

# ── Subcommands ───────────────────────────────────────────────────────────────

cmd_token() {
    [[ -f "$CREDS_FILE" ]] || { echo "Not logged in. Run: $(basename "$0") --server URL --oauth-server URL" >&2; exit 1; }
    json_get "$(cat "$CREDS_FILE")" api_key
}

cmd_status() {
    [[ -f "$CREDS_FILE" ]] || { echo "Not logged in."; exit 1; }
    local d; d=$(cat "$CREDS_FILE")
    echo "Server:  $(json_get "$d" server)"
    echo "User:    $(json_get "$d" user)"
    echo "Expires: $(json_get "$d" expires_at)"
}

cmd_login() {
    local server="" oauth_server="" no_server=0

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --server)       server="$2";       shift 2 ;;
            --oauth-server) oauth_server="$2"; shift 2 ;;
            --no-server)    no_server=1;        shift   ;;
            *) echo "Unknown option: $1" >&2; exit 1 ;;
        esac
    done

    [[ -z "$server" ]]       && { echo "Error: --server is required" >&2; exit 1; }
    [[ -z "$oauth_server" ]] && { echo "Error: --oauth-server is required" >&2; exit 1; }

    server="${server%/}"
    oauth_server="${oauth_server%/}"

    # ── Generate PKCE + state ─────────────────────────────────────────────────
    local verifier challenge state
    verifier=$(openssl rand -base64 64 | tr -d '=+/' | head -c 96)
    challenge=$(printf '%s' "$verifier" \
        | openssl dgst -sha256 -binary \
        | base64 | tr -d $'\n=' | tr '+/' '-_')
    state=$(openssl rand -hex 32)

    # ── Determine redirect URI and start callback server ──────────────────────
    local redirect_uri code callback_path tmpfile server_pid port
    if [[ $no_server -eq 0 ]]; then
        # Find a free port
        port=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); p=s.getsockname()[1]; s.close(); print(p)")
        redirect_uri="http://127.0.0.1:${port}/callback"

        # Write the callback server to a temp file
        tmpfile=$(mktemp /tmp/rcars-XXXXXX)
        cat > "${tmpfile}.py" <<'PYEOF'
import sys, http.server, pathlib

result_file = pathlib.Path(sys.argv[2])
result_file.write_text("")

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        result_file.write_text(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h2>Login successful!</h2><p>You can close this tab.</p></body></html>")
    def log_message(self, *a):
        pass

httpd = http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H)
httpd.timeout = 120
while not result_file.read_text():
    httpd.handle_request()
PYEOF
        python3 "${tmpfile}.py" "$port" "$tmpfile" &
        server_pid=$!
        trap "kill $server_pid 2>/dev/null; rm -f $tmpfile ${tmpfile}.py" EXIT
    else
        redirect_uri="http://127.0.0.1/callback"
        tmpfile=""
    fi

    # ── Open browser ──────────────────────────────────────────────────────────
    local auth_url
    auth_url="${oauth_server}/oauth/authorize"
    auth_url+="?client_id=rcars-api"
    auth_url+="&redirect_uri=$(urlencode "$redirect_uri")"
    auth_url+="&response_type=code"
    auth_url+="&code_challenge=${challenge}"
    auth_url+="&code_challenge_method=S256"
    auth_url+="&state=${state}"

    echo "Opening browser for OpenShift login..."
    if command -v open &>/dev/null; then
        open "$auth_url"
    elif command -v xdg-open &>/dev/null; then
        xdg-open "$auth_url"
    else
        echo "(Could not auto-open browser)"
    fi
    echo "If browser did not open, visit:"
    echo "  $auth_url"
    echo ""

    # ── Wait for callback ─────────────────────────────────────────────────────
    if [[ $no_server -eq 0 ]]; then
        echo "Waiting for OAuth callback (timeout: 120s)..."
        local waited=0
        while [[ -z "$(cat "$tmpfile" 2>/dev/null)" && $waited -lt 120 ]]; do
            sleep 1
            ((waited++)) || true
        done
        callback_path=$(cat "$tmpfile" 2>/dev/null || true)
        [[ -n "$callback_path" ]] || { echo "Error: timed out waiting for callback" >&2; exit 1; }
    else
        echo "After authenticating, your browser will redirect to a URL like:"
        echo "  http://127.0.0.1/callback?code=...&state=..."
        echo ""
        read -rp "Paste the full callback URL here: " callback_url
        callback_path="${callback_url#http://127.0.0.1}"
    fi

    # ── Validate state + extract code ─────────────────────────────────────────
    code=$(python3 -c "
import urllib.parse, sys
p = urllib.parse.parse_qs(urllib.parse.urlparse(sys.argv[1]).query)
print(p.get('code', [''])[0])
" "$callback_path")

    local returned_state
    returned_state=$(python3 -c "
import urllib.parse, sys
p = urllib.parse.parse_qs(urllib.parse.urlparse(sys.argv[1]).query)
print(p.get('state', [''])[0])
" "$callback_path")

    [[ "$returned_state" == "$state" ]] || { echo "Error: state mismatch — possible CSRF attack" >&2; exit 1; }
    [[ -n "$code" ]]                    || { echo "Error: no authorization code received" >&2; exit 1; }

    # ── Exchange code for API key ─────────────────────────────────────────────
    echo "Exchanging auth code for API key..."
    local response http_code
    response=$(curl -s -w "\n%{http_code}" -X POST "${server}/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{\"code\": \"${code}\", \"code_verifier\": \"${verifier}\", \"redirect_uri\": \"${redirect_uri}\"}")
    http_code=$(echo "$response" | tail -1)
    response=$(echo "$response" | head -n -1)
    if [[ "$http_code" != "200" ]]; then
        echo "Error: token exchange failed (HTTP ${http_code}): ${response}" >&2
        exit 1
    fi

    # ── Save credentials ──────────────────────────────────────────────────────
    local api_key expires_at user
    api_key=$(json_get "$response" api_key)
    expires_at=$(json_get "$response" expires_at)
    user=$(json_get "$response" user)

    mkdir -p "$CREDS_DIR"
    python3 -c "
import json, os
creds = {
    'server':     '${server}',
    'api_key':    '${api_key}',
    'expires_at': '${expires_at}',
    'user':       '${user}',
}
with open('${CREDS_FILE}', 'w') as f:
    json.dump(creds, f, indent=2)
os.chmod('${CREDS_FILE}', 0o600)
"
    echo ""
    echo "Logged in as ${user}"
    echo "Key expires: ${expires_at}"
    echo "Credentials saved to ${CREDS_FILE}"
    echo ""
    echo "Use with curl:"
    echo "  curl -H \"X-API-Key: \$($(basename "$0") token)\" ${server}/api/v1/catalog/items"
}

# ── Entry point ───────────────────────────────────────────────────────────────

case "${1:-}" in
    token)  cmd_token ;;
    status) cmd_status ;;
    "")
        echo "Usage:"
        echo "  $(basename "$0") --server URL --oauth-server URL    # login"
        echo "  $(basename "$0") --server URL --oauth-server URL --no-server  # manual mode"
        echo "  $(basename "$0") token                              # print saved key"
        echo "  $(basename "$0") status                             # show login status"
        exit 1
        ;;
    *) cmd_login "$@" ;;
esac
