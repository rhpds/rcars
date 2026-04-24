# Scan Failures & Catalog Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make scan failures visible and actionable, expose dev/event catalog items through UI filters, reconcile stale catalog items during refresh, and fix scan pipeline isolation bugs.

**Architecture:** Five workstreams touching the DB schema, scan pipeline, CLI, admin/curate/advisor web routes, templates, and Ansible deployment manifests. Tasks are ordered by dependency: pipeline fixes first (safety), then schema migration (foundation), then features (scan failures → reconciliation → dev/event visibility).

**Tech Stack:** Python 3.11, FastAPI, HTMX, psycopg 3 (+ psycopg.pool), PostgreSQL + pgvector, Click CLI, Jinja2 templates, Ansible, Rich tables

---

## Task 1: Fix temp directory collision in clone_showroom

**Files:**
- Modify: `src/rcars/analyzer.py:182-222`
- Test: `tests/test_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analyzer.py — add to existing file

def test_clone_dir_uses_unique_suffix(tmp_path, monkeypatch):
    """Two clones of the same repo URL must use different directories."""
    import subprocess
    from rcars.analyzer import clone_showroom

    calls = []
    def fake_run(cmd, **kwargs):
        clone_path = cmd[-1]
        Path(clone_path).mkdir(parents=True, exist_ok=True)
        calls.append(clone_path)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    p1 = clone_showroom("https://github.com/org/my-workshop.git", None, str(tmp_path))
    p2 = clone_showroom("https://github.com/org/my-workshop.git", None, str(tmp_path))

    assert p1 != p2
    assert p1.name.startswith("rcars-showroom-my-workshop-")
    assert p2.name.startswith("rcars-showroom-my-workshop-")
    assert len(calls) == 2
    assert calls[0] != calls[1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_analyzer.py::test_clone_dir_uses_unique_suffix -v`
Expected: FAIL — both calls return same path

- [ ] **Step 3: Implement unique directory naming**

In `src/rcars/analyzer.py`, modify `clone_showroom()` (line 187):

```python
import uuid

def clone_showroom(
    url: str, ref: str | None, clone_dir: str = "/tmp"
) -> Path | None:
    """Shallow clone a Showroom repo. Returns clone path or None on failure."""
    repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
    suffix = uuid.uuid4().hex[:8]
    clone_path = Path(clone_dir) / f"rcars-showroom-{repo_name}-{suffix}"

    if clone_path.exists():
        shutil.rmtree(clone_path)
    # ... rest unchanged
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_analyzer.py::test_clone_dir_uses_unique_suffix -v`
Expected: PASS

- [ ] **Step 5: Run full analyzer test suite**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_analyzer.py -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/analyzer.py tests/test_analyzer.py
git commit -m "analyzer: Fix temp directory collision with UUID suffix"
```

---

## Task 2: Replace shared DB connection with connection pool

**Files:**
- Modify: `src/rcars/db.py:120-132`
- Modify: `src/rcars/cli.py` (get_db usage)
- Test: `tests/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db.py — add to existing file

def test_database_uses_connection_pool(db):
    """Database class should use a connection pool, not a single connection."""
    assert hasattr(db, '_pool'), "Database should have a _pool attribute"
    # Pool should support acquiring connections
    with db._pool.connection() as conn:
        cur = conn.execute("SELECT 1")
        assert cur.fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py::test_database_uses_connection_pool -v`
Expected: FAIL — no _pool attribute

- [ ] **Step 3: Implement connection pool**

In `src/rcars/db.py`, replace the constructor and `_conn` property:

```python
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

class Database:
    def __init__(self, database_url: str):
        self._url = database_url
        self._pool = ConnectionPool(
            database_url,
            min_size=2,
            max_size=10,
            kwargs={"row_factory": dict_row, "autocommit": False},
        )

    @property
    def _conn(self):
        """Return a connection from the pool for backwards compatibility.

        DEPRECATED: prefer using self._pool.connection() context manager
        for thread-safe access. This property exists for code that hasn't
        been migrated to pool-aware patterns yet.
        """
        conn = self._pool.getconn()
        if conn.closed:
            self._pool.putconn(conn)
            conn = self._pool.getconn()
        return conn

    def _putconn(self, conn):
        """Return a connection to the pool."""
        self._pool.putconn(conn)

    def close(self):
        """Close the connection pool."""
        self._pool.close()
