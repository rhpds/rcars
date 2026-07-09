# RCARS Security Audit v3 — Consolidated Report

**Date:** 2026-07-09
**Commit:** `5fe7886` (main)
**Previous audit:** v2 (2026-06-30, commit `0b08d10`, RHDPCD-164)
**Jira:** RHDPCD-184
**Scope:** Full repository — Python backend, React frontend (PF6), Ansible/OpenShift deployment, LLM integration, CLI tools

## Methodology

Three independent security review agents with distinct perspectives, each reading the full codebase:

| Agent | Focus | Files Read | Findings |
|-------|-------|-----------|----------|
| **Red Team / Pen Tester** | Exploitable attack vectors, auth bypass, injection, token theft | 20+ source files + 5 test files | 9 findings |
| **InfoSec Architect** | Security architecture, secrets lifecycle, trust boundaries, data flows | 25+ source + infra files | 16 findings |
| **DevSecOps / Supply Chain** | Container security, K8s config, dependencies, IaC, RBAC | All infra + build files | 19 findings |

Findings were deduplicated (13 overlapping items confirmed by 2+ agents), severity-ranked using the highest severity when agents disagreed, and organized into a unified numbering scheme.

## Summary

| Severity | v2 Count | v3 Count | New | Fixed since v2 | Carried forward |
|----------|----------|----------|-----|----------------|-----------------|
| CRITICAL | 0 | 1 | 0 | — | 1 (elevated from M-8) |
| HIGH | 3 | 5 | 4 | 3 (H-1, H-2, H-3) | 0 |
| MEDIUM | 8 | 16 | 9 | 2 (M-1, M-6 partial) | 7 |
| LOW | 10 | 12 | 8 | 6 | 4 |
| INFO | 5 | 3 | 0 | — | 3 |

**Net assessment:** The codebase security posture continues to improve — all v2 HIGH findings remain fixed, and the new OAuth/API key system is architecturally sound (proxy secret validation, SHA-256 key hashing, role ceiling enforcement). However, the expanded feature set introduces new attack surface, and several infrastructure items from v2 remain unaddressed. The shared dev/prod credentials finding has been elevated to CRITICAL after confirming it spans three credential sets.

---

## CRITICAL Findings

### C-1: Identical credentials shared between dev and prod environments
**Agents:** DevSecOps (DS-1) | **v2 ref:** M-8 (elevated)
**Files:** `ansible/vars/dev.yml`, `ansible/vars/prod.yml` (gitignored)

Three credential sets are byte-identical between dev and prod: LiteMaaS API key, Reporting MCP token, and Jira API token. Compromise of the dev environment grants immediate access to production external services with zero additional credential discovery.

**Recommendation:** Generate unique credentials per environment for all three services. Rotate current shared keys immediately.
**Effort:** Low

---

## HIGH Findings

### H-1: CLI login token stored in plaintext JSON
**Agents:** InfoSec (IA-1) | **Status:** NEW
**Files:** `tools/rcars-login.py:54`, `tools/rcars-login.sh:186-197`

The CLI login tools store the raw API key in `~/.config/rcars/credentials.json` as plaintext JSON. File permissions are set to 0o600, but the key is readable by any process running as the same user, backup systems, and cloud sync tools. No logout/revocation mechanism exists.

**Recommendation:** (1) Add a `logout` subcommand that revokes the key via API and deletes the file. (2) Consider OS keychain integration. (3) At minimum, add auto-revoke on process exit.
**Effort:** Medium

### H-2: No expired/revoked API key cleanup — unbounded table growth
**Agents:** InfoSec (IA-2) | **Status:** NEW
**Files:** `src/api/rcars/db/database.py:2267-2329`

Every CLI login creates a new `api_keys` row (24h TTL). Revoked keys are soft-deleted. No garbage collection exists — the table grows without bound. Every expired key's hash, creation metadata, and user email remain in the database indefinitely with no retention policy.

**Recommendation:** Add `prune_expired_api_keys(retain_days=7)` to the nightly maintenance pipeline.
**Effort:** Low

