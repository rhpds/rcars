"""Ops worker tasks — catalog refresh, stale check."""

from __future__ import annotations

import shutil
from rcars.workers.base import WorkerContext, publish_progress
from rcars.services.catalog import CatalogReader
from rcars.services.analyzer import clone_showroom, check_showroom_stale, ls_remote_sha
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

        total = len(items)
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="catalog_refresh", status="upserting",
                               message=f"Upserting {total} items...", total=total)

        current_ci_names = set()
        for i, item in enumerate(items, 1):
            wctx.db.upsert_catalog_item(item)
            current_ci_names.add(item["ci_name"])
            if i % 100 == 0:
                await publish_progress(wctx.relay, job_id, wctx.db,
                                       phase="catalog_refresh", status="upserting",
                                       message=f"Upserting... {i}/{total}", current=i, total=total)

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

        # Deduplicate by (showroom_url, showroom_ref) — clone each unique repo once
        groups: dict[tuple[str, str | None], list[dict]] = {}
        for item in checkable:
            url = item.get("showroom_url_override") or item["showroom_url"]
            ref = item.get("showroom_ref")
            groups.setdefault((url, ref), []).append(item)

        total_groups = len(groups)
        total_cis = len(checkable)
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="stale_check", status="started",
                               message=f"Checking {total_groups} unique Showrooms ({total_cis} CIs) for content changes...",
                               total=total_groups)

        # Phase 1: fast ls-remote to find repos with new commits
        changed = []
        skipped = 0
        for (url, ref), group_items in groups.items():
            analysis = wctx.db.get_showroom_analysis(group_items[0]["ci_name"])
            stored_sha = analysis.get("last_repo_commit")
            remote_sha = ls_remote_sha(url, ref)
            if remote_sha and stored_sha and remote_sha == stored_sha:
                for item in group_items:
                    wctx.db.clear_stale(item["ci_name"])
                skipped += 1
            else:
                changed.append(((url, ref), group_items, analysis))
            if (skipped + len(changed)) % 50 == 0:
                await publish_progress(wctx.relay, job_id, wctx.db,
                                       phase="stale_check", status="ls-remote",
                                       message=f"Quick check: {skipped + len(changed)}/{total_groups} scanned, {len(changed)} have new commits...",
                                       current=skipped + len(changed), total=total_groups)

        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="stale_check", status="cloning",
                               message=f"Quick check done: {skipped} unchanged, {len(changed)} need content check...",
                               skipped=skipped, need_clone=len(changed))

        # Phase 2: clone only changed repos and compare content hash
        checked = 0
        stale_count = 0
        stale_cis = 0

        for (url, ref), group_items, analysis in changed:
            clone_path = clone_showroom(url, ref, wctx.settings.clone_dir)
            if not clone_path:
                checked += 1
                continue
            try:
                stale_result = check_showroom_stale(clone_path, analysis.get("content_hash"))
                for item in group_items:
                    if stale_result["is_stale"]:
                        wctx.db.mark_stale(item["ci_name"], stale_result.get("head_sha"))
                    else:
                        wctx.db.clear_stale(item["ci_name"])
                if stale_result["is_stale"]:
                    stale_count += 1
                    stale_cis += len(group_items)
                checked += 1
                if checked % 5 == 0:
                    await publish_progress(wctx.relay, job_id, wctx.db,
                                           phase="stale_check", status="progress",
                                           message=f"Content check: {checked}/{len(changed)}, {stale_count} stale so far...",
                                           current=checked, total=len(changed), stale=stale_count)
            finally:
                shutil.rmtree(clone_path, ignore_errors=True)

        result = {"checked": total_groups, "skipped": skipped, "cloned": len(changed), "stale": stale_count, "stale_cis": stale_cis, "total_cis": total_cis}
        await publish_progress(wctx.relay, job_id, wctx.db,
                               phase="complete", status="complete",
                               message=f"Stale check complete: {skipped} unchanged, {len(changed)} checked, {stale_count} stale ({stale_cis} CIs)",
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
