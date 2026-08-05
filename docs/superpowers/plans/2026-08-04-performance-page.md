# Performance Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Jira:** [RHDPCD-662](https://redhat.atlassian.net/browse/RHDPCD-662)
**Spec:** `docs/superpowers/specs/2026-08-04-performance-page-design.md`
**Branch:** ALL implementation commits go on `feature/advisor-chat` (already checked out locally, tracks `origin/feature/advisor-chat`). Do NOT create a new branch. `main` has already been merged in (spec + this plan).

**Goal:** Replace the Retirement Analysis page with a Performance page — inverted scoring (higher = better), Browse-style sidebar layout, URL state, channel tabs, renamed API endpoints — so the advisor chat's performance deep-links work.

**Architecture:** Backend-first: invert the scoring formula in `reporting_sync.py`, rename `/analysis/retirement*` endpoints to `/analysis/performance*` with new `window`/`channel` params, then rewrite the frontend page copying BrowsePage's sidebar + URL-sync patterns while porting the existing retirement workflow drawer unchanged. Chat handler drops the `retirement_flavored` flag. Docs and CLAUDE.md updated last.

**Tech Stack:** Python 3.11 + FastAPI + psycopg (pytest), React 19 + TypeScript + react-router-dom (vitest), Ansible/Jinja2 for OpenShift deploy.

## Global Constraints

- All commits on `feature/advisor-chat`. Commit messages prefixed `[RHDPCD-662]`.
- Time window values are `3m` / `6m` / `9m` / `12m` **everywhere** (API param, URL param, chat args, stored `windowed_metrics` keys — they already match). Default is `12m`. The old `1q/2q/3q/1y` values and the `WINDOW_KEYS` mapping are removed.
- Channel API/URL values are `sales` and `marketing`. Internal source mapping: `{"sales": "rhdp", "marketing": "interactive_labs"}` — defined once as `CHANNEL_SOURCES` in `src/api/rcars/api/routes/analysis.py`.
- Score thresholds: Strong ≥ 55 (green), Moderate 35–54 (amber), Low < 35 (red). Higher = better everywhere.
- Zero-activity items score minimum (0) per factor. Age discount is removed entirely.
- New env var `RCARS_PERFORMANCE_PUBLIC` (Settings field `performance_public: bool = True`). When `false`, page + endpoint revert to curator-only.
- `retirement_flavored` is removed from all four files that reference it (chat models, handlers, registry, PerformanceTableBlock).
- No redirects from old `/analysis/retirement*` paths — clean rename, no external callers.
- No shared component extraction between Browse and Performance.
- Existing retirement **workflow** behavior (stepper, Jira, mute, notes) is unchanged except the approval snapshot becomes channel-keyed.
- Python tests: `source ~/.virtualenvs/rcars-v2/bin/activate && cd src/api && python -m pytest tests/ -m "not integration"` (needs local PostgreSQL+Redis from `./dev-services.sh start`). Frontend: `cd src/frontend && npx vitest run && npm run build`.
- After code changes, run `graphify update .` (AST-only) before the final commit of each task batch is optional; run it once in Task 15.

---

### Task 1: Invert the scoring formula (TDD)

**Files:**
- Modify: `src/api/rcars/services/reporting_sync.py:42-273` (scorer), `:507-556` (`_recompute_windowed_scores`), `:583-662` (`_build_windowed_metrics`)
- Test: `src/api/tests/test_reporting.py`

**Interfaces:**
- Produces: `compute_performance_score(**score_args) -> int` and `compute_performance_score_breakdown(**score_args) -> dict` where `score_args` keys are: `provisions_zero, provisions_pct, touched_zero, touched_pct, closed_zero, closed_pct, total_cost, closed_amount, provisions_raw, touched_raw, roi_zero, roi_pct` (the `first_provision` parameter is REMOVED — no age discount). Breakdown dict shape: `{"score": int, "factors": [{"factor","points","max","level","reason"}], "summary": str}` — **no `age_discount` key**. Levels are `"none" | "low" | "moderate" | "strong"`.
- `compute_sales_impact()` is unchanged.

- [ ] **Step 1: Rewrite the scoring tests as failing tests**

In `src/api/tests/test_reporting.py`, replace the retirement-scoring test classes. Update imports at top of file from `compute_retirement_score, compute_retirement_score_breakdown` to `compute_performance_score, compute_performance_score_breakdown`. Replace `TestComputeRetirementScore` (and the age-discount test) with:

```python
class TestComputePerformanceScore:
    def test_zero_activity_scores_zero(self):
        score = compute_performance_score(
            provisions_zero=True, provisions_pct=0,
            touched_zero=True, touched_pct=0,
            closed_zero=True, closed_pct=0,
            total_cost=0, closed_amount=0,
        )
        assert score == 0

    def test_top_performer_scores_high(self):
        score = compute_performance_score(
            provisions_zero=False, provisions_pct=90, provisions_raw=612,
            touched_zero=False, touched_pct=90, touched_raw=3_800_000,
            closed_zero=False, closed_pct=90,
            total_cost=50_000, closed_amount=4_200_000,
            roi_zero=False, roi_pct=90,
        )
        # 25 (usage) + 15 (pipeline) + 25 (closed) + round(15*0.90)=14 → 79
        assert score >= 75

    def test_high_cost_zero_sales_gets_zero_roi_points(self):
        breakdown = compute_performance_score_breakdown(
            provisions_zero=False, provisions_pct=80, provisions_raw=100,
            touched_zero=True, touched_pct=0,
            closed_zero=True, closed_pct=0,
            total_cost=50_000, closed_amount=0,
            roi_zero=True, roi_pct=0,
        )
        roi = next(f for f in breakdown["factors"] if f["factor"] == "roi")
        assert roi["points"] == 0
        assert roi["level"] == "none"

    def test_median_item_moderate_score(self):
        score = compute_performance_score(
            provisions_zero=False, provisions_pct=45, provisions_raw=28,
            touched_zero=False, touched_pct=45, touched_raw=120_000,
            closed_zero=False, closed_pct=45,
            total_cost=8_000, closed_amount=90_000,
            roi_zero=False, roi_pct=45,
        )
        # 15 + 5 + 10 + round(15*0.45)=7 → 37: moderate band
        assert 35 <= score < 55

    def test_no_age_discount_parameter(self):
        import inspect
        from rcars.services.reporting_sync import _compute_performance_score_with_breakdown
        params = inspect.signature(_compute_performance_score_with_breakdown).parameters
        assert "first_provision" not in params

    def test_breakdown_has_no_age_discount_key(self):
        breakdown = compute_performance_score_breakdown(
            provisions_zero=True, provisions_pct=0,
            touched_zero=True, touched_pct=0,
            closed_zero=True, closed_pct=0,
            total_cost=0, closed_amount=0,
        )
        assert "age_discount" not in breakdown
        assert breakdown["score"] == 0
```

In the windowed-metrics tests further down (`test_zero_item_gets_max_retirement_score` around line 181), invert the assertion: rename to `test_zero_item_gets_min_performance_score` and assert `performance_score == 0` for an all-zero item; in `test_percentile_ranking_varies_across_items` assert the high-activity item scores HIGHER than the low-activity item (flip any existing comparison). Also update `test_basic_structure` (line 149) if it asserts `age_discount` in `score_breakdown` — remove that assertion.

- [ ] **Step 2: Run tests, verify they fail**

Run: `cd src/api && python -m pytest tests/test_reporting.py -v -m "not integration"`
Expected: FAIL with `ImportError: cannot import name 'compute_performance_score'`

- [ ] **Step 3: Rewrite the scorer in `reporting_sync.py`**

Replace `compute_retirement_score`, `compute_retirement_score_breakdown`, and `_compute_retirement_score_with_breakdown` (lines 42–273) with the inverted versions. Public wrappers keep the same delegation shape, renamed, without `first_provision`:

