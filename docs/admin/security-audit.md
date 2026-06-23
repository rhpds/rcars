# RCARS Security Audit Report

**Date:** 2026-06-23
**Commit:** `8e2d99d432e952c7f6cd3d08e580f4f54c4e16c4` (main)
**Auditor:** Automated security review (Claude Opus 4.6) with adversarial verification
**Scope:** Full repository — Python backend, React frontend, Ansible/OpenShift deployment, LLM integration

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 10 |
| LOW | 10 |
| INFO | 5 |

The codebase demonstrates strong security fundamentals: all containers run as non-root with dropped capabilities, secrets are properly managed through gitignored Ansible vars and K8s Secrets, SQL queries use parameterized placeholders consistently, and the auth middleware enforces role-based access on all non-health endpoints. The two HIGH findings (SSRF and XSS) are the priority remediation items.

---

## HIGH Findings

### H-1: Server-Side Request Forgery (SSRF) via Event URLs in Advisor Queries — FIXED

**Severity:** HIGH
**Files:** `src/api/rcars/services/event_parser.py:34-43`, `src/api/rcars/services/recommender/pipeline.py:175-181`
**Adversarially verified:** Yes — traced user input from `QueryRequest.query` through `_extract_urls()` to `httpx.get()` with no URL validation.
**Status:** Fixed in PR #50 — `_validate_url()` added with private IP blocklist, DNS resolution check, HTTPS enforcement, and redirect validation.

**Evidence:**

```python
# event_parser.py:34-38
def _fetch_html(url: str, timeout: int = 30) -> str | None:
    try:
        response = httpx.get(url, follow_redirects=True, timeout=timeout,
                             headers=_HTTP_HEADERS)
```

```python
# pipeline.py:175-181
urls, remaining_text = _extract_urls(query)
if urls:
    url = urls[0]
    event_profile = parse_event_url(url, settings=settings, model=settings.model)
```

**Attack:** Any authenticated user submits a query like `"recommend demos for https://169.254.169.254/latest/meta-data/"`. The server extracts URLs from the query text via regex, then fetches the first URL from within the server's network context. With `follow_redirects=True`, an attacker can also host a redirect from a public URL to an internal target. Fetched content is sent to the LLM, so response data can be extracted through the analysis output.

**Impact:** Internal network probing, cloud metadata exfiltration, access to ClusterIP services (Redis, PostgreSQL, internal APIs).

**Recommendation:**
1. Validate URLs against a blocklist of private/internal IP ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, fd00::/8)
2. Resolve DNS before fetching and validate the resolved IP against the same blocklist
3. Disable `follow_redirects` or validate each redirect target
4. Restrict to HTTPS-only
5. Consider an allowlist of known event/conference domains

---

### H-2: Cross-Site Scripting (XSS) via `dangerouslySetInnerHTML` on LLM Output — FIXED

**Severity:** HIGH
**File:** `src/frontend/src/pages/AdvisorPage.tsx:30, 36-38, 51`
**Adversarially verified:** Yes — confirmed `dangerouslySetInnerHTML` renders unsanitized LLM-generated `overall_assessment` text.
**Status:** Fixed in PR #50 — `escapeHtml()` now runs before markdown transforms in `inlineMd()`, neutralizing HTML injection before `dangerouslySetInnerHTML` renders.

**Evidence:**

