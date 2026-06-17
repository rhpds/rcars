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
    provisions_pct: float,
    touched_zero: bool,
    touched_pct: float,
    closed_zero: bool,
    closed_pct: float,
    total_cost: float,
    closed_amount: float,
    first_provision: str,
) -> int:
    """Compute retirement score 0-100 using percentile ranks.

    Higher = stronger retirement candidate. Percentile args are 0-100 where
    0 = lowest among peers. touched_pct/closed_pct are ranks among non-zero
    items only; the _zero flags handle the zero case separately.
    """
    score = 0

    if provisions_pct < 10:
        score += 20
    elif provisions_pct < 25:
        score += 15
    elif provisions_pct < 50:
        score += 8
    elif provisions_pct < 75:
        score += 3

    if touched_zero:
        score += 15
    elif touched_pct < 50:
        score += 10
    elif touched_pct < 75:
        score += 4

    if closed_zero:
        score += 25
    elif closed_pct < 50:
        score += 15
    elif closed_pct < 75:
        score += 5

    if total_cost > 0 and closed_amount > 0:
        roi = closed_amount / total_cost
        if roi < 10:
            score += 15
        elif roi < 50:
            score += 5
    elif total_cost > 5000 and closed_amount == 0:
        score += 15

    if first_provision:
        try:
            from datetime import date
            if isinstance(first_provision, date):
                first_date = datetime.combine(first_provision, datetime.min.time())
            else:
                first_date = datetime.strptime(str(first_provision), "%Y-%m-%d")
            age_days = (datetime.now() - first_date).days
            if age_days <= 90:
                score = max(0, score - 40)
            elif age_days <= 180:
                score = max(0, score - 15)
        except (ValueError, TypeError):
            pass

    return min(score, 100)


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
            SUM(ps.user_experiences) AS experiences,
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
            SUM(c.total_cost) AS total_cost,
            ROUND(SUM(c.total_cost) / NULLIF(COUNT(*), 0), 2) AS avg_cost_per_provision
        FROM costs c
        JOIN provisions_summary ps ON ps.uuid = c.provision_uuid
        JOIN catalog_items ci ON ci.id = ps.catalog_id
        WHERE 1=1 {PROVISION_FILTERS}
        GROUP BY ci.name
    """


def _build_provisions_by_quarter_sql(start_date: str) -> str:
    return f"""
        SELECT
            ci.name AS catalog_base_name,
            TO_CHAR(DATE_TRUNC('quarter', ps.provisioned_at), 'YYYY-"Q"Q') AS quarter,
            COUNT(DISTINCT ps.uuid) AS provisions
        FROM provisions_summary ps
        JOIN catalog_items ci ON ci.id = ps.catalog_id
        WHERE ps.provisioned_at >= '{start_date}'
          {PROVISION_FILTERS}
        GROUP BY ci.name, quarter
    """


def _build_touched_by_quarter_sql(start_date: str) -> str:
    return f"""
        WITH unique_opps AS (
            SELECT DISTINCT ON (so.number, ci.name,
                TO_CHAR(DATE_TRUNC('quarter', ps.provisioned_at), 'YYYY-"Q"Q'))
                ci.name AS catalog_base_name, so.number, so.amount,
                TO_CHAR(DATE_TRUNC('quarter', ps.provisioned_at), 'YYYY-"Q"Q') AS quarter
            FROM provisions_summary ps
            JOIN catalog_items ci ON ci.id = ps.catalog_id
            JOIN sales_opportunity so ON so.id = ps.sales_opportunity_id
            WHERE ps.sales_opportunity_id IS NOT NULL
              AND ps.provisioned_at >= '{start_date}'
              {PROVISION_FILTERS}
            ORDER BY so.number, ci.name,
                TO_CHAR(DATE_TRUNC('quarter', ps.provisioned_at), 'YYYY-"Q"Q')
        )
        SELECT catalog_base_name, quarter, SUM(amount) AS touched_amount
        FROM unique_opps
        GROUP BY catalog_base_name, quarter
    """


def _build_closed_by_quarter_sql(start_date: str) -> str:
    return f"""
        WITH unique_opps AS (
            SELECT DISTINCT ON (so.number, ci.name,
                TO_CHAR(DATE_TRUNC('quarter', so.closed_at), 'YYYY-"Q"Q'))
                ci.name AS catalog_base_name, so.number, so.amount,
                TO_CHAR(DATE_TRUNC('quarter', so.closed_at), 'YYYY-"Q"Q') AS quarter
            FROM provisions_summary ps
            JOIN catalog_items ci ON ci.id = ps.catalog_id
            JOIN sales_opportunity so ON so.id = ps.sales_opportunity_id
            WHERE ps.sales_opportunity_id IS NOT NULL
              AND so.is_closed = true
              AND so.stage IN ('Closed Won', 'Closed Booked')
              AND so.closed_at >= '{start_date}'
              {PROVISION_FILTERS}
            ORDER BY so.number, ci.name,
                TO_CHAR(DATE_TRUNC('quarter', so.closed_at), 'YYYY-"Q"Q')
        )
        SELECT catalog_base_name, quarter, SUM(amount) AS closed_amount
        FROM unique_opps
        GROUP BY catalog_base_name, quarter
    """


def _build_cost_by_quarter_sql(start_date: str) -> str:
    return f"""
        WITH costs AS (
            SELECT provision_uuid, SUM(total_cost) AS total_cost
            FROM provision_cost
            WHERE month_ts >= DATE_TRUNC('month', '{start_date}'::date)
            GROUP BY provision_uuid
        )
        SELECT
            ci.name AS catalog_base_name,
            TO_CHAR(DATE_TRUNC('quarter', ps.provisioned_at), 'YYYY-"Q"Q') AS quarter,
            SUM(c.total_cost) AS total_cost
        FROM costs c
        JOIN provisions_summary ps ON ps.uuid = c.provision_uuid
        JOIN catalog_items ci ON ci.id = ps.catalog_id
        WHERE 1=1 {PROVISION_FILTERS}
        GROUP BY ci.name, DATE_TRUNC('quarter', ps.provisioned_at)
    """


def _build_quarterly_data(
    prov_q_rows: list[dict],
    touched_q_rows: list[dict],
    closed_q_rows: list[dict],
    cost_q_rows: list[dict],
) -> dict[str, dict]:
    """Build per-base-name quarterly breakdown dict from query results."""
    result: dict[str, dict[str, dict]] = {}

    for r in prov_q_rows:
        name, q = r["catalog_base_name"], r["quarter"]
        result.setdefault(name, {}).setdefault(q, {})["provisions"] = int(r["provisions"])

    for r in touched_q_rows:
        name, q = r["catalog_base_name"], r["quarter"]
        result.setdefault(name, {}).setdefault(q, {})["touched"] = float(r["touched_amount"] or 0)

    for r in closed_q_rows:
        name, q = r["catalog_base_name"], r["quarter"]
        result.setdefault(name, {}).setdefault(q, {})["closed"] = float(r["closed_amount"] or 0)

    for r in cost_q_rows:
        name, q = r["catalog_base_name"], r["quarter"]
        result.setdefault(name, {}).setdefault(q, {})["cost"] = float(r["total_cost"] or 0)

    return result


def compute_windowed_scores(items: list[dict], num_quarters: int) -> list[dict]:
    """Recompute retirement scores for a subset of trailing quarters.

    Sums provisions/touched/closed/cost from the most recent N quarters,
    computes fresh percentile rankings, and returns items with updated scores.
    """
    all_quarters = set()
    for item in items:
        qd = item.get("quarterly_data") or {}
        all_quarters.update(qd.keys())

    recent = sorted(all_quarters, reverse=True)[:num_quarters]
    recent_set = set(recent)

    windowed = []
    for item in items:
        qd = item.get("quarterly_data") or {}
        prov = sum(qd.get(q, {}).get("provisions", 0) for q in recent_set)
        touched = sum(qd.get(q, {}).get("touched", 0) for q in recent_set)
        closed = sum(qd.get(q, {}).get("closed", 0) for q in recent_set)
        cost = sum(qd.get(q, {}).get("cost", 0) for q in recent_set)

        windowed.append({
            **item,
            "provisions": prov,
            "touched_amount": touched,
            "closed_amount": closed,
            "total_cost": cost,
            "avg_cost_per_provision": round(cost / prov, 2) if prov > 0 else 0,
        })

    sorted_provisions = sorted(w["provisions"] for w in windowed)
    sorted_touched = sorted(w["touched_amount"] for w in windowed if w["touched_amount"] > 0)
    sorted_closed = sorted(w["closed_amount"] for w in windowed if w["closed_amount"] > 0)

    for w in windowed:
        w["retirement_score"] = compute_retirement_score(
            provisions_pct=_percentile_rank(w["provisions"], sorted_provisions),
            touched_zero=w["touched_amount"] == 0,
            touched_pct=_percentile_rank(w["touched_amount"], sorted_touched),
            closed_zero=w["closed_amount"] == 0,
            closed_pct=_percentile_rank(w["closed_amount"], sorted_closed),
            total_cost=w["total_cost"],
            closed_amount=w["closed_amount"],
            first_provision=w.get("first_provision") or "",
        )
        w["sales_impact"] = compute_sales_impact(w["closed_amount"])

    return windowed


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


def run_reporting_sync(db, settings) -> dict:
    """Pull reporting data from MCP server, compute scores, upsert locally.

    Returns summary dict with counts. Raises on MCP connection failure.
    """
    url = settings.reporting_mcp_url
    token = settings.reporting_mcp_token
    log = logger.bind(action="reporting_sync")

    sales_start = (datetime.now() - timedelta(days=settings.reporting_sales_days)).strftime("%Y-%m-%d")
    quarter_start = (datetime.now() - timedelta(days=settings.reporting_provisions_days)).strftime("%Y-%m-%d")

    log.info("fetching_provisions", sales_start=sales_start)
    prov_rows = mcp_query(_build_provisions_sql(sales_start), url=url, token=token)
    prov_data = {r["catalog_base_name"]: r for r in prov_rows}
    log.info("fetched_provisions", count=len(prov_data))

    log.info("fetching_provisions_quarter", quarter_start=quarter_start)
    quarter_rows = mcp_query(_build_provisions_quarter_sql(quarter_start), url=url, token=token)
    quarter_data = {r["catalog_base_name"]: int(r["provisions_quarter"]) for r in quarter_rows}
    log.info("fetched_provisions_quarter", count=len(quarter_data))

    log.info("fetching_touched", sales_start=sales_start)
    touched_rows = mcp_query(_build_touched_sql(sales_start), url=url, token=token)
    touched_data = {r["catalog_base_name"]: float(r["touched_amount"] or 0) for r in touched_rows}
    log.info("fetched_touched", count=len(touched_data))

    log.info("fetching_closed", sales_start=sales_start)
    closed_rows = mcp_query(_build_closed_sql(sales_start), url=url, token=token)
    closed_data = {r["catalog_base_name"]: float(r["closed_amount"] or 0) for r in closed_rows}
    log.info("fetched_closed", count=len(closed_data))

    log.info("fetching_cost", sales_start=sales_start)
    cost_rows = mcp_query(_build_cost_sql(sales_start), url=url, token=token)
    cost_data = {r["catalog_base_name"]: r for r in cost_rows}
    log.info("fetched_cost", count=len(cost_data))

    log.info("fetching_dates")
    date_rows = mcp_query(DATES_SQL, url=url, token=token, timeout=60)
    date_data = {r["catalog_base_name"]: r for r in date_rows}
    log.info("fetched_dates", count=len(date_data))

    log.info("fetching_quarterly_breakdowns")
    prov_q_rows = mcp_query(_build_provisions_by_quarter_sql(sales_start), url=url, token=token)
    touched_q_rows = mcp_query(_build_touched_by_quarter_sql(sales_start), url=url, token=token)
    closed_q_rows = mcp_query(_build_closed_by_quarter_sql(sales_start), url=url, token=token)
    cost_q_rows = mcp_query(_build_cost_by_quarter_sql(sales_start), url=url, token=token, timeout=300)
    quarterly = _build_quarterly_data(prov_q_rows, touched_q_rows, closed_q_rows, cost_q_rows)
    log.info("fetched_quarterly", items_with_quarters=len(quarterly))

    all_names = set(prov_data) | set(touched_data) | set(closed_data) | set(cost_data) | set(date_data)
    excluded = {n for n in all_names if any(n.startswith(p) for p in EXCLUDE_PREFIXES)}
    filtered_names = all_names - excluded
    log.info("merging", total_base_names=len(all_names), excluded=len(excluded),
             filtered=len(filtered_names))

    merged_rows = []
    for name in filtered_names:
        prov = prov_data.get(name, {})
        cost = cost_data.get(name, {})
        dates = date_data.get(name, {})

        merged_rows.append({
            "catalog_base_name": name,
            "display_name": prov.get("display_name", "") or dates.get("display_name", "") or name,
            "provisions": int(prov.get("provisions", 0)),
            "provisions_quarter": quarter_data.get(name, 0),
            "requests": int(prov.get("requests", 0)),
            "experiences": int(prov.get("experiences", 0)),
            "unique_users": int(prov.get("unique_users", 0)),
            "success_ratio": float(prov.get("success_ratio", 0) or 0),
            "failure_ratio": float(prov.get("failure_ratio", 0) or 0),
            "touched_amount": touched_data.get(name, 0.0),
            "closed_amount": closed_data.get(name, 0.0),
            "total_cost": float(cost.get("total_cost", 0) or 0),
            "avg_cost_per_provision": float(cost.get("avg_cost_per_provision", 0) or 0),
            "first_provision": (dates.get("first_provision", "") or "") or None,
            "last_provision": (dates.get("last_provision", "") or None),
            "quarterly_data": json.dumps(quarterly.get(name, {})),
        })

    sorted_provisions = sorted(r["provisions"] for r in merged_rows)
    sorted_touched = sorted(r["touched_amount"] for r in merged_rows if r["touched_amount"] > 0)
    sorted_closed = sorted(r["closed_amount"] for r in merged_rows if r["closed_amount"] > 0)

    for row in merged_rows:
        row["retirement_score"] = compute_retirement_score(
            provisions_pct=_percentile_rank(row["provisions"], sorted_provisions),
            touched_zero=row["touched_amount"] == 0,
            touched_pct=_percentile_rank(row["touched_amount"], sorted_touched),
            closed_zero=row["closed_amount"] == 0,
            closed_pct=_percentile_rank(row["closed_amount"], sorted_closed),
            total_cost=row["total_cost"],
            closed_amount=row["closed_amount"],
            first_provision=row["first_provision"] or "",
        )

    upserted = db.upsert_reporting_metrics(merged_rows)
    synced_names = {r["catalog_base_name"] for r in merged_rows}
    orphans = db.delete_orphan_reporting_metrics(synced_names=synced_names)

    summary = {
        "synced": upserted,
        "orphans_removed": orphans,
        "provisions_rows": len(prov_data),
        "touched_rows": len(touched_data),
        "closed_rows": len(closed_data),
        "cost_rows": len(cost_data),
        "date_rows": len(date_data),
    }
    log.info("sync_complete", **summary)
    return summary