```python
def compute_performance_score(
    provisions_zero: bool, provisions_pct: float,
    touched_zero: bool, touched_pct: float,
    closed_zero: bool, closed_pct: float,
    total_cost: float, closed_amount: float,
    **kwargs,
) -> int:
    """Compute performance score 0-100 using percentile ranks.

    Higher = stronger performer. Percentile args are 0-100 ranks among
    non-zero peers only; the _zero flags handle the zero case separately.
    Max achievable ~80.
    """
    _, score = _compute_performance_score_with_breakdown(
        provisions_zero, provisions_pct, touched_zero, touched_pct,
        closed_zero, closed_pct, total_cost, closed_amount, **kwargs,
    )
    return score


def compute_performance_score_breakdown(
    provisions_zero: bool, provisions_pct: float,
    touched_zero: bool, touched_pct: float,
    closed_zero: bool, closed_pct: float,
    total_cost: float, closed_amount: float,
    **kwargs,
) -> dict:
    """Return the full score breakdown dict (factors + explanation)."""
    breakdown, _ = _compute_performance_score_with_breakdown(
        provisions_zero, provisions_pct, touched_zero, touched_pct,
        closed_zero, closed_pct, total_cost, closed_amount, **kwargs,
    )
    return breakdown
```

Internal function — keep `_fmt_dollars` and `_pct_label` helpers as-is, invert every factor (point values mirror the old ones: `new = max - old`):

```python
def _compute_performance_score_with_breakdown(
    provisions_zero: bool, provisions_pct: float,
    touched_zero: bool, touched_pct: float,
    closed_zero: bool, closed_pct: float,
    total_cost: float, closed_amount: float,
    provisions_raw: int = 0, touched_raw: float = 0,
    roi_zero: bool = False, roi_pct: float = 0,
) -> tuple[dict, int]:
    """Internal: compute score and return (breakdown_dict, final_score)."""
    score = 0
    factors = []

    # ... _fmt_dollars / _pct_label unchanged ...

    # --- Provisions (max 25) ---
    if provisions_zero:
        pts, level = 0, "none"
        reason = "Zero provisions in this window — no usage"
    elif provisions_pct < 10:
        pts, level = 3, "low"
        reason = f"{provisions_raw} provisions — bottom 10% ({_pct_label(provisions_pct)})"
    elif provisions_pct < 25:
        pts, level = 7, "low"
        reason = f"{provisions_raw} provisions — bottom 25% ({_pct_label(provisions_pct)})"
    elif provisions_pct < 50:
        pts, level = 15, "moderate"
        reason = f"{provisions_raw} provisions — below median ({_pct_label(provisions_pct)})"
    elif provisions_pct < 75:
        pts, level = 22, "strong"
        reason = f"{provisions_raw} provisions — above median ({_pct_label(provisions_pct)})"
    else:
        pts, level = 25, "strong"
        reason = f"{provisions_raw} provisions — top 25% ({_pct_label(provisions_pct)})"
    score += pts
    factors.append({"factor": "usage", "points": pts, "max": 25, "level": level, "reason": reason})

    # --- Pipeline Touched (max 15) ---
    if touched_zero:
        pts, level = 0, "none"
        reason = "$0 pipeline influenced — no linked opportunities"
    elif touched_pct < 50:
        pts, level = 5, "moderate"
        reason = f"{_fmt_dollars(touched_raw)} pipeline — below median ({_pct_label(touched_pct)})"
    elif touched_pct < 75:
        pts, level = 11, "strong"
        reason = f"{_fmt_dollars(touched_raw)} pipeline — above median ({_pct_label(touched_pct)})"
    else:
        pts, level = 15, "strong"
        reason = f"{_fmt_dollars(touched_raw)} pipeline — top 25% ({_pct_label(touched_pct)})"
    score += pts
    factors.append({"factor": "pipeline", "points": pts, "max": 15, "level": level, "reason": reason})

    # --- Closed Sales (max 25) ---
    if closed_zero:
        pts, level = 0, "none"
        reason = "$0 closed — no deals won from demos of this item"
    elif closed_pct < 50:
        pts, level = 10, "moderate"
        reason = f"{_fmt_dollars(closed_amount)} closed — below median ({_pct_label(closed_pct)})"
    elif closed_pct < 75:
        pts, level = 20, "strong"
        reason = f"{_fmt_dollars(closed_amount)} closed — above median ({_pct_label(closed_pct)})"
    else:
        pts, level = 25, "strong"
        reason = f"{_fmt_dollars(closed_amount)} closed — top 25% ({_pct_label(closed_pct)})"
    score += pts
    factors.append({"factor": "sales", "points": pts, "max": 25, "level": level, "reason": reason})

    # --- Cost Efficiency (max 15) — continuous percentile-scaled ---
    roi_val = (closed_amount / total_cost) if total_cost > 0 and closed_amount > 0 else 0
    roi_label = f"{roi_val:.1f}x return ({_fmt_dollars(closed_amount)} closed / {_fmt_dollars(total_cost)} cost)"
    if roi_zero:
        pts, level = 0, "none"
        reason = f"{_fmt_dollars(total_cost)} spent with $0 closed — no return on investment"
    elif total_cost == 0:
        pts, level = 0, "none"
        reason = "No cost data"
    else:
        pts = round(15 * roi_pct / 100)
        if roi_pct < 25:
            level, band = "low", f"bottom 25% ({_pct_label(roi_pct)})"
        elif roi_pct < 50:
            level, band = "moderate", f"below median ({_pct_label(roi_pct)})"
        else:
            level, band = "strong", (f"above median ({_pct_label(roi_pct)})" if roi_pct < 75
                                     else f"top 25% ({_pct_label(roi_pct)})")
        reason = f"{roi_label} — {band}"
    score += pts
    factors.append({"factor": "roi", "points": pts, "max": 15, "level": level, "reason": reason})

    final = min(score, 100)

    # Summary sentence — lead with strengths, note weaknesses
    good_names = {"usage": "strong usage", "pipeline": "strong pipeline", "sales": "strong sales", "roi": "good ROI"}
    mid_names = {"usage": "moderate usage", "pipeline": "moderate pipeline", "sales": "moderate sales", "roi": "moderate ROI"}
    concern_names = {"usage": "no usage", "pipeline": "no pipeline", "sales": "no sales", "roi": "poor ROI"}

    strong_factors = [f for f in factors if f["level"] == "strong"]
    mid_factors = [f for f in factors if f["level"] == "moderate"]
    weak_factors = [f for f in factors if f["level"] in ("low", "none")]

    parts = []
    if strong_factors:
        parts.append(", ".join(good_names.get(f["factor"], f["factor"]) for f in strong_factors))
    if mid_factors and not strong_factors:
        parts.append(", ".join(mid_names.get(f["factor"], f["factor"]) for f in mid_factors))
    if weak_factors:
        label = ", ".join(concern_names.get(f["factor"], f["factor"]) for f in weak_factors)
        parts.append(f"held back by {label}" if strong_factors or mid_factors else label)

    summary = ". ".join(p.capitalize() if i == 0 else p for i, p in enumerate(parts)) if parts else "Neutral across all factors"
    summary += "."

    breakdown = {"score": final, "factors": factors, "summary": summary}
    return breakdown, final
```

Update the two call sites: in `_recompute_windowed_scores` (line 537-553) and `_build_windowed_metrics` (line 642-658), remove `first_provision=...` from `score_args` and rename the called functions. In `run_reporting_sync` (line 830), rename the call and remove `first_provision=row["first_provision"] or ""`. The `first_provisions` dict plumbing into `_build_windowed_metrics` can be deleted (remove the parameter from its signature at line 583-591 and the argument at line 739-742) — first/last provision dates still flow through `merged_rows` untouched. Update the docstrings mentioning "retirement_score" to "performance_score".

- [ ] **Step 4: Run tests, verify pass**

Run: `cd src/api && python -m pytest tests/test_reporting.py -v -m "not integration"`
Expected: PASS

- [ ] **Step 5: Check nothing else imports the old names**

Run: `grep -rn "compute_retirement_score" src/ --include="*.py"`
Expected: no matches except possibly `analysis.py` (fixed in Task 4). If `analysis.py:138` shows `from rcars.services.reporting_sync import compute_sales_impact` only, that's fine.

- [ ] **Step 6: Commit**

```bash
git add src/api/rcars/services/reporting_sync.py src/api/tests/test_reporting.py
git commit -m "[RHDPCD-662] Invert scoring: higher performance score = better, drop age discount"
```

---

### Task 2: Rename sync-status buckets and update CLI wording

**Files:**
- Modify: `src/api/rcars/db/database.py:2379-2396` (`get_reporting_sync_status`)
- Modify: `src/api/rcars/cli.py:690-705` (`reporting_db_status`)

**Interfaces:**
- Produces: `get_reporting_sync_status()` returns keys `total, with_provisions, with_cost, with_sales, strong, moderate, low, last_synced` (renamed from `high/review/keepers`). The dashboard route passes this dict through as `summary`; Task 12's frontend reads `last_synced` only, so the rename is safe.