```tsx
// Line 36-38: regex converts markdown to HTML but does NOT escape existing HTML
const inlineMd = (s: string) =>
  s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
   .replace(/`([^`]+)`/g, '<code ...>$1</code>')

// Line 30: rendered unsanitized
{listItems.map((li, i) => <li key={i} dangerouslySetInnerHTML={{ __html: inlineMd(li) }} />)}

// Line 51: rendered unsanitized
<p key={`p-${i}`} dangerouslySetInnerHTML={{ __html: inlineMd(line) }} />
```

**Attack:** If LLM output contains `<img src=x onerror=alert(document.cookie)>`, the `inlineMd()` function passes it through untouched and `dangerouslySetInnerHTML` renders it as live DOM. The attack chain: (1) attacker embeds prompt injection payload in a Showroom repo they control, (2) RCARS scans the content and stores LLM-generated analysis, (3) the analysis results flow into advisor rationale text, (4) `overall_assessment` containing the payload is stored in DB and rendered to all users who view that session.

**Mitigating factors:** Requires attacker to have commit access to a Showroom repo AND successfully inject through the LLM's structured JSON output parsing. Session IDs are UUIDs (not enumerable).

**Recommendation:** Replace `dangerouslySetInnerHTML` with React elements — rewrite `inlineMd()` to split on regex patterns and return `<strong>` and `<code>` React elements directly. If raw HTML is required, sanitize with DOMPurify before insertion.

---

## MEDIUM Findings

### M-1: Indirect Prompt Injection via Showroom Content — FIXED

**Severity:** MEDIUM
**File:** `src/api/rcars/services/analyzer.py:483-513`
**Status:** Fixed in PR #51 — system/user prompt separation enforces boundary at the API level across all 5 call sites.

**Evidence:**

```python
def build_analysis_prompt(ci_name, display_name, category, product, content_files):
    template = PROMPT_TEMPLATE_PATH.read_text()
    content_parts = []
    for filename, content in sorted(content_files.items()):
        content_parts.append(f"=== File: {filename} ===\n{content}")
    all_content = "\n\n".join(content_parts)
    # ... inserted directly into prompt via string replacement
```

Content from external Showroom repos (cloned from GitHub) is concatenated directly into the LLM analysis prompt without sanitization. A malicious actor with commit access to a Showroom repo could embed instructions that manipulate LLM analysis output. The same pattern applies to triage prompts (`triage.py:50-53`) and rationale prompts (`rationale.py:94-101`).

**Recommendation:**
1. Use Anthropic API's `system` parameter to separate trusted instructions from external data (see M-4)
2. Wrap external content in XML delimiters (e.g., `<external-content>...</external-content>`) with explicit instructions to treat as data
3. Validate LLM JSON outputs against strict schemas before storing

---

### M-2: IDOR — Advisor Sessions Accessible Across Users — FIXED

**Severity:** MEDIUM
**Files:** `src/api/rcars/api/routes/advisor.py:77-83`, `src/api/rcars/db/database.py:1388-1394`
**Status:** Fixed in PR #30 — `user_email` filter added to `get_advisor_session()` and `update_advisor_session_choice()`.

**Evidence:**

```python
# advisor.py:77-83
@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request, user: str = Depends(require_auth)):
    turns = db.get_advisor_session(session_id)  # No ownership check
    # ...

# database.py:1388-1394
def get_advisor_session(self, session_id: str) -> list[dict]:
    cur = conn.execute(
        "SELECT * FROM advisor_sessions WHERE session_id = %s ORDER BY turn_index",
        (session_id,),  # No user_email filter
    )
```

Any authenticated user can read or modify any other user's advisor sessions by knowing the session_id. The `list_sessions()` endpoint correctly scopes by `user_email=user`, but `get_session()` and `select_recommendation()` do not verify ownership. UUIDs reduce brute-force risk but do not eliminate it (session IDs could leak via logs, shared links, or referrer headers).

**Recommendation:** Add `WHERE user_email = %s` to `get_advisor_session()` and `update_advisor_session_choice()` queries, or verify ownership at the route level.

---

### M-3: No Rate Limiting on LLM-Consuming Endpoints

**Severity:** MEDIUM
**Files:** `src/api/rcars/api/routes/advisor.py:27`, `src/api/rcars/api/routes/analysis.py:109,143`

No rate limiting library is configured. The `/advisor/query` endpoint is available to any authenticated user and triggers multi-phase LLM calls (vector search + Haiku triage + Sonnet rationale). The arq worker's `max_jobs=3` provides backpressure on concurrent execution but not queue depth — a single user could flood the queue with hundreds of queries, consuming LLM API credits and starving other users.

**Recommendation:** Add per-user rate limiting via `slowapi` or Redis-backed sliding window on at minimum `POST /advisor/query` (e.g., 10-20 requests per minute per user).

---

### M-4: No System/User Prompt Separation in LLM Calls — FIXED

**Severity:** MEDIUM
**File:** `src/api/rcars/config.py:181-239`
**Status:** Fixed in PR #51 — `call_llm()` now accepts `system` parameter; Anthropic uses native `system` kwarg, LiteMaaS uses OpenAI `system` role.

All LLM calls send a single `{"role": "user", "content": prompt}` message combining system instructions with external data. The Anthropic API's dedicated `system` parameter is not used. Separating system instructions from user/data content provides defense-in-depth against prompt injection.

**Recommendation:** Refactor `call_llm()` to accept an optional `system` parameter. Move instructional parts of prompt templates into the system prompt; keep only external data in the user message.

---

### M-5: Missing nginx Security Headers

**Severity:** MEDIUM
**File:** `src/frontend/nginx.conf:21-55`

The nginx configuration has no security headers: no `X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`, `Strict-Transport-Security`, `Referrer-Policy`, or `Permissions-Policy`. Server version is not suppressed (`server_tokens` not set to `off`).

**Recommendation:** Add to the `server` block:
```nginx
server_tokens off;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

