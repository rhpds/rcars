# Content Owner Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pure stub virtual CI stops owning an analysis: the scan skips it, deletes its artifacts, mirrors its owner's card fields, and the Advisor shows the stub instead of the owner.

**Architecture:** One helper, `content_owner(item)`, reads the already-resolved `showroom_source_json` link and decides ownership. Every path uses it. No path compares `AnalysisSignature` hashes to decide ownership. The scan owns reconciliation and card mirroring. The Advisor replaces an owner hit with its single stub. Reads go through a new `db.get_display_analysis()`.

**Tech Stack:** Python 3.11, FastAPI 2.0, psycopg 3 + psycopg_pool, PostgreSQL + pgvector, pytest + pytest-asyncio. React 19 + TypeScript for the Browse line.

**Spec:** `docs/superpowers/specs/2026-11-04-content-owner-model-design.md`

**Jira:** RHDPCD-2238

## Global Constraints

- Ownership is decided only by `content_owner(item)` from `rcars/services/showroom_source.py`. No module may compare signatures to decide ownership.
- `find_showroom_donor` and `order_for_reuse` stay unchanged. They still serve stage siblings (RHDPCD-74). Changing them is out of scope.
- The stage-counterpart half of `_authorized_promotion` (`vector_search.py:146-149`) stays. Only the alias half is replaced.
- Curator **source** overrides (`showroom_url_override`, `content_path`) are not curated fields. They must never be redirected to the owner; they make a CI stop being a stub.
- No schema change. `SCHEMA_SQL` in `src/api/rcars/db/database.py` is untouched.
- Tests need PostgreSQL with pgvector on `localhost:5432` and Redis on `localhost:6379`. Run them as:
  `source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest ...`
- All test data uses the `isolation-test.` CI-name prefix so the `tests/showroom_helpers.py` fixture cleans it.
- Commit subjects: `[RHDPCD-2238] Imperative description`. End every commit message with `Co-Authored-By: Claude Code <noreply@anthropic.com>`.

## Review Focus

- A CI in the middle of the chain that overrides `ref` or `content_path` must stay a normal, scanned CI. Task 1 and Task 3 pin it.
- A curator `content_path` override on an existing stub must return it to normal scanning. Task 1 and Task 3 pin it.
- An owner with zero stubs, or with two stubs, must be shown as the owner. Task 6 pins it.
- A stub outside the requested stages or scope must not replace its owner. Task 6 pins it.
- An owner whose scan returns `unchanged` must still mirror its card fields to a newly added stub. Task 5 pins it.

---

### Task 1: `content_owner` helper

**Files:**
- Modify: `src/api/rcars/services/showroom_source.py`
- Test: `src/api/tests/test_showroom_source.py`

**Interfaces:**
- Consumes: `effective_showroom_source(item) -> ResolvedShowroom` (already in this module). `ResolvedShowroom` has `status`, `owner_ci_name`, `override_origins: dict[str, str]`.
- Produces: `content_owner(item: dict) -> str | None`. Returns the owner CI name when `item` is a pure stub, else `None`. Every later task imports this.

- [ ] **Step 1: Write the failing tests**

Append to `src/api/tests/test_showroom_source.py` (it already defines `node()` and `resolve()`):

```python
from rcars.services.showroom_source import content_owner


def test_pure_stub_returns_its_content_owner():
    result = resolve(node("example.virtual.prod", links=("example.content.prod",)),
                     node("example.content.prod", repo=URL))
    item = {"ci_name": "example.virtual.prod", "showroom_source": result.to_dict()}
    assert content_owner(item) == "example.content.prod"


def test_owner_is_not_its_own_stub():
    result = resolve(node("example.content.prod", repo=URL))
    item = {"ci_name": "example.content.prod", "showroom_source": result.to_dict()}
    assert content_owner(item) is None


def test_mid_chain_override_is_not_a_pure_stub():
    result = resolve(node("example.virtual.prod", links=("example.wrapper.prod",)),
                     node("example.wrapper.prod", ref="custom", links=("example.content.prod",)),
                     node("example.content.prod", repo=URL, ref="main"))
    item = {"ci_name": "example.virtual.prod", "showroom_source": result.to_dict()}
    assert result.override_origins == {"ref": "example.wrapper.prod"}
    assert content_owner(item) is None


def test_curator_content_path_override_is_not_a_pure_stub():
    result = resolve(node("example.virtual.prod", links=("example.content.prod",)),
                     node("example.content.prod", repo=URL))
    item = {"ci_name": "example.virtual.prod", "showroom_source": result.to_dict(),
            "content_path": "content/modules/ROOT/pages"}
    assert content_owner(item) is None


@pytest.mark.parametrize("source", [None, {"status": "invalid"}, {"status": "none"}, {"status": "ambiguous"}])
def test_unresolved_source_has_no_content_owner(source):
    assert content_owner({"ci_name": "example.virtual.prod", "showroom_source": source}) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_showroom_source.py -k content_owner -v`
Expected: FAIL with `ImportError: cannot import name 'content_owner'`.

- [ ] **Step 3: Implement `content_owner` in `src/api/rcars/services/showroom_source.py`**

Place it after `effective_showroom_source`.

```python
def content_owner(item: dict) -> str | None:
    """Owner CI name when item is a pure stub, else None.

    A pure stub resolves to an owner other than itself and nothing at or below
    the stub overrode repo, ref, or content_path.
    """
    source = effective_showroom_source(item)
    name = item.get("ci_name") or item.get("content_id") or ""
    if source.status != "resolved" or not source.owner_ci_name:
        return None
    if source.owner_ci_name == name:
        return None
    if any(origin != source.owner_ci_name for origin in source.override_origins.values()):
        return None
    return source.owner_ci_name
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_showroom_source.py -v`
Expected: PASS for the whole file.

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/showroom_source.py src/api/tests/test_showroom_source.py
git commit -m "[RHDPCD-2238] Add content_owner helper for pure stubs