### H-3: SQL string interpolation in MCP reporting queries
**Agents:** InfoSec (IA-3) | **Status:** NEW
**Files:** `src/api/rcars/services/reporting_sync.py:348-440`

The SQL queries built by `_build_provisions_sql()`, `_build_touched_sql()`, `_build_closed_sql()`, etc. use Python f-string interpolation to inject values into SQL strings sent to the external MCP server. Currently safe because all interpolated values are internally generated, but the pattern is fragile — a future developer adding user-controllable parameters would create SQL injection against the remote reporting database.

**Recommendation:** Refactor to use parameterized query patterns or add safety documentation at each interpolation point.
**Effort:** Medium

### H-4: Python dependencies use unbounded version ranges with no lock file
**Agents:** DevSecOps (DS-4) | **Status:** NEW
**Files:** `src/api/pyproject.toml`

All 16 Python dependencies use `>=` ranges with no upper bound. No `poetry.lock`, `uv.lock`, or pinned `requirements.txt` exists. Builds are not reproducible — two builds on different days produce different dependency trees. Notable: `sentence-transformers>=3.0` pulls PyTorch (>2GB, native C++ code).

**Recommendation:** Add a `uv.lock` or `pip-compile` output with exact versions and hashes. Update Containerfile to install from the lock file with `--require-hashes`.
**Effort:** Low

### H-5: No Ansible Vault encryption for deployment secrets
**Agents:** DevSecOps (DS-6) | **Status:** NEW
**Files:** `ansible/vars/dev.yml`, `ansible/vars/prod.yml`

All deployment secrets (database passwords, API keys, OAuth secrets, Jira tokens, MCP tokens) are stored in plaintext YAML files. No Ansible Vault encryption is used anywhere. The files are properly gitignored and were never committed, but exist as plaintext on the operator's workstation.

**Recommendation:** Encrypt with Ansible Vault: `ansible-vault encrypt ansible/vars/dev.yml ansible/vars/prod.yml`.
**Effort:** Low

---

## MEDIUM Findings

### M-1: Rate limiter key poisoning allows per-user DoS
**Agents:** Red Team (RT-3) | **Status:** NEW
**Files:** `src/api/rcars/api/middleware/rate_limit.py:9-16`

The rate limiter reads `X-Forwarded-Email` directly from the request header **before** auth middleware validates the proxy secret. An attacker can consume a victim's rate limit quota by sending 50 requests with `X-Forwarded-Email: victim@redhat.com` (no proxy secret needed). All 50 are rejected 401 by auth, but the rate limiter has already counted them. The real user cannot submit queries for the remainder of the rate window.

**Recommendation:** Key rate limiting off the authenticated user identity (from `request.state`) rather than the raw header.
**Effort:** Low

### M-2: API key cache cross-replica invalidation gap
**Agents:** Red Team (RT-1), InfoSec (IA-5) | **Status:** NEW
**Files:** `src/api/rcars/api/middleware/auth.py:22-23, 91-113`

The in-memory API key cache (`_api_key_cache`, 60s TTL) is process-local. When a key is revoked, `invalidate_api_key_cache()` clears only the local process. In a multi-replica deployment, other replicas continue accepting the revoked key for up to 60 seconds.

**Recommendation:** Publish revocation events via Redis pub/sub, or reduce TTL to 5-10 seconds.
**Effort:** Low

### M-3: No rate limit on total API keys per user
**Agents:** InfoSec (IA-6) | **Status:** NEW
**Files:** `src/api/rcars/api/routes/auth.py:157-219`

The token exchange endpoint creates a new API key per call with no per-user limit. Combined with H-2 (no cleanup), a user or attacker with a valid OAuth token can create unbounded keys.

**Recommendation:** Check for existing active key and return/replace it, or enforce a maximum active-keys-per-user limit (e.g., 10).
**Effort:** Low

### M-4: Token exchange missing explicit `conn.commit()`
**Agents:** Red Team (RT-2) | **Status:** NEW
**Files:** `src/api/rcars/db/database.py:2267-2282`