---

### M-6: No Content Security Policy (CSP)

**Severity:** MEDIUM
**Files:** `src/frontend/index.html`, `src/frontend/nginx.conf`

No CSP is configured in either the HTML meta tag or nginx headers. Without CSP, the browser allows execution of inline scripts and loading resources from any origin, widening the blast radius of any XSS vulnerability (such as H-2).

**Recommendation:** Configure CSP headers in nginx:
```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'
```

---

### M-7: Source Maps Shipped in Production Builds

**Severity:** MEDIUM
**File:** `src/frontend/vite.config.ts:18`

```typescript
build: {
  sourcemap: true,  // generates .map files in production
},
```

Production builds include full source maps (1.6 MB) exposing the entire TypeScript source, component structure, API endpoints, and admin functionality to anyone who accesses the application.

**Recommendation:** Set `sourcemap: false` or `sourcemap: 'hidden'` (generates maps for error tracking services but does not reference them in the JS bundle).

---

### M-8: No NetworkPolicies Defined

**Severity:** MEDIUM
**Files:** All of `ansible/templates/`, `ansible/tasks/`

Zero `NetworkPolicy` resources anywhere in the project. All pods in the namespace can communicate with each other and with any namespace. PostgreSQL and Redis are accessible from any pod in the cluster.

**Recommendation:** Add NetworkPolicies:
1. Default deny all ingress for the namespace
2. Allow PostgreSQL/Redis ingress only from API, scan-worker, and recommend-worker pods
3. Allow API ingress only from the frontend nginx pod

---

### M-9: Redis Has No Authentication

**Severity:** MEDIUM
**File:** `ansible/templates/manifests-infra.yaml.j2:224-271`

Redis is deployed with no `requirepass` and no auth secret. Connection URL is plain `redis://rcars-redis:6379`. Any pod in the cluster can connect without authentication.

**Recommendation:** Add a Redis password via a K8s Secret and configure `--requirepass`. Update `RCARS_REDIS_URL` to `redis://:$(REDIS_PASSWORD)@rcars-redis:6379`. Mitigated by ClusterIP (not externally exposed), but any compromised pod could access job queues.

---

### M-10: Missing `readOnlyRootFilesystem` on All Containers

**Severity:** MEDIUM
**Files:** `ansible/templates/manifests-app.yaml.j2:170-173,305-308,411-414,474-477,566-569`, `ansible/templates/manifests-infra.yaml.j2:198-201,264-266`

All seven container `securityContext` blocks set `allowPrivilegeEscalation: false` and `capabilities.drop: ["ALL"]` but none include `readOnlyRootFilesystem: true`.

**Recommendation:** Add `readOnlyRootFilesystem: true` to each container. Use `emptyDir` volume mounts for writable paths (nginx temp, PostgreSQL data, Redis data, API clone workspace).

---

## LOW Findings

### L-1: No Input Length Validation on Advisor Queries

**File:** `src/api/rcars/api/routes/advisor.py:14-15`

`QueryRequest.query` has no `max_length` constraint. An attacker could submit extremely long query strings causing excessive token consumption and storage bloat.

**Recommendation:** Add `query: str = Field(max_length=2000)`.

---

### L-2: IDOR — Job Results Accessible Across Users

**File:** `src/api/rcars/api/routes/advisor.py:57-67`

`get_query_result()` and `stream_query()` accept any `job_id` without verifying `created_by` matches the authenticated user. Mitigated by UUID randomness.

**Recommendation:** Add ownership check: `if job["created_by"] != user: raise HTTPException(403)`.

---

### L-3: Enrichment Tag Deletion Without CI Name Validation — FIXED

**Files:** `src/api/rcars/api/routes/catalog.py:207-211`, `src/api/rcars/db/database.py:680-683`
**Status:** Fixed in PR #30 — DELETE query now includes `AND ci_name = %s`.

The `ci_name` in the URL path is not used in the DELETE query — a curator could delete a tag from a different catalog item by supplying a mismatched `tag_id`.

**Recommendation:** Change SQL to `DELETE FROM enrichment_tags WHERE id = %s AND ci_name = %s`.

---

### L-4: Weak Pydantic Model Validation

**File:** `src/api/rcars/api/routes/catalog.py:106-110,195-197,232-233,254-255`

`OverrideUrlRequest.url` has no URL format validation. `ContentPathRequest.path` has no path traversal protection. `WorkloadMappingRequest`, `TagRequest`, `NoteRequest` have no `max_length` constraints.