Decide stub ownership from the resolved AgnosticV chain instead of
comparing analysis signatures.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 2: Database read and write methods for stubs

**Files:**
- Modify: `src/api/rcars/db/database.py` (add to the class; place near `get_virtual_content_aliases` at ~line 1893 and `clear_embeddings` at ~line 1937)
- Test: `src/api/tests/test_content_owner.py` (create)

**Interfaces:**
- Consumes: `content_owner` from Task 1.
- Produces:
  - `get_pure_stubs_for_owner(owner_ci_name: str, stages: list[str] | None = None, conn=None) -> list[dict]`
  - `get_stub_reconciliation_candidates() -> list[dict]`
  - `delete_stub_artifacts(content_id: str, conn=None) -> dict[str, int]`
  - `mirror_content_owner(stub_content_id: str, owner_ci_name: str, conn=None) -> None`

- [ ] **Step 1: Write the failing tests**

Create `src/api/tests/test_content_owner.py`:

```python
from types import SimpleNamespace

from tests.showroom_helpers import db
from rcars.services.showroom_source import ResolvedShowroom

URL = "https://github.com/example/content"


def add_item(db, name, *, owner_ci_name=None, paths=None, override_origins=None, repo=URL, **overrides):
    owner = owner_ci_name or name
    source = ResolvedShowroom("resolved", owner, name.rsplit(".", 1)[0], repo, "main",
                              paths=paths or ((name,),),
                              override_origins=override_origins or {})
    return db.upsert_babylon_catalog_item({
        "ci_name": name, "stage": name.rsplit(".", 1)[-1], "display_name": name,
        "category": "Workshop", "showroom_url": repo, "showroom_ref": "main",
        "showroom_source": source.to_dict(), **overrides})


def seed_stub_artifacts(db, content_id, summary="Own stub summary"):
    db.upsert_showroom_analysis({"content_id": content_id, "summary": summary,
                                 "modules_json": [], "content_hash": "content"})
    db.store_embedding(content_id, "lab", "babylon", "summary", summary, [0.1] * 768)


def test_get_pure_stubs_for_owner_returns_only_pure_stubs(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod",
                    paths=(("isolation-test.virtual.prod", "isolation-test.owner.prod"),))
    overridden = add_item(db, "isolation-test.override.prod", owner_ci_name="isolation-test.owner.prod",
                          paths=(("isolation-test.override.prod", "isolation-test.owner.prod"),),
                          override_origins={"ref": "isolation-test.middle.prod"})
    rows = db.get_pure_stubs_for_owner("isolation-test.owner.prod")
    assert [row["content_id"] for row in rows] == [stub]
    assert overridden not in [row["content_id"] for row in rows]


def test_get_pure_stubs_for_owner_honours_stages(db):
    add_item(db, "isolation-test.owner.prod")
    dev = add_item(db, "isolation-test.virtual.dev", owner_ci_name="isolation-test.owner.prod",
                   paths=(("isolation-test.virtual.dev", "isolation-test.owner.prod"),))
    assert [row["content_id"] for row in db.get_pure_stubs_for_owner(
        "isolation-test.owner.prod", stages=["prod"])] == []
    assert [row["content_id"] for row in db.get_pure_stubs_for_owner(
        "isolation-test.owner.prod", stages=["dev"])] == [dev]


def test_delete_stub_artifacts_removes_analysis_embeddings_and_overlaps(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    seed_stub_artifacts(db, stub)
    with db.pool.connection() as conn:
        conn.execute("INSERT INTO overlap_candidates (content_id_a, content_id_b, shared_products, "
                     "shared_topics, content_hash_a, content_hash_b) VALUES (%s, %s, 1, 1, 'a', 'b') "
                     "ON CONFLICT DO NOTHING", (owner, stub))
    result = db.delete_stub_artifacts(stub)
    assert result == {"analysis": 1, "embeddings": 1, "overlaps": 1}
    assert db.get_showroom_analysis(stub) is None
    assert db.get_embeddings_for_content(stub) == []


def test_mirror_content_owner_copies_card_fields_and_scan_status(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    db.update_content_entity_card(owner, summary="Owner summary", products_json=["OpenShift"],
                                  topics_json=["virt"], audience_json=["architect"],
                                  difficulty="intermediate")
    db.set_scan_status(owner, "success")
    db.mirror_content_owner(stub, "isolation-test.owner.prod")
    card = db.get_content_entity(stub)
    assert card["summary"] == "Owner summary"
    assert card["products_json"] == ["OpenShift"]
    assert card["topics_json"] == ["virt"]
    assert card["audience_json"] == ["architect"]
    assert card["difficulty"] == "intermediate"
    assert card["scan_status"] == "success"


def test_get_stub_reconciliation_candidates_includes_stubs(db):
    add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    ids = {row["content_id"] for row in db.get_stub_reconciliation_candidates()}
    assert stub in ids
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_content_owner.py -v`
Expected: FAIL with `AttributeError: 'Database' object has no attribute 'get_pure_stubs_for_owner'`.

- [ ] **Step 3: Implement the four methods**

Add `content_owner` to the `rcars.services.showroom_source` import list at the top of `database.py`.

