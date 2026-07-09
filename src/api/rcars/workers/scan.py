"""Analysis/scan worker tasks."""

from __future__ import annotations

import asyncio
import functools
from rcars.workers.base import WorkerContext
from rcars.services.analyzer import analyze_showroom, classify_scan_error
import structlog

logger = structlog.get_logger()


_VALID_FORMAT_KEYS = {"demo", "hands_on_lab"}


def _sanitize_format_suitability(data: dict | None) -> dict | None:
    """Strip LLM-hallucinated keys from format_suitability — only demo and hands_on_lab are valid."""
    if not data or not isinstance(data, dict):
        return data
    return {k: v for k, v in data.items() if k in _VALID_FORMAT_KEYS}


def _propagate_to_sibling(db, sib_name: str, analysis_data: dict, result: dict) -> None:
    """Propagate analysis + embeddings to a single sibling CI."""
    sib_data = dict(analysis_data)
    sib_data["ci_name"] = sib_name
    db.upsert_showroom_analysis(sib_data)
    db.clear_embeddings(sib_name)
    db.store_embedding(
        ci_name=sib_name, embed_type="ci_summary",
        content_text=result["ci_embedding_text"], embedding=result["ci_embedding"],
    )
    for mod_emb in result.get("module_embeddings", []):
        db.store_embedding(
            ci_name=sib_name, embed_type="module",
            module_title=mod_emb["module_title"],
            content_text=mod_emb["content_text"], embedding=mod_emb["embedding"],
        )
    db.set_scan_status(sib_name, "success")