`create_api_key()` executes an INSERT but relies on auto-commit-on-exit rather than explicit `conn.commit()`, unlike every other write method. If an exception occurs between INSERT and context manager exit, the key is returned to the user but not persisted.

**Recommendation:** Add explicit `conn.commit()` to match the pattern used in all other write methods.
**Effort:** Trivial

### M-5: SSRF DNS rebinding TOCTOU gap
**Agents:** Red Team (RT-4), InfoSec (IA-4) | **v2 ref:** M-2 (carried forward)
**Files:** `src/api/rcars/services/event_parser.py:36-78`

`_validate_url()` resolves and validates the hostname IP, then `_fetch_html()` re-resolves via `httpx.get()`. A DNS rebinding attack can pass validation with a public IP then resolve to a private IP for the actual request.

**Recommendation:** Pin the resolved IP and pass it to httpx via custom transport.
**Effort:** Medium

### M-6: No NetworkPolicies — zero network segmentation
**Agents:** InfoSec (IA-8), DevSecOps (DS-3) | **v2 ref:** M-3 (carried forward)
**Files:** All of `ansible/templates/`, `ansible/tasks/`

Zero NetworkPolicy resources. All pods communicate freely. A compromised container gains direct network access to PostgreSQL, Redis, and the API.

**Recommendation:** Deploy default-deny ingress/egress with explicit allow rules per component.
**Effort:** Medium

### M-7: Redis communication lacks TLS
**Agents:** InfoSec (IA-7), DevSecOps (DS-7) | **v2 ref:** M-4 (carried forward)
**Files:** `ansible/templates/manifests-infra.yaml.j2:319`, `ansible/vars/common.yml:14`

Redis uses password auth but plaintext TCP. All job data, pub/sub messages, and SSE stream data is unencrypted.

**Recommendation:** Configure Redis TLS or deploy NetworkPolicies as compensating control.
**Effort:** Medium

### M-8: PostgreSQL communication lacks TLS
**Agents:** InfoSec (IA-7), DevSecOps (DS-8) | **v2 ref:** M-5 (carried forward)
**Files:** `ansible/templates/manifests-infra.yaml.j2:222-272`, `ansible/templates/manifests-app.yaml.j2:89`

Database connections use `postgresql://` without TLS. Credentials and query data (including API key hashes) flow in plaintext.

**Recommendation:** Enable PostgreSQL TLS and add `?sslmode=verify-full` to connection strings.
**Effort:** Medium

### M-9: pgvector image from Docker Hub — supply chain risk
**Agents:** DevSecOps (DS-2) | **v2 ref:** M-6 (partially fixed)
**Files:** `ansible/vars/common.yml:13`

`pgvector/pgvector:0.8.0-pg16` is from Docker Hub (not Red Hat). Version-pinned but still a mutable tag, not a SHA256 digest. This image runs the database containing all catalog data, embeddings, API keys, and user sessions.

**Recommendation:** Build custom image from `registry.redhat.io/rhel9/postgresql-16` with pgvector compiled from source, or pin to SHA256 digest.
**Effort:** Medium

### M-10: Management SA excessive permissions with non-expiring token
**Agents:** InfoSec (IA-10), DevSecOps (DS-5) | **v2 ref:** M-7 (carried forward)
**Files:** `ansible/tasks/mgmt-rbac.yml:46-62, 120-131`

`rcars-mgmt-sa` has built-in `admin` ClusterRole in the target namespace plus cluster-level namespace and OAuthClient management. The token is long-lived and non-expiring, stored in a local kubeconfig file.

**Recommendation:** Replace with custom least-privilege Role. Switch to short-lived tokens via `kubectl create token --duration`.
**Effort:** Medium

### M-11: Opt-out mode does not fully suppress data retention
**Agents:** InfoSec (IA-11) | **v2 ref:** L-9 (elevated, expanded)
**Files:** `src/api/rcars/db/database.py:1355-1367, 1574-1592`

When `opted_out=True`, `query_text` is nullified but `user_email`, `event_url`, and `ci_name` are retained. The system records WHO queried and WHICH event URL they submitted, just not WHAT they asked.