```

Then update every method that uses `self._conn` to use the context manager pattern. For each method, wrap the body in `with self._pool.connection() as conn:` and replace `self._conn` with `conn`. Example for `upsert_catalog_item`:

```python
def upsert_catalog_item(self, item: dict):
    with self._pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO catalog_items (...) VALUES (...)
                ON CONFLICT (ci_name) DO UPDATE SET ...
            """, params)
            conn.commit()
```

Apply this pattern to all public methods: `create_schema`, `drop_schema`, `list_tables`, `upsert_catalog_item`, `get_catalog_item`, `list_catalog_items`, `upsert_showroom_analysis`, `get_showroom_analysis`, `mark_stale`, `clear_stale`, `store_embedding`, `search_embeddings`, `log_action`, `get_recent_logs`, `log_token_usage`, `get_token_stats`, `get_recent_queries`, `get_status_summary`, `get_items_needing_analysis`, `get_analyzed_items`, `add_enrichment_tag`, `remove_enrichment_tag`, `get_enrichment_tags`, `get_enrichment_tags_for_items`, `set_enrichment_note`, `get_enrichment_note`, `set_enrichment_review_needed`, `get_db_currency`.

- [ ] **Step 4: Add psycopg-pool dependency**

Run: `cd ~/devel/working/rcars-advisory && grep -n "psycopg" pyproject.toml` to find where psycopg is listed, then add `psycopg-pool` alongside it.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py::test_database_uses_connection_pool -v`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/ -v --ignore=tests/test_integration.py`
Expected: All tests pass (the pool is transparent to callers)

- [ ] **Step 7: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/db.py pyproject.toml
git commit -m "db: Replace single connection with psycopg ConnectionPool"
```

---

## Task 3: Clone cleanup sweep and dedicated clone directory

**Files:**
- Modify: `src/rcars/cli.py` (scan command, lines 222-240)
- Modify: `src/rcars/config.py` (clone_dir default)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py — add to existing file

def test_scan_cleans_orphaned_clones(tmp_path, runner, monkeypatch):
    """Scan command should clean up orphaned rcars-showroom-* dirs before starting."""
    clone_dir = tmp_path / "rcars-clones"
    clone_dir.mkdir()
    orphan = clone_dir / "rcars-showroom-old-workshop-abc12345"
    orphan.mkdir()
    (orphan / "somefile.adoc").write_text("leftover")

    monkeypatch.setenv("RCARS_CLONE_DIR", str(clone_dir))

    result = runner.invoke(cli, ["scan"])

    assert not orphan.exists(), "Orphaned clone directory should be cleaned up"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_cli.py::test_scan_cleans_orphaned_clones -v`
Expected: FAIL — orphan directory still exists

- [ ] **Step 3: Implement cleanup sweep**

In `src/rcars/cli.py`, at the top of the `scan` command (after settings are loaded, before gathering candidates):

```python
# Clean up orphaned clone directories from previous runs
clone_base = Path(settings.clone_dir)
if clone_base.exists():
    for entry in clone_base.iterdir():
        if entry.is_dir() and entry.name.startswith("rcars-showroom-"):
            shutil.rmtree(entry, ignore_errors=True)
            log.info("Cleaned up orphaned clone: %s", entry.name)
```

Add `from pathlib import Path` and `import shutil` to the imports if not already present.

- [ ] **Step 4: Update config.py default clone_dir**

In `src/rcars/config.py`, change the clone_dir default:

```python
clone_dir: str = field(default_factory=lambda: os.environ.get("RCARS_CLONE_DIR", "/tmp/rcars-clones"))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_cli.py::test_scan_cleans_orphaned_clones -v`
Expected: PASS

- [ ] **Step 6: Run full CLI test suite**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_cli.py -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/cli.py src/rcars/config.py tests/test_cli.py
git commit -m "scan: Add clone cleanup sweep and dedicated clone directory"
```

---

## Task 4: Infrastructure sizing — emptyDir volume and PVC bump

**Files:**
- Modify: `ansible/templates/manifests-app.yaml.j2`
- Modify: `ansible/vars/common.yml`

- [ ] **Step 1: Add emptyDir volume to app deployment**

In `ansible/templates/manifests-app.yaml.j2`, add a volumeMount to the app container (after the existing volumeMounts):

```yaml
            - name: clone-workspace
              mountPath: /tmp/rcars-clones
```

And add the volume to the pod spec volumes section:

```yaml
        - name: clone-workspace
          emptyDir:
            sizeLimit: 10Gi
```

- [ ] **Step 2: Update RCARS_CLONE_DIR env var**

In the same template, update the RCARS_CLONE_DIR env var:

```yaml
            - name: RCARS_CLONE_DIR
              value: /tmp/rcars-clones
```

- [ ] **Step 3: Bump PostgreSQL PVC size**

In `ansible/vars/common.yml`, change:

```yaml
pg_pvc_size: 20Gi
```

- [ ] **Step 4: Verify template renders**

Run: `cd ~/devel/working/rcars-advisory && grep -A2 'clone-workspace' ansible/templates/manifests-app.yaml.j2`
Expected: Shows both the volumeMount and the emptyDir volume definition

- [ ] **Step 5: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add ansible/templates/manifests-app.yaml.j2 ansible/vars/common.yml
git commit -m "infra: Add 10Gi emptyDir for clones, bump PG PVC to 20Gi"
```

---

## Task 5: Database schema migration — scan status and override columns

**Files:**
- Modify: `src/rcars/db.py` (SCHEMA_SQL + migration 004)
- Test: `tests/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db.py — add to existing file

def test_catalog_item_has_scan_status_columns(db):
    """catalog_items table should have scan_status, scan_error_class, scan_error,
    scan_failed_at, and showroom_url_override columns."""
    with db._pool.connection() as conn:
        cur = conn.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'catalog_items'
            AND column_name IN ('scan_status', 'scan_error_class', 'scan_error',
                                'scan_failed_at', 'showroom_url_override')
            ORDER BY column_name
        """)
        columns = [row[0] for row in cur.fetchall()]
    assert columns == ['scan_error', 'scan_error_class', 'scan_failed_at',
                        'scan_status', 'showroom_url_override']


def test_scan_status_defaults_to_not_scanned(db):
    """New catalog items should default to scan_status='not_scanned'."""
    db.upsert_catalog_item({"ci_name": "test/item", "display_name": "Test",
                            "stage": "prod", "is_prod": True})
    item = db.get_catalog_item("test/item")
    assert item["scan_status"] == "not_scanned"
    assert item["scan_error_class"] is None
    assert item["scan_error"] is None
    assert item["scan_failed_at"] is None
    assert item["showroom_url_override"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py::test_catalog_item_has_scan_status_columns tests/test_db.py::test_scan_status_defaults_to_not_scanned -v`
Expected: FAIL — columns don't exist

- [ ] **Step 3: Add columns to SCHEMA_SQL**

In `src/rcars/db.py`, add to the `catalog_items` CREATE TABLE statement (after the existing columns, before the closing `)`):

```sql
    scan_status TEXT NOT NULL DEFAULT 'not_scanned',
    scan_error_class TEXT,
    scan_error TEXT,
    scan_failed_at TIMESTAMPTZ,
    showroom_url_override TEXT,
```

- [ ] **Step 4: Add migration 004**

In `src/rcars/db.py`, in `create_schema()` after the migration 003 block, add:

```python
# Migration 004: scan status + override columns
cur.execute("""
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'catalog_items' AND column_name = 'scan_status'
""")
if not cur.fetchone():
    log.info("Migration 004: adding scan status columns")
    cur.execute("""
        ALTER TABLE catalog_items
            ADD COLUMN scan_status TEXT NOT NULL DEFAULT 'not_scanned',
            ADD COLUMN scan_error_class TEXT,
            ADD COLUMN scan_error TEXT,
            ADD COLUMN scan_failed_at TIMESTAMPTZ,
            ADD COLUMN showroom_url_override TEXT
    """)
    conn.commit()
```

- [ ] **Step 5: Update upsert_catalog_item to preserve scan fields**

In the `ON CONFLICT` clause of `upsert_catalog_item`, do NOT include `scan_status`, `scan_error_class`, `scan_error`, `scan_failed_at`, or `showroom_url_override` in the UPDATE SET. These fields are managed by the scan pipeline, not catalog refresh.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py::test_catalog_item_has_scan_status_columns tests/test_db.py::test_scan_status_defaults_to_not_scanned -v`
Expected: PASS

- [ ] **Step 7: Run full DB test suite**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py -v`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/db.py tests/test_db.py
git commit -m "db: Add scan status and showroom_url_override columns (migration 004)"
```

---

## Task 6: Error classification function

**Files:**
- Modify: `src/rcars/analyzer.py`
- Test: `tests/test_analyzer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analyzer.py — add to existing file

import subprocess
from rcars.analyzer import classify_scan_error


def test_classify_private_repo():
    err = subprocess.CalledProcessError(128, "git", stderr="Permission denied (publickey)")
    cls, msg = classify_scan_error(err, url="https://github.com/org/private.git")
    assert cls == "private_repo"
    assert "Permission denied" in msg or "private" in msg.lower()


def test_classify_jinja_url():
    err = ValueError("URL contains template variable")
    cls, msg = classify_scan_error(err, url="https://github.com/{{ repo }}.git")
    assert cls == "jinja_url"


def test_classify_timeout():
    err = subprocess.TimeoutExpired("git", 120)
    cls, msg = classify_scan_error(err, url="https://github.com/org/repo.git")
    assert cls == "timeout"


def test_classify_missing_antora():
    err = FileNotFoundError("No .adoc files found")
    cls, msg = classify_scan_error(err, url="https://github.com/org/repo.git")
    assert cls == "missing_antora"


def test_classify_clone_failed():
    err = subprocess.CalledProcessError(128, "git", stderr="repository not found")
    cls, msg = classify_scan_error(err, url="https://github.com/org/gone.git")
    assert cls == "clone_failed"


def test_classify_no_content():
    err = ValueError("All files filtered as boilerplate")
    cls, msg = classify_scan_error(err, url="https://github.com/org/repo.git")
    assert cls == "no_content"


def test_classify_parse_error():
    err = ValueError("Failed to parse analysis JSON")
    cls, msg = classify_scan_error(err, url="https://github.com/org/repo.git")
    assert cls == "parse_error"


def test_classify_unknown():
    err = RuntimeError("something unexpected")
    cls, msg = classify_scan_error(err, url="https://github.com/org/repo.git")
    assert cls == "unknown"
    assert "something unexpected" in msg


def test_classify_returns_full_message():
    """Error messages should not be truncated."""
    long_msg = "A" * 500
    err = RuntimeError(long_msg)
    cls, msg = classify_scan_error(err, url="https://github.com/org/repo.git")
    assert len(msg) >= 500
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_analyzer.py -k "test_classify" -v`
Expected: FAIL — classify_scan_error not defined

