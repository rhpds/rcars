"""RHDP reporting MCP sync — utilities, MCP client, and sync orchestration."""

from __future__ import annotations

import bisect
import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta

import structlog

logger = structlog.get_logger(component="reporting_sync")

STAGE_SUFFIXES = (".prod", ".dev", ".event", ".test")

PROVISION_FILTERS = """
    AND ps.environment = 'PROD'
    AND ps.user_group IN ('Only Regular Users', 'Red Hat Console')
"""

EXCLUDE_PREFIXES = ("tests.", "clusterplatform.", "resourcehub.")


def extract_base_name(ci_name: str) -> str:
    """Strip stage suffix from an RCARS ci_name to get the reporting DB base name."""
    for suffix in STAGE_SUFFIXES:
        if ci_name.endswith(suffix):
            return ci_name[: -len(suffix)]
    return ci_name


def _percentile_rank(val: float, sorted_vals: list[float]) -> float:
    """Return 0-100 percentile rank (0=lowest, 100=highest)."""
    if not sorted_vals:
        return 0.0
    pos = bisect.bisect_right(sorted_vals, val)
    return (pos / len(sorted_vals)) * 100


def compute_retirement_score(
    provisions_zero: bool,
    provisions_pct: float,
    touched_zero: bool,
    touched_pct: float,
    closed_zero: bool,
    closed_pct: float,
    total_cost: float,
    closed_amount: float,
    first_provision: str,
    **kwargs,
) -> int:
    """Compute retirement score 0-100 using percentile ranks.

    Higher = stronger retirement candidate. Percentile args are 0-100
    ranks among non-zero peers only; the _zero flags handle the zero
    case separately. Max achievable ~80.
    """
    _, score = _compute_retirement_score_with_breakdown(
        provisions_zero, provisions_pct,
        touched_zero, touched_pct,
        closed_zero, closed_pct,
        total_cost, closed_amount, first_provision,
        **kwargs,
    )
    return score


def compute_retirement_score_breakdown(
    provisions_zero: bool,
    provisions_pct: float,
    touched_zero: bool,
    touched_pct: float,
    closed_zero: bool,
    closed_pct: float,
    total_cost: float,
    closed_amount: float,
    first_provision: str,
    **kwargs,
) -> dict:
    """Return the full score breakdown dict (factors + explanation)."""
    breakdown, _ = _compute_retirement_score_with_breakdown(
        provisions_zero, provisions_pct,
        touched_zero, touched_pct,
        closed_zero, closed_pct,
        total_cost, closed_amount, first_provision,
        **kwargs,
    )
    return breakdown