```python
def get_pure_stubs_for_owner(self, owner_ci_name: str, stages: list[str] | None = None,
                             conn=None) -> list[dict]:
    """Non-retired Babylon items whose content owner is owner_ci_name."""
    sql = """
        SELECT ce.*, bi.*, ce.scan_status
        FROM content_entities ce
        JOIN babylon_items bi ON bi.content_id = ce.content_id
        WHERE ce.retired_at IS NULL
          AND bi.showroom_source_json->>'status' = 'resolved'
          AND bi.showroom_source_json->>'owner_ci_name' = %(owner)s
          AND ce.content_id != %(owner_id)s
    """
    params = {"owner": owner_ci_name, "owner_id": f"babylon:{owner_ci_name}"}
    if stages is not None:
        sql += " AND bi.stage = ANY(%(stages)s)"
        params["stages"] = stages
    sql += " ORDER BY bi.ci_name"
    with self._artifact_connection(conn) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row for row in rows if content_owner(row) == owner_ci_name]


def get_stub_reconciliation_candidates(self) -> list[dict]:
    """Every resolved lab/demo Babylon item; Python decides which are pure stubs."""
    with self._pool.connection() as conn:
        return conn.execute("""
            SELECT ce.*, bi.*, ce.scan_status
            FROM content_entities ce
            JOIN babylon_items bi ON bi.content_id = ce.content_id
            WHERE ce.content_type IN ('lab', 'demo')
              AND ce.retired_at IS NULL
              AND ce.content_id NOT LIKE 'babylon:tests.%%'
              AND bi.showroom_source_json->>'status' = 'resolved'
        """).fetchall()


def delete_stub_artifacts(self, content_id: str, conn=None) -> dict[str, int]:
    """Delete a pure stub's own analysis, embeddings, and overlap pairs."""
    with self._artifact_connection(conn) as conn:
        analysis = conn.execute("DELETE FROM showroom_analysis WHERE content_id = %s",
                                (content_id,)).rowcount
        embeddings = conn.execute("DELETE FROM embeddings WHERE content_id = %s",
                                  (content_id,)).rowcount
        overlaps = conn.execute("DELETE FROM overlap_candidates WHERE content_id_a = %s OR content_id_b = %s",
                                (content_id, content_id)).rowcount
    return {"analysis": analysis, "embeddings": embeddings, "overlaps": overlaps}


def mirror_content_owner(self, stub_content_id: str, owner_ci_name: str, conn=None) -> None:
    """Copy the owner's card fields and scan_status onto its pure stub.

    No-op while the owner has no summary: copying NULL would blank a stub
    whose owner was never scanned.
    """
    with self._artifact_connection(conn) as conn:
        conn.execute("""
            UPDATE content_entities t
            SET summary = o.summary, products_json = o.products_json,
                topics_json = o.topics_json, audience_json = o.audience_json,
                difficulty = o.difficulty, scan_status = o.scan_status, updated_at = NOW()
            FROM content_entities o
            WHERE o.content_id = %s AND t.content_id = %s AND o.summary IS NOT NULL
        """, (f"babylon:{owner_ci_name}", stub_content_id))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_content_owner.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/db/database.py src/api/tests/test_content_owner.py
git commit -m "[RHDPCD-2238] Add database methods for pure stub reconciliation

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 3: Scan skips pure stubs

**Files:**
- Modify: `src/api/rcars/db/database.py` (`get_items_needing_analysis` at ~2712, `get_stale_check_candidates` at ~2741)
- Modify: `src/api/rcars/services/showroom_scan.py` (guard in `_scan_babylon_item`, after the `excluded` check)
- Test: `src/api/tests/test_content_owner.py`, `src/api/tests/test_showroom_scan.py`

**Interfaces:**
- Consumes: `content_owner` (Task 1); `delete_stub_artifacts` and `mirror_content_owner` (Task 2).
- Produces: scan outcome `"content_owner_stub"` from `_scan_babylon_item`. `get_items_needing_analysis` and `get_stale_check_candidates` never return a pure stub.

- [ ] **Step 1: Write the failing tests**

Append to `src/api/tests/test_content_owner.py`:

```python
from rcars.services.showroom_scan import scan_babylon_item
from tests.test_showroom_reuse import scan  # noqa: F401  (LLM/embedding mocks + local git)


def test_pure_stub_is_not_selected_and_scan_makes_no_llm_call(db, scan):
    owner = add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                    paths=(("isolation-test.virtual.prod", "isolation-test.a.prod"),),
                    repo=scan.source.repo)
    assert stub not in {row["content_id"] for row in db.get_items_needing_analysis(scan.settings)}
    seed_stub_artifacts(db, stub)
    scan.llm.reset_mock()
    scan.embed.reset_mock()
    result = scan_babylon_item(db, scan.settings, stub)
    assert result["outcome"] == "content_owner_stub"
    assert result["success"] is True
    assert scan.llm.call_count == scan.embed.call_count == 0
    assert db.get_showroom_analysis(stub) is None
    assert db.get_embeddings_for_content(stub) == []


def test_stub_with_a_mid_chain_override_is_scanned(db, scan):
    add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    overridden = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                          paths=(("isolation-test.virtual.prod", "isolation-test.a.prod"),),
                          override_origins={"ref": "isolation-test.middle.prod"},
                          repo=scan.source.repo)
    assert overridden in {row["content_id"] for row in db.get_items_needing_analysis(scan.settings)}
    scan.llm.reset_mock()
    assert scan_babylon_item(db, scan.settings, overridden)["outcome"] in ("analyzed", "reused")
    assert scan.llm.call_count == 1


def test_stub_with_a_curator_content_path_is_scanned(db, scan):
    add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    overridden = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                          repo=scan.source.repo)
    db.set_content_path(overridden, "content/modules/ROOT/pages")
    assert overridden in {row["content_id"] for row in db.get_items_needing_analysis(scan.settings)}