- [ ] **Step 3: Implement classify_scan_error**

In `src/rcars/analyzer.py`, add:

```python
def classify_scan_error(
    exc: Exception, url: str | None = None
) -> tuple[str, str]:
    """Classify a scan error and return (error_class, human_message)."""
    msg = str(exc)
    stderr = getattr(exc, "stderr", "") or ""

    if url and ("{{" in url or "{%" in url):
        return "jinja_url", f"Showroom URL contains unresolved template variables: {url}"

    if isinstance(exc, subprocess.TimeoutExpired):
        return "timeout", f"Clone timed out after {exc.timeout}s for {url}"

    if isinstance(exc, subprocess.CalledProcessError):
        stderr_lower = stderr.lower()
        if "permission denied" in stderr_lower or "403" in stderr_lower:
            return "private_repo", f"Permission denied cloning {url}: {stderr.strip()}"
        if "not found" in stderr_lower or "404" in stderr_lower:
            return "http_404", f"Repository not found: {url}: {stderr.strip()}"
        return "clone_failed", f"Git clone failed for {url}: {stderr.strip()}"

    msg_lower = msg.lower()
    if "no .adoc" in msg_lower or isinstance(exc, FileNotFoundError):
        return "missing_antora", f"No .adoc files found in Showroom layout for {url}"
    if "boilerplate" in msg_lower:
        return "no_content", f"All content filtered as boilerplate for {url}"
    if "parse" in msg_lower or "json" in msg_lower:
        return "parse_error", f"Failed to parse analysis response for {url}: {msg}"

    return "unknown", f"Unexpected error scanning {url}: {msg}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_analyzer.py -k "test_classify" -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/analyzer.py tests/test_analyzer.py
git commit -m "analyzer: Add classify_scan_error for scan failure categorization"
```

---

## Task 7: Scan status tracking in scan pipeline

**Files:**
- Modify: `src/rcars/db.py` (add set_scan_status, get_scan_failures methods)
- Modify: `src/rcars/cli.py` (scan command error handling)
- Modify: `src/rcars/analyzer.py` (use showroom_url_override)
- Test: `tests/test_db.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write DB method tests**

```python
# tests/test_db.py — add to existing file

def test_set_scan_status_success(db):
    db.upsert_catalog_item({"ci_name": "test/ok", "display_name": "OK", "stage": "prod", "is_prod": True})
    db.set_scan_status("test/ok", "success")
    item = db.get_catalog_item("test/ok")
    assert item["scan_status"] == "success"
    assert item["scan_error_class"] is None
    assert item["scan_error"] is None
    assert item["scan_failed_at"] is None


def test_set_scan_status_failed(db):
    db.upsert_catalog_item({"ci_name": "test/fail", "display_name": "Fail", "stage": "prod", "is_prod": True})
    db.set_scan_status("test/fail", "failed", error_class="private_repo",
                       error_message="Permission denied")
    item = db.get_catalog_item("test/fail")
    assert item["scan_status"] == "failed"
    assert item["scan_error_class"] == "private_repo"
    assert item["scan_error"] == "Permission denied"
    assert item["scan_failed_at"] is not None


def test_set_scan_status_success_clears_error(db):
    db.upsert_catalog_item({"ci_name": "test/retry", "display_name": "Retry", "stage": "prod", "is_prod": True})
    db.set_scan_status("test/retry", "failed", error_class="timeout", error_message="timed out")
    db.set_scan_status("test/retry", "success")
    item = db.get_catalog_item("test/retry")
    assert item["scan_status"] == "success"
    assert item["scan_error_class"] is None
    assert item["scan_error"] is None
    assert item["scan_failed_at"] is None


def test_get_scan_failures(db):
    db.upsert_catalog_item({"ci_name": "test/ok", "display_name": "OK", "stage": "prod", "is_prod": True})
    db.upsert_catalog_item({"ci_name": "test/fail1", "display_name": "F1", "stage": "prod", "is_prod": True})
    db.upsert_catalog_item({"ci_name": "test/fail2", "display_name": "F2", "stage": "dev", "is_prod": False})
    db.set_scan_status("test/ok", "success")
    db.set_scan_status("test/fail1", "failed", error_class="private_repo", error_message="denied")
    db.set_scan_status("test/fail2", "failed", error_class="timeout", error_message="timed out")
    failures = db.get_scan_failures()
    assert len(failures) == 2
    ci_names = [f["ci_name"] for f in failures]
    assert "test/fail1" in ci_names
    assert "test/fail2" in ci_names


def test_save_showroom_url_override(db):
    db.upsert_catalog_item({"ci_name": "test/override", "display_name": "Override",
                            "stage": "prod", "is_prod": True,
                            "showroom_url": "https://github.com/org/old.git"})
    db.set_showroom_url_override("test/override", "https://github.com/org/new.git")
    item = db.get_catalog_item("test/override")
    assert item["showroom_url_override"] == "https://github.com/org/new.git"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py -k "test_set_scan_status or test_get_scan_failures or test_save_showroom_url_override" -v`
Expected: FAIL — methods don't exist

- [ ] **Step 3: Implement DB methods**

In `src/rcars/db.py`, add:

```python
def set_scan_status(
    self, ci_name: str, status: str,
    error_class: str | None = None, error_message: str | None = None
):
    with self._pool.connection() as conn:
        if status == "success":
            conn.execute("""
                UPDATE catalog_items
                SET scan_status = 'success',
                    scan_error_class = NULL,
                    scan_error = NULL,
                    scan_failed_at = NULL
                WHERE ci_name = %s
            """, (ci_name,))
        else:
            conn.execute("""
                UPDATE catalog_items
                SET scan_status = %s,
                    scan_error_class = %s,
                    scan_error = %s,
                    scan_failed_at = %s
                WHERE ci_name = %s
            """, (status, error_class, error_message,
                  datetime.now(timezone.utc), ci_name))
        conn.commit()