def _compute_retirement_score_with_breakdown(
    provisions_zero: bool,
    provisions_pct: float,
    touched_zero: bool,
    touched_pct: float,
    closed_zero: bool,
    closed_pct: float,
    total_cost: float,
    closed_amount: float,
    first_provision: str,
    provisions_raw: int = 0,
    touched_raw: float = 0,
    roi_zero: bool = False,
    roi_pct: float = 0,
) -> tuple[dict, int]:
    """Internal: compute score and return (breakdown_dict, final_score)."""
    score = 0
    factors = []

    def _fmt_dollars(v: float) -> str:
        if v >= 1_000_000:
            return f"${v / 1_000_000:.1f}M"
        if v >= 1_000:
            return f"${v / 1_000:.1f}K"
        return f"${v:.0f}"

    def _pct_label(pct: float) -> str:
        return f"percentile {int(pct)} of items with activity"

    # --- Provisions (max 25) ---
    if provisions_zero:
        pts = 25
        reason = "Zero provisions in this window — nobody ordered it"
        level = "critical"
    elif provisions_pct < 10:
        pts = 22
        reason = f"{provisions_raw} provisions — bottom 10% ({_pct_label(provisions_pct)})"
        level = "high"
    elif provisions_pct < 25:
        pts = 18
        reason = f"{provisions_raw} provisions — bottom 25% ({_pct_label(provisions_pct)})"
        level = "high"
    elif provisions_pct < 50:
        pts = 10
        reason = f"{provisions_raw} provisions — below median ({_pct_label(provisions_pct)})"
        level = "moderate"
    elif provisions_pct < 75:
        pts = 3
        reason = f"{provisions_raw} provisions — above median ({_pct_label(provisions_pct)})"
        level = "low"
    else:
        pts = 0
        reason = f"{provisions_raw} provisions — top 25% ({_pct_label(provisions_pct)})"
        level = "none"
    score += pts
    factors.append({"factor": "usage", "points": pts, "max": 25, "level": level, "reason": reason})

    # --- Pipeline Touched (max 15) ---
    if touched_zero:
        pts = 15
        reason = "$0 pipeline influenced — no linked opportunities"
        level = "critical"
    elif touched_pct < 50:
        pts = 10
        reason = f"{_fmt_dollars(touched_raw)} pipeline — below median ({_pct_label(touched_pct)})"
        level = "moderate"
    elif touched_pct < 75:
        pts = 4
        reason = f"{_fmt_dollars(touched_raw)} pipeline — above median ({_pct_label(touched_pct)})"
        level = "low"
    else:
        pts = 0
        reason = f"{_fmt_dollars(touched_raw)} pipeline — top 25% ({_pct_label(touched_pct)})"
        level = "none"
    score += pts
    factors.append({"factor": "pipeline", "points": pts, "max": 15, "level": level, "reason": reason})

    # --- Closed Sales (max 25) ---
    if closed_zero:
        pts = 25
        reason = "$0 closed — no deals won from demos of this item"
        level = "critical"
    elif closed_pct < 50:
        pts = 15
        reason = f"{_fmt_dollars(closed_amount)} closed — below median ({_pct_label(closed_pct)})"
        level = "moderate"
    elif closed_pct < 75:
        pts = 5
        reason = f"{_fmt_dollars(closed_amount)} closed — above median ({_pct_label(closed_pct)})"
        level = "low"
    else:
        pts = 0
        reason = f"{_fmt_dollars(closed_amount)} closed — top 25% ({_pct_label(closed_pct)})"
        level = "none"
    score += pts
    factors.append({"factor": "sales", "points": pts, "max": 25, "level": level, "reason": reason})

    # --- Cost Efficiency (max 15) — percentile-ranked ROI ---
    roi_val = (closed_amount / total_cost) if total_cost > 0 and closed_amount > 0 else 0
    roi_label = f"{roi_val:.1f}x return ({_fmt_dollars(closed_amount)} closed / {_fmt_dollars(total_cost)} cost)"
    if roi_zero:
        pts = 15
        reason = f"{_fmt_dollars(total_cost)} spent with $0 closed — no return on investment"
        level = "critical"
    elif total_cost == 0:
        pts = 0
        reason = "No cost data"
        level = "none"
    elif roi_pct < 10:
        pts = 15
        reason = f"{roi_label} — bottom 10% ({_pct_label(roi_pct)})"
        level = "high"
    elif roi_pct < 25:
        pts = 12
        reason = f"{roi_label} — bottom 25% ({_pct_label(roi_pct)})"
        level = "high"
    elif roi_pct < 50:
        pts = 8
        reason = f"{roi_label} — below median ({_pct_label(roi_pct)})"
        level = "moderate"
    elif roi_pct < 75:
        pts = 3
        reason = f"{roi_label} — above median ({_pct_label(roi_pct)})"
        level = "low"
    else:
        pts = 0
        reason = f"{roi_label} — top 25% ({_pct_label(roi_pct)})"
        level = "none"
    score += pts
    factors.append({"factor": "roi", "points": pts, "max": 15, "level": level, "reason": reason})

    # --- Age discount ---
    age_discount = 0
    age_reason = None
    if first_provision:
        try:
            from datetime import date
            if isinstance(first_provision, date):
                first_date = datetime.combine(first_provision, datetime.min.time())
            else:
                first_date = datetime.strptime(str(first_provision), "%Y-%m-%d")
            age_days = (datetime.now() - first_date).days
            if age_days <= 90:
                age_discount = -30
                age_reason = f"New item ({age_days} days old) — score reduced by 30"
            elif age_days <= 180:
                age_discount = -10
                age_reason = f"Relatively new ({age_days} days old) — score reduced by 10"
        except (ValueError, TypeError):
            pass

    if age_discount:
        score = max(0, score + age_discount)

    final = min(score, 100)

    # Build summary sentence
    high_factors = [f for f in factors if f["level"] in ("critical", "high")]
    ok_factors = [f for f in factors if f["level"] == "none"]

    parts = []
    if high_factors:
        names = {"usage": "low usage", "pipeline": "weak pipeline", "sales": "low sales", "roi": "poor ROI"}
        parts.append(", ".join(names.get(f["factor"], f["factor"]) for f in high_factors))
    if ok_factors:
        names = {"usage": "strong usage", "pipeline": "strong pipeline", "sales": "strong sales", "roi": "good ROI"}
        parts.append(", ".join(names.get(f["factor"], f["factor"]) for f in ok_factors))
        parts[-1] = "offset by " + parts[-1]

    summary = ". ".join(p.capitalize() if i == 0 else p for i, p in enumerate(parts)) if parts else "Neutral across all factors"
    if age_reason:
        summary += f". {age_reason}"
    summary += "."

    breakdown = {
        "score": final,
        "factors": factors,
        "age_discount": age_discount,
        "summary": summary,
    }
    return breakdown, final


