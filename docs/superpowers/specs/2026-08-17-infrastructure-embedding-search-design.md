# Infrastructure Embedding Search — Design Spec

**Date:** 2026-08-17
**Jira:** RHDPCD-1003
**Branch:** rhdpcd-1003-infrastructure-catalog

## Problem

The infrastructure chat handler currently searches the `infrastructure` table using ILIKE substring matching. This fails when users phrase queries differently from role names — "what deploys RHOAI?" won't match `ocp4_workload_openshift_ai` by substring. A band-aid fuzzy word-split was added but it's inadequate and unprincipled.

The root cause: the handler isn't using the infrastructure embeddings that are already stored in the `embeddings` table (`content_type='infrastructure'`). The existing `search_embeddings` method can't be used directly because it does INNER JOINs to `content_entities` and `babylon_items` — tables that automation components (workloads, configs) deliberately don't have rows in.

## Solution

Add a focused `search_infrastructure_embeddings` database method. Replace ILIKE in the handler with embedding-based semantic search. Tighten router examples to correctly distinguish automation questions (infrastructure intent) from product-description questions (out_of_scope).

## Architecture

### Why two separate search methods

`search_embeddings` is complex by necessity: catalog items can have multiple embeddings (one per module), require stage and ZT filtering, and need JOIN enrichment from `content_entities`/`babylon_items`. None of that applies to automation components. Sharing would require conditional branching inside the query — more complexity than two focused methods. The only redundancy is the vector distance expression (`1 - (embedding <=> query_vector::vector)`) — a reasonable price.

### Intent boundaries

- **infrastructure intent**: user asks about an automation component by name or by what it deploys/configures. "What deploys RHOAI?" / "What does the RHODS workload do?" / "What configs provision an OpenShift cluster?"
- **out_of_scope**: user asks what a product *is* or does as a product. "What does OpenShift AI do?" — RCARS is not a product encyclopedia.
- **item_facts**: user asks about a specific catalog item (lab, demo, workshop).

The router reads verb framing and subject type to distinguish these. The handler doesn't need to second-guess the router.

## Changes

### 1. `src/api/rcars/db/database.py`

Add method `search_infrastructure_embeddings`:

```python
def search_infrastructure_embeddings(
    self,
    query_embedding: list[float],
    limit: int = 10,
    quality_threshold: float = 0.45,
) -> list[dict]:
    """Vector similarity search across infrastructure embeddings only.
    Returns [{role_name, similarity}] sorted by similarity descending.
    No joins needed — caller fetches full rows from infrastructure table.
    """
    with self._pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT content_id AS role_name,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM embeddings
            WHERE content_type = 'infrastructure'
              AND 1 - (embedding <=> %s::vector) >= %s
            ORDER BY similarity DESC
            LIMIT %s
            """,
            (query_embedding, query_embedding, quality_threshold, limit),
        ).fetchall()
    return rows
```

### 2. `src/api/rcars/services/chat/handlers.py`

Replace the ILIKE search block (exact match + ILIKE + fuzzy fallback) with embedding search:

```python
from rcars.services.analyzer import generate_embedding

# embed the query
query_vec = generate_embedding(query, prefix="search_query")
matches = db.search_infrastructure_embeddings(query_vec, limit=10)

if not matches:
    return HandlerResult(
        blocks=[Block(type="notice", data={
            "kind": "no_items",
            "message": (
                "I didn't find automation matching that. "
                "Try asking 'what deploys OpenShift AI?' or "
                "'what configs provision an OpenShift cluster?'"
            ),
        })],
        scaffold_facts={"error": "no_match", "query": query})

role_names = [r["role_name"] for r in matches]
results = [db.get_infrastructure(rn) for rn in role_names if db.get_infrastructure(rn)]
```

The rest of the handler (fetch linked items, build infra_detail block) stays unchanged.

Remove the band-aid fuzzy search lines (the `"%".join(query.split())` fallback).

### 3. `src/api/rcars/services/chat/registry.py`

Tighten the infrastructure intent's `prompt_fragment`:

```
infrastructure: user asks about an automation component — a workload role or
base config — by name or by what product it deploys/configures. Signal: the
subject is automation (a role name like ocp4_workload_rhods, or "workloads
that deploy X", "configs that provision Y"). NOT for product description
questions ("what does OpenShift AI do?" is out_of_scope — that asks about
a product, not RCARS automation).
```

Add/update examples:

```python
examples=(
    {"message": "what deploys RHOAI?",
     "output": {"intent": "infrastructure", "args": {"search_query": "RHOAI"},
                "scope": None, "item_refs": [], "confidence": 0.9, "clarify": None}},
    {"message": "what does the ocp4_workload_openshift_ai role do?",
     "output": {"intent": "infrastructure", "args": {"search_query": "ocp4_workload_openshift_ai"},
                "scope": None, "item_refs": [], "confidence": 0.95, "clarify": None}},
    {"message": "what automation configures an OpenShift cluster?",
     "output": {"intent": "infrastructure", "args": {"search_query": "OpenShift cluster provisioning"},
                "scope": None, "item_refs": [], "confidence": 0.85, "clarify": None}},
)
```

### 4. `src/api/tests/data/routing_golden.yaml`

Add cases:

```yaml
- message: "what does OpenShift AI do?"
  expect: {intent: out_of_scope}

- message: "what deploys RHOAI?"
  expect: {intent: infrastructure}

- message: "what automation configures an OpenShift cluster?"
  expect: {intent: infrastructure}
```

## Files Changed

| File | Change |
|---|---|
| `src/api/rcars/db/database.py` | Add `search_infrastructure_embeddings` |
| `src/api/rcars/services/chat/handlers.py` | Replace ILIKE with embedding search; remove fuzzy band-aid |
| `src/api/rcars/services/chat/registry.py` | Tighten prompt fragment; update examples |
| `src/api/tests/data/routing_golden.yaml` | Add 3 golden routing cases |

No frontend changes. No new intents. No new block types.

## Testing

- Unit: mock `generate_embedding` and `search_infrastructure_embeddings` in handler tests — verify it calls embedding search instead of `list_infrastructure`
- Golden: 3 new routing cases (2 infrastructure, 1 out_of_scope boundary)
- Manual: exec into scan pod after deploy, ask "what deploys RHOAI?" and "what does OpenShift AI do?" — verify correct routing
