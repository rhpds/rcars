# API Reference

RCARS exposes a REST API under `/api/v1/` that serves the React frontend and is available for programmatic access by external tools and services.

## Design Principles

- **API-first architecture** — The frontend communicates with the backend exclusively through REST API calls. There is no server-side rendering, no direct database access from the frontend, and no shared file state. Any client that can make HTTP requests and handle JSON can use the same API the frontend uses.
- **Async job pattern** — Long-running operations (analysis scans, catalog refresh, recommendation queries) return a `job_id` immediately. Poll the result endpoint or connect to the SSE stream for real-time progress.
- **Role-based access** — Three roles control access: `user` (read-only browsing and advisor queries), `curator` (curation tools, content analysis, retirement workflow), and `admin` (full system access including scans, config, and maintenance).

## Interactive API Documentation

RCARS uses [FastAPI](https://fastapi.tiangolo.com/), which auto-generates interactive API documentation from the source code:

| Interface | Path | Description |
|-----------|------|-------------|
| **Swagger UI** | `/api/v1/docs` | Interactive explorer with "Try it out" buttons for every endpoint |
| **ReDoc** | `/api/v1/redoc` | Clean, read-only API reference organized by tag |
| **OpenAPI JSON** | `/api/v1/openapi.json` | Machine-readable OpenAPI 3.1 spec for code generation |

These docs are always in sync with the deployed code — they're generated from the route definitions, type hints, and Pydantic models at runtime.

## Endpoint Groups

| Tag | Prefix | Auth | Description |
|-----|--------|------|-------------|
| **Health** | `/api/v1/health` | None | Liveness and readiness probes |
| **Auth** | `/api/v1/auth` | User | Current user identity and roles |
| **Advisor** | `/api/v1/advisor` | User | Recommendation queries, sessions, and selections |
| **Catalog** | `/api/v1/catalog` | User+ | Browsing, search, curation, workload mappings |
| **Content Analysis** | `/api/v1/analysis` | Curator+ | Scans, stale checks, single-item analysis |
| **Retirement** | `/api/v1/analysis/retirement` | Curator+ | Retirement scoring, workflow (review → approve → notify → start) |
| **Administration** | `/api/v1/admin` | Admin | Jobs, workers, maintenance, token usage, overlap |

## Authentication

The API supports two authentication mechanisms:

### OAuth Proxy (Web UI)

The production deployment sits behind an OpenShift OAuth proxy. Authenticated users are identified by the `X-Forwarded-Email` header set by the proxy. This is the mechanism used by the web frontend.

### ServiceAccount Bearer Tokens (Programmatic)

For service-to-service calls (e.g., from Publishing House), pass a Kubernetes ServiceAccount bearer token in the `Authorization` header:

```
Authorization: Bearer <token>
```

The token is validated against the Kubernetes TokenReview API and checked against the configured SA allowlist.

### Development Mode

When `RCARS_DEV_USER` is set, all requests are authenticated as that user with full admin access. This is for local development only.

## Common Patterns

### Async Jobs

Many endpoints return a `job_id` for tracking:

```json
POST /api/v1/advisor/query
→ {"job_id": "abc-123"}
```

Then either poll:
```json
GET /api/v1/advisor/query/abc-123/result
→ {"status": "running", "result": null, "error": null}
```

Or stream via SSE:
```
GET /api/v1/advisor/query/abc-123/stream
→ data: {"type": "triage", "progress": 3, "total": 10, ...}
→ data: {"type": "complete", "result": {...}}
```

### Pagination

List endpoints accept `limit` and `offset` query parameters:

```
GET /api/v1/catalog?limit=25&offset=50
```

### Error Responses

All errors follow the standard FastAPI format:

```json
{"detail": "Catalog item not found"}
```

With appropriate HTTP status codes: 401 (unauthenticated), 403 (insufficient role), 404 (not found), 422 (validation error), 429 (rate limited).