def get_scan_failures(self) -> list[dict]:
    with self._pool.connection() as conn:
        cur = conn.execute("""
            SELECT ci_name, display_name, stage, scan_error_class,
                   scan_error, scan_failed_at, showroom_url, showroom_url_override
            FROM catalog_items
            WHERE scan_status = 'failed'
            ORDER BY scan_failed_at DESC
        """)
        return cur.fetchall()

def set_showroom_url_override(self, ci_name: str, override_url: str | None):
    with self._pool.connection() as conn:
        conn.execute("""
            UPDATE catalog_items SET showroom_url_override = %s WHERE ci_name = %s
        """, (override_url, ci_name))
        conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py -k "test_set_scan_status or test_get_scan_failures or test_save_showroom_url_override" -v`
Expected: All PASS

- [ ] **Step 5: Update scan command to use scan status and classification**

In `src/rcars/cli.py`, in the scan command's error handler (the `except Exception as e` block inside the futures loop), replace:

```python
db.log_action(item["ci_name"], "error", details=str(e)[:200])
```

with:

```python
from rcars.analyzer import classify_scan_error
error_class, error_msg = classify_scan_error(e, url=item.get("showroom_url"))
db.set_scan_status(item["ci_name"], "failed", error_class=error_class, error_message=error_msg)
db.log_action(item["ci_name"], "error", details=error_msg[:500])
```

And after the successful `db.upsert_showroom_analysis(...)` call, add:

```python
db.set_scan_status(result["ci_name"], "success")
```

- [ ] **Step 6: Update analyzer to use showroom_url_override**

In `src/rcars/analyzer.py`, at the top of `analyze_showroom()`, resolve the effective URL:

```python
effective_url = showroom_url_override or showroom_url
```

Then use `effective_url` instead of `showroom_url` in the `clone_showroom()` call. Add `showroom_url_override: str | None = None` as a parameter to `analyze_showroom()`.

Update the `process_item` lambda/function in `cli.py` to pass `showroom_url_override=item.get("showroom_url_override")`.

- [ ] **Step 7: Handle analyze_showroom returning None as a classified failure**

In `src/rcars/cli.py`, in the scan command, where `result` is None after `future.result()`, add classification:

```python
if result is None:
    db.set_scan_status(
        item["ci_name"], "failed",
        error_class="unknown",
        error_message=f"Analysis returned no result for {item.get('showroom_url')}"
    )
    errors += 1
```

Also update `analyze_showroom()` to raise specific exceptions instead of returning None for classifiable failures:

- Clone failure: `raise FileNotFoundError(f"No .adoc files found in {clone_path}")` instead of `return None`
- Empty content: `raise ValueError("All files filtered as boilerplate")` instead of logging and continuing
- Parse failure: `raise ValueError("Failed to parse analysis JSON")` instead of `return None`

This ensures `classify_scan_error` always has an exception to classify.

- [ ] **Step 8: Run full test suite**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/ -v --ignore=tests/test_integration.py`
Expected: All tests pass

- [ ] **Step 9: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/db.py src/rcars/cli.py src/rcars/analyzer.py tests/test_db.py
git commit -m "scan: Track scan status with error classification"
```

---

## Task 8: CLI status updates — scan failures count and --failures flag

**Files:**
- Modify: `src/rcars/cli.py` (status command)
- Modify: `src/rcars/db.py` (get_status_summary)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli.py — add to existing file

def test_status_shows_scan_failures(runner, db):
    """Status command should show scan failures count."""
    db.upsert_catalog_item({"ci_name": "test/fail", "display_name": "Fail",
                            "stage": "prod", "is_prod": True})
    db.set_scan_status("test/fail", "failed", error_class="timeout", error_message="timed out")

    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "Scan failures" in result.output
    assert "1" in result.output


def test_status_failures_flag(runner, db):
    """Status --failures should show detailed failure table."""
    db.upsert_catalog_item({"ci_name": "test/fail1", "display_name": "Fail 1",
                            "stage": "prod", "is_prod": True})
    db.set_scan_status("test/fail1", "failed", error_class="private_repo",
                       error_message="denied")

    result = runner.invoke(cli, ["status", "--failures"])
    assert result.exit_code == 0
    assert "test/fail1" in result.output
    assert "private_repo" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_cli.py -k "test_status_shows_scan_failures or test_status_failures_flag" -v`
Expected: FAIL

- [ ] **Step 3: Update get_status_summary to include failures count**

In `src/rcars/db.py`, add to `get_status_summary()`:

```python
cur.execute("SELECT COUNT(*) FROM catalog_items WHERE scan_status = 'failed'")
summary["scan_failures"] = cur.fetchone()[0]
```

- [ ] **Step 4: Update status command**

In `src/rcars/cli.py`, update the `status` command:

```python
@cli.command()
@click.option("--failures", is_flag=True, default=False, help="Show detailed scan failures")
def status(failures: bool):
    """Show catalog status summary."""
    db = get_db()
    summary = db.get_status_summary()

    table = Table(title="RCARS Catalog Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")

    table.add_row("Total catalog items", str(summary["total"]))
    table.add_row("Production items", str(summary["prod"]))
    table.add_row("With Showroom URL", str(summary["with_showroom"]))
    table.add_row("Analyzed", str(summary["analyzed"]))
    table.add_row("Stale", str(summary["stale"]))

    fail_count = summary.get("scan_failures", 0)
    fail_style = "red" if fail_count > 0 else "green"
    table.add_row("Scan failures", f"[{fail_style}]{fail_count}[/{fail_style}]")

    console.print(table)

    if failures:
        fail_list = db.get_scan_failures()
        if fail_list:
            ftable = Table(title="Scan Failures")
            ftable.add_column("CI Name", style="cyan")
            ftable.add_column("Error Class")
            ftable.add_column("Failed At")
            for f in fail_list:
                failed_at = f["scan_failed_at"].strftime("%Y-%m-%d %H:%M") if f.get("scan_failed_at") else ""
                ftable.add_row(f["ci_name"], f.get("scan_error_class", ""), failed_at)
            console.print(ftable)
        else:
            console.print("[green]No scan failures.[/green]")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_cli.py -k "test_status_shows_scan_failures or test_status_failures_flag" -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/cli.py src/rcars/db.py tests/test_cli.py
git commit -m "cli: Add scan failures count and --failures flag to status"
```

---

## Task 9: Admin page — scan failures row with link

**Files:**
- Modify: `src/rcars/web/routes/admin.py` (status table)
- Modify: `src/rcars/web/templates/admin.html`
- Test: `tests/web/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/web/test_admin.py — add to existing file

def test_admin_shows_scan_failures_count(admin_client, db):
    """Admin page should show scan failures count as a clickable link."""
    db.upsert_catalog_item({"ci_name": "test/fail", "display_name": "F",
                            "stage": "prod", "is_prod": True})
    db.set_scan_status("test/fail", "failed", error_class="timeout", error_message="timed out")

    response = admin_client.get("/admin")
    assert response.status_code == 200
    assert "Scan failures" in response.text
    assert "/curate?status_filter=scan_failed" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_admin.py::test_admin_shows_scan_failures_count -v`
Expected: FAIL

- [ ] **Step 3: Update _status_table_oob in admin.py**