```

Also append to `src/api/tests/test_content_owner.py`:

```python
def test_stale_check_candidates_exclude_pure_stubs(db):
    add_item(db, "isolation-test.a.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod")
    seed_stub_artifacts(db, stub)
    ids = {row["content_id"] for row in db.get_stale_check_candidates()}
    assert stub not in ids
```

Modify `src/api/tests/test_showroom_scan.py`: replace `test_explicit_four_level_virtual_materializes_own_artifacts` with:

```python
def test_four_level_virtual_is_a_stub_with_no_artifacts_of_its_own(db, scan):
    owner = add_item(db, scan, "isolation-test.owner.prod")
    scan_babylon_item(db, scan.settings, owner)
    source = replace(scan.source, owner_ci_name="isolation-test.owner.prod", scope_key="isolation-test.owner",
        paths=(("isolation-test.virtual.prod", "example.wrapper.prod", "example.content.prod", "isolation-test.owner.prod"),))
    target = db.upsert_babylon_catalog_item({"ci_name": "isolation-test.virtual.prod", "stage": "prod",
        "display_name": "TLS workshop", "category": "Workshop", "keywords": ["target-only"],
        "showroom_url": source.repo, "showroom_ref": source.ref, "showroom_source": source.to_dict(), "is_published": True})
    scan.llm.reset_mock()
    result = scan_babylon_item(db, scan.settings, target)
    assert result["outcome"] == "content_owner_stub"
    assert scan.llm.call_count == 0
    assert db.get_showroom_analysis(target) is None
    assert db.get_embeddings_for_content(target) == []
    assert db.get_content_entity(target)["summary"] == "Configure TLS"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_content_owner.py tests/test_showroom_scan.py -k "stub or four_level" -v`
Expected: FAIL — the stub is selected and scanned, and the outcome is `"analyzed"`.

- [ ] **Step 3: Implement the three filters and the guard**

In `get_items_needing_analysis`, inside the existing `for item in all_needing` loop, after the `source.status != "resolved"` check:

```python
            if content_owner(item) is not None:
                continue
```

In `get_stale_check_candidates`, keep the SQL and filter in Python:

```python
        with self._pool.connection() as conn:
            rows = conn.execute(sql).fetchall()
        return [row for row in rows if content_owner(row) is None]
```

In `_scan_babylon_item` in `src/api/rcars/services/showroom_scan.py`, after the `source.status == "excluded"` block and before `snapshot = _snapshot(item)`:

```python
    owner = content_owner(item)
    if owner is not None:
        db.delete_stub_artifacts(content_id)
        db.mirror_content_owner(content_id, owner)
        log.info("showroom_scan_content_owner_stub", component="scanner", content_id=content_id,
                 action="content_owner_stub", owner=owner)
        return {"content_id": content_id, "success": True, "outcome": "content_owner_stub",
                "source": source.to_dict()}
```

Add `content_owner` to the `showroom_source` import in `showroom_scan.py`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_content_owner.py tests/test_showroom_scan.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/db/database.py src/api/rcars/services/showroom_scan.py src/api/tests/test_content_owner.py src/api/tests/test_showroom_scan.py
git commit -m "[RHDPCD-2238] Skip pure stubs in scans and stale checks

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 4: Reconcile stub artifacts at every scan entry point

**Files:**
- Modify: `src/api/rcars/services/showroom_scan.py` (add `reconcile_pure_stubs`, `scan_candidates`)
- Modify: `src/api/rcars/api/routes/analysis.py:866-867` and `:910`
- Modify: `src/api/rcars/workers/ops.py:213`
- Modify: `src/api/rcars/cli.py:128`
- Test: `src/api/tests/test_content_owner.py`

**Interfaces:**
- Consumes: `get_stub_reconciliation_candidates`, `delete_stub_artifacts`, `mirror_content_owner` (Task 2); `get_items_needing_analysis` (Task 3).
- Produces:
  - `reconcile_pure_stubs(db) -> dict[str, int]` — keys `stubs`, `cleared`.
  - `scan_candidates(db, settings, *, force: bool = False) -> list[dict]` — reconciles, then returns `get_items_needing_analysis`.

- [ ] **Step 1: Write the failing tests**

Append to `src/api/tests/test_content_owner.py`:

```python
from rcars.services.showroom_scan import reconcile_pure_stubs, scan_candidates


def test_reconcile_clears_stub_artifacts_and_mirrors_owner_card(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    db.update_content_entity_card(owner, summary="Owner summary", products_json=["OpenShift"])
    db.set_scan_status(owner, "success")
    seed_stub_artifacts(db, stub)
    result = reconcile_pure_stubs(db)
    assert result["cleared"] >= 1
    assert db.get_showroom_analysis(stub) is None
    assert db.get_embeddings_for_content(stub) == []
    assert db.get_content_entity(stub)["summary"] == "Owner summary"
    assert db.get_content_entity(stub)["scan_status"] == "success"


def test_reconcile_leaves_the_owner_analysis_alone(db):
    owner = add_item(db, "isolation-test.owner.prod")
    add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    seed_stub_artifacts(db, owner, summary="Owner analysis")
    reconcile_pure_stubs(db)
    assert db.get_showroom_analysis(owner)["summary"] == "Owner analysis"
    assert db.get_embeddings_for_content(owner)


def test_scan_candidates_reconciles_before_selecting(db, scan):
    owner = add_item(db, "isolation-test.owner.prod", repo=scan.source.repo)
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod",
                    repo=scan.source.repo)
    seed_stub_artifacts(db, stub)
    ids = {row["content_id"] for row in scan_candidates(db, scan.settings)}
    assert stub not in ids
    assert db.get_showroom_analysis(stub) is None


