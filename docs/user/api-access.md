# External API Access

RCARS exposes its full API externally, allowing programmatic access from scripts, CI pipelines, other services, and tools like Swagger UI. All external access requires an API key.

## Prerequisites

- A Red Hat account that can log into the OpenShift cluster where RCARS is deployed
- The RCARS external API URL (ask an admin — e.g. `https://rcars-api.apps.cluster.example.com`)
- The OpenShift OAuth server URL (e.g. `https://oauth-openshift.apps.cluster.example.com`)

No `oc` CLI or cluster access required. Everything runs over HTTPS.

## Getting an API Key

API keys are obtained by authenticating with OpenShift OAuth. The login scripts handle the full flow — they open your browser, complete the OAuth dance, and save a 24-hour key to `~/.config/rcars/credentials.json`.

### Using the bash script

```bash
# From the rcars-advisory repo
chmod +x tools/rcars-login.sh

./tools/rcars-login.sh \
  --server https://rcars-api.apps.cluster.example.com \
  --oauth-server https://oauth-openshift.apps.cluster.example.com
```

On headless or remote systems (no browser), add `--no-server`. The script will print the authorize URL for you to open manually, then prompt you to paste back the callback URL:

```bash
./tools/rcars-login.sh \
  --server https://rcars-api.apps.cluster.example.com \
  --oauth-server https://oauth-openshift.apps.cluster.example.com \
  --no-server
```

### Using the Python script

```bash
python3 tools/rcars-login.py \
  --server https://rcars-api.apps.cluster.example.com \
  --oauth-server https://oauth-openshift.apps.cluster.example.com
```

Both scripts save credentials to `~/.config/rcars/credentials.json` (permissions: 600).

Keys expire after 24 hours. Re-run the login command to get a new one.

## Calling the API with curl

Once you have a key, pass it in the `X-API-Key` header:

```bash
# Print your current key
./tools/rcars-login.sh token

# Store in a variable
export RCARS_KEY=$(./tools/rcars-login.sh token)

# List catalog items
curl -H "X-API-Key: $RCARS_KEY" \
  https://rcars-api.apps.cluster.example.com/api/v1/catalog/items

# Get your authenticated identity and roles
curl -H "X-API-Key: $RCARS_KEY" \
  https://rcars-api.apps.cluster.example.com/api/v1/auth/me

# Submit an advisor query
curl -H "X-API-Key: $RCARS_KEY" \
  -H "Content-Type: application/json" \
  -X POST https://rcars-api.apps.cluster.example.com/api/v1/advisor/query \
  -d '{"query": "OpenShift networking demos for a financial services customer"}'
```

## Interactive API exploration (Swagger UI)

The API has full Swagger documentation with a built-in test interface:

```
https://rcars-api.apps.cluster.example.com/api/v1/docs
```

1. Open the URL in your browser
2. Click the **Authorize** button (top right)
3. Paste your API key and click **Authorize**
4. Use the **Try it out** buttons on any endpoint

## Checking login status

```bash
./tools/rcars-login.sh status
# Server:  https://rcars-api.apps.cluster.example.com
# User:    user@redhat.com
# Expires: 2026-07-04T15:30:00Z
```

## API key roles

Each API key grants access up to the role it was issued with:

| Role | Access |
|------|--------|
| `user` | Read-only — catalog, advisor queries, history |
| `curator` | Read + curation actions — analysis, retirement workflow |
| `admin` | Full access including admin endpoints |

OAuth-issued keys (from the login scripts) always grant `user` role. If you need curator or admin access via API key, ask an admin to create a long-lived key for you through the RCARS admin UI.

## Long-lived service keys (admin only)

For CI pipelines or other services that need persistent access, admins can create non-expiring keys through the RCARS admin UI at **System → API Keys**, or via the API:

```bash
# Create a service key (requires admin key)
curl -H "X-API-Key: $RCARS_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -X POST https://rcars-api.apps.cluster.example.com/api/v1/auth/keys \
  -d '{"name": "Publishing House integration", "role": "user", "expires_in_days": null}'
```

The raw key is returned once and never retrievable again — copy it immediately.

## Troubleshooting

**`401 Authentication required`** — Key is missing, expired, or revoked. Re-run the login script.

**`403 Curator role required`** — Your key's role is `user`. You need a curator-level key from an admin.

**`503 OAuth login not configured`** — The RCARS instance doesn't have `RCARS_OAUTH_SERVER_URL` set. Contact an admin.

**Login script times out** — The callback server waits 120 seconds. If the browser didn't open, check the URL printed by the script and open it manually. Alternatively, use `--no-server` mode.