def compute_sales_impact(closed_amount: float) -> str:
    """Compute sales impact tier from closed amount."""
    if closed_amount >= 1_000_000:
        return "high"
    if closed_amount >= 100_000:
        return "moderate"
    return "low"


def _mcp_call(
    tool_name: str,
    arguments: dict,
    url: str,
    token: str,
    timeout: int = 180,
) -> dict:
    """Call an MCP tool via HTTP JSON-RPC, return parsed JSON result."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }).encode("utf-8")

    if not url.startswith("https://"):
        raise ValueError(f"MCP URL must use HTTPS, got: {url[:50]}")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    if "error" in body:
        raise RuntimeError(f"MCP error: {body['error']}")

    text = body["result"]["content"][0]["text"]
    idx = text.find("{")
    if idx > 0:
        text = text[idx:]
    return json.loads(text)


def mcp_query(
    sql: str,
    url: str,
    token: str,
    timeout: int = 180,
) -> list[dict]:
    """Execute SQL via MCP server, auto-paginating past 500-row cap."""
    PAGE = 500
    MAX_PAGES = 50
    all_rows: list[dict] = []
    offset = 0
    for _ in range(MAX_PAGES):
        paged = f"WITH _q AS ({sql}) SELECT * FROM _q ORDER BY 1 LIMIT {PAGE} OFFSET {offset}"
        result = _mcp_call(
            "query",
            {"sql": paged, "output_format": "json", "limit": PAGE},
            url=url, token=token, timeout=timeout,
        )
        rows = result["rows"]
        all_rows.extend(rows)
        if len(rows) < PAGE:
            break
        offset += PAGE
    return all_rows


def _build_provisions_sql(start_date: str) -> str:
    return f"""
        SELECT
            ci.name AS catalog_base_name,
            ci.display_name,
            COUNT(DISTINCT ps.uuid) AS provisions,
            COUNT(DISTINCT ps.request_id) AS requests,
            COALESCE(SUM(ps.user_experiences), 0) AS experiences,
            COUNT(DISTINCT ps.user_id) AS unique_users,
            ROUND(
                SUM(ps.provision_success)::numeric
                / NULLIF(SUM(ps.provision_success) + SUM(ps.provision_failure), 0), 4
            ) AS success_ratio,
            ROUND(
                SUM(ps.provision_failure)::numeric
                / NULLIF(SUM(ps.provision_success) + SUM(ps.provision_failure), 0), 4
            ) AS failure_ratio
        FROM provisions_summary ps
        JOIN catalog_items ci ON ci.id = ps.catalog_id
        WHERE ps.provisioned_at >= '{start_date}'
          {PROVISION_FILTERS}
        GROUP BY ci.name, ci.display_name
    """


def _build_provisions_quarter_sql(start_date: str) -> str:
    return f"""
        SELECT ci.name AS catalog_base_name, COUNT(DISTINCT ps.uuid) AS provisions_quarter
        FROM provisions_summary ps
        JOIN catalog_items ci ON ci.id = ps.catalog_id
        WHERE ps.provisioned_at >= '{start_date}'
          {PROVISION_FILTERS}
        GROUP BY ci.name
    """


def _build_touched_sql(start_date: str) -> str:
    """Opportunities touched by PROD provisions from real users in the date window."""
    return f"""
        WITH unique_opps AS (
            SELECT DISTINCT ON (so.number, ci.name)
                ci.name AS catalog_base_name, so.number, so.amount
            FROM provisions_summary ps
            JOIN catalog_items ci ON ci.id = ps.catalog_id
            JOIN sales_opportunity so ON so.id = ps.sales_opportunity_id
            WHERE ps.sales_opportunity_id IS NOT NULL
              AND ps.provisioned_at >= '{start_date}'
              {PROVISION_FILTERS}
            ORDER BY so.number, ci.name
        )
        SELECT catalog_base_name, SUM(amount) AS touched_amount
        FROM unique_opps
        GROUP BY catalog_base_name
    """


def _build_closed_sql(start_date: str) -> str:
    """Closed-won deals from PROD/real-user provisions, filtered by close date."""
    return f"""
        WITH unique_opps AS (
            SELECT DISTINCT ON (so.number, ci.name)
                ci.name AS catalog_base_name, so.number, so.amount
            FROM provisions_summary ps
            JOIN catalog_items ci ON ci.id = ps.catalog_id
            JOIN sales_opportunity so ON so.id = ps.sales_opportunity_id
            WHERE ps.sales_opportunity_id IS NOT NULL
              AND so.is_closed = true
              AND so.stage IN ('Closed Won', 'Closed Booked')
              AND so.closed_at >= '{start_date}'
              {PROVISION_FILTERS}
            ORDER BY so.number, ci.name
        )
        SELECT catalog_base_name, SUM(amount) AS closed_amount
        FROM unique_opps
        GROUP BY catalog_base_name
    """


def _build_cost_sql(start_date: str) -> str:
    return f"""
        WITH costs AS (
            SELECT provision_uuid, SUM(total_cost) AS total_cost
            FROM provision_cost
            WHERE month_ts >= '{start_date}'
            GROUP BY provision_uuid
        )
        SELECT
            ci.name AS catalog_base_name,
            SUM(c.total_cost) AS total_cost
        FROM costs c
        JOIN provisions_summary ps ON ps.uuid = c.provision_uuid
        JOIN catalog_items ci ON ci.id = ps.catalog_id
        GROUP BY ci.name
    """


WINDOW_DAYS = {"3m": 91, "6m": 182, "9m": 274, "12m": 365}


def _window_start(window: str) -> str:
    """Return the start date for a sliding window (today - N days)."""
    return (datetime.now() - timedelta(days=WINDOW_DAYS[window])).strftime("%Y-%m-%d")


def _merge_published_base_pairs(
    merged_rows: list[dict],
    pub_base_map: dict[str, str],
) -> int:
    """Merge base CI rows into their published CI counterparts.

    For each published/base pair, sums metrics into the published row
    and removes the base row. Returns the number of pairs merged.
    """
    rows_by_name = {r["catalog_base_name"]: r for r in merged_rows}
    remove_names: set[str] = set()
    merged = 0

    for base_name, pub_name in pub_base_map.items():
        base_row = rows_by_name.get(base_name)
        pub_row = rows_by_name.get(pub_name)
        if not base_row or not pub_row:
            continue

        for field in ("provisions", "provisions_quarter", "requests",
                      "experiences", "unique_users",
                      "touched_amount", "closed_amount", "total_cost"):
            pub_row[field] += base_row[field]

        for field, fn in (("first_provision", min), ("last_provision", max)):
            vals = [v for v in (pub_row[field], base_row[field]) if v]
            pub_row[field] = fn(vals) if vals else None

        pub_wm = json.loads(pub_row["windowed_metrics"]) if isinstance(pub_row["windowed_metrics"], str) else pub_row["windowed_metrics"]
        base_wm = json.loads(base_row["windowed_metrics"]) if isinstance(base_row["windowed_metrics"], str) else base_row["windowed_metrics"]
        for wk in WINDOW_DAYS:
            if wk in base_wm:
                pub_w = pub_wm.setdefault(wk, {})
                for metric, value in base_wm[wk].items():
                    if metric in ("retirement_score", "sales_impact", "avg_cost_per_provision", "success_ratio", "failure_ratio", "score_breakdown"):
                        continue
                    pub_w[metric] = pub_w.get(metric, 0) + value
        pub_row["windowed_metrics"] = json.dumps(pub_wm)

        pub_row["avg_cost_per_provision"] = (
            round(pub_row["total_cost"] / pub_row["provisions"], 2)
            if pub_row["provisions"] > 0 else 0
        )

        remove_names.add(base_name)
        merged += 1

    merged_rows[:] = [r for r in merged_rows if r["catalog_base_name"] not in remove_names]
    return merged


def _recompute_windowed_scores(merged_rows: list[dict]) -> None:
    """Recompute per-window retirement_score and sales_impact after merges."""
    for wk in WINDOW_DAYS:
        items_with_window = []
        for row in merged_rows:
            wm = json.loads(row["windowed_metrics"]) if isinstance(row["windowed_metrics"], str) else row["windowed_metrics"]
            w = wm.get(wk, {})
            if w:
                items_with_window.append((row, wm, w))

        if not items_with_window:
            continue

        sorted_prov = sorted(w["provisions"] for _, _, w in items_with_window if w.get("provisions", 0) > 0)
        sorted_touched = sorted(w["touched_amount"] for _, _, w in items_with_window if w.get("touched_amount", 0) > 0)
        sorted_closed = sorted(w["closed_amount"] for _, _, w in items_with_window if w.get("closed_amount", 0) > 0)
        sorted_roi = sorted(
            w["closed_amount"] / w["total_cost"]
            for _, _, w in items_with_window
            if w.get("total_cost", 0) > 0 and w.get("closed_amount", 0) > 0
        )

        for row, wm, w in items_with_window:
            prov = w.get("provisions", 0)
            touched = w.get("touched_amount", 0)
            closed = w.get("closed_amount", 0)
            cost = w.get("total_cost", 0)
            has_roi = cost > 0 and closed > 0
            roi_val = closed / cost if has_roi else 0
            w["avg_cost_per_provision"] = round(cost / prov, 2) if prov > 0 else 0
            score_args = dict(
                provisions_zero=prov == 0,
                provisions_pct=_percentile_rank(prov, sorted_prov),
                touched_zero=touched == 0,
                touched_pct=_percentile_rank(touched, sorted_touched),
                closed_zero=closed == 0,
                closed_pct=_percentile_rank(closed, sorted_closed),
                total_cost=cost,
                closed_amount=closed,
                first_provision=row.get("first_provision") or "",
                provisions_raw=prov,
                touched_raw=touched,
                roi_zero=closed == 0 and cost > 0,
                roi_pct=_percentile_rank(roi_val, sorted_roi) if has_roi else 0,
            )
            w["retirement_score"] = compute_retirement_score(**score_args)
            w["score_breakdown"] = compute_retirement_score_breakdown(**score_args)
            w["sales_impact"] = compute_sales_impact(closed)
            wm[wk] = w
            row["windowed_metrics"] = json.dumps(wm)


def _build_unique_users_window_sql(start_date: str) -> str:
    return f"""
        SELECT ci.name AS catalog_base_name,
               COUNT(DISTINCT ps.user_id) AS unique_users
        FROM provisions_summary ps
        JOIN catalog_items ci ON ci.id = ps.catalog_id
        WHERE ps.provisioned_at >= '{start_date}'
          {PROVISION_FILTERS}
        GROUP BY ci.name
    """


DATES_SQL = f"""
    SELECT
        ci.name AS catalog_base_name,
        MIN(ps.provisioned_at)::date::text AS first_provision,
        MAX(ps.provisioned_at)::date::text AS last_provision
    FROM provisions_summary ps
    JOIN catalog_items ci ON ci.id = ps.catalog_id
    WHERE 1=1 {PROVISION_FILTERS}
    GROUP BY ci.name
