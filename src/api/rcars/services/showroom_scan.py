"""One target's scan and source-checked, atomic artifact persistence.

Queue and job lifecycle belong to the caller. No row lock or pooled connection
spans Git/LLM requests; only a per-reuse-key advisory lock on a dedicated
connection serializes stages that can share one generation.
"""
import hashlib
import subprocess

from rcars.services.analyzer import analyze_showroom, classify_scan_error, regenerate_embeddings, showroom_reuse_key
from rcars.services.showroom_source import effective_showroom_source, analysis_generation
import structlog

log = structlog.get_logger()


def _snapshot(item):
    return (effective_showroom_source(item).to_dict(), *(item.get(key) for key in
        ("display_name", "category", "product", "keywords", "content_type", "retired_at")))


# Longer than one analysis, well inside the 600s scan job timeout.
REUSE_LOCK_WAIT_SECONDS = 300


def reuse_lock_id(reuse_key: str) -> int:
    return int.from_bytes(hashlib.blake2b(f"showroom-reuse:{reuse_key}".encode(), digest_size=8).digest(), signed=True)


def scan_babylon_item(db, settings, content_id: str, *, force: bool = False) -> dict:
    """Serialize stages sharing a reuse key so the second finds the first's
    persisted generation as a donor instead of making its own LLM call."""
    item = db.get_babylon_item(content_id)
    reuse_key = showroom_reuse_key(item, settings) if item and not force else None
    if reuse_key is None:
        return _scan_babylon_item(db, settings, content_id, force=force)
    with db.wait_advisory_lock(reuse_lock_id(reuse_key), wait_seconds=REUSE_LOCK_WAIT_SECONDS) as acquired:
        if not acquired:
            log.warning("showroom_reuse_lock_timeout", component="scanner", content_id=content_id,
                        action="reuse_lock_timeout", wait_seconds=REUSE_LOCK_WAIT_SECONDS)
        return _scan_babylon_item(db, settings, content_id, force=force)


def _scan_babylon_item(db, settings, content_id: str, *, force: bool = False) -> dict:
    item = db.get_babylon_item(content_id)
    if not item:
        return {"content_id": content_id, "success": False, "error": "missing_item", "outcome": "failed"}
    source = effective_showroom_source(item)
    if source.status == "excluded":
        log.info("showroom_scan_excluded", component="scanner", content_id=content_id, action="excluded")
        return {"content_id": content_id, "success": True, "outcome": "excluded", "source": source.to_dict()}
    snapshot = _snapshot(item)
    observed_generation = analysis_generation(db.get_showroom_analysis(content_id))
    result = None
    try:
        if source.status == "none":
            return {"content_id": content_id, "success": True, "outcome": "no_showroom", "source": source.to_dict()}
        if item.get("retired_at"):
            return {"content_id": content_id, "success": False, "outcome": "superseded"}
        if source.status != "resolved":
            result = {"error": f"{source.status}_source", "message": source.error or "Unresolved source"}
        else:
            result = analyze_showroom(ci_name=item["ci_name"], display_name=item.get("display_name", ""),
                category=item.get("category", ""), product=item.get("product", ""),
                showroom_url=source.repo, showroom_ref=source.ref, settings=settings, model=settings.model,
                clone_dir=settings.clone_dir, db=db, content_path=source.content_path,
                keywords=item.get("keywords") or [], entity_content_type=item.get("content_type") or "lab",
                source=source, force=force)
        if not result:
            result = {"error": "no_result", "message": "Analysis returned no results"}
        with db.pool.connection() as conn:
            current = db.lock_babylon_item(conn, content_id)
            if (current is None or _snapshot(current) != snapshot
                    or analysis_generation(db.get_showroom_analysis(content_id, conn=conn, for_update=True)) != observed_generation):
                return {"content_id": content_id, "success": False, "outcome": "superseded", "source": source.to_dict()}
            if "error" in result:
                db.invalidate_babylon_scan_failure(content_id, result["error"], result.get("message"), conn=conn)
                return {"content_id": content_id, "success": False, "outcome": "failed", "source": source.to_dict(), **result}
            outcome = result["outcome"]
            if outcome != "unchanged":
                analysis = result["analysis"]
                data = {"content_id": content_id, "analysis_provenance_json": result["analysis_provenance"],
                        "last_repo_commit": result["last_repo_commit"], "last_repo_updated": result.get("last_repo_updated"),
                        "content_hash": result["content_hash"], "is_stale": False, "stale_commit": None,
                        "last_analyzed": result["last_analyzed"]}
                if outcome in ("analyzed", "reused"):
                    data.update({key: analysis.get(key) for key in ("summary", "content_type", "difficulty", "estimated_duration_min")})
                    data.update({key + "_json": analysis.get(key) for key in ("products", "audience", "recommender_audience", "topics",
                        "modules", "learning_objectives", "use_cases")})
                    formats = analysis.get("format_suitability")
                    data["format_suitability_json"] = ({key: value for key, value in formats.items() if key in ("demo", "hands_on_lab")}
                                                       if isinstance(formats, dict) else None)
                    db.update_content_entity_card(content_id, summary=analysis.get("summary"), products_json=analysis.get("products"),
                        topics_json=analysis.get("topics"), audience_json=analysis.get("audience"), difficulty=analysis.get("difficulty"), conn=conn)
                db.upsert_showroom_analysis(data, conn=conn)
                if outcome in ("analyzed", "reused", "embeddings_repaired") or result.get("embedding_changes"):
                    regenerate_embeddings(db, content_id, item["content_type"], "babylon", result["ci_embedding_text"],
                        result["ci_embedding"], module_embeddings=result.get("module_embeddings"), conn=conn)
                db.set_scan_status(content_id, "success", conn=conn)
        outcome_result = {"content_id": content_id, "ci_name": item["ci_name"], "success": True, "outcome": outcome,
                          "reused_from": result.get("reused_from"), "source": source.to_dict(),
                          "signature": result["analysis_provenance"]["signature"]}
        log.info("showroom_scan_complete", component="scanner", action=outcome, **outcome_result)
        return outcome_result
    except Exception as exc:
        error, message = classify_scan_error(exc, source.repo, source.ref, source.content_path)
        if isinstance(exc, (subprocess.CalledProcessError, subprocess.TimeoutExpired)) and error != "http_404":
            # Retryable Git failures keep prior artifacts; a missing repo is definitive.
            log.warning("showroom_scan_transient_failure", component="scanner", content_id=content_id, error_class=error)
            return {"content_id": content_id, "success": False, "outcome": "failed", "error": error, "message": message}
        with db.pool.connection() as conn:
            current = db.lock_babylon_item(conn, content_id)
            if (current is None or _snapshot(current) != snapshot
                    or analysis_generation(db.get_showroom_analysis(content_id, conn=conn, for_update=True)) != observed_generation):
                return {"content_id": content_id, "success": False, "outcome": "superseded"}
            db.invalidate_babylon_scan_failure(content_id, error, message, conn=conn)
        log.exception("showroom_scan_failed", content_id=content_id, error_class=error)
        return {"content_id": content_id, "success": False, "outcome": "failed", "error": error, "message": message}