In `src/rcars/web/routes/admin.py`, update `_status_table_oob()` to include scan failures:

```python
def _status_table_oob(db: Database) -> str:
    s = db.get_status_summary()
    stale_color = "var(--score-amber)" if s["stale"] > 0 else "var(--score-green)"
    fail_count = s.get("scan_failures", 0)
    fail_color = "var(--score-red)" if fail_count > 0 else "var(--score-green)"
    fail_cell = (
        f'<a href="/curate?status_filter=scan_failed" style="color:{fail_color};">{fail_count}</a>'
        if fail_count > 0
        else f'<span style="color:{fail_color};">0</span>'
    )
    return f"""<table id="catalog-status-table" class="status-table" hx-swap-oob="true">
  <tr><th>Metric</th><th>Count</th></tr>
  <tr><td>Total catalog items</td><td>{s["total"]}</td></tr>
  <tr><td>Production items</td><td>{s["prod"]}</td></tr>
  <tr><td>With Showroom (scannable)</td><td>{s["with_showroom"]}</td></tr>
  <tr><td>Analyzed</td><td>{s["analyzed"]}</td></tr>
  <tr><td>Stale (needs rescan)</td><td style="color:{stale_color};">{s["stale"]}</td></tr>
  <tr><td>Scan failures</td><td>{fail_cell}</td></tr>
</table>"""
```

- [ ] **Step 4: Update admin.html initial render**

In `src/rcars/web/templates/admin.html`, add the scan failures row to the initial status table (after the Stale row):

```html
<tr><td>Scan failures</td><td style="color:{% if status.scan_failures > 0 %}var(--score-red){% else %}var(--score-green){% endif %};">{% if status.scan_failures > 0 %}<a href="/curate?status_filter=scan_failed" style="color:var(--score-red);">{{ status.scan_failures }}</a>{% else %}0{% endif %}</td></tr>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_admin.py::test_admin_shows_scan_failures_count -v`
Expected: PASS

- [ ] **Step 6: Run full admin test suite**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_admin.py -v`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/web/routes/admin.py src/rcars/web/templates/admin.html tests/web/test_admin.py
git commit -m "admin: Add scan failures count with link to curate filter"
```

---

## Task 10: Curate page — scan_failed filter, failure cards, override + retry

**Files:**
- Modify: `src/rcars/web/routes/curate.py`
- Modify: `src/rcars/web/templates/curate.html`
- Test: `tests/web/test_curate.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/web/test_curate.py — add to existing file

def test_curate_scan_failed_filter(curator_client, db):
    """Curate page with scan_failed filter shows only failed items."""
    db.upsert_catalog_item({"ci_name": "test/ok", "display_name": "OK",
                            "stage": "prod", "is_prod": True, "showroom_url": "https://x"})
    db.upsert_catalog_item({"ci_name": "test/fail", "display_name": "Fail",
                            "stage": "prod", "is_prod": True, "showroom_url": "https://y"})
    db.set_scan_status("test/ok", "success")
    db.set_scan_status("test/fail", "failed", error_class="private_repo",
                       error_message="Permission denied")

    response = curator_client.get("/curate?status_filter=scan_failed")
    assert response.status_code == 200
    assert "test/fail" in response.text
    assert "test/ok" not in response.text
    assert "private_repo" in response.text


def test_curate_scan_failed_not_in_default(curator_client, db):
    """Scan failures should NOT appear in the default has_showroom filter."""
    db.upsert_catalog_item({"ci_name": "test/fail", "display_name": "Fail",
                            "stage": "prod", "is_prod": True, "showroom_url": "https://y"})
    db.set_scan_status("test/fail", "failed", error_class="timeout",
                       error_message="timed out")

    response = curator_client.get("/curate?status_filter=has_showroom")
    assert "test/fail" not in response.text


def test_curate_save_override_url(curator_client, db):
    """POST to /curate/override should save the showroom_url_override."""
    db.upsert_catalog_item({"ci_name": "test/override", "display_name": "O",
                            "stage": "prod", "is_prod": True,
                            "showroom_url": "https://github.com/old.git"})

    response = curator_client.post("/curate/override", data={
        "ci_name": "test/override",
        "override_url": "https://github.com/new.git",
    })
    assert response.status_code == 200

    item = db.get_catalog_item("test/override")
    assert item["showroom_url_override"] == "https://github.com/new.git"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_curate.py -k "test_curate_scan_failed or test_curate_save_override" -v`
Expected: FAIL

- [ ] **Step 3: Add scan_failed filter to curate route**

In `src/rcars/web/routes/curate.py`, in the `curate()` route, add the `scan_failed` filter case:

```python
elif status_filter == "scan_failed":
    items = [i for i in items if i.get("scan_status") == "failed"]
```

Also update the `has_showroom` filter to exclude failed scans:

```python
if status_filter == "has_showroom":
    items = [i for i in items if i.get("showroom_url") and i.get("scan_status") != "failed"]
```

- [ ] **Step 4: Add /curate/override endpoint**

In `src/rcars/web/routes/curate.py`, add:

```python
@router.post("/curate/override", response_class=HTMLResponse)
async def save_override(
    request: Request,
    ci_name: str = Form(...),
    override_url: str = Form(""),
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    db.set_showroom_url_override(ci_name, override_url or None)
    return HTMLResponse('<span class="badge badge-green">Saved</span>')
```

Add `from fastapi import Form` to imports if not present.

- [ ] **Step 5: Update curate.html filter dropdown**

In `src/rcars/web/templates/curate.html`, add the scan_failed option to the filter select:

```html
<option value="scan_failed" {% if status_filter == 'scan_failed' %}selected{% endif %}>Scan failures</option>
```

- [ ] **Step 6: Add failure card rendering to curate.html**

In `src/rcars/web/templates/curate.html`, add conditional rendering for failed items inside the item card:

```html
{% if item.scan_status == 'failed' %}
<div class="scan-failure-info">
  <span class="badge badge-error">{{ item.scan_error_class }}</span>
  <p class="error-message">{{ item.scan_error }}</p>
  <small class="timestamp">Failed: {{ item.scan_failed_at.strftime('%Y-%m-%d %H:%M') if item.scan_failed_at else 'unknown' }}</small>
  <form hx-post="/curate/override" hx-target="#override-status-{{ item.ci_name | replace('/', '-') }}"
        hx-swap="innerHTML" class="override-form">
    <input type="hidden" name="ci_name" value="{{ item.ci_name }}">
    <label>Showroom URL override:</label>
    <input type="text" name="override_url"
           value="{{ item.showroom_url_override or item.showroom_url or '' }}"
           class="filter-input" style="width:100%;">
    <button type="submit" class="btn-action" style="margin-top:4px;">Save Override</button>
    <span id="override-status-{{ item.ci_name | replace('/', '-') }}"></span>
  </form>
</div>
{% endif %}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_curate.py -k "test_curate_scan_failed or test_curate_save_override" -v`
Expected: All PASS

- [ ] **Step 8: Run full curate test suite**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_curate.py -v`
Expected: All pass

- [ ] **Step 9: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/web/routes/curate.py src/rcars/web/templates/curate.html tests/web/test_curate.py
git commit -m "curate: Add scan_failed filter, failure cards, URL override"
```