def test_rescan_all_never_enqueues_a_pure_stub(db, scan):
    import asyncio
    from unittest.mock import AsyncMock
    from rcars.api.routes.analysis import rescan_all
    add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                    repo=scan.source.repo)
    redis = SimpleNamespace(enqueue_job=AsyncMock())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        db=db, arq_redis=redis, settings=scan.settings)))
    asyncio.run(rescan_all(request, user="isolation-test@example.com"))
    enqueued = {call.kwargs["content_id"] for call in redis.enqueue_job.call_args_list}
    assert stub not in enqueued
    with db.pool.connection() as conn:
        conn.execute("DELETE FROM jobs WHERE created_by IN ('isolation-test@example.com', 'rescan-all')")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_content_owner.py -k "reconcile or scan_candidates or rescan_all" -v`
Expected: FAIL with `ImportError: cannot import name 'reconcile_pure_stubs'`.

- [ ] **Step 3: Implement the reconciliation and wire the call sites**

In `src/api/rcars/services/showroom_scan.py`:

```python
def reconcile_pure_stubs(db) -> dict[str, int]:
    """Some CIs may have artifacts from before they became pure stubs."""
    stubs = cleared = 0
    for item in db.get_stub_reconciliation_candidates():
        owner = content_owner(item)
        if owner is None:
            continue
        stubs += 1
        if db.get_showroom_analysis(item["content_id"]) or db.get_embeddings_for_content(item["content_id"]):
            db.delete_stub_artifacts(item["content_id"])
            cleared += 1
        db.mirror_content_owner(item["content_id"], owner)
    if stubs:
        log.info("showroom_stub_reconciled", component="scanner", action="reconcile_stubs",
                 stubs=stubs, cleared=cleared)
    return {"stubs": stubs, "cleared": cleared}


def scan_candidates(db, settings, *, force: bool = False) -> list[dict]:
    """The single scan front door: reconcile stubs, then select work."""
    reconcile_pure_stubs(db)
    return db.get_items_needing_analysis(settings, force=force)
```

In `src/api/rcars/api/routes/analysis.py`:

- Import `from rcars.services.showroom_scan import scan_candidates`.
- `start_scan`: replace
  `dedup_stats = db.get_scan_dedup_stats()` + `items = order_for_reuse(db.get_items_needing_analysis(settings), settings)`
  with
  `items = order_for_reuse(scan_candidates(db, settings), settings)` followed by
  `dedup_stats = db.get_scan_dedup_stats()`.
- `rescan_all`: replace `db.get_items_needing_analysis(force=True)` with `scan_candidates(db, None, force=True)`.

In `src/api/rcars/workers/ops.py:213`: import `scan_candidates` and replace `wctx.db.get_items_needing_analysis(wctx.settings)` with `scan_candidates(wctx.db, wctx.settings)`.

In `src/api/rcars/cli.py:128`: import `scan_candidates` and replace `db.get_items_needing_analysis(settings, force=force)` with `scan_candidates(db, settings, force=force)`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_content_owner.py tests/test_showroom_scan.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/showroom_scan.py src/api/rcars/api/routes/analysis.py src/api/rcars/workers/ops.py src/api/rcars/cli.py src/api/tests/test_content_owner.py
git commit -m "[RHDPCD-2238] Reconcile pure stub artifacts at every scan entry point

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 5: Mirror card fields when an owner scan saves

**Files:**
- Modify: `src/api/rcars/services/showroom_scan.py` (`_scan_babylon_item`, inside the transaction)
- Test: `src/api/tests/test_content_owner.py`

**Interfaces:**
- Consumes: `get_pure_stubs_for_owner` (Task 2), `mirror_content_owner` (Task 2).
- Produces: nothing new. Every owner scan refreshes its stubs' card fields and `scan_status` in the same transaction.

- [ ] **Step 1: Write the failing tests**

Append to `src/api/tests/test_content_owner.py` (it already imports `scan_babylon_item` in Task 3):

```python
def test_owner_scan_mirrors_card_fields_to_its_stub(db, scan):
    owner = add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                    repo=scan.source.repo)
    assert scan_babylon_item(db, scan.settings, owner)["success"]
    card = db.get_content_entity(stub)
    assert card["summary"] == "Configure TLS"
    assert card["scan_status"] == "success"


def test_unchanged_owner_scan_still_mirrors_a_newly_added_stub(db, scan):
    owner = add_item(db, "isolation-test.a.prod", repo=scan.source.repo)
    assert scan_babylon_item(db, scan.settings, owner)["outcome"] == "analyzed"
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.a.prod",
                    repo=scan.source.repo)
    result = scan_babylon_item(db, scan.settings, owner)
    assert result["outcome"] == "unchanged"
    assert db.get_content_entity(stub)["summary"] == "Configure TLS"
    assert db.get_content_entity(stub)["scan_status"] == "success"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_content_owner.py -k "mirrors" -v`
Expected: FAIL — the stub's summary is `None`.

- [ ] **Step 3: Add the mirror loop inside the scan transaction**

In `_scan_babylon_item`, inside `with db.pool.connection() as conn:`, **after the `if outcome != "unchanged":` block closes** — so an `unchanged` owner still mirrors — at the same indentation as that `if` statement:

```python
            for stub in db.get_pure_stubs_for_owner(item["ci_name"], conn=conn):
                db.mirror_content_owner(stub["content_id"], item["ci_name"], conn=conn)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_content_owner.py tests/test_showroom_scan.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/showroom_scan.py src/api/tests/test_content_owner.py
git commit -m "[RHDPCD-2238] Mirror owner card fields to pure stubs after a scan

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 6: Advisor shows the stub in place of its owner