**Recommendation:** Also null out `user_email` and `event_url` in opt-out mode, or hash the email.
**Effort:** Low

### M-12: Jira integration uses personal API token
**Agents:** InfoSec (IA-9) | **Status:** NEW
**Files:** `src/api/rcars/services/jira.py:20-72`, `src/api/rcars/config.py:96-97`

Jira uses Basic auth with a personal API token inheriting the full permissions of the associated user's Atlassian account. If the user leaves the organization, the integration breaks.

**Recommendation:** Use a dedicated Atlassian service account (bot account) with minimum required permissions.
**Effort:** Medium

### M-13: Redis password exposed in process command-line arguments
**Agents:** DevSecOps (DS-10) | **Status:** NEW
**Files:** `ansible/templates/manifests-infra.yaml.j2:319`

Redis is started with `--requirepass "$(REDIS_PASSWORD)"` which K8s resolves at container creation, placing the plaintext password into `/proc/1/cmdline`.

**Recommendation:** Mount the password via a Redis config file instead of command-line arguments.
**Effort:** Low

### M-14: OAuthClient not environment-scoped
**Agents:** DevSecOps (DS-12) | **Status:** NEW
**Files:** `ansible/templates/manifests-infra.yaml.j2:136-148`

The OAuthClient `rcars-api` uses a hardcoded name not scoped by environment. Dev and prod on the same cluster would conflict on this cluster-scoped resource. `grantMethod: auto` means any cluster user can self-service an API key without authorization.

**Recommendation:** Scope the name: `rcars-api-{{ env }}`. Change `grantMethod` to `prompt`. Make `secret` field mandatory.
**Effort:** Low

### M-15: Mutable image tags on all external images
**Agents:** DevSecOps (DS-11) | **Status:** NEW (expanded from v2 M-6)
**Files:** `ansible/vars/common.yml:13-15`

All three external images use mutable version tags. No SHA256 digest pinning. Tag-based references can silently change content.

**Recommendation:** Pin all external images to SHA256 digests.
**Effort:** Trivial

### M-16: Workers and Redis missing health probes
**Agents:** DevSecOps (DS-13) | **Status:** NEW
**Files:** `ansible/templates/manifests-app.yaml.j2:339-344,461-466`, `ansible/templates/manifests-infra.yaml.j2:316-350`

Scan-worker and recommend-worker have only livenessProbe, no readinessProbe. Redis has neither. K8s cannot detect a hung Redis process, leaving the job queue silently broken.

**Recommendation:** Add readinessProbes to workers. Add liveness and readiness probes to Redis.
**Effort:** Low

---

## LOW Findings

### L-1: SQL column interpolation in ORDER BY (defense in depth)
**Agents:** Red Team (RT-5) | **v2 ref:** Carried forward
**Files:** `src/api/rcars/db/database.py:2006`

`sort_by` is interpolated via f-string into `ORDER BY`. Currently safe due to allowlist, but fragile.

**Recommendation:** Use `sql.SQL`/`sql.Identifier` from psycopg.

### L-2: API key cache unbounded growth
**Agents:** Red Team (RT-6) | **Status:** NEW
**Files:** `src/api/rcars/api/middleware/auth.py:22`

`_api_key_cache` dict grows without bound — no max-size eviction.

**Recommendation:** Use `cachetools.TTLCache` with max size.

### L-3: Advisor session choice update lacks ownership scoping
**Agents:** Red Team (RT-7) | **Status:** NEW
**Files:** `src/api/rcars/api/routes/advisor.py:157-169`

`update_advisor_session_choice()` called without `user_email` parameter. Currently protected by read-side ownership check, but future regression risk.

**Recommendation:** Pass `user_email=user` for defense in depth.

### L-4: readOnlyRootFilesystem missing on PG and OAuth proxy
**Agents:** InfoSec (IA-12), DevSecOps (DS-9) | **v2 ref:** L-8 (carried forward)
**Files:** `ansible/templates/manifests-infra.yaml.j2:265-268`, `ansible/templates/manifests-app.yaml.j2:660-663`