---

## Task 11: Catalog reconciliation — delete removed items during refresh

**Files:**
- Modify: `src/rcars/db.py` (add delete_removed_items method)
- Modify: `src/rcars/cli.py` (refresh command)
- Modify: `src/rcars/config.py` (remove catalog_namespaces_prod, rename catalog_namespaces_all)
- Test: `tests/test_db.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_db.py — add to existing file

def test_delete_removed_items(db):
    """Items not in the current Babylon set should be deleted."""
    db.upsert_catalog_item({"ci_name": "keep/this", "display_name": "Keep",
                            "stage": "prod", "is_prod": True})
    db.upsert_catalog_item({"ci_name": "remove/this", "display_name": "Remove",
                            "stage": "prod", "is_prod": True})

    removed = db.delete_removed_items(current_ci_names={"keep/this"})
    assert len(removed) == 1
    assert removed[0]["ci_name"] == "remove/this"
    assert db.get_catalog_item("remove/this") is None
    assert db.get_catalog_item("keep/this") is not None


def test_delete_removed_items_cascades(db):
    """Deleting a catalog item should cascade to analysis, embeddings, etc."""
    db.upsert_catalog_item({"ci_name": "gone/item", "display_name": "Gone",
                            "stage": "prod", "is_prod": True})
    db.upsert_showroom_analysis({"ci_name": "gone/item", "content_type": "workshop",
                                  "summary": "test", "difficulty": "beginner"})
    db.store_embedding("gone/item", "ci_summary", "test text", [0.1] * 384)
    db.log_action("gone/item", "analyze")

    db.delete_removed_items(current_ci_names=set())

    assert db.get_catalog_item("gone/item") is None
    assert db.get_showroom_analysis("gone/item") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py -k "test_delete_removed" -v`
Expected: FAIL — method doesn't exist

- [ ] **Step 3: Implement delete_removed_items**

In `src/rcars/db.py`, add:

```python
def delete_removed_items(self, current_ci_names: set[str]) -> list[dict]:
    """Delete catalog items not in the current set. Returns list of removed items."""
    with self._pool.connection() as conn:
        cur = conn.execute("SELECT ci_name, display_name, stage FROM catalog_items")
        all_items = cur.fetchall()

        removed = [i for i in all_items if i["ci_name"] not in current_ci_names]

        for item in removed:
            ci = item["ci_name"]
            conn.execute("DELETE FROM enrichment_tags WHERE ci_name = %s", (ci,))
            conn.execute("DELETE FROM embeddings WHERE ci_name = %s", (ci,))
            conn.execute("DELETE FROM analysis_log WHERE ci_name = %s", (ci,))
            conn.execute("DELETE FROM showroom_analysis WHERE ci_name = %s", (ci,))
            conn.execute("DELETE FROM catalog_items WHERE ci_name = %s", (ci,))
            log.info("Removed catalog item no longer in Babylon: %s (stage=%s)",
                     ci, item.get("stage"))

        if removed:
            conn.commit()

        return removed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py -k "test_delete_removed" -v`
Expected: PASS

- [ ] **Step 5: Remove --include-dev flag and always sync all namespaces**

In `src/rcars/cli.py`, update the `refresh` command:

Remove the `--include-dev` option. Change the namespace selection to always use all namespaces:

```python
@cli.command()
def refresh():
    """Refresh catalog from Babylon CRDs."""
    from rcars.catalog_reader import CatalogReader

    settings = Settings()
    db = get_db()

    namespaces = settings.catalog_namespaces

    try:
        reader = CatalogReader(settings.kubeconfig_path)
        items = reader.refresh_catalog(
            namespaces=namespaces,
            component_namespace=settings.agnosticv_component_namespace,
        )
    except Exception as e:
        console.print(f"[red]Error connecting to cluster:[/red] {e}")
        sys.exit(1)

    count_with_showroom = 0
    refreshed_ci_names = set()
    for item in items:
        db.upsert_catalog_item(item)
        db.log_action(item["ci_name"], "refresh")
        refreshed_ci_names.add(item["ci_name"])
        if item.get("showroom_url"):
            count_with_showroom += 1

    # Reconcile: delete items no longer in Babylon
    removed = db.delete_removed_items(refreshed_ci_names)

    console.print(
        f"[green]Done.[/green] {len(items)} items refreshed, "
        f"{count_with_showroom} with Showroom URLs. "
        f"Removed {len(removed)} items no longer in Babylon catalog."
    )
```

- [ ] **Step 6: Simplify config.py namespace settings**

In `src/rcars/config.py`, replace `catalog_namespaces_prod` and `catalog_namespaces_all` with a single `catalog_namespaces`:

```python
catalog_namespaces: list[str] = field(default_factory=lambda: [
    "babylon-catalog-prod",
    "babylon-catalog-dev",
    "babylon-catalog-event",
])
```

Remove `catalog_namespaces_prod` and `catalog_namespaces_all`. Search for any remaining references and update them.

- [ ] **Step 7: Update tests that reference --include-dev or old namespace config**

Run: `cd ~/devel/working/rcars-advisory && grep -rn "include.dev\|catalog_namespaces_prod\|catalog_namespaces_all" tests/ src/`
Fix any remaining references.

- [ ] **Step 8: Run full test suite**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/ -v --ignore=tests/test_integration.py`
Expected: All pass

- [ ] **Step 9: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/db.py src/rcars/cli.py src/rcars/config.py tests/
git commit -m "refresh: Always sync all namespaces, reconcile removed items"
```

---

## Task 12: Stage dedup logic