**Files:**
- Modify: `src/api/rcars/services/recommender/vector_search.py:126-153`
- Modify: `src/api/rcars/db/database.py` (delete `get_virtual_content_aliases` at ~1893)
- Test: `src/api/tests/test_showroom_recommendation_isolation.py` (rewrite the alias tests)

**Interfaces:**
- Consumes: `content_owner` (Task 1), `get_pure_stubs_for_owner` (Task 2).
- Produces: `_eligible_stub(target, stages, include_zt, scope) -> bool`. Promoted rows carry the stub's `content_id`, `ci_name`, and `stage`, with `best_similarity` preserved from the owner hit.

- [ ] **Step 1: Write the failing tests**

In `src/api/tests/test_showroom_recommendation_isolation.py`: delete `add_alias` and the three alias tests (`test_explicit_multihop_virtual_alias_is_recognized_and_hydrates_own_analysis`, `test_infrastructure_base_is_not_a_content_alias`, `test_multiple_virtual_targets_are_not_selected_arbitrarily`). Keep `search()`, `test_unrelated_same_hash_prod_cannot_replace_dev`, `test_exact_same_item_prod_requires_complete_matching_signature`, `test_scoped_queries_never_promote_outside_requested_ids`, `test_independent_ids_keep_their_own_scores`. Add:

```python
def add_stub(db, owner_ci_name, name, *, stage="prod"):
    source = ResolvedShowroom("resolved", owner_ci_name, owner_ci_name.rsplit(".", 1)[0],
                              "https://github.com/example/content", "main",
                              paths=((name, owner_ci_name),))
    return db.upsert_babylon_catalog_item({
        "ci_name": name, "stage": stage, "display_name": name,
        "showroom_url": source.repo, "showroom_ref": "main",
        "showroom_source": source.to_dict(), "is_published": True})


def test_owner_hit_is_shown_as_its_only_stub(db, monkeypatch):
    owner, _, _ = seed(db)
    stub = add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.prod")
    candidates = search(db, monkeypatch, [owner], stages=["prod"])
    assert [c.content_id for c in candidates] == [stub]
    assert candidates[0].vector_similarity_pct == 90  # the owner hit's score is kept


def test_owner_without_a_stub_is_shown_as_the_owner(db, monkeypatch):
    owner, _, _ = seed(db)
    assert [c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"])] == [owner]


def test_owner_with_two_stubs_is_shown_as_the_owner(db, monkeypatch):
    owner, _, _ = seed(db)
    add_stub(db, owner.removeprefix("babylon:"), "isolation-test.first.prod")
    add_stub(db, owner.removeprefix("babylon:"), "isolation-test.second.prod")
    assert [c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"])] == [owner]


def test_stub_outside_the_requested_stage_is_not_shown(db, monkeypatch):
    owner, _, _ = seed(db)
    add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.dev", stage="dev")
    assert [c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"])] == [owner]


def test_stub_outside_the_requested_scope_is_not_shown(db, monkeypatch):
    owner, _, _ = seed(db)
    add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.prod")
    assert [c.content_id for c in search(db, monkeypatch, [owner], stages=["prod"], scope=[owner])] == [owner]


def test_each_owner_promotes_to_its_own_stub(db, monkeypatch):
    a, _, _ = seed(db)
    b, _, _ = seed(db, "isolation-test.b.prod")
    stub_a = add_stub(db, "isolation-test.item.prod", "isolation-test.virtual-a.prod")
    stub_b = add_stub(db, "isolation-test.b.prod", "isolation-test.virtual-b.prod")
    candidates = search(db, monkeypatch, [a, b], stages=["prod"])
    assert [c.content_id for c in candidates] == [stub_a, stub_b]
```

Note: `search()` builds candidate names and ids only; `vector_similarity_pct` is 90 because the harness gives the first row `best_similarity = 0.9`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_showroom_recommendation_isolation.py -v`
Expected: FAIL — the candidate is the owner, not the stub.

- [ ] **Step 3: Replace the alias block and delete `get_virtual_content_aliases`**

In `src/api/rcars/services/recommender/vector_search.py`, add above `_authorized_promotion`:

```python
def _eligible_stub(target, stages, include_zt, scope) -> bool:
    if not target or target.get("stage") not in stages:
        return False
    if scope and target["content_id"] not in scope:
        return False
    if not include_zt and ((target.get("ci_name") or "").startswith("zt-")
                           or (target.get("catalog_namespace") or "").startswith("zt-")):
        return False
    return True
```

Replace these two lines in `_authorized_promotion`:

```python
    aliases = [alias for alias in db.get_virtual_content_aliases(row["content_id"]) if eligible(alias)]
    if len(aliases) == 1:
        row = {**aliases[0], "best_similarity": row["best_similarity"]}
```

with:

```python
    promoted = db.get_babylon_item(row["content_id"])
    stubs = [stub for stub in db.get_pure_stubs_for_owner(promoted["ci_name"], list(stages))
             if _eligible_stub(stub, stages, include_zt, scope)]
    if len(stubs) == 1:
        row = {**stubs[0], "best_similarity": row["best_similarity"]}