5 of 7 containers have it set. PG and OAuth proxy still missing.

**Recommendation:** Add `readOnlyRootFilesystem: true` with emptyDir mounts for writable paths.

### L-5: LLM provider status endpoint exposes internal configuration
**Agents:** InfoSec (IA-13) | **Status:** NEW
**Files:** `src/api/rcars/api/routes/admin.py:325-341`

Admin-only, but reveals LiteMaaS endpoint URL and GCP region.

**Recommendation:** Return only enabled/disabled status and model names, not URLs/regions.

### L-6: No CSRF protection (mitigated by architecture)
**Agents:** InfoSec (IA-14) | **v2 ref:** L-10 (carried forward)

Proxy verification secret acts as implicit CSRF token. Sound architecture.

**Recommendation:** Document as security property. Consider `SameSite=Strict` on OAuth proxy cookie.

### L-7: Reporting MCP token has no rotation procedure
**Agents:** InfoSec (IA-15) | **Status:** NEW
**Files:** `src/api/rcars/services/reporting_sync.py:280-318`

Static bearer token with no expiry or documented rotation.

**Recommendation:** Document rotation procedure. Consider short-lived tokens.

### L-8: No CI/CD pipeline for security scanning
**Agents:** DevSecOps (DS-15) | **Status:** NEW
**Files:** `.github/workflows/docs.yml`

Only CI pipeline is docs deployment. No `npm audit`, `pip audit`, SAST/DAST, or container scanning.

**Recommendation:** Add `npm audit`/`pip audit` on PRs, Trivy container scanning, and `pytest` CI.

### L-9: SA tokens auto-mounted on pods that don't need K8s API access
**Agents:** DevSecOps (DS-14) | **Status:** NEW
**Files:** `ansible/templates/manifests-app.yaml.j2`, `ansible/templates/manifests-infra.yaml.j2`

All pods receive mounted SA tokens, even frontend, PostgreSQL, and Redis which never call the K8s API.

**Recommendation:** Add `automountServiceAccountToken: false` to pods that don't need it.

### L-10: No PodDisruptionBudgets
**Agents:** DevSecOps (DS-16) | **Status:** NEW

All single-replica with no disruption protection.

**Recommendation:** Add PDBs for API and frontend.

### L-11: CSP missing frame-ancestors directive
**Agents:** DevSecOps (DS-17) | **Status:** NEW
**Files:** `src/frontend/nginx.conf:39`

X-Frame-Options provides legacy protection, but CSP `frame-ancestors` is the modern standard.

**Recommendation:** Add `frame-ancestors 'self'` and `form-action 'self'` to CSP.

### L-12: No CORS configuration on direct API route
**Agents:** DevSecOps (DS-18) | **Status:** NEW
**Files:** `src/api/rcars/api/app.py`

No `CORSMiddleware` configured. Currently acceptable (API key auth, not cookies), but no future-proofing.

**Recommendation:** Add explicit CORS middleware with `allow_origins=[]` to prevent future regressions.

---

## Positive Security Observations

All three agents independently noted these well-implemented controls:

1. **Proxy verification secret** — `X-Proxy-Secret` with `hmac.compare_digest()` effectively prevents header spoofing
2. **API key security** — SHA-256 hashing, prefix-only display, soft-revocation, 24h CLI expiry, role ceiling enforcement
3. **Container security** — All containers: `runAsNonRoot`, `seccompProfile: RuntimeDefault`, `allowPrivilegeEscalation: false`, `capabilities: drop: ["ALL"]`, resource limits
4. **CSP and security headers** — Strict CSP (`script-src 'self'`), HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, `server_tokens off`
5. **Structured auth logging** — Every auth decision logged with method, user, source IP, and outcome
6. **Multi-stage builds** — No source code in runtime images
7. **UBI9 base images** — Red Hat vulnerability scanning on all application containers
8. **Dev bypass safety** — `RCARS_DEV_USER` explicitly empty in deployed manifests
9. **SSRF mitigation** — URL validation against private IP ranges including IPv4-mapped IPv6
10. **Retirement workflow audit trail** — Every step logged to `analysis_log` with user attribution
11. **Secret change detection** — Pod annotation checksums trigger rolling restarts on secret changes
12. **TLS termination** — Route-level with `insecureEdgeTerminationPolicy: Redirect`

