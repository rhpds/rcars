# RCARS API Authentication for External Access

**Jira:** [RHDPCD-109](https://redhat.atlassian.net/browse/RHDPCD-109)
**Date:** 2026-07-03
**Status:** Design

## Problem

The RCARS API (56 endpoints under `/api/v1/`) is only accessible within the cluster. The two existing external-facing auth mechanisms have limitations:

- **OAuth proxy headers** (`X-Forwarded-Email`) are spoofable by any pod in the namespace when `proxy_verification_secret` is unset.
- **K8s ServiceAccount bearer tokens** require in-cluster access and K8s credentials.

External consumers (Babylon UI, Publishing House MCP, other teams, external MCP tools) need authenticated programmatic access to the API without relying on the OAuth proxy or cluster-internal networking.

## Approach

API keys as the single external credential type, with OpenShift OAuth as the identity verification mechanism for interactive key creation. This approach was chosen over direct OAuth token usage (per-request K8s API validation overhead) and RHSSO/Keycloak (infrastructure dependency). The design is forward-compatible with a future RHSSO migration — adding JWT validation is additive, and API keys remain useful for consumers that can't do OAuth flows.

## Design

### 1. Database Schema

The existing `api_keys` table is extended with three new columns. An Alembic migration adds `key_prefix`, `role`, and `expires_at`:

```sql
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    name TEXT NOT NULL,
    created_by TEXT NOT NULL,
    scopes TEXT[],
    role TEXT NOT NULL DEFAULT 'user',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_created_by ON api_keys(created_by);
```

Column details:

- **`key_hash`** — SHA-256 of the raw API key. The raw key is never stored.
- **`key_prefix`** — First 8 characters of the raw key (e.g., `rcars_a1`). Used for identification in the admin UI without exposing the full key.
- **`name`** — Human-readable label (e.g., "Babylon integration", "CLI session 2026-07-03").
- **`created_by`** — Email of the user who created the key. NOT NULL — every key traces to a person.
- **`scopes`** — Reserved for future fine-grained permissions (e.g., `read:catalog`, `write:retirement`). Not enforced in v1.
- **`role`** — Maximum role this key grants: `user`, `curator`, or `admin`. Acts as a ceiling — the effective role is `min(key.role, user's current role in env var lists)`.
- **`expires_at`** — NULL for admin-created service keys (revocation only). Set to NOW() + 24h for OAuth-bootstrapped interactive keys.
- **`last_used_at`** — Updated on each successful authentication. Used for admin visibility and anomaly detection.
- **`revoked_at`** — Soft-revoke timestamp. Row is preserved for audit trail.

Key format: `rcars_` prefix + 32 cryptographically random bytes encoded as hex (64 hex chars). Total key length: 70 characters. Entropy: 256 bits.

### 2. Auth Middleware

The `get_current_user()` function in `src/api/rcars/api/middleware/auth.py` gains API key validation as step 3 in the chain:

```
1. Dev bypass        — RCARS_DEV_USER env var (local development only)
2. K8s SA token      — Bearer token validated via TokenReview API, SA allowlist
3. API key           — X-API-Key header, SHA-256 hash lookup in DB  ← NEW
4. OAuth proxy       — X-Forwarded-Email header, proxy secret REQUIRED
```

#### API key validation (step 3)

- Read `X-API-Key` header (distinct from `Authorization: Bearer` used by SA tokens).
- Compute SHA-256 hash of the provided key.
- DB lookup: `WHERE key_hash = $1 AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > NOW())`.
- On match: update `last_used_at`, return the `created_by` email as the user identity along with the key's `role` ceiling.
- On no match: fall through to step 4.

#### Proxy secret enforcement (step 4 — tightened)

The `proxy_verification_secret` check becomes mandatory in production:

- If `proxy_verification_secret` is empty and `dev_user` is not set, the API rejects all OAuth proxy header auth attempts and logs a warning on startup.
- Requests with `X-Forwarded-Email` but without a matching `X-Proxy-Secret` header are rejected.
- This closes the header spoofing vector on the direct API route — a request without a valid API key, SA token, or proxy secret gets 401.
- **Migration:** Existing deployments that rely on OAuth proxy headers without a proxy secret must set `RCARS_PROXY_VERIFICATION_SECRET` in both the API deployment env vars and the OAuth proxy's upstream header configuration before deploying this change. The Ansible playbook will configure this automatically for new deploys; existing environments need the secret added to their vars file.

#### Role resolution

`require_auth`, `require_curator`, and `require_admin` continue to work unchanged. They call `get_current_user()` which returns a user identity regardless of auth method. Role checks use `is_curator()` / `is_admin()` against the env var email lists.

For API key auth, the key's `role` column acts as a ceiling. A key with `role=user` cannot access curator endpoints even if the `created_by` email is in the curator list. This is enforced by storing the auth method and key metadata on `request.state` and checking it in `require_curator` / `require_admin`.

#### In-memory cache

Validated API keys are cached in a dict with a 60-second TTL to avoid a DB query on every request. Cache entries map `key_hash → (user_email, role, expires_at)`. Expired and revoked keys are evicted on access. The 60-second window after revocation is an accepted trade-off — consistent with how OAuth token validity windows work.

### 3. Networking

A second OpenShift Route exposes the API service directly, bypassing the OAuth proxy:

```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {{ app_name }}-api
  labels:
    app: {{ app_name }}
    component: api
  annotations:
    haproxy.router.openshift.io/timeout: 180s
spec:
  host: "{{ api_host }}"
  to:
    kind: Service
    name: {{ app_name }}-api
  port:
    targetPort: {{ app_port }}
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
```

- **Separate hostname** — `api_host` variable in Ansible vars (e.g., `rcars-api.apps.cluster.example.com`), alongside existing `frontend_host`.
- **Points directly to the API ClusterIP service** — no OAuth proxy, no frontend nginx in the path.
- **Same TLS** — edge termination, HTTPS enforced.
- **Auth handled entirely by middleware** — API keys, SA tokens. No proxy headers trusted without the proxy secret.

The existing Route (`frontend_host → OAuth proxy → frontend → API`) remains unchanged. The web UI continues to work exactly as before.

Swagger UI (`/api/v1/docs`) is accessible on both routes. On the direct route, users authenticate via the "Authorize" button with their API key.

### 4. OAuth Login Flow

Interactive users obtain API keys through an OpenShift OAuth login ceremony. The flow requires a one-time cluster-level `OAuthClient` CRD:

```yaml
apiVersion: oauth.openshift.io/v1
kind: OAuthClient
metadata:
  name: rcars-cli
redirectURIs:
  - "http://127.0.0.1"
grantMethod: auto
```

This is added to the Ansible manifests alongside the existing OAuth proxy OAuthClient. It requires cluster-admin (one-time setup, same as the existing OAuthClient).

#### Login flow

```
1. User runs: python tools/rcars-login.py --server https://rcars-api.apps.example.com
2. Script generates PKCE code_verifier (random 43-128 chars) + SHA-256 code_challenge
3. Script starts HTTP server on a random localhost port
4. Script opens browser to OpenShift OAuth /authorize endpoint:
   ?client_id=rcars-cli
   &redirect_uri=http://127.0.0.1:PORT/callback
   &response_type=code
   &code_challenge=XXXX
   &code_challenge_method=S256
5. User authenticates via OpenShift login page
6. Browser redirects to http://127.0.0.1:PORT/callback?code=XXXX
7. Script captures the auth code, shuts down the HTTP server
8. Script sends the code to RCARS:
   POST https://rcars-api.apps.example.com/api/v1/auth/token
   {"code": "...", "code_verifier": "...", "redirect_uri": "http://127.0.0.1:PORT/callback"}
9. RCARS API exchanges the code with OpenShift's token endpoint (server-side)
10. RCARS extracts user email, creates a 24h API key, returns it
11. Script saves credentials to ~/.config/rcars/credentials.json
```

PKCE prevents auth code interception — an attacker who captures the redirect can't use the code without the verifier, which never leaves the script's memory.

The RCARS API does the code exchange with OpenShift (step 9), not the script. The script never handles OAuth tokens directly.

#### Helper script

`tools/rcars-login.py` is a single-file, zero-external-dependency Python script (stdlib only: `http.server`, `webbrowser`, `urllib`, `hashlib`, `secrets`, `json`).

Capabilities:

- `python rcars-login.py --server URL` — full OAuth login flow, saves credentials
- `python rcars-login.py token` — prints the current key if still valid
- `python rcars-login.py status` — shows expiry time and authenticated user

Credentials file (`~/.config/rcars/credentials.json`):

```json
{
  "server": "https://rcars-api.apps.example.com",
  "api_key": "rcars_a1b2c3d4...",
  "expires_at": "2026-07-04T15:30:00Z",
  "user": "user@redhat.com"
}
```

Usage after login:

```bash
curl -H "X-API-Key: $(python tools/rcars-login.py token)" \
  https://rcars-api.apps.example.com/api/v1/catalog/items
```

### 5. API Endpoints

Four new endpoints under `/api/v1/auth/`:

#### `POST /api/v1/auth/token` — OAuth login (unauthenticated)

The only unauthenticated endpoint besides health checks. Exchanges an OAuth authorization code for a 24h API key.

- **Request:** `{"code": "...", "code_verifier": "...", "redirect_uri": "http://127.0.0.1:PORT/callback"}`
- **Response:** `{"api_key": "rcars_...", "expires_at": "2026-07-04T15:30:00Z", "user": "user@redhat.com"}`
- **Rate limit:** 5 attempts per source IP per minute. Returns 429 when exceeded.
- The raw API key is returned exactly once and never stored or retrievable again.

#### `POST /api/v1/auth/keys` — Create long-lived API key (admin only)

For service-to-service consumers (Babylon, Publishing House, etc.). Created by admins through the API or admin UI.

- **Request:** `{"name": "Babylon integration", "role": "user", "expires_in_days": null}`
- **Response:** `{"api_key": "rcars_...", "id": 42, "name": "Babylon integration", "role": "user", "expires_at": null}`
- **Role ceiling enforced:** admin can create any role, curator can create user/curator, user can create user only.
- `expires_in_days: null` means never expires (revocation only).
- **Requires:** `require_admin`

#### `GET /api/v1/auth/keys` — List API keys (admin only)

Returns all keys with metadata. Never returns the raw key or hash.

- **Response:** array of `{id, key_prefix, name, created_by, role, created_at, expires_at, last_used_at, is_active}`
- **Query params:** `?active=true` filters to non-revoked, non-expired keys.
- **Requires:** `require_admin`

#### `DELETE /api/v1/auth/keys/{id}` — Revoke a key (admin only)

Soft-revokes by setting `revoked_at = NOW()`. Row preserved for audit trail. Invalidates in-memory cache entry.

- **Response:** `{"id": 42, "revoked_at": "2026-07-03T12:00:00Z"}`
- **Requires:** `require_admin`

The existing `GET /api/v1/auth/me` endpoint continues to work unchanged — it returns the authenticated user's email and roles regardless of auth method.

### 6. Security

#### Threat model

| Vector | Risk | Mitigation |
|--------|------|------------|
| Header spoofing on direct route | HIGH | Proxy verification secret mandatory. Requests with `X-Forwarded-Email` but no valid proxy secret are rejected. |
| Brute-force key guessing | LOW | 256-bit entropy makes guessing infeasible. Rate-limit failed auth attempts (5/min per IP on `/auth/token`; general failed auth logged and monitored). |
| Stolen key in transit | LOW | TLS enforced on both routes (edge termination). Key only transmitted over HTTPS. |
| Stolen key from user's machine | MEDIUM | 24h expiry limits exposure window. `last_used_at` tracking for anomaly detection. Admin revocation via UI. |
| DB breach (api_keys table) | LOW | Only SHA-256 hashes stored. High-entropy input makes reversal infeasible. |
| OAuth callback interception | LOW | PKCE — interceptor can't use auth code without the code_verifier. OAuthClient CRD restricts redirectURIs to `http://127.0.0.1`. |
| Privilege escalation via key creation | MEDIUM | Role ceiling enforced — key role cannot exceed creator's current role. |
| Cache staleness after revocation | LOW | 60-second TTL. Accepted trade-off, consistent with OAuth token validity windows. |

#### Auth logging

Every auth decision produces a structlog entry:

```json
{
  "component": "auth",
  "auth_method": "api_key|sa_token|oauth_proxy|dev_bypass",
  "user": "user@redhat.com",
  "key_id": 42,
  "source_ip": "10.0.0.1",
  "outcome": "success|rejected_expired|rejected_revoked|rejected_no_credentials"
}
```

#### Security test suite

`tests/test_auth_security.py` — runs in CI, validates:

1. Every endpoint returns 401 with no credentials.
2. Every endpoint returns 401 with an expired API key.
3. Every endpoint returns 401 with a revoked API key.
4. Spoofed `X-Forwarded-Email` without proxy secret returns 401.
5. API key with `role=user` returns 403 on curator/admin endpoints.
6. Key creation with role above creator's role returns 403.
7. `/auth/token` rate-limits after 5 failed attempts.

### 7. Future Path to RHSSO

This design is forward-compatible with RHSSO/Keycloak integration:

- **Additive:** A JWT validation step slots between SA tokens and API keys in the middleware chain. Nothing is removed or restructured.
- **API keys coexist:** Long-lived API keys remain useful for consumers that can't do OAuth flows (cron jobs, CI, webhooks). JWTs handle interactive users and service accounts with OAuth capability.
- **Same Route:** The direct API Route serves both API keys and JWTs. No networking changes.
- **Same role resolution:** Whether identity comes from a JWT claim or API key lookup, it resolves to an email, and `is_curator()` / `is_admin()` works identically.
- **No awkward migration:** API keys are opaque random strings, not custom token formats. There's no halfway-JWT to migrate away from.

### 8. Out of Scope (v1)

- Admin UI for key management (API-only for v1; admin UI is a follow-up)
- Self-service key creation by non-admins (only OAuth login flow creates user keys)
- Key rotation endpoint (revoke + create new)
- Expiry extension (revoke old, create new)
- Per-endpoint scope enforcement (column exists, not wired)
- NetworkPolicy restricting API service access
- IP allowlisting on the direct route
- `rcars client` CLI subgroup (future Option C)
