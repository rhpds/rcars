"""Ops worker tasks — catalog refresh, stale check."""

from __future__ import annotations

import shutil
from rcars.workers.base import WorkerContext
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
        reader = CatalogReader(kubeconfig_path=wctx.settings.kubeconfig_path)
        items = reader.refresh_catalog(
            namespaces=wctx.settings.catalog_namespaces,
            component_namespace=wctx.settings.agnosticv_component_namespace,
        )

        current_ci_names = set()
        for item in items:
            wctx.db.upsert_catalog_item(item)
            current_ci_names.add(item["ci_name"])

        removed = wctx.db.delete_removed_items(current_ci_names)

        result = {"total_items": len(items), "removed_items": len(removed)}
        wctx.db.complete_job(job_id, result_json=result)
        log.info("refresh_complete", action="job_complete", **result)
        return result

    except Exception as e:
        log.error("refresh_failed", action="job_failed", error=str(e))
        wctx.db.fail_job(job_id, error=str(e))
        raise


async def run_stale_check(ctx: dict, job_id: str) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id)

    log.info("picked_up", action="picked_up", queue="ops")
    wctx.db.update_job_status(job_id, "running")

    try:
        items = wctx.db.list_catalog_items()
        checked = 0
        stale_count = 0

        for item in items:
            analysis = wctx.db.get_showroom_analysis(item["ci_name"])
            if not analysis or not item.get("showroom_url"):
                continue
            showroom_url = item.get("showroom_url_override") or item["showroom_url"]
            clone_path = clone_showroom(showroom_url, item.get("showroom_ref"), wctx.settings.clone_dir)
            if not clone_path:
                continue
            try:
                result = check_showroom_stale(clone_path, analysis.get("content_hash"))
                if result["is_stale"]:
                    wctx.db.mark_stale(item["ci_name"], result.get("head_sha"))
                    stale_count += 1
                else:
                    wctx.db.clear_stale(item["ci_name"])
                checked += 1
            finally:
                shutil.rmtree(clone_path, ignore_errors=True)

        result = {"checked": checked, "stale": stale_count}
        wctx.db.complete_job(job_id, result_json=result)
        log.info("stale_check_complete", action="job_complete", **result)
        return result

    except Exception as e:
        log.error("stale_check_failed", action="job_failed", error=str(e))
        wctx.db.fail_job(job_id, error=str(e))
        raise