"""


def _build_windowed_metrics(
    all_names: set[str],
    w_provisions: dict[str, dict[str, dict]],
    w_touched: dict[str, dict[str, float]],
    w_closed: dict[str, dict[str, float]],
    w_cost: dict[str, dict[str, float]],
    w_uu: dict[str, dict[str, int]],
    first_provisions: dict[str, str | None],
) -> dict[str, dict]:
    """Build per-item windowed_metrics JSONB from per-window query results.

    For each window (3m/6m/9m/12m), assembles raw metrics, computes
    percentile rankings, and pre-computes retirement_score + sales_impact.
    """
    per_item: dict[str, dict] = {}

    for wk in WINDOW_DAYS:
        prov_w = w_provisions.get(wk, {})
        touched_w = w_touched.get(wk, {})
        closed_w = w_closed.get(wk, {})
        cost_w = w_cost.get(wk, {})
        uu_w = w_uu.get(wk, {})

        entries: list[tuple[str, dict]] = []
        for name in all_names:
            p = prov_w.get(name, {})
            provisions = int(p.get("provisions", 0))
            touched = touched_w.get(name, 0.0)
            closed = closed_w.get(name, 0.0)
            cost = cost_w.get(name, 0.0)

            entry = {
                "provisions": provisions,
                "experiences": int(p.get("experiences", 0)),
                "requests": int(p.get("requests", 0)),
                "unique_users": uu_w.get(name, 0),
                "success_ratio": float(p.get("success_ratio", 0) or 0),
                "failure_ratio": float(p.get("failure_ratio", 0) or 0),
                "touched_amount": touched,
                "closed_amount": closed,
                "total_cost": cost,
                "avg_cost_per_provision": round(cost / provisions, 2) if provisions > 0 else 0,
            }
            entries.append((name, entry))

        sorted_prov = sorted(e["provisions"] for _, e in entries if e["provisions"] > 0)
        sorted_touched = sorted(e["touched_amount"] for _, e in entries if e["touched_amount"] > 0)
        sorted_closed = sorted(e["closed_amount"] for _, e in entries if e["closed_amount"] > 0)
        sorted_roi = sorted(
            e["closed_amount"] / e["total_cost"]
            for _, e in entries
            if e["total_cost"] > 0 and e["closed_amount"] > 0
        )

        for name, entry in entries:
            cost = entry["total_cost"]
            closed = entry["closed_amount"]
            has_roi = cost > 0 and closed > 0
            roi_val = closed / cost if has_roi else 0
            score_args = dict(
                provisions_zero=entry["provisions"] == 0,
                provisions_pct=_percentile_rank(entry["provisions"], sorted_prov),
                touched_zero=entry["touched_amount"] == 0,
                touched_pct=_percentile_rank(entry["touched_amount"], sorted_touched),
                closed_zero=entry["closed_amount"] == 0,
                closed_pct=_percentile_rank(entry["closed_amount"], sorted_closed),
                total_cost=cost,
                closed_amount=closed,
                first_provision=first_provisions.get(name) or "",
                provisions_raw=entry["provisions"],
                touched_raw=entry["touched_amount"],
                roi_zero=closed == 0 and cost > 0,
                roi_pct=_percentile_rank(roi_val, sorted_roi) if has_roi else 0,
            )
            entry["retirement_score"] = compute_retirement_score(**score_args)
            entry["score_breakdown"] = compute_retirement_score_breakdown(**score_args)
            entry["sales_impact"] = compute_sales_impact(entry["closed_amount"])
            per_item.setdefault(name, {})[wk] = entry

    return per_item


def run_reporting_sync(db, settings) -> dict:
    """Pull reporting data from MCP server, compute scores, upsert locally.

    Returns summary dict with counts. Raises on MCP connection failure.
    """
    url = settings.reporting_mcp_url
    token = settings.reporting_mcp_token
    log = logger.bind(action="reporting_sync")

    quarter_start = (datetime.now() - timedelta(days=settings.reporting_provisions_days)).strftime("%Y-%m-%d")

    log.info("fetching_sliding_window_metrics")
    w_provisions: dict[str, dict[str, dict]] = {}
    w_touched: dict[str, dict[str, float]] = {}
    w_closed: dict[str, dict[str, float]] = {}
    w_cost: dict[str, dict[str, float]] = {}
    w_uu: dict[str, dict[str, int]] = {}

    for wk in WINDOW_DAYS:
        w_start = _window_start(wk)
        log.info("fetching_window", window=wk, start=w_start)

        prov_rows = mcp_query(_build_provisions_sql(w_start), url=url, token=token)
        w_provisions[wk] = {r["catalog_base_name"]: r for r in prov_rows}

        touched_rows = mcp_query(_build_touched_sql(w_start), url=url, token=token)
        w_touched[wk] = {r["catalog_base_name"]: float(r["touched_amount"] or 0) for r in touched_rows}

        closed_rows = mcp_query(_build_closed_sql(w_start), url=url, token=token)
        w_closed[wk] = {r["catalog_base_name"]: float(r["closed_amount"] or 0) for r in closed_rows}

        cost_rows = mcp_query(_build_cost_sql(w_start), url=url, token=token, timeout=300)
        w_cost[wk] = {r["catalog_base_name"]: float(r.get("total_cost", 0) or 0) for r in cost_rows}

        uu_rows = mcp_query(_build_unique_users_window_sql(w_start), url=url, token=token)
        w_uu[wk] = {r["catalog_base_name"]: int(r["unique_users"]) for r in uu_rows}

        log.info("fetched_window", window=wk, provisions=len(w_provisions[wk]),
                 touched=len(w_touched[wk]), closed=len(w_closed[wk]),
                 cost=len(w_cost[wk]), unique_users=len(w_uu[wk]))

    prov_data = w_provisions["12m"]
    touched_data = w_touched["12m"]
    closed_data = w_closed["12m"]
    cost_data = w_cost["12m"]

    log.info("fetching_provisions_quarter", quarter_start=quarter_start)
    quarter_rows = mcp_query(_build_provisions_quarter_sql(quarter_start), url=url, token=token)
    quarter_data = {r["catalog_base_name"]: int(r["provisions_quarter"]) for r in quarter_rows}
    log.info("fetched_provisions_quarter", count=len(quarter_data))

    log.info("fetching_dates")
    date_rows = mcp_query(DATES_SQL, url=url, token=token, timeout=60)
    date_data = {r["catalog_base_name"]: r for r in date_rows}
    log.info("fetched_dates", count=len(date_data))

    all_names = set(prov_data) | set(touched_data) | set(closed_data) | set(cost_data) | set(date_data)
    excluded = {n for n in all_names if any(n.startswith(p) for p in EXCLUDE_PREFIXES)}
    retired_names = db.get_fully_retired_base_names()
    filtered_names = all_names - excluded - retired_names
    log.info("merging", total_base_names=len(all_names), excluded=len(excluded),
             retired_excluded=len(retired_names & all_names),
             filtered=len(filtered_names))

    first_provisions = {
        name: (date_data.get(name, {}).get("first_provision", "") or "") or None
        for name in filtered_names
    }
    windowed = _build_windowed_metrics(
        filtered_names, w_provisions, w_touched, w_closed, w_cost, w_uu,
        first_provisions,
    )
    log.info("built_windowed_metrics", items=len(windowed))

    merged_rows = []
    for name in filtered_names:
        prov = prov_data.get(name, {})
        cost_row = cost_data.get(name, 0.0)
        total_cost = cost_row if isinstance(cost_row, float) else float(cost_row)
        dates = date_data.get(name, {})
        provisions = int(prov.get("provisions", 0))

        merged_rows.append({
            "catalog_base_name": name,
            "display_name": prov.get("display_name", "") or dates.get("display_name", "") or name,
            "provisions": provisions,
            "provisions_quarter": quarter_data.get(name, 0),
            "requests": int(prov.get("requests", 0)),
            "experiences": int(prov.get("experiences", 0)),
            "unique_users": int(prov.get("unique_users", 0)),
            "success_ratio": float(prov.get("success_ratio", 0) or 0),
            "failure_ratio": float(prov.get("failure_ratio", 0) or 0),
            "touched_amount": touched_data.get(name, 0.0),
            "closed_amount": closed_data.get(name, 0.0),
            "total_cost": total_cost,
            "avg_cost_per_provision": round(total_cost / provisions, 2) if provisions > 0 else 0,
            "first_provision": first_provisions.get(name),
            "last_provision": (dates.get("last_provision", "") or None),
            "windowed_metrics": json.dumps(windowed.get(name, {})),
        })

    pub_base_map = db.get_published_base_mapping()
    log.info("published_base_mapping", pairs=len(pub_base_map))

    catalog_names = db.get_catalog_base_names()
    published_bases = set(pub_base_map.keys())
    missing = set(catalog_names) - filtered_names - published_bases
    log.info("backfilling_catalog", catalog_items=len(catalog_names),
             already_in_reporting=len(filtered_names & set(catalog_names)),
             missing=len(missing), published_bases_excluded=len(published_bases & set(catalog_names)))
    for name in missing:
        merged_rows.append({
            "catalog_base_name": name,
            "display_name": catalog_names[name] or name,
            "provisions": 0,
            "provisions_quarter": 0,
            "requests": 0,
            "experiences": 0,
            "unique_users": 0,
            "success_ratio": 0,
            "failure_ratio": 0,
            "touched_amount": 0.0,
            "closed_amount": 0.0,
            "total_cost": 0.0,
            "avg_cost_per_provision": 0.0,
            "first_provision": None,
            "last_provision": None,
            "windowed_metrics": json.dumps({}),
        })

    merged_pairs = _merge_published_base_pairs(merged_rows, pub_base_map)
    log.info("merged_published_base", pairs=merged_pairs)

    _recompute_windowed_scores(merged_rows)

    sorted_provisions = sorted(r["provisions"] for r in merged_rows if r["provisions"] > 0)
    sorted_touched = sorted(r["touched_amount"] for r in merged_rows if r["touched_amount"] > 0)
    sorted_closed = sorted(r["closed_amount"] for r in merged_rows if r["closed_amount"] > 0)
    sorted_roi = sorted(
        r["closed_amount"] / r["total_cost"]
        for r in merged_rows
        if r["total_cost"] > 0 and r["closed_amount"] > 0
    )

    for row in merged_rows:
        cost = row["total_cost"]
        closed = row["closed_amount"]
        has_roi = cost > 0 and closed > 0
        roi_val = closed / cost if has_roi else 0
        row["retirement_score"] = compute_retirement_score(
            provisions_zero=row["provisions"] == 0,
            provisions_pct=_percentile_rank(row["provisions"], sorted_provisions),
            touched_zero=row["touched_amount"] == 0,
            touched_pct=_percentile_rank(row["touched_amount"], sorted_touched),
            closed_zero=row["closed_amount"] == 0,
            closed_pct=_percentile_rank(row["closed_amount"], sorted_closed),
            total_cost=cost,
            closed_amount=closed,
            first_provision=row["first_provision"] or "",
            roi_zero=closed == 0 and cost > 0,
            roi_pct=_percentile_rank(roi_val, sorted_roi) if has_roi else 0,
        )

    upserted = db.upsert_reporting_metrics(merged_rows)
    synced_names = {r["catalog_base_name"] for r in merged_rows}
    orphans = db.delete_orphan_reporting_metrics(synced_names=synced_names)

    summary = {
        "synced": upserted,
        "orphans_removed": orphans,
        "catalog_backfilled": len(missing),
        "published_base_merged": merged_pairs,
        "provisions_rows": len(prov_data),
        "touched_rows": len(touched_data),
        "closed_rows": len(closed_data),
        "cost_rows": len(cost_data),
        "date_rows": len(date_data),
    }
    log.info("sync_complete", **summary)
    return summary
