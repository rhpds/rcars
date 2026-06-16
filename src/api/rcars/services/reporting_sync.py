"""RHDP reporting MCP sync — utilities, MCP client, and sync orchestration."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta

import structlog

logger = structlog.get_logger(component="reporting_sync")

STAGE_SUFFIXES = (".prod", ".dev", ".event", ".test")


def extract_base_name(ci_name: str) -> str:
    """Strip stage suffix from an RCARS ci_name to get the reporting DB base name."""
    for suffix in STAGE_SUFFIXES:
        if ci_name.endswith(suffix):
            return ci_name[: -len(suffix)]
    return ci_name


def compute_retirement_score(
    provisions: int,
    experiences: int,
    touched_amount: float,
    closed_amount: float,
    total_cost: float,
    has_prod: bool,
    first_provision: str,
) -> int:
    """Compute retirement score 0-100. Higher = stronger retirement candidate."""
    score = 0

    if not has_prod:
        score += 20

    if provisions < 60:
        score += 20
    elif provisions < 120:
        score += 8

    if experiences < 300:
        score += 10
    elif experiences < 600:
        score += 4

    if touched_amount < 10_000_000:
        score += 15
    elif touched_amount < 50_000_000:
        score += 6

    if closed_amount < 1_000_000:
        score += 20
    elif closed_amount < 5_000_000:
        score += 8

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
            first_date = datetime.strptime(first_provision, "%Y-%m-%d")
            age_days = (datetime.now() - first_date).days
            if age_days <= 90:
                score = max(0, score - 40)
            elif age_days <= 180:
                score = max(0, score - 15)
        except ValueError:
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
    all_rows: list[dict] = []
    offset = 0
    while True:
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
            COUNT(DISTINCT p.uuid) AS provisions,
            COUNT(DISTINCT p.request_id) AS requests,
            SUM(p.user_experiences) AS experiences,
            COUNT(DISTINCT p.user_id) AS unique_users,
            ROUND(
                COUNT(DISTINCT CASE WHEN p.provision_result = 'success' THEN p.uuid END)::numeric
                / NULLIF(COUNT(DISTINCT p.uuid), 0), 4
            ) AS success_ratio,
            ROUND(
                COUNT(DISTINCT CASE WHEN p.provision_result = 'failure' THEN p.uuid END)::numeric
                / NULLIF(COUNT(DISTINCT p.uuid), 0), 4
            ) AS failure_ratio
        FROM provisions p
        JOIN catalog_items ci ON ci.id = p.catalog_id
        WHERE p.provisioned_at >= '{start_date}'
        GROUP BY ci.name, ci.display_name
    """


def _build_provisions_quarter_sql(start_date: str) -> str:
    return f"""
        SELECT ci.name AS catalog_base_name, COUNT(DISTINCT p.uuid) AS provisions_quarter
        FROM provisions p
        JOIN catalog_items ci ON ci.id = p.catalog_id
        WHERE p.provisioned_at >= '{start_date}'
        GROUP BY ci.name
    """


def _build_sales_sql(start_date: str) -> str:
    return f"""
        WITH unique_opps AS (
            SELECT DISTINCT
                ci.name AS catalog_base_name, so.number, so.amount,
                so.is_closed, so.stage
            FROM provisions p
            JOIN catalog_items ci ON ci.id = p.catalog_id
            JOIN provision_sales ps ON ps.provision_uuid = p.uuid
            JOIN sales_opportunity so ON so.number = ps.sales_opportunity_number
            WHERE p.provisioned_at >= '{start_date}'
              AND ps.sales_opportunity_number IS NOT NULL
        )
        SELECT
            catalog_base_name,
            SUM(amount) AS touched_amount,
            SUM(CASE WHEN is_closed = true
                      AND stage IN ('Closed Won', 'Closed Booked')
                 THEN amount ELSE 0 END) AS closed_amount
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
        JOIN provisions p ON p.uuid = c.provision_uuid
        JOIN catalog_items ci ON ci.id = p.catalog_id
        GROUP BY ci.name
    """


DATES_SQL = """
    SELECT
        ci.name AS catalog_base_name,
        MIN(p.provisioned_at)::date::text AS first_provision,
        MAX(p.provisioned_at)::date::text AS last_provision
    FROM provisions p
    JOIN catalog_items ci ON ci.id = p.catalog_id
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

    log.info("fetching_sales", sales_start=sales_start)
    sales_rows = mcp_query(_build_sales_sql(sales_start), url=url, token=token)
    sales_data = {r["catalog_base_name"]: r for r in sales_rows}
    log.info("fetched_sales", count=len(sales_data))

    log.info("fetching_cost", sales_start=sales_start)
    cost_rows = mcp_query(_build_cost_sql(sales_start), url=url, token=token)
    cost_data = {r["catalog_base_name"]: r for r in cost_rows}
    log.info("fetched_cost", count=len(cost_data))

    log.info("fetching_dates")
    date_rows = mcp_query(DATES_SQL, url=url, token=token, timeout=60)
    date_data = {r["catalog_base_name"]: r for r in date_rows}
    log.info("fetched_dates", count=len(date_data))

    prod_base_names = db.get_all_base_names_with_prod()

    all_names = set(prov_data) | set(sales_data) | set(cost_data) | set(date_data)
    log.info("merging", total_base_names=len(all_names))

    merged_rows = []
    for name in all_names:
        prov = prov_data.get(name, {})
        sales = sales_data.get(name, {})
        cost = cost_data.get(name, {})
        dates = date_data.get(name, {})

        provisions = int(prov.get("provisions", 0))
        experiences = int(prov.get("experiences", 0))
        touched = float(sales.get("touched_amount", 0) or 0)
        closed = float(sales.get("closed_amount", 0) or 0)
        total_cost = float(cost.get("total_cost", 0) or 0)
        first_prov = dates.get("first_provision", "") or ""
        has_prod = name in prod_base_names

        score = compute_retirement_score(
            provisions=provisions, experiences=experiences,
            touched_amount=touched, closed_amount=closed,
            total_cost=total_cost, has_prod=has_prod,
            first_provision=first_prov,
        )

        merged_rows.append({
            "catalog_base_name": name,
            "display_name": prov.get("display_name", "") or dates.get("display_name", "") or name,
            "provisions": provisions,
            "provisions_quarter": quarter_data.get(name, 0),
            "requests": int(prov.get("requests", 0)),
            "experiences": experiences,
            "unique_users": int(prov.get("unique_users", 0)),
            "success_ratio": float(prov.get("success_ratio", 0) or 0),
            "failure_ratio": float(prov.get("failure_ratio", 0) or 0),
            "touched_amount": touched,
            "closed_amount": closed,
            "total_cost": total_cost,
            "avg_cost_per_provision": float(cost.get("avg_cost_per_provision", 0) or 0),
            "first_provision": first_prov or None,
            "last_provision": (dates.get("last_provision", "") or None),
            "retirement_score": score,
        })

    upserted = db.upsert_reporting_metrics(merged_rows)
    orphans = db.delete_orphan_reporting_metrics()

    summary = {
        "synced": upserted,
        "orphans_removed": orphans,
        "provisions_rows": len(prov_data),
        "sales_rows": len(sales_data),
        "cost_rows": len(cost_data),
        "date_rows": len(date_data),
    }
    log.info("sync_complete", **summary)
    return summary