```

Delete `get_virtual_content_aliases` from `src/api/rcars/db/database.py`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_showroom_recommendation_isolation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/recommender/vector_search.py src/api/rcars/db/database.py src/api/tests/test_showroom_recommendation_isolation.py
git commit -m "[RHDPCD-2238] Recommend the single stub of a content owner

Replace the signature-matched virtual alias path with the explicit
content_owner link.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 7: `get_display_analysis` and the three runtime read sites

**Files:**
- Modify: `src/api/rcars/db/database.py` (add next to `get_showroom_analysis` at ~1830)
- Modify: `src/api/rcars/services/recommender/vector_search.py:226`
- Modify: `src/api/rcars/services/recommender/drivers/hands_on.py:55`
- Modify: `src/api/rcars/services/recommender/rationale.py:221`
- Test: `src/api/tests/test_content_owner.py`, `src/api/tests/test_showroom_recommendation_isolation.py`

**Interfaces:**
- Consumes: `content_owner` (Task 1), `get_showroom_analysis_by_ci_name` (existing), `get_pure_stubs_for_owner` (Task 2).
- Produces: `get_display_analysis(content_id: str) -> dict | None`. Returns the owner's `showroom_analysis` row for a pure stub, the item's own row otherwise. Task 8 also uses it.

- [ ] **Step 1: Write the failing tests**

Append to `src/api/tests/test_content_owner.py`:

```python
def test_display_analysis_of_a_stub_is_the_owner_analysis(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    seed_stub_artifacts(db, owner, summary="Owner analysis")
    assert db.get_display_analysis(stub)["summary"] == "Owner analysis"


def test_display_analysis_of_an_owner_is_its_own_analysis(db):
    owner = add_item(db, "isolation-test.owner.prod")
    seed_stub_artifacts(db, owner, summary="Owner analysis")
    assert db.get_display_analysis(owner)["summary"] == "Owner analysis"
```

Append to `src/api/tests/test_showroom_recommendation_isolation.py`:

```python
def test_promoted_stub_card_hydrates_the_owner_analysis(db, monkeypatch):
    owner, _, _ = seed(db)
    add_stub(db, owner.removeprefix("babylon:"), "isolation-test.virtual.prod")
    candidate = search(db, monkeypatch, [owner], stages=["prod"])[0]
    assert candidate.content_id == "babylon:isolation-test.virtual.prod"
    assert candidate.summary == "A real lab"
    from rcars.services.recommender.drivers.hands_on import HandsOnDriver
    assert HandsOnDriver().fetch_analysis(db, candidate)["summary"] == "A real lab"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_content_owner.py tests/test_showroom_recommendation_isolation.py -k display_analysis -v`
Expected: FAIL with `AttributeError: 'Database' object has no attribute 'get_display_analysis'`.

- [ ] **Step 3: Implement and switch the three sites**

In `src/api/rcars/db/database.py`, after `get_showroom_analysis`:

```python
def get_display_analysis(self, content_id: str) -> dict | None:
    """What a viewer should see: a pure stub shows its owner's analysis."""
    item = self.get_babylon_item(content_id)
    owner = content_owner(item) if item else None
    if owner:
        return self.get_showroom_analysis_by_ci_name(owner)
    return self.get_showroom_analysis(content_id)
```

Switch these three call sites to `db.get_display_analysis(...)`:
- `src/api/rcars/services/recommender/vector_search.py:226`
- `src/api/rcars/services/recommender/drivers/hands_on.py:55`
- `src/api/rcars/services/recommender/rationale.py:221`

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_content_owner.py tests/test_showroom_recommendation_isolation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/db/database.py src/api/rcars/services/recommender src/api/tests/test_content_owner.py src/api/tests/test_showroom_recommendation_isolation.py
git commit -m "[RHDPCD-2238] Read a pure stub's analysis from its owner

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 8: Browse detail shows the owner's analysis and names the owner

**Files:**
- Modify: `src/api/rcars/api/routes/catalog.py:254-302` and `:311-320`
- Modify: `src/frontend/src/pages/BrowsePage.tsx` (`ItemDetail` at ~89, detail body at ~993)
- Modify: `src/frontend/src/styles/rcars-app.css` (after `.browse-description` at ~1336)
- Test: `src/api/tests/test_catalog_content_owner_routes.py` (create)

**Interfaces:**
- Consumes: `content_owner` (Task 1), `get_display_analysis` (Task 7).
- Produces: `GET /api/v1/catalog/{id}` response gains `content_owner: str | null`. `analysis` for a pure stub is the owner's row.

- [ ] **Step 1: Write the failing test**

Create `src/api/tests/test_catalog_content_owner_routes.py`:

```python
from types import SimpleNamespace

import pytest

from tests.showroom_helpers import db
from rcars.api.routes.catalog import get_catalog_item, get_analysis
from rcars.config import Settings

URL = "https://github.com/example/content"


def add_item(db, name, *, owner_ci_name=None):
    owner = owner_ci_name or name
    from rcars.services.showroom_source import ResolvedShowroom
    source = ResolvedShowroom("resolved", owner, name.rsplit(".", 1)[0], URL, "main",
                              paths=((name, owner) if owner_ci_name else (name,),))
    return db.upsert_babylon_catalog_item({
        "ci_name": name, "stage": name.rsplit(".", 1)[-1], "display_name": name,
        "category": "Workshop", "showroom_url": URL, "showroom_ref": "main",
        "showroom_source": source.to_dict()})


def request(db):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        db=db, settings=Settings(database_url=db._url))))