- [ ] **Step 1: Rename the SQL aliases**

In `get_reporting_sync_status`, change:
```sql
COUNT(*) FILTER (WHERE ps.performance_score >= 55) AS strong,
COUNT(*) FILTER (WHERE ps.performance_score >= 35 AND ps.performance_score < 55) AS moderate,
COUNT(*) FILTER (WHERE ps.performance_score < 35) AS low,
```

- [ ] **Step 2: Update CLI output**

In `reporting_db_status` (cli.py:701-704), replace the three lines:
```python
    _print(f"  Strong (>=55):    {status['strong']}")
    _print(f"  Moderate (35-54): {status['moderate']}")
    _print(f"  Low (<35):        {status['low']}")
```

- [ ] **Step 3: Verify no other consumers of the old keys**

Run: `grep -rn "'high'\]\|\"high\"\]\|\['review'\]\|\['keepers'\]" src/api/rcars src/frontend/src | grep -v test`
Expected: no remaining references to `high`/`review`/`keepers` from `get_reporting_sync_status` consumers (check `src/api/rcars/api/routes/admin.py` reporting-status endpoint — if it names these keys, rename there and in the `api.ts` `getReportingStatus` type; if it only passes `total/with_provisions/with_cost/with_sales/last_synced`, no change).

- [ ] **Step 4: Run test suite slice + commit**

Run: `cd src/api && python -m pytest tests/test_db.py tests/test_reporting.py -v -m "not integration"`
Expected: PASS

```bash
git add src/api/rcars/db/database.py src/api/rcars/cli.py
git commit -m "[RHDPCD-662] Rename score buckets to strong/moderate/low in sync status and CLI"
```

---

### Task 3: `performance_public` setting, access dependency, and `/auth/me` flag

**Files:**
- Modify: `src/api/rcars/config.py` (Auth/roles section, ~line 82; chat section ~line 56)
- Modify: `src/api/rcars/api/middleware/auth.py` (after `require_curator`, ~line 210)
- Modify: `src/api/rcars/api/routes/auth.py:52-60` (`auth_me`)
- Modify: `src/api/rcars/api/schemas.py` (`AuthMeResponse`)
- Test: `src/api/tests/test_auth_routes.py`, `src/api/tests/test_auth_middleware.py`

**Interfaces:**
- Produces: `Settings.performance_public: bool` (env `RCARS_PERFORMANCE_PUBLIC`, default `True`). `require_performance_view(request) -> str` FastAPI dependency in `middleware/auth.py`. `/auth/me` response gains `"performance_public": bool`.
- Changes: `chat_intent_roles_str` default from `"performance:curator"` to `""` (performance chat intent open to all users, matching the page; deployments that set `RCARS_PERFORMANCE_PUBLIC=false` should also set `RCARS_CHAT_INTENT_ROLES=performance:curator` — documented in Task 14).

- [ ] **Step 1: Write failing tests**

