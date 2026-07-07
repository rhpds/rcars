# RCARS External API Tools

Tools for authenticating with and calling the RCARS external API.

## Prerequisites

- Access to the RCARS direct API route (`rcars-api-dev.apps...` or `rcars-api.apps...`)
- An OpenShift account with access to the cluster

## Getting an API key

Two login scripts are available — both do the same PKCE OAuth flow, pick whichever suits your environment:

| Script | Requirements | Best for |
|--------|-------------|----------|
| `rcars-login.sh` | bash, curl, openssl, python3 (stdlib) | macOS/Linux shell users |
| `rcars-login.py` | python3 (stdlib) | Scripting, cross-platform |

### Bash

```bash
chmod +x tools/rcars-login.sh

./tools/rcars-login.sh \
  --server https://rcars-api-dev.apps.cluster.example.com \
  --oauth-server https://oauth-openshift.apps.cluster.example.com
```

On systems without a working browser (e.g. a remote shell), add `--no-server` to get a manual flow where you paste the callback URL instead:

```bash
./tools/rcars-login.sh \
  --server https://rcars-api-dev.apps.cluster.example.com \
  --oauth-server https://oauth-openshift.apps.cluster.example.com \
  --no-server
```

### Python

```bash
python3 tools/rcars-login.py \
  --server https://rcars-api-dev.apps.cluster.example.com \
  --oauth-server https://oauth-openshift.apps.cluster.example.com
```

Both scripts save credentials to `~/.config/rcars/credentials.json` (mode 600). Keys expire after 24 hours — re-run the login command to get a new one.

## Using the API with curl

Once logged in, use the saved key with any API endpoint:

```bash
# Use the helper to pull the key from credentials
curl -H "X-API-Key: $(./tools/rcars-login.sh token)" \
  https://rcars-api-dev.apps.cluster.example.com/api/v1/catalog/items

# Or store it in a variable
export RCARS_API_KEY=$(./tools/rcars-login.sh token)

curl -H "X-API-Key: $RCARS_API_KEY" \
  https://rcars-api-dev.apps.cluster.example.com/api/v1/catalog/items

curl -H "X-API-Key: $RCARS_API_KEY" \
  https://rcars-api-dev.apps.cluster.example.com/api/v1/auth/me

# Check the interactive Swagger docs (authenticate with X-API-Key in the Authorize button)
open https://rcars-api-dev.apps.cluster.example.com/api/v1/docs
```

## Check login status

```bash
./tools/rcars-login.sh status
# Server:  https://rcars-api-dev.apps...
# User:    user@redhat.com
# Expires: 2026-07-04T15:30:00Z
```

## Service account keys (admin only)

For long-lived programmatic access (CI pipelines, other services), admins can create non-expiring keys through the RCARS admin UI at `/system/api-keys`, or via the API:

```bash
curl -H "X-API-Key: $RCARS_API_KEY" \
  -X POST https://rcars-api-dev.apps.cluster.example.com/api/v1/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "My service", "role": "user", "expires_in_days": null}'
```