async def run_analysis(ctx: dict, job_id: str, ci_name: str, sha_siblings: list[dict] | None = None) -> dict:
    wctx: WorkerContext = ctx["worker_ctx"]
    log = logger.bind(job_id=job_id, ci_name=ci_name)

    log.info("picked_up", action="picked_up", queue="analyze")
    wctx.db.update_job_status(job_id, "running", progress_json={"ci_name": ci_name})

    item = None
    try:
        item = wctx.db.get_catalog_item(ci_name)
        if not item:
            raise ValueError(f"Catalog item not found: {ci_name}")

        showroom_url = item.get("showroom_url_override") or item.get("showroom_url")
        if not showroom_url:
            raise ValueError(f"No Showroom URL for: {ci_name}")

        result = await asyncio.to_thread(
            functools.partial(
                analyze_showroom,
                ci_name=ci_name,
                display_name=item.get("display_name", ""),
                category=item.get("category", ""),
                product=item.get("product", ""),
                showroom_url=showroom_url,
                showroom_ref=item.get("showroom_ref"),
                settings=wctx.settings,
                model=wctx.settings.model,
                clone_dir=wctx.settings.clone_dir,
                db=wctx.db,
                content_path=item.get("content_path"),
                keywords=item.get("keywords") or [],
            )
        )

        if result and "error" in result:
            error_class = result["error"]
            error_msg = result["message"]
            wctx.db.complete_scan(ci_name, job_id, "failed",
                                  result_json={"ci_name": ci_name, "status": "failed"}, error=error_msg,
                                  error_class=error_class, error_message=error_msg)
            log.warning("analysis_failed", action="job_failed", error_class=error_class, error_msg=error_msg)
            return {"ci_name": ci_name, "success": False}

        if result and "analysis" in result:
            analysis = result["analysis"]

            analysis_data = {
                "ci_name": ci_name,
                "content_type": analysis.get("content_type"),
                "summary": analysis.get("summary"),
                "products_json": analysis.get("products"),
                "audience_json": analysis.get("audience"),
                "topics_json": analysis.get("topics"),
                "modules_json": analysis.get("modules"),
                "learning_objectives_json": analysis.get("learning_objectives"),
                "difficulty": analysis.get("difficulty"),
                "estimated_duration_min": analysis.get("estimated_duration_min"),
                "format_suitability_json": _sanitize_format_suitability(analysis.get("format_suitability")),
                "use_cases_json": analysis.get("use_cases"),
                "last_repo_commit": result.get("last_repo_commit"),
                "last_repo_updated": result.get("last_repo_updated"),
                "content_hash": result.get("content_hash"),
                "is_stale": False,
                "stale_commit": None,
            }
            wctx.db.upsert_showroom_analysis(analysis_data)

            wctx.db.clear_embeddings(ci_name)
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
                    module_title=mod_emb["module_title"],
                    content_text=mod_emb["content_text"],
                    embedding=mod_emb["embedding"],
                )

            # Propagate analysis to siblings sharing the same Showroom content
            propagated_set = {ci_name}
            effective_url = item.get("showroom_url_override") or item["showroom_url"]
            siblings = wctx.db.get_siblings_by_showroom(effective_url, item.get("showroom_ref"))
            for sibling in siblings:
                sib_name = sibling["ci_name"]
                if sib_name in propagated_set:
                    continue
                _propagate_to_sibling(wctx.db, sib_name, analysis_data, result)
                propagated_set.add(sib_name)

            # Propagate to SHA siblings (different ref, same commit SHA)
            if sha_siblings:
                log.info("sha_siblings_propagating", count=len(sha_siblings),
                         refs=[s.get("showroom_ref") for s in sha_siblings])
                for sha_sib in sha_siblings:
                    sib_name = sha_sib["ci_name"]
                    if sib_name in propagated_set:
                        continue
                    _propagate_to_sibling(wctx.db, sib_name, analysis_data, result)
                    propagated_set.add(sib_name)
                    # Also propagate to this SHA sibling's own ref-based siblings
                    sib_url = sha_sib.get("effective_url", "")
                    sib_ref = sha_sib.get("showroom_ref")
                    ref_siblings = wctx.db.get_siblings_by_showroom(sib_url, sib_ref)
                    for ref_sib in ref_siblings:
                        if ref_sib["ci_name"] in propagated_set:
                            continue
                        _propagate_to_sibling(wctx.db, ref_sib["ci_name"], analysis_data, result)
                        propagated_set.add(ref_sib["ci_name"])

            # Propagate to published CIs linked via published_ci_name
            published_propagated = 0
            for scanned_name in list(propagated_set):
                scanned_item = wctx.db.get_catalog_item(scanned_name) if scanned_name != ci_name else item
                pub_name = (scanned_item or {}).get("published_ci_name")
                if pub_name and pub_name not in propagated_set:
                    _propagate_to_sibling(wctx.db, pub_name, analysis_data, result)
                    propagated_set.add(pub_name)
                    published_propagated += 1
            if published_propagated:
                log.info("published_ci_propagated", count=published_propagated)

            propagated = len(propagated_set) - 1
            wctx.db.complete_scan(ci_name, job_id, "success",
                                  result_json={"ci_name": ci_name, "status": "analyzed", "propagated": propagated})
            log.info(
                "analysis_complete",
                action="job_complete",
                ci_name=ci_name,
                showroom_url=showroom_url,
                showroom_ref=item.get("showroom_ref"),
                content_files=result.get("content_file_count", 0),
                input_tokens=result.get("input_tokens", 0),
                output_tokens=result.get("output_tokens", 0),
                elapsed_seconds=result.get("elapsed_seconds"),
                propagated=propagated,
            )
            return {"ci_name": ci_name, "success": True}

        wctx.db.complete_scan(ci_name, job_id, "failed",
                              result_json={"ci_name": ci_name, "status": "failed"}, error="Analysis returned no results",
                              error_class="no_result", error_message="Analysis returned no results")
        log.warning("analysis_empty", action="job_failed")
        return {"ci_name": ci_name, "success": False}

    except Exception as e:
        log.error("analysis_failed", action="job_failed", error=str(e))
        error_class, error_msg = classify_scan_error(
            e, url=item.get("showroom_url") if item else None,
            ref=item.get("showroom_ref") if item else None,
            content_path=item.get("content_path") if item else None)
        wctx.db.complete_scan(ci_name, job_id, "failed",
                              result_json={"ci_name": ci_name, "status": "failed"}, error=str(e),
                              error_class=error_class, error_message=error_msg)
        raise