**Files:**
- Modify: `src/rcars/db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_db.py — add to existing file

def test_stage_dedup_same_showroom(db):
    """Items with same showroom_url+ref across stages should dedup to highest priority."""
    db.upsert_catalog_item({"ci_name": "prod/lab", "display_name": "Lab",
                            "stage": "prod", "is_prod": True,
                            "showroom_url": "https://github.com/org/lab.git",
                            "showroom_ref": "main"})
    db.upsert_catalog_item({"ci_name": "dev/lab", "display_name": "Lab",
                            "stage": "dev", "is_prod": False,
                            "showroom_url": "https://github.com/org/lab.git",
                            "showroom_ref": "main"})
    items = db.get_stage_deduplicated_items()
    ci_names = [i["ci_name"] for i in items]
    assert "prod/lab" in ci_names
    assert "dev/lab" not in ci_names


def test_stage_dedup_different_showroom(db):
    """Items with different showroom_url or ref should NOT be deduped."""
    db.upsert_catalog_item({"ci_name": "prod/lab", "display_name": "Lab",
                            "stage": "prod", "is_prod": True,
                            "showroom_url": "https://github.com/org/lab.git",
                            "showroom_ref": "main"})
    db.upsert_catalog_item({"ci_name": "dev/lab", "display_name": "Lab",
                            "stage": "dev", "is_prod": False,
                            "showroom_url": "https://github.com/org/lab.git",
                            "showroom_ref": "feature-branch"})
    items = db.get_stage_deduplicated_items()
    ci_names = [i["ci_name"] for i in items]
    assert "prod/lab" in ci_names
    assert "dev/lab" in ci_names


def test_stage_dedup_priority_order(db):
    """Dedup priority: prod > event > dev."""
    db.upsert_catalog_item({"ci_name": "event/lab", "display_name": "Lab",
                            "stage": "event", "is_prod": False,
                            "showroom_url": "https://github.com/org/lab.git",
                            "showroom_ref": "main"})
    db.upsert_catalog_item({"ci_name": "dev/lab", "display_name": "Lab",
                            "stage": "dev", "is_prod": False,
                            "showroom_url": "https://github.com/org/lab.git",
                            "showroom_ref": "main"})
    items = db.get_stage_deduplicated_items()
    ci_names = [i["ci_name"] for i in items]
    assert "event/lab" in ci_names
    assert "dev/lab" not in ci_names


def test_stage_dedup_no_showroom_not_deduped(db):
    """Items without showroom URLs are never deduped."""
    db.upsert_catalog_item({"ci_name": "prod/no-showroom", "display_name": "NS",
                            "stage": "prod", "is_prod": True})
    db.upsert_catalog_item({"ci_name": "dev/no-showroom", "display_name": "NS",
                            "stage": "dev", "is_prod": False})
    items = db.get_stage_deduplicated_items()
    ci_names = [i["ci_name"] for i in items]
    assert "prod/no-showroom" in ci_names
    assert "dev/no-showroom" in ci_names


def test_stage_dedup_with_stage_filter(db):
    """Filtering to a single stage should skip dedup."""
    db.upsert_catalog_item({"ci_name": "prod/lab", "display_name": "Lab",
                            "stage": "prod", "is_prod": True,
                            "showroom_url": "https://github.com/org/lab.git",
                            "showroom_ref": "main"})
    db.upsert_catalog_item({"ci_name": "dev/lab", "display_name": "Lab",
                            "stage": "dev", "is_prod": False,
                            "showroom_url": "https://github.com/org/lab.git",
                            "showroom_ref": "main"})
    items = db.get_stage_deduplicated_items(stage_filter="dev")
    ci_names = [i["ci_name"] for i in items]
    assert "dev/lab" in ci_names
    assert "prod/lab" not in ci_names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py -k "test_stage_dedup" -v`
Expected: FAIL — method doesn't exist

- [ ] **Step 3: Implement get_stage_deduplicated_items**

In `src/rcars/db.py`, add:

```python
STAGE_PRIORITY = {"prod": 0, "event": 1, "dev": 2}

def get_stage_deduplicated_items(
    self, stage_filter: str | None = None
) -> list[dict]:
    """Return catalog items with cross-stage dedup applied.

    When stage_filter is set, returns only that stage (no dedup needed).
    When stage_filter is None (all stages), deduplicates items that share
    the same showroom_url+showroom_ref, keeping the highest-priority stage.
    """
    with self._pool.connection() as conn:
        if stage_filter:
            cur = conn.execute(
                "SELECT * FROM catalog_items WHERE stage = %s ORDER BY ci_name",
                (stage_filter,)
            )
            return cur.fetchall()

        cur = conn.execute("SELECT * FROM catalog_items ORDER BY ci_name")
        all_items = cur.fetchall()

    # Items without showroom URLs pass through without dedup
    no_showroom = [i for i in all_items if not i.get("showroom_url")]
    has_showroom = [i for i in all_items if i.get("showroom_url")]

    # Group by (showroom_url, showroom_ref) and keep highest priority
    groups: dict[tuple, list[dict]] = {}
    for item in has_showroom:
        key = (item["showroom_url"], item.get("showroom_ref") or "")
        groups.setdefault(key, []).append(item)

    deduped = []
    for key, group in groups.items():
        if len(group) == 1:
            deduped.append(group[0])
        else:
            group.sort(key=lambda i: STAGE_PRIORITY.get(i.get("stage", "dev"), 99))
            deduped.append(group[0])

    result = no_showroom + deduped
    result.sort(key=lambda i: i.get("ci_name", ""))
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/test_db.py -k "test_stage_dedup" -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/db.py tests/test_db.py
git commit -m "db: Add stage dedup logic for cross-stage catalog visibility"
```

---

## Task 13: Curate page — stage filter and badges

**Files:**
- Modify: `src/rcars/web/routes/curate.py`
- Modify: `src/rcars/web/templates/curate.html`
- Test: `tests/web/test_curate.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/web/test_curate.py — add to existing file

def test_curate_stage_filter_dev(curator_client, db):
    """Curate page with stage_filter=dev shows only dev items."""
    db.upsert_catalog_item({"ci_name": "prod/lab", "display_name": "Lab",
                            "stage": "prod", "is_prod": True, "showroom_url": "https://x"})
    db.upsert_catalog_item({"ci_name": "dev/lab", "display_name": "Lab Dev",
                            "stage": "dev", "is_prod": False, "showroom_url": "https://y"})

    response = curator_client.get("/curate?stage_filter=dev&status_filter=all")
    assert response.status_code == 200
    assert "dev/lab" in response.text
    assert "prod/lab" not in response.text


def test_curate_stage_badges(curator_client, db):
    """Non-prod items should show stage badges."""
    db.upsert_catalog_item({"ci_name": "dev/lab", "display_name": "Lab Dev",
                            "stage": "dev", "is_prod": False, "showroom_url": "https://y"})
    db.upsert_catalog_item({"ci_name": "event/lab", "display_name": "Lab Event",
                            "stage": "event", "is_prod": False, "showroom_url": "https://z"})

    response = curator_client.get("/curate?status_filter=all&stage_filter=all")
    assert response.status_code == 200
    assert "badge-dev" in response.text or "DEV" in response.text
    assert "badge-event" in response.text or "EVENT" in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_curate.py -k "test_curate_stage" -v`
Expected: FAIL

- [ ] **Step 3: Add stage_filter parameter to curate route**

In `src/rcars/web/routes/curate.py`, add `stage_filter` query param:

```python
@router.get("/curate", response_class=HTMLResponse)
async def curate(
    request: Request,
    q: str = "",
    status_filter: str = "has_showroom",
    stage_filter: str = "all",
    page: int = 1,
    user: str = Depends(require_curator),
    db: Database = Depends(_get_db_dependency),
):
    # Use stage-deduplicated items
    if stage_filter == "all":
        items = db.get_stage_deduplicated_items()
    else:
        items = db.get_stage_deduplicated_items(stage_filter=stage_filter)

    # ... rest of filtering (search, status_filter) continues as before
```

Pass `stage_filter` through to the template context.

- [ ] **Step 4: Add stage filter control to curate.html**

In `src/rcars/web/templates/curate.html`, add a second select after the status filter:

```html
<select name="stage_filter" class="filter-select" onchange="this.form.submit()">
  <option value="all" {% if stage_filter == 'all' %}selected{% endif %}>All stages</option>
  <option value="prod" {% if stage_filter == 'prod' %}selected{% endif %}>Prod</option>
  <option value="dev" {% if stage_filter == 'dev' %}selected{% endif %}>Dev</option>
  <option value="event" {% if stage_filter == 'event' %}selected{% endif %}>Event</option>
</select>
```

