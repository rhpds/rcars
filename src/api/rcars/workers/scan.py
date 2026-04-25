"""Analysis/scan worker tasks."""

from __future__ import annotations

from rcars.workers.base import WorkerContext
from rcars.services.analyzer import analyze_showroom
import structlog

logger = structlog.get_logger()


async def run_analysis(ctx: dict, job_id: str, ci_name: str) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id, ci_name=ci_name)

    log.info("picked_up", action="picked_up", queue="analyze")
    wctx.db.update_job_status(job_id, "running")

    try:
        item = wctx.db.get_catalog_item(ci_name)
        if not item:
            raise ValueError(f"Catalog item not found: {ci_name}")

        showroom_url = item.get("showroom_url_override") or item.get("showroom_url")
        if not showroom_url:
            raise ValueError(f"No Showroom URL for: {ci_name}")

        client = wctx.settings.get_anthropic_client()
        result = analyze_showroom(
            ci_name=ci_name,
            display_name=item.get("display_name", ""),
            category=item.get("category", ""),
            product=item.get("product", ""),
            showroom_url=showroom_url,
            showroom_ref=item.get("showroom_ref"),
            anthropic_client=client,
            model=wctx.settings.model,
            clone_dir=wctx.settings.clone_dir,
            db=wctx.db,
        )

        if result:
            wctx.db.upsert_showroom_analysis(result["analysis"])
            wctx.db.store_embedding(
                ci_name=ci_name,
                embed_type="ci_summary",
                content_text=result["ci_embedding_text"],
                embedding=result["ci_embedding"],
            )
            for mod_emb in result.get("module_embeddings", []):
                wctx.db.store_embedding(
                    ci_name=ci_name,
                    embed_type="module",
                    content_text=mod_emb["text"],
                    embedding=mod_emb["embedding"],
                    module_title=mod_emb["title"],
                )
            wctx.db.set_scan_status(ci_name, "success")
            wctx.db.complete_job(job_id, result_json={"ci_name": ci_name, "status": "analyzed"})
            log.info("analysis_complete", action="job_complete", ci_name=ci_name)
        else:
            wctx.db.set_scan_status(ci_name, "failed", error_class="no_result", error_message="Analysis returned no results")
            wctx.db.fail_job(job_id, error="Analysis returned no results")
            log.warning("analysis_empty", action="job_failed", ci_name=ci_name)

        return {"ci_name": ci_name, "success": result is not None}

    except Exception as e:
        log.error("analysis_failed", action="job_failed", error=str(e))
        from rcars.services.analyzer import classify_scan_error
        error_class, error_msg = classify_scan_error(e, item.get("showroom_url") if item else None)
        wctx.db.set_scan_status(ci_name, "failed", error_class=error_class, error_message=error_msg)
        wctx.db.fail_job(job_id, error=str(e))
        raise