@pytest.mark.asyncio
async def test_stub_detail_returns_the_owner_analysis_and_names_the_owner(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    db.upsert_showroom_analysis({"content_id": owner, "summary": "Owner analysis",
                                 "modules_json": [], "content_hash": "content"})
    detail = await get_catalog_item("isolation-test.virtual.prod", request(db), user="test@example.com")
    assert detail["content_owner"] == "isolation-test.owner.prod"
    assert detail["analysis"]["summary"] == "Owner analysis"
    analysis = await get_analysis("isolation-test.virtual.prod", request(db), user="test@example.com")
    assert analysis["summary"] == "Owner analysis"


@pytest.mark.asyncio
async def test_owner_detail_has_no_content_owner(db):
    owner = add_item(db, "isolation-test.owner.prod")
    detail = await get_catalog_item("isolation-test.owner.prod", request(db), user="test@example.com")
    assert detail["content_owner"] is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_catalog_content_owner_routes.py -v`
Expected: FAIL with `KeyError: 'content_owner'`.

- [ ] **Step 3: Implement the route changes**

In `src/api/rcars/api/routes/catalog.py`, import `content_owner` from `rcars.services.showroom_source`.

In `get_catalog_item`:
- The `pa:` branch return dict gains `"content_owner": None`.
- Replace `analysis = db.get_showroom_analysis(content_id)` with `analysis = db.get_display_analysis(content_id)`, and add `"content_owner": content_owner(item)` to the final return.

In `get_analysis`, replace the `else` branch body with `analysis = db.get_display_analysis(content_id)`.

- [ ] **Step 4: Add the frontend line**

In `src/frontend/src/pages/BrowsePage.tsx`:
- Add `content_owner?: string | null` to `ItemDetail`, next to `scan_status`.
- After the `detail.analysis?.summary` paragraph (inside the same `<div>`), add:

```tsx
{detail.content_owner && (
  <p className="browse-content-owner">
    Content from{' '}
    <a className="browse-content-owner-link"
       href={`/browse?search=${encodeURIComponent(detail.content_owner)}`}>
      {detail.content_owner}
    </a>
  </p>
)}
```

- In `src/frontend/src/styles/rcars-app.css`, after `.browse-description`:

```css
.browse-content-owner {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 6px 0 0;
}

.browse-content-owner-link {
  color: var(--text-link);
  font-weight: 500;
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_catalog_content_owner_routes.py -v`
Expected: PASS.

Run: `cd src/frontend && npm run build`
Expected: build succeeds with no TypeScript error.

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/api/routes/catalog.py src/frontend/src/pages/BrowsePage.tsx src/frontend/src/styles/rcars-app.css src/api/tests/test_catalog_content_owner_routes.py
git commit -m "[RHDPCD-2238] Show a stub's owner analysis and owner link in Browse

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 9: Curator edits on a stub write the owner's analysis row

**Files:**
- Modify: `src/api/rcars/api/routes/catalog.py` (add `_curation_target`, use it in `set_note` ~378, `flag_item` ~391, `set_duration` ~425)
- Test: `src/api/tests/test_catalog_content_owner_routes.py`

**Interfaces:**
- Consumes: `content_owner` (Task 1).
- Produces: `_curation_target(content_id: str, db) -> str`. Returns the owner's `content_id` for a pure stub, the given `content_id` otherwise. `set_note`, `flag_item`, and `set_duration` call it. `override_url` and `set_content_path` do not.

- [ ] **Step 1: Write the failing tests**

Append to `src/api/tests/test_catalog_content_owner_routes.py`:

```python
from rcars.api.routes.catalog import NoteRequest, DurationRequest, set_note, set_duration


@pytest.mark.asyncio
async def test_curator_note_on_a_stub_writes_the_owner_row(db):
    owner = add_item(db, "isolation-test.owner.prod")
    add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    seed = {"content_id": owner, "summary": "Owner analysis", "modules_json": [],
            "content_hash": "content"}
    db.upsert_showroom_analysis(seed)
    await set_note("isolation-test.virtual.prod", NoteRequest(note="Curated note"),
                   request(db), user="test@example.com")
    assert db.get_showroom_analysis(owner)["notes"] == "Curated note"
    assert db.get_showroom_analysis("babylon:isolation-test.virtual.prod") is None


@pytest.mark.asyncio
async def test_curator_duration_on_a_stub_writes_the_owner_row(db):
    owner = add_item(db, "isolation-test.owner.prod")
    add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    db.upsert_showroom_analysis({"content_id": owner, "summary": "Owner analysis",
                                 "modules_json": [], "content_hash": "content"})
    await set_duration("isolation-test.virtual.prod", DurationRequest(duration_min=90),
                       request(db), user="test@example.com")
    assert db.get_showroom_analysis(owner)["curated_duration_min"] == 90
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_catalog_content_owner_routes.py -v`
Expected: FAIL — the note is written to the stub's row, which does not exist, so the owner's `notes` stays `None`.

- [ ] **Step 3: Implement `_curation_target` and use it**

In `src/api/rcars/api/routes/catalog.py`, next to `_resolve_item`:

```python
def _curation_target(content_id: str, db) -> str:
    """Curated fields on a pure stub belong to its owner: the content is shared."""
    if content_id.startswith("pa:"):
        return content_id
    item = db.get_babylon_item(content_id)
    owner = content_owner(item) if item else None
    return f"babylon:{owner}" if owner else content_id
```

In `set_note`, `flag_item`, and `set_duration`, change `content_id = _resolve_to_content_id(identifier, db)` to:

```python
    content_id = _curation_target(_resolve_to_content_id(identifier, db), db)
```

Leave `override_url` and `set_content_path` unchanged.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_catalog_content_owner_routes.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest tests/ -v -m "not integration"`
Expected: PASS. Any failure outside the files this plan touches is a regression to investigate before the next step.

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/api/routes/catalog.py src/api/tests/test_catalog_content_owner_routes.py
git commit -m "[RHDPCD-2238] Write curator edits on a stub to its owner's analysis

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Rollout

After the branch merges, follow the spec's rollout on dev:

1. `ansible-playbook ansible/deploy.yml -e env=dev --tags full`
2. Run a scan from System → Sync (or `POST /api/v1/analysis/scan`).
3. Check that no pure stub has a `showroom_analysis` row or `embeddings` rows, and that each stub's `content_entities` card fields equal its owner's.
4. Query the Advisor for "OpenShift Virtualization modernization". Expect one card, `published.ocp-virt-modernize.prod`.
5. Check the Tokens page: no `scan` rows for stub CI names.