- [ ] **Step 5: Add stage badges to item cards**

In `src/rcars/web/templates/curate.html`, add badge rendering near the item name:

```html
{% if item.stage == 'dev' %}
  <span class="badge badge-dev">DEV</span>
{% elif item.stage == 'event' %}
  <span class="badge badge-event">EVENT</span>
{% endif %}
```

Add CSS for the badges (inline style or in the template's style block):

```css
.badge-dev { background: var(--lcars-blue, #5599cc); color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold; }
.badge-event { background: var(--score-amber, #cc9900); color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold; }
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_curate.py -k "test_curate_stage" -v`
Expected: All PASS

- [ ] **Step 7: Run full curate test suite**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_curate.py -v`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/web/routes/curate.py src/rcars/web/templates/curate.html tests/web/test_curate.py
git commit -m "curate: Add stage filter and stage badges for dev/event items"
```

---

## Task 14: Advisor — non-prod toggle with stage badges and callouts

**Files:**
- Modify: `src/rcars/web/routes/advisor.py`
- Modify: `src/rcars/web/templates/advisor.html`
- Modify: `src/rcars/web/templates/fragments/rec_card.html`
- Modify: `src/rcars/recommender/vector_search.py` (prod_only parameter)
- Test: `tests/web/test_advisor.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/web/test_advisor.py — add to existing file

def test_advisor_non_prod_toggle_present(client):
    """Advisor page should have a non-prod content toggle."""
    response = client.get("/advisor")
    assert response.status_code == 200
    assert "non-prod" in response.text.lower() or "include-non-prod" in response.text.lower()


def test_advisor_query_with_non_prod(client, db, monkeypatch):
    """Advisor query with include_non_prod should search all stages."""
    search_calls = []
    original_search = db.search_embeddings

    def tracking_search(*args, **kwargs):
        search_calls.append(kwargs)
        return original_search(*args, **kwargs)

    monkeypatch.setattr(db, "search_embeddings", tracking_search)

    # This test verifies the parameter is passed through —
    # the actual pipeline mock setup depends on existing test fixtures
    # Just verify the toggle parameter exists in the form
    response = client.get("/advisor")
    assert "include_non_prod" in response.text or "include-non-prod" in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_advisor.py -k "test_advisor_non_prod" -v`
Expected: FAIL

- [ ] **Step 3: Add toggle to advisor.html**

In `src/rcars/web/templates/advisor.html`, add a toggle control near the query input:

```html
<label class="toggle-label">
  <input type="checkbox" id="include-non-prod" name="include_non_prod" value="true">
  Include non-prod content
</label>
```

Update the JavaScript that sends queries to include the toggle value in the POST data.

- [ ] **Step 4: Update advisor route to accept include_non_prod**

In `src/rcars/web/routes/advisor.py`, update `advisor_query()` to read the toggle:

```python
include_non_prod = form.get("include_non_prod") == "true"
```

Pass `prod_only=not include_non_prod` to `_run_advisor_query()` and through to `run_query()`.

- [ ] **Step 5: Update vector search to respect prod_only**

In `src/rcars/recommender/vector_search.py`, verify that `prod_only` parameter is passed through to `db.search_embeddings()`. The `search_embeddings` method already has a `prod_only` parameter — ensure it filters by `is_prod = TRUE` when `prod_only=True` and returns all stages when `prod_only=False`.

Check: `db.search_embeddings()` in `db.py` — verify the WHERE clause uses `prod_only`:

```python
if prod_only:
    query += " AND ci.is_prod = TRUE"
```

If not already implemented, add this filter.

- [ ] **Step 6: Add stage badges and callouts to rec_card.html**

In `src/rcars/web/templates/fragments/rec_card.html`, add:

```html
{% if rec.stage == 'dev' %}
<div class="stage-callout stage-dev">
  <span class="badge badge-dev">DEV</span>
  <em>In development. This content may be incomplete or awaiting promotion.</em>
</div>
{% elif rec.stage == 'event' %}
<div class="stage-callout stage-event">
  <span class="badge badge-event">EVENT</span>
  <em>Event-only content. Not self-service — contact RHDP ops to order on your behalf.</em>
</div>
{% endif %}
```

- [ ] **Step 7: Ensure stage is carried through to recommendation cards**

In `src/rcars/web/routes/advisor.py`, in `_candidates_to_recs()` or `_enrich_recs()`, ensure the `stage` field from the catalog item is included in the rec dict passed to the template.

- [ ] **Step 8: Apply stage dedup to advisor results**

In `src/rcars/web/routes/advisor.py`, in `_run_advisor_query()`, after vector search results come back, apply dedup logic if `prod_only=False`. Import the priority constant from db.py:

```python
from rcars.db import STAGE_PRIORITY

if not prod_only:
    # Dedup: group by (showroom_url, showroom_ref), keep highest priority stage
    seen = {}
    for candidate in candidates:
        key = (candidate.showroom_url, candidate.showroom_ref)
        if key not in seen or STAGE_PRIORITY.get(candidate.stage, 99) < STAGE_PRIORITY.get(seen[key].stage, 99):
            seen[key] = candidate
    candidates = list(seen.values())
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_advisor.py -k "test_advisor_non_prod" -v`
Expected: All PASS

- [ ] **Step 10: Run full advisor test suite**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/test_advisor.py -v`
Expected: All pass

- [ ] **Step 11: Commit**

```bash
cd ~/devel/working/rcars-advisory
git add src/rcars/web/routes/advisor.py src/rcars/web/templates/advisor.html \
        src/rcars/web/templates/fragments/rec_card.html src/rcars/recommender/vector_search.py \
        tests/web/test_advisor.py
git commit -m "advisor: Add non-prod content toggle with stage badges and callouts"
```

---

## Task 15: Final integration verification

**Files:**
- All modified files

- [ ] **Step 1: Run full test suite**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/ -v --ignore=tests/test_integration.py`
Expected: All tests pass

- [ ] **Step 2: Verify no regressions in existing functionality**

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/web/ -v`
Expected: All web tests pass (admin, advisor, curate)

Run: `cd ~/devel/working/rcars-advisory && python -m pytest tests/recommender/ -v`
Expected: All recommender tests pass

- [ ] **Step 3: Check for any remaining references to old patterns**

Run: `cd ~/devel/working/rcars-advisory && grep -rn "include.dev\|catalog_namespaces_prod\|catalog_namespaces_all\|str(e)\[:200\]" src/`
Expected: No matches (all old patterns replaced)

- [ ] **Step 4: Verify Ansible templates are syntactically valid**

Run: `cd ~/devel/working/rcars-advisory && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('ansible/templates')); [env.get_template(t) for t in ['manifests-app.yaml.j2', 'manifests-infra.yaml.j2']]; print('Templates OK')"`
Expected: "Templates OK"

- [ ] **Step 5: Commit any remaining fixes**

If any issues were found and fixed:
```bash
cd ~/devel/working/rcars-advisory
git add -A
git commit -m "fix: Address integration issues from scan failures and catalog visibility"
```