**Recommendation:** Add `max_length` to string fields, `HttpUrl` type to URL fields, path pattern validation.

---

### L-5: No Request Body Size Limits

**File:** `src/api/rcars/api/app.py`

No `ContentSizeLimitMiddleware` or global body size cap configured.

**Recommendation:** Add `starlette.middleware.ContentSizeLimitMiddleware` with a reasonable cap (e.g., 1 MB).

---

### L-6: Error Messages Expose Internal Details via SSE

**File:** `src/api/rcars/workers/recommend.py:101-103`

Raw exception messages (which can contain internal paths, DB connection strings, stack trace fragments) are published to the SSE stream and stored in the jobs table.

**Recommendation:** Sanitize error messages before publishing. Map known exception types to user-friendly messages; use generic fallback for unknown exceptions.

---

### L-7: Unvalidated External URLs Rendered as Clickable Links

**File:** `src/frontend/src/pages/BrowsePage.tsx:679`

`showroom_url` from the backend is rendered directly as `href` without URL scheme validation. React 19 blocks `javascript:` URLs by default, but defense-in-depth suggests validation.

**Recommendation:** Add scheme validation: `const isSafeUrl = (url: string) => /^https?:\/\//i.test(url)`.

---

### L-8: SSRF Risk in Showroom URL Override (Curator-Only)

**File:** `src/api/rcars/api/routes/catalog.py:236-239`

Curators can set arbitrary URLs as showroom overrides. The URL is later used in `git clone` during scans. Mitigated by requiring curator role.

**Recommendation:** Validate override URLs match expected patterns (e.g., `https://github.com/` or `https://gitlab.com/` prefix).

---

### L-9: OAuth Proxy Image Uses `:latest` Tag

**File:** `ansible/vars/common.yml:15`

```yaml
oauth_proxy_image: "registry.redhat.io/openshift4/ose-oauth-proxy-rhel9:latest"
```

**Recommendation:** Pin to a specific version tag (e.g., `v4.16`) for reproducibility.

---

### L-10: No CSRF Protection (Mitigated by Architecture)

**File:** `src/frontend/src/services/api.ts`

No CSRF tokens or `SameSite` cookie configuration. Mitigated by OAuth proxy architecture (browser never holds API auth cookies) and JSON `Content-Type` (requires CORS preflight).

**Recommendation:** Acceptable given OAuth proxy architecture. For defense-in-depth, verify `Origin` or `Referer` headers on state-changing requests.

---

## INFO Findings

### I-1: Admin Query History Exposes All Users' Queries

**File:** `src/api/rcars/api/routes/admin.py:130-147`

Admins can view all users' full query text. The `opted_out` mechanism nullifies text but is opt-in. Acceptable design trade-off for admin observability.

### I-2: OAuth Proxy `email-domain=*` Accepts Any Domain

**File:** `ansible/templates/manifests-app.yaml.j2:528`

Standard for OpenShift OAuth proxy using the built-in `openshift` provider. No action needed unless the provider changes.

### I-3: OAuthClient `grantMethod: auto` Skips User Consent

**File:** `ansible/templates/manifests-infra.yaml.j2:346`

Standard for internal applications on trusted clusters.

### I-4: FastAPI Docs/OpenAPI Exposed in All Environments

**File:** `src/api/rcars/api/app.py:38-40`

API sits behind OAuth proxy so docs require authentication. Low risk. Consider disabling in production via environment variable check.

### I-5: Dead `api_keys` Table Schema

**File:** `src/api/rcars/db/database.py:157-166`

The `api_keys` table is defined but has no corresponding routes, middleware, or service code. Remove or document as planned future work.

---

## Areas Checked and Found Clean

### Secrets & Credentials — CLEAN
- No hardcoded secrets, API keys, tokens, or passwords in source code (only local dev placeholder `rcars:dev` in dev-services.sh)
- `.env` and `ansible/vars/{dev,prod}.yml` properly gitignored; never appear in git history
- Git history clean: searched for `AKIA`, `sk-`, `password`, `api_key` patterns — no actual credentials found
- All production secrets managed through gitignored Ansible vars → K8s Secrets at deploy time
- Example files use `CHANGEME` placeholders consistently
- No `.env` files exist in the repository
- Kubeconfig output writes to `~/devel/secrets/` (outside repo)
- Auth middleware explicitly does not log raw tokens (auth.py:31)

