#!/usr/bin/env bash
# rcars-login.sh — Get an RCARS API key via OpenShift OAuth (implicit grant)
#
# Usage:
#   ./rcars-login.sh --server URL --oauth-server URL
#   ./rcars-login.sh --server URL --oauth-server URL --no-server  # manual mode
#   ./rcars-login.sh token    # print saved key
#   ./rcars-login.sh status   # show login status
#
# Requirements: curl, python3 (stdlib only — for callback server and JSON).
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

    local state access_token
    state=$(openssl rand -hex 32)

    # ── Start callback server or manual mode ──────────────────────────────────
    local redirect_uri port tmpfile server_pid
    if [[ $no_server -eq 0 ]]; then
        port=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); p=s.getsockname()[1]; s.close(); print(p)")
        redirect_uri="http://127.0.0.1:${port}/callback"

        # Callback server: serves JS to extract the token from the URL fragment
        tmpfile=$(mktemp /tmp/rcars-XXXXXX)
        cat > "${tmpfile}.py" <<'PYEOF'
import sys, http.server, pathlib, urllib.parse

result_file = pathlib.Path(sys.argv[2])
result_file.write_text("")

CALLBACK_HTML = b"""<!DOCTYPE html><html><body>
<h2>Completing login...</h2>
<script>
var h = window.location.hash.substring(1);
var p = new URLSearchParams(h);
var t = p.get("access_token");
if (t) {
    window.location = "/complete?access_token=" + encodeURIComponent(t);
} else {
    document.body.innerHTML = "<h2>Login failed</h2><p>No access token received.</p>";
}
</script>
</body></html>"""

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(CALLBACK_HTML)
        elif parsed.path == "/complete":
            params = urllib.parse.parse_qs(parsed.query)
            token = params.get("access_token", [None])[0]
            if token:
                result_file.write_text(token)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Login successful!</h2><p>You can close this tab.</p></body></html>")
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, *a): pass

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
    auth_url+="&response_type=token"
    auth_url+="&state=${state}"

    echo "Opening browser for login..."
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

    # ── Wait for token ────────────────────────────────────────────────────────
    if [[ $no_server -eq 0 ]]; then
        echo "Waiting for OAuth callback (timeout: 120s)..."
        local waited=0
        while [[ -z "$(cat "$tmpfile" 2>/dev/null)" && $waited -lt 120 ]]; do
            sleep 1
            ((waited++)) || true
        done
        access_token=$(cat "$tmpfile" 2>/dev/null || true)
        [[ -n "$access_token" ]] || { echo "Error: timed out waiting for callback" >&2; exit 1; }
    else
        echo "After authenticating, your browser will show a page."
        echo "Copy the access_token value from the URL fragment."
        echo ""
        read -rp "Paste the access_token here: " access_token
        [[ -n "$access_token" ]] || { echo "Error: no access token provided" >&2; exit 1; }
    fi

    # ── Exchange token for API key ────────────────────────────────────────────
    echo "Exchanging access token for API key..."
    local response http_code tmpresponse payload
    tmpresponse=$(mktemp /tmp/rcars-resp-XXXXXX)
    payload=$(python3 -c "import json,sys; print(json.dumps({'access_token': sys.argv[1]}))" "$access_token")
    http_code=$(curl -s -o "$tmpresponse" -w "%{http_code}" -X POST "${server}/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "$payload")
    response=$(cat "$tmpresponse"); rm -f "$tmpresponse"
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
