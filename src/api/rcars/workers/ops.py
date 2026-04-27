"""Ops worker tasks — catalog refresh, stale check."""

from __future__ import annotations

import shutil
from rcars.workers.base import WorkerContext, publish_progress
from rcars.services.catalog import CatalogReader
from rcars.services.analyzer import clone_showroom, check_showroom_stale
import structlog

logger = structlog.get_logger()


async def run_catalog_refresh(ctx: dict, job_id: str) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id)

    log.info("picked_up", action="picked_up", queue="ops")
    wctx.db.update_job_status(job_id, "running")

    try:
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="catalog_refresh", status="reading", message="Reading catalog from all namespaces...")

        reader = CatalogReader(kubeconfig_path=wctx.settings.kubeconfig_path)
        items = reader.refresh_catalog(
            namespaces=wctx.settings.catalog_namespaces,
            component_namespace=wctx.settings.agnosticv_component_namespace,
        )

        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="catalog_refresh", status="upserting",
                               message=f"Upserting {len(items)} items...", total=len(items))

        current_ci_names = set()
        for item in items:
            wctx.db.upsert_catalog_item(item)
            current_ci_names.add(item["ci_name"])

        removed = wctx.db.delete_removed_items(current_ci_names)

        result = {"total_items": len(items), "removed_items": len(removed)}
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="complete", status="complete",
                               message=f"Catalog refreshed: {len(items)} items, {len(removed)} removed",
                               **result)
        wctx.db.complete_job(job_id, result_json=result)
        log.info("refresh_complete", action="job_complete", **result)
        return result

    except Exception as e:
        log.error("refresh_failed", action="job_failed", error=str(e))
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="failed", status="failed", message=str(e), error=str(e))
        wctx.db.fail_job(job_id, error=str(e))
        raise


async def run_stale_check(ctx: dict, job_id: str) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id)

    log.info("picked_up", action="picked_up", queue="ops")
    wctx.db.update_job_status(job_id, "running")

    try:
        items = wctx.db.list_catalog_items()
        checkable = [i for i in items if i.get("showroom_url") and wctx.db.get_showroom_analysis(i["ci_name"])]
        total = len(checkable)

        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="stale_check", status="started",
                               message=f"Checking {total} analyzed Showrooms for content changes...", total=total)

        checked = 0
        stale_count = 0

        for item in checkable:
            analysis = wctx.db.get_showroom_analysis(item["ci_name"])
            showroom_url = item.get("showroom_url_override") or item["showroom_url"]
            clone_path = clone_showroom(showroom_url, item.get("showroom_ref"), wctx.settings.clone_dir)
            if not clone_path:
                continue
            try:
                stale_result = check_showroom_stale(clone_path, analysis.get("content_hash"))
                if stale_result["is_stale"]:
                    wctx.db.mark_stale(item["ci_name"], stale_result.get("head_sha"))
                    stale_count += 1
                else:
                    wctx.db.clear_stale(item["ci_name"])
                checked += 1
                if checked % 10 == 0:
                    await publish_progress(wctx.relay, job_id, wctx.db,
                                           phase="stale_check", status="progress",
                                           message=f"Checked {checked}/{total}, {stale_count} stale so far...",
                                           current=checked, total=total, stale=stale_count)
            finally:
                shutil.rmtree(clone_path, ignore_errors=True)

        result = {"checked": checked, "stale": stale_count}
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="complete", status="complete",
                               message=f"Stale check complete: {checked} checked, {stale_count} stale",
                               **result)
        wctx.db.complete_job(job_id, result_json=result)
        log.info("stale_check_complete", action="job_complete", **result)
        return result

    except Exception as e:
        log.error("stale_check_failed", action="job_failed", error=str(e))
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="failed", status="failed", message=str(e), error=str(e))
        wctx.db.fail_job(job_id, error=str(e))
        raise