---

## Security Test Coverage Gaps

The Red Team agent identified 12 gaps in the test suite:

1. No test for rate limiter key poisoning (M-1)
2. No test for API key cache invalidation across replicas (M-2)
3. No test for cache TTL vs. DB revocation timing
4. No test for cache unbounded growth (L-2)
5. No negative test for `update_advisor_session_choice` without ownership (L-3)
6. No test for `content_path` traversal at the full API stack level
7. No test for Jira ticket creation input sanitization
8. No test for token exchange rate limiting enforcement
9. No test for `sort_by` allowlist in `list_reporting_metrics`
10. No integration test for the full OAuth implicit grant flow
11. No test for SSE stream auth (API key auth won't work with EventSource)
12. No CSRF protection tests

---

## Trust Boundary Diagram

```
                                  INTERNET
                                     |
                            [TLS termination]
                                     |
                     ┌───────────────┴───────────────┐
                     |                               |
              ┌──────┴──────┐                 ┌──────┴──────┐
              │  OAuth Proxy │                │ Direct API  │
              │  (Web UI)    │                │ Route       │
              │              │                │ (CLI/API)   │
              └──────┬───────┘                └──────┬──────┘
                     |                               |
          [X-Forwarded-Email]              [X-API-Key / Bearer]
          [X-Proxy-Secret]                          |
                     |                               |
              ┌──────┴───────┐                       |
              │  Frontend    │                       |
              │  (nginx)     ├───────────────────────┘
              │  adds Proxy  │          proxy_pass /api/
              │  Secret hdr  │
              └──────┬───────┘
                     |
            [X-Proxy-Secret + X-Forwarded-Email]
                     |
              ┌──────┴──────────────────────────────────┐
              │           FastAPI API                    │
              │  Auth chain: dev_bypass → SA → API key   │
              │  → OAuth proxy headers                   │
              │  Role check: require_auth/curator/admin   │
              └───┬──────────┬──────────┬───────────────┘
                  |          |          |
           ┌─────┴───┐ ┌────┴───┐ ┌────┴─────┐
           │  Redis   │ │  PG    │ │ External │
           │  (arq+   │ │ pgvec  │ │ Services │
           │  pubsub) │ │        │ │          │
           └──────────┘ └────────┘ └──────────┘
                                   |    |    |
                              Jira  MCP  LLM
                            (Basic) (Bearer) (API key)
```

---

## Remediation Priority

### Immediate (this sprint)
| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 1 | C-1: Rotate shared dev/prod credentials | Low | Critical |
| 2 | H-5: Encrypt vars files with Ansible Vault | Low | High |
| 3 | H-2: Add API key pruning to nightly maintenance | Low | High |
| 4 | M-1: Fix rate limiter key to use authenticated identity | Low | Medium |
| 5 | M-15: Pin all images to SHA256 digests | Trivial | Medium |
| 6 | L-9: Set `automountServiceAccountToken: false` where unneeded | Trivial | Medium |

### Next sprint
| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 7 | M-6: Deploy NetworkPolicies | Medium | High |
| 8 | H-4: Create Python lock file with hashes | Low | High |
| 9 | M-2: Redis pub/sub for cache invalidation | Low | Medium |
| 10 | M-3: Enforce per-user API key limit | Low | Medium |
| 11 | M-4: Add explicit `conn.commit()` | Trivial | Medium |
| 12 | M-14: Scope OAuthClient by environment | Low | Medium |
| 13 | M-13: Mount Redis password via config file | Low | Medium |
| 14 | M-16: Add missing health probes | Low | Medium |
| 15 | L-4: readOnlyRootFilesystem on PG/OAuth proxy | Low | Low |

### Backlog
| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 16 | H-1: CLI logout + keychain integration | Medium | High |
| 17 | H-3: Refactor MCP SQL interpolation | Medium | Medium |
| 18 | M-5: SSRF DNS rebinding fix | Medium | Medium |
| 19 | M-9: Replace Docker Hub pgvector | Medium | Medium |
| 20 | M-10: Least-privilege SA + short-lived tokens | Medium | Medium |
| 21 | M-7/M-8: Redis and PostgreSQL TLS | Medium | Medium |
| 22 | M-11: Full opt-out data suppression | Low | Medium |
| 23 | M-12: Jira service account migration | Medium | Low |
| 24 | L-8: CI/CD security scanning pipeline | Medium | Low |

---

## Comparison with v2

### Items FIXED (from v1→v2 cycle, verified still fixed)
H-1 (SSRF), H-2 (XSS), H-3 (header trust), M-1 (rate limiting), M-1/v1 (prompt injection), M-2/v1 (IDOR sessions), M-5/v1 (nginx headers), M-6/v1 (CSP), M-7/v1 (source maps), M-9/v1 (Redis auth), L-1 through L-7 from v2

### Items CARRIED FORWARD (8)
M-2→M-5, M-3→M-6, M-4→M-7, M-5→M-8, M-6→M-9/M-15, M-7→M-10, M-8→C-1 (elevated), L-8→L-4, L-9→M-11 (elevated)

### NEW Items (26)
H-1 through H-5, M-1 through M-4, M-12 through M-16, L-1 through L-3, L-5, L-7 through L-12

---

## Disposition — 2026-07-09

Branch: `feature/security-audit-v3-fixes`

### Code fixes applied

| Finding | Status | Detail |
|---------|--------|--------|
| H-1 | **FIXED** | `logout` subcommand added to `rcars-login.py` — revokes key on server + deletes local file |
| H-2 | **FIXED** | `prune_expired_api_keys(retain_days=30)` added to nightly maintenance pipeline |
| H-4 | **FIXED** | `requirements.lock.txt` generated with 92 pinned dependencies |
| M-1 | **FIXED** | Rate limiter keys off `request.state.user` (authenticated identity), not raw header |
| M-2 | **FIXED** | API key cache TTL reduced from 60s to 10s |
| M-3 | **FIXED** | Token exchange revokes existing CLI keys before creating new one (one active key per user) |
| M-4 | **FIXED** | Explicit `conn.commit()` added to `create_api_key()` |
| M-9 | **IN PROGRESS** | Image reference updated to `quay.io/rhpds/rcars-pgvector`; manual build required |
| M-11 | **IN PROGRESS** | Backend opt-out will hash email; frontend dead-code parameter to be removed |
| M-14 | **IN PROGRESS** | OAuthClient to be scoped by environment (`rcars-api-{{ env }}`) |
| M-16 | **FIXED** | ReadinessProbes on scan-worker + recommend-worker; liveness+readiness on Redis |

### Deferred (owner decision)

| Finding | Disposition | Reason |
|---------|-------------|--------|
| C-1 | Owner action | Nate will generate unique credentials per environment |
| H-3 | Acknowledged | MCP SQL interpolation — safe today, add safety comments. Full refactor deferred |
| H-5 | Deferred | Ansible Vault — will formalize with future GitOps deployment approach |
| M-5 | Deferred | SSRF DNS rebinding — complex httpx transport change |
| M-6 | Deferred | NetworkPolicies — separate infrastructure hardening ticket |
| M-7 | Deferred | Redis TLS — NetworkPolicies are the preferred compensating control |
| M-8 | Deferred | PostgreSQL TLS — same rationale as M-7 |
| M-10 | Accepted risk | Management SA permissions — single operator with access |
| M-12 | **CLOSED** | Jira personal token is the official IT-provided solution |
| M-13 | Accepted risk | Redis cmdline password — requires cluster compromise to exploit |
| M-15 | Partial | pgvector covered by M-9; Red Hat registry tags accepted as trusted |

### Tests

130 passed, 0 new failures. 2 pre-existing failures (env config + Redis connectivity) unrelated to changes.