### SQL Injection — CLEAN
- All database queries in `database.py` (~1760 lines) use psycopg3 parameterized queries (`%s`, `%(name)s`)
- Dynamic `ORDER BY` in `list_reporting_metrics` validated against strict allowlist before interpolation
- No use of `eval()`, `exec()`, or `yaml.unsafe_load()` anywhere in the codebase
- `subprocess.run()` always uses list-form arguments (never `shell=True`)

### Authentication & Authorization — CLEAN
- Dev bypass (`RCARS_DEV_USER`) explicitly set to empty string in deployment template — cannot be accidentally enabled in production
- Header injection not possible: OAuth proxy is the only external Route; API is ClusterIP-only
- All 45 endpoints audited: health checks unauthenticated (correct), all others have appropriate `require_auth`/`require_curator`/`require_admin` decorators
- Role derivation is server-side from env vars only — no user-facing endpoint to modify roles
- SA tokens validated via K8s TokenReview API with explicit allowlist; unknown SAs rejected
- No session fixation risk — application is stateless; authentication on every request

### Container Security — CLEAN
- All containers set `runAsNonRoot: true`, `seccompProfile: RuntimeDefault`, `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]`
- All containers have CPU/memory requests and limits defined
- All base images use Red Hat UBI9 from trusted registries
- Multi-stage builds used correctly — no source code or dev dependencies in runtime images
- No secrets copied into container images

### RBAC — CLEAN
- ClusterRole scoped to only `namespaces` and `oauthclients` resources
- Namespace-level admin RoleBinding scoped to `target_namespace` only
- TokenReview uses `system:auth-delegator` (read-only validation)
- No cluster-admin or wildcard RBAC found

### Network Architecture — CLEAN
- Only one Route exists (OAuth proxy frontend)
- API, PostgreSQL, Redis all ClusterIP-only — not externally exposed
- `rcars_api_external_route` defaults to `false`
- TLS edge termination with HTTP→HTTPS redirect

### CORS — CLEAN (Not Applicable)
- No CORS middleware configured — correct because frontend nginx reverse-proxies API requests on same origin
- No cross-origin access pattern exists

### Frontend Security — CLEAN
- No `localStorage`/`sessionStorage`/cookie usage for sensitive data
- No `eval()`, `Function()`, or dynamic code execution
- No hardcoded API keys or credentials
- All `target="_blank"` links include `rel="noopener noreferrer"`
- URL parameters consistently use `encodeURIComponent()`
- Client-side role checks are cosmetic; actual authorization is server-side
- The frontend handles zero tokens — authentication is entirely server-side via OAuth proxy
- `npm audit`: 1 moderate vulnerability in dev-only dependency (`brace-expansion` in `@typescript-eslint/typescript-estree`) — not shipped to production

### LLM Integration — CLEAN
- All LLM calls use `temperature=0` (deterministic, appropriate for structured extraction)
- All LLM calls specify explicit `max_tokens` limits (1024–8192)
- Model selection via server config, not user-controllable
- Embedding model (`all-MiniLM-L6-v2`) runs locally — no data exfiltration vector
- Prompt templates stored as static `.txt` files in container image — not modifiable at runtime
- LLM provider fallback chain (LiteMaaS → Vertex/Anthropic) handles failures cleanly
- `parse_analysis_response()` does defensive JSON extraction — no `eval()` or unsafe deserialization
- Worker job isolation: separate queues, concurrency limits, timeouts

### Path Traversal — CLEAN
- Clone paths generated with UUID suffix under controlled directory
- File reads restricted to `.adoc` files within clone path
- Workload scanner restricted to `clone_path / "roles" / role_name`

### Data Privacy — CLEAN
- `opted_out` flag in advisor sessions suppresses query text and results storage

---

## Remediation Priority

| Priority | Finding | Effort | Status |
|----------|---------|--------|--------|
| 1 | H-1: SSRF — add URL validation/blocklist to event_parser.py | Low | **FIXED** (PR #50) |
| 2 | H-2: XSS — escape HTML before markdown transforms | Low | **FIXED** (PR #50) |
| 3 | M-2: IDOR — add user_email filter to session/job queries | Low | **FIXED** (PR #30) |
| 4 | M-5+M-6: nginx security headers + CSP | Low | Open |
| 5 | M-7: Disable source maps in production | Trivial | Open |
| 6 | M-3: Rate limiting on /advisor/query | Medium | Open |
| 7 | M-1+M-4: System prompt separation + content delimiters | Medium | **FIXED** (PR #51) |
| 8 | M-8: NetworkPolicies | Medium | Open |
| 9 | M-9: Redis authentication | Low | Open |
| 10 | M-10: readOnlyRootFilesystem | Low | Open |
