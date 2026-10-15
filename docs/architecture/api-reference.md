# API Reference

RCARS exposes a REST API under `/api/v1/` that serves the React frontend and is available for programmatic access by external tools and services.

## Design Principles

- **API-first architecture** — The frontend communicates with the backend exclusively through REST API calls. There is no server-side rendering, no direct database access from the frontend, and no shared file state. Any client that can make HTTP requests and handle JSON can use the same API the frontend uses.
- **Async job pattern** — Long-running operations (analysis scans, catalog refresh, recommendation queries) return a `job_id` immediately. Poll the result endpoint or connect to the SSE stream for real-time progress.
- **Role-based access** — Three roles control access: `user` (read-only browsing and advisor queries), `curator` (curation tools, content analysis, performance workflow), and `admin` (full system access including scans, config, and maintenance).

## Interactive API Documentation

RCARS uses [FastAPI](https://fastapi.tiangolo.com/), which auto-generates interactive API documentation from the source code:

| Interface | Path | Description |
|-----------|------|-------------|
| **Swagger UI** | `/api/v1/docs` | Interactive explorer with "Try it out" buttons for every endpoint |
| **ReDoc** | `/api/v1/redoc` | Clean, read-only API reference organized by tag |
| **OpenAPI JSON** | `/api/v1/openapi.json` | Machine-readable OpenAPI 3.1 spec for code generation |

Open these paths on your RCARS deployment, not on this documentation site. Swagger UI is the endpoint reference: use its groups to find operations, access requirements, parameters, request and response schemas, and errors. Architecture and user guides explain behavior without maintaining duplicate endpoint inventories.

The reference is generated from the deployed route definitions and models, so it describes that deployment's version rather than an unreleased branch. Retirement workflow operations are in the **Retirement** group; see [Retirement System](retirement-system.md) for lifecycle and safety guidance.

## Authentication

See [External API Access](../user/api-access.md) for obtaining an API key, authenticating in Swagger, and making programmatic requests.

### OAuth Proxy (Web UI)

The production deployment sits behind an OpenShift OAuth proxy. Authenticated users are identified by the `X-Forwarded-Email` header set by the proxy. This is the mechanism used by the web frontend.

### ServiceAccount Bearer Tokens (Programmatic)

For service-to-service calls (e.g., from Publishing House), pass a Kubernetes ServiceAccount bearer token in the `Authorization` header:

```
Authorization: Bearer <token>
```

The token is validated against the Kubernetes TokenReview API and checked against the configured SA allowlist.

### Development Mode

When `RCARS_DEV_USER` is set, requests are authenticated as that user; configured role assignments still determine privileges. This bypass is for local development only.

## Common Patterns

### Async Jobs

Many endpoints return a `job_id` for tracking:

```json
POST /api/v1/advisor/chat
{"message": "Find labs about OpenShift AI", "session_id": null}
→ {"job_id": "abc-123", "session_id": "def-456"}
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

!!! note "Deprecated endpoint"
    `POST /advisor/query` still works but is deprecated. It only supports the recommend intent. Use `POST /advisor/chat` for all new integrations — it handles recommendations plus performance, overlap, infrastructure, item details, and help intents.

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