In `src/api/tests/test_auth_routes.py` add (follow the file's existing client/fixture pattern for authenticated requests):

```python
def test_auth_me_includes_performance_public(client_as_user):
    resp = client_as_user.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["performance_public"] is True
```

In `src/api/tests/test_auth_middleware.py` add tests for the new dependency (mirror the structure of existing `require_curator` tests in that file):

```python
def test_performance_view_allows_regular_user_when_public(...):
    # settings.performance_public = True (default) → plain authenticated user passes

def test_performance_view_blocks_regular_user_when_private(...):
    # settings with performance_public=False → non-curator gets 403

def test_performance_view_allows_curator_when_private(...):
    # settings with performance_public=False → curator email passes
```

- [ ] **Step 2: Run, verify fail**

Run: `cd src/api && python -m pytest tests/test_auth_routes.py tests/test_auth_middleware.py -v -m "not integration"`
Expected: new tests FAIL (missing field / missing function).

- [ ] **Step 3: Implement**

`config.py` — in the "Auth / roles" block add `performance_public: bool = True`; change `chat_intent_roles_str: str = "performance:curator"` to `chat_intent_roles_str: str = ""`.

`middleware/auth.py` — after `require_curator`:

```python
async def require_performance_view(request: Request) -> str:
    """Any authenticated user when performance_public; curator/admin otherwise."""
    user = await require_auth(request)
    settings: Settings = request.app.state.settings
    if settings.performance_public:
        return user
    _check_api_key_role_ceiling(request, "curator")
    if not settings.is_curator(user) and not settings.is_admin(user):
        raise HTTPException(status_code=403, detail="Curator role required")
    return user
```

`routes/auth.py` `auth_me` — add `"performance_public": settings.performance_public` to the returned dict. `schemas.py` `AuthMeResponse` — add `performance_public: bool = True`.

Also check `src/api/tests/test_config.py` — if it asserts the old `chat_intent_roles_str` default, update it to `""`.

- [ ] **Step 4: Run, verify pass, commit**

Run: `cd src/api && python -m pytest tests/test_auth_routes.py tests/test_auth_middleware.py tests/test_config.py -v -m "not integration"`
Expected: PASS

```bash
git add src/api/rcars/config.py src/api/rcars/api/middleware/auth.py src/api/rcars/api/routes/auth.py src/api/rcars/api/schemas.py src/api/tests/
git commit -m "[RHDPCD-662] Add RCARS_PERFORMANCE_PUBLIC gate and expose it via /auth/me"
```

---

### Task 4: DB layer — channel parameter and channel availability

**Files:**
- Modify: `src/api/rcars/db/database.py:2217-2310` (`list_performance_data`), add one method after `get_performance_channels` (~line 2090)
- Test: `src/api/tests/test_db.py`

**Interfaces:**
- Produces: `list_performance_data(..., channel: str = "rhdp")` — the `performance_channels` join uses the given source channel; each row gains `channels_present: list[str]` (all channels with data for that item). New method `get_channel_metrics_map(content_ids: list[str], channel: str) -> dict[str, dict]` returning `{content_id: channel_row}` for the marketing addendum.

- [ ] **Step 1: Write failing tests**

In `src/api/tests/test_db.py`, following that file's existing fixture pattern for seeding `content_entities`/`performance_channels`/`performance_scores`:

```python
def test_list_performance_data_includes_channels_present(db_with_perf_data):
    rows = db_with_perf_data.list_performance_data()
    assert rows, "seeded item expected"
    assert "channels_present" in rows[0]
    assert "rhdp" in rows[0]["channels_present"]

def test_get_channel_metrics_map_empty_for_missing_channel(db_with_perf_data):
    ids = [r["content_id"] for r in db_with_perf_data.list_performance_data()]
    result = db_with_perf_data.get_channel_metrics_map(ids, "interactive_labs")
    assert result == {}
```

- [ ] **Step 2: Run, verify fail**

Run: `cd src/api && python -m pytest tests/test_db.py -v -m "not integration" -k "channels_present or channel_metrics"`
Expected: FAIL

- [ ] **Step 3: Implement**

In `list_performance_data`: add `channel: str = "rhdp"` parameter; change the join line to `LEFT JOIN performance_channels pc ON pc.content_id = ps.content_id AND pc.channel = %(channel)s` and add `params["channel"] = channel`. Add to the SELECT list:

```sql
(SELECT COALESCE(array_agg(DISTINCT pc2.channel), '{}')
   FROM performance_channels pc2
  WHERE pc2.content_id = ps.content_id) AS channels_present,
```

New method:

```python
def get_channel_metrics_map(self, content_ids: list[str], channel: str) -> dict[str, dict]:
    """Return {content_id: performance_channels row} for one channel."""
    if not content_ids:
        return {}
    sql = """
        SELECT * FROM performance_channels
        WHERE channel = %s AND content_id = ANY(%s)
    """
    with self._pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (channel, content_ids))
            return {r["content_id"]: r for r in cur.fetchall()}
```

- [ ] **Step 4: Run, verify pass, commit**

Run: `cd src/api && python -m pytest tests/test_db.py -v -m "not integration"`
Expected: PASS

```bash
git add src/api/rcars/db/database.py src/api/tests/test_db.py
git commit -m "[RHDPCD-662] Parameterize performance channel and expose channel availability"
```

---

### Task 5: Rename API endpoints and add `window`/`channel` params

**Files:**
- Modify: `src/api/rcars/api/routes/analysis.py` (all `/retirement*` routes)
- Modify: `src/api/rcars/api/schemas.py:190-196` (`RetirementDashboardResponse`)
- Test: `src/api/tests/test_retirement_workflow.py` (rename to `test_performance_workflow.py` if it references routes; per grep it tests DB methods only — verify), `src/api/tests/test_app.py` (route listing, if any)

**Interfaces:**
- Produces (consumed by Task 8's `api.ts`):
  - `GET /api/v1/analysis/performance?sort_by&sort_dir&min_score&category&has_prod&search&window&channel&workflow_status` — dep `require_performance_view`. `window` in `{3m,6m,9m,12m}` default `12m` (400 otherwise); `channel` in `{sales,marketing}` default `sales` (400 otherwise). Response model `PerformanceDashboardResponse {items, total, synced_at, summary, window, channel}`.
  - Item fields (canonical, no legacy aliases): `content_id, catalog_base_name, display_name, ci_name, category, performance_score, score_breakdown, channel_scores, channels_present, marketing (dict|None), provisions, completions, unique_users, requests, success_ratio, failure_ratio, pipeline_touched, closed_amount, total_cost, avg_cost_per_provision, first_activity, last_activity, stages, owners, has_content, catalog_url?, workflow_status, jira_key, retirement_target_date, ignored_until, sales_impact`.
  - Workflow: `GET/PUT/DELETE /analysis/performance/workflow/{base_name}[/review|/approve|/notify|/start|/link-jira|/notes]`, `PUT/DELETE /analysis/performance/ignore/{base_name}` — same bodies/roles as before.
  - `sort_by` accepts `performance_score` (default), `provisions`, `total_cost`, `closed_amount`, `pipeline_touched`, `display_name`, `touched_roi`, `closed_roi`; default `sort_dir` is `desc`.

- [ ] **Step 1: Update route paths and dashboard handler**

In `analysis.py`:
1. Delete `WINDOW_KEYS` (line 22). Add:
```python
WINDOWS = {"3m", "6m", "9m", "12m"}
CHANNEL_SOURCES = {"sales": "rhdp", "marketing": "interactive_labs"}
```
2. Import `require_performance_view` from middleware.
3. Rename `@router.get("/retirement", ...)` to `@router.get("/performance", tags=["Performance"], summary="Performance dashboard", ...)`, response model `PerformanceDashboardResponse`. New signature:
```python
async def performance_dashboard(
    request: Request,
    user: str = Depends(require_performance_view),
    sort_by: str = Query("performance_score"),
    sort_dir: str = Query("desc"),
    min_score: int | None = Query(None),
    category: str | None = Query(None),
    has_prod: bool | None = Query(None),
    search: str | None = Query(None),
    window: str = Query("12m"),
    channel: str = Query("sales"),
    workflow_status: str | None = Query(None),
):
    if window not in WINDOWS:
        raise HTTPException(400, f"window must be one of {sorted(WINDOWS)}")
    if channel not in CHANNEL_SOURCES:
        raise HTTPException(400, f"channel must be one of {sorted(CHANNEL_SOURCES)}")
    source = CHANNEL_SOURCES[channel]
```
4. Call `db.list_performance_data(..., channel=source)` — delete the `sort_map` (line 92-93); pass `sort_by` straight through (DB validates the allowlist).
5. In the per-item loop: keep `catalog_base_name` derivation; DELETE the alias lines (`touched_amount`, `experiences`, `retirement_score` at 108-110). Windowed overlay: `w = wm.get(window, {})` and set canonical names only — `provisions, completions, requests, unique_users, success_ratio, failure_ratio, pipeline_touched (from w["pipeline_touched"]), closed_amount, total_cost, avg_cost_per_provision, performance_score, sales_impact`. When `channel != "sales"`, override `item["performance_score"]` from `(item.get("channel_scores") or {}).get(source, {}).get("score", 0)`.
6. Score breakdown pop (line 166-170): unchanged logic but `w = wm.get(window, {})`.
7. Re-sort block (line 151-161): replace `retirement_score`→`performance_score`, `touched_amount`→`pipeline_touched` in `allowed_sorts` and the ROI lambdas.
8. Marketing addendum data: after items are built, when `channel == "sales"`:
```python
    marketing_ids = [i["content_id"] for i in items
                     if "interactive_labs" in (i.get("channels_present") or [])]
    marketing_map = db.get_channel_metrics_map(marketing_ids, "interactive_labs")
    for item in items:
        mrow = marketing_map.get(item["content_id"])
        item["marketing"] = None
        if mrow:
            item["marketing"] = {
                "provisions": mrow.get("provisions", 0),
                "unique_users": mrow.get("unique_users", 0),
                "completions": mrow.get("completions", 0),
                "page_views": mrow.get("page_views", 0),
                "score": (item.get("channel_scores") or {}).get("interactive_labs", {}).get("score"),
            }
```
(When `channel == "marketing"`, mirror with `rhdp` under key `"sales"` — same shape plus `pipeline_touched/closed_amount/total_cost`.)
9. Return dict gains `"channel": channel`.
10. Rename every other route path: `/retirement/workflow/...` → `/performance/workflow/...`, `/retirement/ignore/...` → `/performance/ignore/...`. Tags `["Retirement"]` → `["Performance"]`. Handler names/log actions stay (workflow is still retirement).

- [ ] **Step 2: Channel-keyed approval snapshot**

In `approve_item` (line 237-277), replace the flat snapshot build with:

```python
    perf_score = db.get_performance_score(content_id)
    perf_channels = db.get_performance_channels(content_id) or []
    channel_scores = (perf_score or {}).get("channel_scores") or {}
    snapshot: dict = {"snapshot_at": datetime.now().isoformat()}
    for ch in perf_channels:
        key = "sales" if ch.get("channel") == "rhdp" else "marketing"
        snapshot[key] = {
            "score": ((perf_score or {}).get("performance_score", 0) if key == "sales"
                      else (channel_scores.get(ch.get("channel"), {}) or {}).get("score")),
            "provisions": ch.get("provisions", 0),
            "unique_users": ch.get("unique_users", 0),
            "completions": ch.get("completions", 0),
            "pipeline_touched": float(ch.get("pipeline_touched") or 0),
            "closed_amount": float(ch.get("closed_amount") or 0),
            "total_cost": float(ch.get("total_cost") or 0),
            "page_views": ch.get("page_views", 0),
        }
```

- [ ] **Step 3: Rename the schema**

In `schemas.py`, rename `RetirementDashboardResponse` → `PerformanceDashboardResponse`, description "Performance-scored catalog items with reporting metrics", add `channel: str`. Update the import in `analysis.py`.

- [ ] **Step 4: Run the API test suite**

Run: `cd src/api && python -m pytest tests/ -v -m "not integration"`
Expected: PASS. If `test_app.py` or `test_retirement_workflow.py` reference `/analysis/retirement` paths or `RetirementDashboardResponse`, update those references (the workflow DB tests need no changes).

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/api/routes/analysis.py src/api/rcars/api/schemas.py src/api/tests/
git commit -m "[RHDPCD-662] Rename /analysis/retirement to /analysis/performance with window+channel params"
```

---

### Task 6: Remove `retirement_flavored` from chat

**Files:**
- Modify: `src/api/rcars/services/chat/models.py:64-67` (`PerformanceArgs`)
- Modify: `src/api/rcars/services/chat/handlers.py:126-165` (`handle_performance`)
- Modify: `src/api/rcars/services/chat/registry.py:72-76` (performance prompt fragment)
- Test: `src/api/tests/test_chat_handlers.py`, `src/api/tests/test_chat_models.py`, `src/api/tests/test_chat_routing_golden.py`

**Interfaces:**
- Produces: `performance_table` block data is `{"window": str, "rows": [...]}` — no `retirement_flavored` key; every row always has `score` populated (consumed by Task 9's `PerformanceTableBlock`).

- [ ] **Step 1: Update code**

`models.py`: delete `retirement_flavored: bool = False` from `PerformanceArgs`.

`handlers.py` `handle_performance`: change `scores = get_performance_scores(db.pool, ids) if args.retirement_flavored else {}` to `scores = get_performance_scores(db.pool, ids)`; remove `"retirement_flavored": args.retirement_flavored` from the Block data.

`registry.py` line ~73: rewrite the prompt fragment sentence that mentions `retirement_flavored` — remove the instruction entirely (e.g. keep "performance: usage/provisions/cost/sales questions. Set window from any time expression.").

- [ ] **Step 2: Fix tests referencing the flag**

Run: `grep -rn "retirement_flavored" src/api/tests/` and remove/adjust each occurrence (routing golden expectations, handler assertions). Where a handler test asserted `score is None` for non-flavored calls, assert the score is now populated.

- [ ] **Step 3: Run chat tests, verify pass**

Run: `cd src/api && python -m pytest tests/test_chat_models.py tests/test_chat_handlers.py tests/test_chat_registry.py tests/test_chat_routing_golden.py -v -m "not integration"`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/api/rcars/services/chat/ src/api/tests/
git commit -m "[RHDPCD-662] Chat performance blocks always include scores; drop retirement_flavored"
```

---

### Task 7: Ansible — wire `RCARS_PERFORMANCE_PUBLIC`

**Files:**
- Modify: `ansible/templates/manifests-app.yaml.j2` (API deployment env AND recommend-worker deployment env — chat role gating runs in the recommend worker)
- Modify: `ansible/vars/common.yml`

- [ ] **Step 1: Add the var and env entries**

In `ansible/vars/common.yml` add:
```yaml
# Performance page visible to all authenticated users (false = curator-only)
performance_public: true
```

In `manifests-app.yaml.j2`, locate the env lists for the **api** Deployment and the **recommend-worker** Deployment (pattern-match how existing settings like `RCARS_CURATOR_EMAILS` are templated) and add to both:
```yaml
            - name: RCARS_PERFORMANCE_PUBLIC
              value: "{{ performance_public | default(true) | lower }}"
```

- [ ] **Step 2: Syntax check + commit**

Run: `ansible-playbook ansible/deploy.yml -e env=dev --tags apply-config --syntax-check`
Expected: `playbook: ansible/deploy.yml` (no errors)

```bash
git add ansible/templates/manifests-app.yaml.j2 ansible/vars/common.yml
git commit -m "[RHDPCD-662] Deploy RCARS_PERFORMANCE_PUBLIC to api and recommend-worker"
```

---

### Task 8: Frontend API client — rename methods, new types

**Files:**
- Modify: `src/frontend/src/services/api.ts:234-291` (retirement methods) and `:310-390` (types)

**Interfaces:**
- Produces (consumed by Tasks 11–12):
  - `api.getPerformanceDashboard(params?: { sort_by?, sort_dir?, min_score?, search?, window?, channel?, workflow_status? })` → `PerformanceDashboardResponse`
  - Workflow methods renamed: `getRetirementWorkflow→getWorkflow`? **No** — keep retirement names for workflow actions (the workflow IS retirement): `getRetirementWorkflow, reviewRetirementItem, approveRetirementItem, notifyRetirementOwner, startRetirement, updateRetirementNotes, linkRetirementJira, cancelRetirementWorkflow, ignoreItem (renamed from ignoreRetirementItem), unignoreItem` — all pointing at `/analysis/performance/...` paths.
  - Types: `PerformanceItem` (replaces `ReportingMetricsItem`), `PerformanceDashboardResponse`, `ScoreBreakdown` without `age_discount`, `MarketingMetrics { provisions; unique_users; completions; page_views; score: number | null }`, `RetirementWorkflow` unchanged.
  - `getMe` return type gains `performance_public: boolean`.

- [ ] **Step 1: Rewrite the retirement section of api.ts**

```typescript
  // Performance analysis
  getPerformanceDashboard: (params?: {
    sort_by?: string; sort_dir?: string; min_score?: number;
    search?: string; window?: string; channel?: string; workflow_status?: string;
  }) => {
    const qs = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qs.set(k, String(v))
      })
    }
    const query = qs.toString()
    return request<PerformanceDashboardResponse>(`/analysis/performance${query ? '?' + query : ''}`)
  },
```

Change every `/analysis/retirement/workflow/` path to `/analysis/performance/workflow/` and `/analysis/retirement/ignore/` to `/analysis/performance/ignore/` (method names: rename only `ignoreRetirementItem`→`ignoreItem`, `unignoreRetirementItem`→`unignoreItem`). Update `getMe` to `request<{ email: string; roles: string[]; performance_public: boolean }>('/auth/me')`.

Replace the `ReportingMetricsItem` interface with:

```typescript
export interface MarketingMetrics {
  provisions: number
  unique_users: number
  completions: number
  page_views: number
  score: number | null
}

export interface PerformanceItem {
  content_id: string
  catalog_base_name: string
  display_name: string
  ci_name?: string | null
  category: string | null
  performance_score: number
  score_breakdown?: ScoreBreakdown | null
  channel_scores?: Record<string, { score?: number }> | null
  channels_present: string[]
  marketing: MarketingMetrics | null
  provisions: number
  completions: number
  requests: number
  unique_users: number
  success_ratio: number
  failure_ratio: number
  pipeline_touched: number
  closed_amount: number
  total_cost: number
  avg_cost_per_provision: number
  first_activity: string | null
  last_activity: string | null
  sales_impact: string | null
  stages: Array<{ stage: string; ci_name: string; catalog_url: string }>
  owners: Array<{ name: string; email: string }>
  has_content: boolean
  catalog_url?: string
  workflow_status?: string | null
  jira_key?: string | null
  retirement_target_date?: string | null
  ignored_until?: string | null
}

export interface PerformanceDashboardResponse {
  items: PerformanceItem[]
  total: number
  synced_at: string | null
  summary: { total: number; last_synced: string | null } | null
  window: string
  channel: string
}
```

Remove `age_discount` from `ScoreBreakdown`. Delete the now-unused `ReportingMetricsItem` and `RetirementDashboardResponse`.

- [ ] **Step 2: Type-check (expect downstream errors only in RetirementPage.tsx)**

Run: `cd src/frontend && npx tsc --noEmit 2>&1 | grep -v "RetirementPage" | head -20`
Expected: no errors outside `RetirementPage.tsx` (that file is deleted in Task 13; it may be temporarily broken — that's acceptable mid-branch but do NOT commit a broken build: do Steps here and Task 9-13 before the final frontend commit if needed, OR delete `RetirementPage.tsx`'s route usage in the same commit). Preferred: proceed to Task 9-13 and make the first frontend commit once `npx tsc --noEmit` is clean.

---

### Task 9: PerformanceTableBlock — inverted colors, new link, no flag

**Files:**
- Modify: `src/frontend/src/components/advisor/blocks/PerformanceTableBlock.tsx`
- Test: `src/frontend/src/components/advisor/blocks/registry.test.ts` (update only if it asserts `retirement_flavored`)

- [ ] **Step 1: Apply the changes**

1. Delete line 23 (`const retirementFlavored = ...`).
2. Invert score colors:
```typescript
  const scoreColor = (score: number) => {
    if (score >= 55) return 'var(--score-green)'
    if (score >= 35) return 'var(--score-amber)'
    return 'var(--score-red)'
  }
  const scoreBg = (score: number) => {
    if (score >= 55) return 'var(--score-green-bg)'
    if (score >= 35) return 'var(--score-amber-bg)'
    return 'var(--score-red-bg)'
  }
```
3. Score column always renders: remove both `{retirementFlavored && ...}` wrappers (keep the `<th>Score</th>` and the score `<td>` unconditionally).
4. Footer link:
```tsx
        <a
          href={rows.length === 1
            ? `/analysis/performance?search=${encodeURIComponent(rows[0].display_name)}`
            : '/analysis/performance'}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'var(--text-link)' }}
        >
          Open Performance Analysis
        </a>
```

- [ ] **Step 2: Run vitest**

Run: `cd src/frontend && npx vitest run`
Expected: PASS (fix `registry.test.ts` if it references `retirement_flavored`).

---

### Task 10: useAuth — `canViewPerformance`

**Files:**
- Modify: `src/frontend/src/hooks/useAuth.ts`

**Interfaces:**
- Produces: `AuthState.canViewPerformance: boolean` — true when `performance_public` from `/auth/me` OR user has curator role (consumed by Tasks 12–13).

- [ ] **Step 1: Implement**

Add `canViewPerformance: boolean` to `AuthState` (default `false` in `defaultState`). In `useAuthProvider`'s `.then`:
```typescript
        canViewPerformance: data.performance_public || data.roles.includes('curator'),
```

---

### Task 11: Performance components — popover and workflow drawer

**Files:**
- Create: `src/frontend/src/components/performance/ScoreBreakdownPopover.tsx`
- Create: `src/frontend/src/components/performance/WorkflowDrawer.tsx`

**Interfaces:**
- Produces:
  - `ScoreBreakdownPopover({ breakdown: ScoreBreakdown; onClose: () => void; anchorRect: DOMRect | null })` — same props as the old inline component.
  - `WorkflowDrawer({ item: PerformanceItem; onClose: () => void; onChanged: () => void })` — self-contained: loads the workflow itself via `api.getRetirementWorkflow`, owns all action state, calls `onChanged()` after any successful action so the page reloads data.
  - Shared score helpers exported from `ScoreBreakdownPopover.tsx`: `scoreColor(score)`, `scoreBg(score)` (inverted: ≥55 green, ≥35 amber, else red) and `fmt`, `num`, `fmtRoi` money helpers (moved from RetirementPage so both files use one copy).

- [ ] **Step 1: ScoreBreakdownPopover.tsx**

Port `ScoreBreakdownPopover` from `RetirementPage.tsx:229-283` verbatim with three changes:
1. New `levelColor` map (performance semantics):
```typescript
  const levelColor = (level: string) => {
    if (level === 'strong') return 'var(--score-green)'
    if (level === 'moderate') return 'var(--score-amber)'
    if (level === 'low') return 'var(--score-red)'
    return 'var(--score-red)'  // 'none'
  }
```
2. Delete the entire `age_discount` block (old lines 269-278) — the field no longer exists.
3. Export the helpers at the top of the file (moved from RetirementPage.tsx lines 19-36, with inverted score colors):
```typescript
export const fmt = (v: number | string) => { /* port RetirementPage.tsx:19-25 unchanged */ }
export const num = (v: unknown): number => typeof v === 'number' ? v : parseFloat(String(v)) || 0
export const fmtRoi = (amount: number | string, cost: number | string) => { /* port :29-33 unchanged */ }
export const scoreColor = (score: number) => score >= 55 ? 'var(--score-green)' : score >= 35 ? 'var(--score-amber)' : 'var(--score-red)'
export const scoreBg = (score: number) => score >= 55 ? 'var(--score-green-bg)' : score >= 35 ? 'var(--score-amber-bg)' : 'var(--score-red-bg)'
```
Reuse existing CSS classes (`ret-score-popover*`, `ret-score-backdrop`) — no CSS changes.

- [ ] **Step 2: WorkflowDrawer.tsx**

Port from `RetirementPage.tsx` the drawer JSX (lines 1190-1629) plus its supporting pieces: `StepperStep` (188-227), `ReplacementPicker` (79-186), `safeHref` (6-10), `stageBadgeClass` (38-40), the drawer state hooks (300-313 minus `drawerItem` which becomes the `item` prop), the handlers `handleApprove/handleNotify/handleStart/handleCancel/handleSaveNotes/handleLinkJira/generateEmailTemplate` (404-545, with `drawerItem` → `item`, `loadData()` → `onChanged()`), and the workflow-step booleans (650-658). Type changes:
- `ReportingMetricsItem` → `PerformanceItem`; field renames within the drawer: `retirement_score` → `performance_score`, `touched_amount` → `pipeline_touched`, `experiences` → `completions`, `first_provision` → `first_activity`, `last_provision` → `last_activity`.
- Drawer score cell uses `scoreColor(item.performance_score)` from the popover module (now green-when-high).
- Snapshot comparison table (old lines 1538-1589): the snapshot is now channel-keyed. Read `const snap = (wf.approval_snapshot?.sales ?? wf.approval_snapshot) as Record<string, number>` (legacy flat fallback), and update the row keys to the canonical names:
```typescript
  ([
    ['score', 'Score', item.performance_score],
    ['provisions', 'Provisions', item.provisions],
    ['unique_users', 'Users', item.unique_users],
    ['completions', 'Completions', item.completions],
    ['total_cost', 'Cost', item.total_cost],
    ['pipeline_touched', 'Touched', item.pipeline_touched],
    ['closed_amount', 'Closed', item.closed_amount],
  ] as [string, string, number][])
```
  For the delta color: score delta UP is now good (green) — invert the old special-case (`key === 'score' ? (delta > 0 ? '--up' : '--down') : (delta > 0 ? '--down' : '--up')` becomes: for `score`, delta > 0 → `--up`; for cost, delta > 0 → `--down`; for provisions/users/completions/touched/closed, delta > 0 → `--up`).
- Email template (old lines 514-545): change "Retirement Score: ${score}" to "Performance Score: ${item.performance_score}" and `fmt(item.pipeline_touched)`.
The component fetches its own workflow in a `useEffect` on mount (port `openDrawer` body, lines 404-422).

- [ ] **Step 3: Type-check**

Run: `cd src/frontend && npx tsc --noEmit 2>&1 | grep -v "RetirementPage\|PerformancePage" | head`
Expected: no errors in the two new files.

---

### Task 12: PerformancePage — Browse-style layout with URL state

**Files:**
- Create: `src/frontend/src/pages/PerformancePage.tsx`

**Interfaces:**
- Consumes: `api.getPerformanceDashboard`, `PerformanceItem`, `WorkflowDrawer`, `ScoreBreakdownPopover` + helpers, `useAuth().isCurator / canViewPerformance`, `api.ignoreItem / api.unignoreItem`.
- URL params (only non-defaults written, `setSearchParams(params, { replace: true })` — copy BrowsePage.tsx:462-474 pattern): `search` (''), `channel` ('sales'), `window` ('12m'), `performance` ('all' | 'strong' | 'moderate' | 'low'), `status` ('all' | 'none' | 'in_process' | 'started' | 'muted'), `namespace` (comma-sep), `provs_min/provs_max/touched_min/touched_max/closed_min/closed_max/cost_min/cost_max/users_min/users_max/exper_min/exper_max`, `sort` ('performance_score'), `order` ('desc').

- [ ] **Step 1: Build the page skeleton with data loading + URL sync**

Component outline (state initialization from `useSearchParams`, mirroring BrowsePage.tsx:361-391):

```tsx
export function PerformancePage() {
  const { isCurator } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  type TimeWindow = '3m' | '6m' | '9m' | '12m'
  type PerfFilter = 'all' | 'strong' | 'moderate' | 'low'
  type StatusFilter = 'all' | 'none' | 'in_process' | 'started' | 'muted'
  type SortField = 'performance_score' | 'provisions' | 'pipeline_touched' | 'touched_roi'
    | 'closed_amount' | 'closed_roi' | 'total_cost' | 'display_name'

  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [channel, setChannel] = useState(searchParams.get('channel') === 'marketing' ? 'marketing' : 'sales')
  const [window_, setWindow] = useState<TimeWindow>((searchParams.get('window') as TimeWindow) || '12m')
  const [perfFilter, setPerfFilter] = useState<PerfFilter>((searchParams.get('performance') as PerfFilter) || 'all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>((searchParams.get('status') as StatusFilter) || 'all')
  const [selectedNamespaces, setSelectedNamespaces] = useState<Set<string>>(
    new Set(searchParams.get('namespace')?.split(',').filter(Boolean) || []))
  const [sortBy, setSortBy] = useState<SortField>((searchParams.get('sort') as SortField) || 'performance_score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>(searchParams.get('order') === 'asc' ? 'asc' : 'desc')
  // range inputs: init each key from its URL param, e.g. searchParams.get('provs_min') || ''
  ...
}
```

Range keys map to URL names: `provMin→provs_min, provMax→provs_max, touchedMin→touched_min, touchedMax→touched_max, closedMin→closed_min, closedMax→closed_max, costMin→cost_min, costMax→cost_max, usersMin→users_min, usersMax→users_max, expMin→exper_min, expMax→exper_max`. Range inputs apply immediately on change (no separate Apply button — sidebar pattern), debounced 300ms like Browse search.

URL sync effect (write only non-defaults):

```tsx
  useEffect(() => {
    const params: Record<string, string> = {}
    if (search) params.search = search
    if (channel !== 'sales') params.channel = channel
    if (window_ !== '12m') params.window = window_
    if (perfFilter !== 'all') params.performance = perfFilter
    if (statusFilter !== 'all') params.status = statusFilter
    if (selectedNamespaces.size > 0) params.namespace = Array.from(selectedNamespaces).sort().join(',')
    if (sortBy !== 'performance_score') params.sort = sortBy
    if (sortDir !== 'desc') params.order = sortDir
    Object.entries(rangeUrlMap).forEach(([stateKey, urlKey]) => {
      if (appliedRanges[stateKey]) params[urlKey] = appliedRanges[stateKey]
    })
    setSearchParams(params, { replace: true })
  }, [search, channel, window_, perfFilter, statusFilter, selectedNamespaces, sortBy, sortDir, appliedRanges, setSearchParams])
```

Data loading (port RetirementPage.tsx:344-372 `loadData`, simplified — no tabs):
```tsx
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getPerformanceDashboard({
        sort_by: sortBy, sort_dir: sortDir,
        search: search || undefined,
        window: window_, channel,
        workflow_status: statusFilter !== 'all' && statusFilter !== 'muted' ? statusFilter : undefined,
      })
      setAllItems(data.items)
      setSyncedAt(data.synced_at)
    } finally { setLoading(false) }
  }, [sortBy, sortDir, search, window_, channel, statusFilter])
```
Performance-band filtering is client-side (like today's keepers/review logic): `strong: s >= 55`, `moderate: 35 <= s < 55`, `low: s < 35` on `performance_score`. Namespace extraction/counting, mute filtering, and range filtering: port RetirementPage.tsx:585-631 unchanged (rename `retirement_score`→`performance_score`, `touched_amount`→`pipeline_touched`, `experiences`→`completions`).

- [ ] **Step 2: Layout — sidebar + main**

Use Browse's structural classes: outer `<div className="browse-layout">`, left `<div className="browse-filter-sidebar">`, right main column. Header: `<h3>Performance</h3>` + `Synced {syncAge}` (port syncAge calc from RetirementPage.tsx:552-554).

Sidebar groups (each `browse-filter-group` with `browse-filter-group-label`):
1. **Performance** — pill buttons using `ret-filter-group` classes: All / Strong (green dot) / Moderate (amber dot) / Low (red dot), with counts computed from mute-and-namespace-filtered items.
2. **Metrics** — six min/max pairs (Provisions, Experiences, Unique Users, Touched ($), Closed ($), Cost ($)) using `browse-drawer-input` number inputs (port the grid rows from RetirementPage.tsx:780-802 into a vertical stack).
3. **Namespace** — checkbox list with counts, `maxHeight: 200px; overflowY: auto; paddingRight: 8px` (port RetirementPage.tsx:813-832).
4. **Retirement Status** — `{isCurator && (...)}` pill buttons All / No Action / In Process / Started / Muted (n) (port from :749-757).
A "Clear filters" link at the bottom resets everything to defaults.

Main column, top to bottom:
1. **Channel tabs** (`ca-tab-bar`): `Sales` active; `Marketing` rendered with `disabled` + `title="Marketing channel — Interactive Labs self-paced usage. Enabled when marketing data is synced."`; below the tabs a one-line muted hint: `Sales: RHDP provisioning tied to sales pipeline (source: rhdp). Marketing: self-paced web usage (source: Interactive Labs).` Time-window toggle on the same row, right-aligned: `(['3m','3 Mo'],['6m','6 Mo'],['9m','9 Mo'],['12m','1 Yr'])` (port :673-682).
2. **Stats cards** (`ca-stats-grid` + `ret-stat-card`): Total Items / Strong (≥55, green) / Moderate (35–54, amber) / Low (<35, red) / Total Cost / Total Closed.
3. **Search + count + CSV** row: `ca-search` input (debounced like Browse :487-494), `{visibleItems.length} of {n} items`, CSV button (port exportCsv from :556-583, header `Score` column value `performance_score`, filename `rcars-performance-...csv`).
4. **Table** (`ca-table`): columns Name / Score / Provisions / Touched / T-ROI / Closed / C-ROI / Cost / Data. Port the row rendering from :881-911 with renames; score badge uses inverted `scoreColor/scoreBg` and opens `ScoreBreakdownPopover` (click-to-toggle, port :896-903). **Data column**: `{item.channels_present.includes('rhdp') && <span className="ca-env-tag ca-env-prod" title="Sales data (RHDP)">S</span>}{item.channels_present.includes('interactive_labs') && <span className="ca-env-tag ca-env-dev" title="Marketing data (Interactive Labs)">M</span>}`.

- [ ] **Step 3: Expanded row**

Port :912-986 with renames, then add after the metrics grid:

**Marketing addendum** (only when `item.marketing`):
```tsx
{item.marketing && (
  <div style={{ gridColumn: '1 / -1', border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)', padding: '8px 12px', marginTop: '6px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
         onClick={e => { e.stopPropagation(); toggleAddendum(item.catalog_base_name) }}>
      <span className="ca-env-tag ca-env-dev">M</span>
      <span style={{ fontWeight: 600, fontSize: '12px' }}>Marketing Data</span>
      <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Interactive Labs</span>
      {item.marketing.score != null && (
        <span className="ca-score-badge" style={{ marginLeft: 'auto',
              background: scoreBg(item.marketing.score), color: scoreColor(item.marketing.score) }}>
          {item.marketing.score}
        </span>
      )}
    </div>
    {addendumOpen.has(item.catalog_base_name) && (
      <div className="ca-detail" style={{ marginTop: '6px' }}>
        {/* IL Provisions / Unique Users / Completions / Page Views as ca-detail-item cells */}
      </div>
    )}
  </div>
)}
```

**Workflow bar** (curator-only, replaces the old Mute/Workflow buttons block :968-982): `{isCurator && (...)}` wrapping the ported Mute 30d / Unmute buttons (handlers port from :324-342 using `api.ignoreItem`/`api.unignoreItem`) and a status line `Retirement Workflow: {item.workflow_status || 'No action'}` plus the "Retirement Workflow" button that sets `drawerItem`.

Drawer mount at the end: `{drawerItem && <WorkflowDrawer item={drawerItem} onClose={() => setDrawerItem(null)} onChanged={loadData} />}`.

- [ ] **Step 4: Verify build**

Run: `cd src/frontend && npx tsc --noEmit 2>&1 | grep -v RetirementPage`
Expected: no errors outside RetirementPage.tsx.

---

### Task 13: Wire routes and nav; delete RetirementPage

**Files:**
- Modify: `src/frontend/src/App.tsx:14,53-59`
- Modify: `src/frontend/src/components/RcarsSidebar.tsx:56-74`
- Delete: `src/frontend/src/pages/RetirementPage.tsx`

- [ ] **Step 1: App.tsx**

Replace the `RetirementPage` import with `import { PerformancePage } from './pages/PerformancePage'`. Restructure the analysis routes — Performance is gated by `canViewPerformance`, Overlap stays curator-only:

```tsx
{auth.isCurator && (
  <>
    <Route path="/analysis" element={<Navigate to="/analysis/overlap" replace />} />
    <Route path="/analysis/overlap" element={<ContentOverlapPage />} />
  </>
)}
{auth.canViewPerformance && (
  <Route path="/analysis/performance" element={<PerformancePage />} />
)}
```

- [ ] **Step 2: RcarsSidebar.tsx**

Split the Analysis section so the label shows for anyone with at least one analysis link:

```tsx
{(auth.isCurator || auth.canViewPerformance) && (
  <div className="rcars-nav-section-label">Analysis</div>
)}
{auth.isCurator && (
  <NavLink to="/analysis/overlap" className={...}>Overlap</NavLink>
)}
{auth.canViewPerformance && (
  <NavLink to="/analysis/performance" className={...}>Performance</NavLink>
)}
```
(keep the existing className callback used by every NavLink in this file).

- [ ] **Step 3: Delete the old page and verify**

```bash
rm src/frontend/src/pages/RetirementPage.tsx
cd src/frontend && npx tsc --noEmit && npx vitest run && npm run build
```
Expected: clean type-check, tests pass, build succeeds. Fix any straggler imports (`grep -rn "RetirementPage\|ReportingMetricsItem\|getRetirementDashboard\|analysis/retirement" src/frontend/src` must return nothing).

- [ ] **Step 4: Commit the whole frontend change**

```bash
git add src/frontend/
git commit -m "[RHDPCD-662] Performance page: Browse-style layout, URL state, channel tabs, inverted scores"
```

---

### Task 14: Documentation and CLAUDE.md

**Files:**
- Create: `docs/architecture/performance-analysis.md` (replaces retirement doc)
- Delete: `docs/architecture/retirement-analysis.md`
- Modify: `mkdocs.yml:41`, `CLAUDE.md`, plus every doc that references retirement pages/endpoints: `docs/overview.md`, `docs/user/web-guide.md`, `docs/admin/operations.md`, `docs/admin/cli-guide.md`, `docs/admin/deployment.md`, `docs/user/api-access.md`, `docs/architecture/data-design.md`, `docs/architecture/system-design.md`, `docs/architecture/api-reference.md`, `docs/architecture/content-overlap.md`

- [ ] **Step 1: Write `docs/architecture/performance-analysis.md`**

Structure (rewrite the old retirement-analysis.md content in performance terms — keep its data-flow and workflow sections, they're still accurate):
1. **Overview** — Performance page purpose, access model (`RCARS_PERFORMANCE_PUBLIC`, default public; curator extras).
2. **Data flow** — RHDP Reporting MCP → `run_reporting_sync()` → `performance_channels` + `performance_scores` → `GET /analysis/performance` → frontend (carry over from the old doc, updating endpoint).
3. **Channels** — `sales` (source `rhdp`) vs `marketing` (source `interactive_labs`, backlogged); `CHANNEL_SOURCES` mapping; `channel_scores` JSONB; what the S/M Data tags mean.
4. **Scoring formula** — inverted table (Usage 25 / Pipeline 15 / Closed 25 / ROI 15 continuous; zero → 0 points; no age discount; thresholds Strong ≥55 / Moderate 35–54 / Low <35; max ~80); score_breakdown structure and level vocabulary (`none/low/moderate/strong`).
5. **Time windows** — `3m/6m/9m/12m` keys in `windowed_metrics`, API `window` param, default `12m`.
6. **Retirement workflow** — unchanged stepper, Jira, mute; channel-keyed approval snapshot format with the JSON example from the spec §9.
7. **URL state** — the param table from spec §10 (with `window` default `12m`).
8. **API endpoints** — the renamed endpoint list.

- [ ] **Step 2: Sweep the other docs**

`mkdocs.yml:41` → `- Performance Analysis: architecture/performance-analysis.md`. For each other file run `grep -n "retirement\|Retirement" <file>` and update: page name ("Retirement Analysis" → "Performance"), route (`/analysis/retirement` → `/analysis/performance`), endpoint paths, scoring direction ("higher = retirement candidate" → "higher = better performance"), threshold labels (High/Review/Keepers → Strong/Moderate/Low), CLI output names, window values (1q/2q/3q/1y → 3m/6m/9m/12m). Keep references to the retirement *workflow* (it still exists) — only re-anchor them under the Performance page. Add `RCARS_PERFORMANCE_PUBLIC` to the deployment env-var docs, with the note: *"When set to `false`, also set `RCARS_CHAT_INTENT_ROLES=performance:curator` so chat performance answers match page access."*

- [ ] **Step 3: Update CLAUDE.md**

Rewrite the "Retirement Analysis — Key Implementation Details" section as "Performance Analysis — Key Implementation Details": update the scoring table to the inverted point values (0/3/7/15/22/25 usage; 0/5/11/15 pipeline; 0/10/20/25 closed; `round(15 * pct/100)` ROI; no age discount), zero-value → minimum, thresholds "Strong ≥ 55, Moderate ≥ 35, Low < 35 — higher is better", endpoints `/analysis/performance...`, mute endpoints, window values `3m/6m/9m/12m` default `12m`, channel param + `CHANNEL_SOURCES`, `RCARS_PERFORMANCE_PUBLIC`. Update the frontend pages list (`RetirementPage` → `PerformancePage`) and the Content Analysis page description in the Architecture section.

- [ ] **Step 4: Build docs check + commit**

Run: `grep -rn "analysis/retirement" docs/ CLAUDE.md mkdocs.yml | grep -v superpowers`
Expected: no matches.

```bash
git add docs/ mkdocs.yml CLAUDE.md
git commit -m "[RHDPCD-662] Replace retirement docs with performance-analysis architecture doc"
```

---

### Task 15: Full verification + graph update

- [ ] **Step 1: Full backend suite**

Run: `cd src/api && python -m pytest tests/ -m "not integration"`
Expected: PASS (0 failures)

- [ ] **Step 2: Full frontend**

Run: `cd src/frontend && npx tsc --noEmit && npx vitest run && npm run build`
Expected: PASS

- [ ] **Step 3: Repo-wide stragglers**

Run: `grep -rn "retirement_score\|retirement_flavored\|analysis/retirement\|WINDOW_KEYS\|1q\|RetirementDashboard" src/ --include="*.py" --include="*.ts" --include="*.tsx" | grep -v test_ | grep -v "retirement_workflow\|retirement_target_date\|RetirementWorkflow\|step_retired"`
Expected: no hits (workflow-related names are intentionally kept).

- [ ] **Step 4: Update knowledge graph + commit + push**

```bash
graphify update .
git add graphify-out/
git commit -m "[RHDPCD-662] Update knowledge graph"
git push origin feature/advisor-chat
```

---

### Task 16: Deploy to dev and verify end-to-end

Per project rules: commit and push BEFORE building; deploy to dev to verify (don't rely on local testing alone).

- [ ] **Step 1: Deploy both components**

```bash
ansible-playbook ansible/deploy.yml -e env=dev --tags full
```
(full because API, frontend, and config/env all changed). Confirm `git_ref` in `ansible/vars/dev.yml` points at `feature/advisor-chat` before running — if it points at `main`, set it to `feature/advisor-chat` for this dev deploy.

- [ ] **Step 2: Re-score via a normal sync**

Trigger the reporting sync (no one-off scripts): in the dev UI System → Sync & Analysis → reporting sync button, or `curl -X POST .../api/v1/admin/sync-reporting` with an admin token. Wait for the job to complete, then `rcars reporting-db status` on the pod — Strong/Moderate/Low counts should show most items as Low/Moderate and known-popular items as Strong (inverted from before).

- [ ] **Step 3: Smoke-check the page**

1. `/analysis/performance` loads for a non-curator dev user (set a non-curator `RCARS_DEV_USER` briefly or check `/auth/me` shows `performance_public: true`); Retirement Status sidebar group hidden for them.
2. Deep link `/analysis/performance?search=openshift&window=3m&performance=strong` initializes all three filters from the URL.
3. In the Advisor, ask a performance question about one item → the performance table block links to `/analysis/performance?search=...` and the search filter is applied on arrival; scores show green-for-high.
4. Score badge popover opens on click with strong/moderate language; no age-discount row.
5. Curator: expanded row shows Mute 30d and Retirement Workflow; drawer stepper works; approving an item writes a channel-keyed snapshot (check `retirement_workflow.approval_snapshot` has a `sales` key).

- [ ] **Step 4: Report results** — summarize pass/fail per check; fix and redeploy as needed.

---

## Self-Review (completed at planning time)

- **Spec coverage:** §1 route/nav → Tasks 5, 13. §2 access → Tasks 3, 5, 7, 13. §3 layout → Task 12. §4 scoring → Task 1 (+popover Task 11). §5 channel tabs → Task 12 (marketing disabled), Task 5 (channel param). §6 sidebar filters → Task 12. §7 collapsed row + Data column → Tasks 4, 12. §8 expanded row + addendum → Tasks 5 (marketing payload), 12. §9 workflow + snapshot → Tasks 5, 11. §10 URL state → Task 12 (window default `12m` per user decision, superseding the spec's `6m`). §11 advisor integration → Tasks 6, 9. §12 API changes → Task 5 (no redirects per user decision, superseding spec's backward-compat note). §13 file changes → Tasks 8–13. Out-of-scope items (marketing formula, combined tab, Without Prod, shared components, threshold tuning) are not planned.
- **User decisions honored:** bundle into `feature/advisor-chat`; sync-based rescoring only (Task 16 Step 2); `3m/6m/9m/12m` window values with `12m` (1-year) default and zero mapping layers; `sales`/`marketing` param names with internal `CHANNEL_SOURCES` mapping + UI hint text (Task 12 Step 2) + docs (Task 14); no redirects; `retirement_flavored` removed; Without Prod dropped; CLI wording flipped (Task 2); docs replaced including `retirement-analysis.md` (Task 14).
- **Type consistency check:** `performance_score`, `pipeline_touched`, `completions`, `first_activity`/`last_activity`, `channels_present`, `marketing` are used consistently across Task 5 (API), Task 8 (types), Tasks 11–12 (components). `require_performance_view` defined Task 3, consumed Task 5. `get_channel_metrics_map` defined Task 4, consumed Task 5. `scoreColor/scoreBg/fmt/num/fmtRoi` exported Task 11, consumed Task 12.
