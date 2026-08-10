"""LLM-based overlap assessment for content similarity pairs."""

from pathlib import Path
from typing import Any
import structlog

from rcars.config import Settings, call_llm
from rcars.services.analyzer import parse_analysis_response


logger = structlog.get_logger(component="overlap_assessment")

VALID_VERDICTS = frozenset({"redundant", "complementary", "differentiated"})
VALID_RECOMMENDATIONS = frozenset({"merge", "keep_both", "retire_one"})

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "overlap_assessment.txt"


def _coerce_list(val: Any) -> list[str]:
    """Coerce value to string list. None→[], str→[str], list→filtered strings, else→[]."""
    if val is None:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        return [item for item in val if isinstance(item, str)]
    return []


def _validate_assessment(parsed: dict) -> dict | None:
    """Validate LLM assessment response and coerce to canonical form.

    Returns None if verdict or recommendation enums are invalid.
    Returns cleaned dict with all required keys if valid.
    """
    verdict = parsed.get("verdict")
    recommendation = parsed.get("recommendation")

    if verdict not in VALID_VERDICTS:
        logger.warning("invalid_verdict", verdict=verdict)
        return None
    if recommendation not in VALID_RECOMMENDATIONS:
        logger.warning("invalid_recommendation", recommendation=recommendation)
        return None

    return {
        "verdict": verdict,
        "shared_topics": _coerce_list(parsed.get("shared_topics")),
        "differentiators_a": _coerce_list(parsed.get("differentiators_a")),
        "differentiators_b": _coerce_list(parsed.get("differentiators_b")),
        "recommendation": recommendation,
        "rationale": parsed["rationale"] if isinstance(parsed.get("rationale"), str) else "",
    }


def _load_analysis_pair(pool, content_id_a: str, content_id_b: str) -> tuple[dict | None, dict | None]:
    """Load showroom_analysis + content_entities for both items."""
    with pool.connection() as conn:
        cur = conn.execute(
            """SELECT
                 ce.content_id, ce.display_name,
                 sa.summary, sa.products_json, sa.modules_json,
                 sa.learning_objectives_json, sa.audience_json,
                 sa.difficulty, sa.estimated_duration_min, sa.use_cases_json,
                 sa.topics_json
               FROM content_entities ce
               JOIN showroom_analysis sa ON sa.content_id = ce.content_id
               WHERE ce.content_id = ANY(%s)""",
            ([content_id_a, content_id_b],),
        )
        rows = {row["content_id"]: dict(row) for row in cur.fetchall()}
    return rows.get(content_id_a), rows.get(content_id_b)


def _fmt_json_field(val: Any) -> str:
    """Format JSONB field for prompt. None/empty → 'None available'."""
    if not val:
        return "None available"
    if isinstance(val, list):
        if not val:
            return "None available"
        if isinstance(val[0], dict):
            # Extract title or name key
            items = [item.get("title") or item.get("name") or str(item) for item in val]
            return "\n".join(f"- {item}" for item in items)
        return "\n".join(f"- {item}" for item in val)
    return str(val)


def _build_assessment_prompt(analysis_a: dict, analysis_b: dict) -> str:
    """Build overlap assessment prompt from template."""
    template = PROMPT_PATH.read_text()
    return template.format(
        display_name_a=analysis_a["display_name"],
        learning_objectives_a=_fmt_json_field(analysis_a.get("learning_objectives_json")),
        modules_a=_fmt_json_field(analysis_a.get("modules_json")),
        products_a=_fmt_json_field(analysis_a.get("products_json")),
        summary_a=analysis_a.get("summary") or "None available",
        audience_a=_fmt_json_field(analysis_a.get("audience_json")),
        difficulty_a=analysis_a.get("difficulty") or "unknown",
        duration_a=analysis_a.get("estimated_duration_min") or "unknown",
        use_cases_a=_fmt_json_field(analysis_a.get("use_cases_json")),
        topics_a=_fmt_json_field(analysis_a.get("topics_json")),
        display_name_b=analysis_b["display_name"],
        learning_objectives_b=_fmt_json_field(analysis_b.get("learning_objectives_json")),
        modules_b=_fmt_json_field(analysis_b.get("modules_json")),
        products_b=_fmt_json_field(analysis_b.get("products_json")),
        summary_b=analysis_b.get("summary") or "None available",
        audience_b=_fmt_json_field(analysis_b.get("audience_json")),
        difficulty_b=analysis_b.get("difficulty") or "unknown",
        duration_b=analysis_b.get("estimated_duration_min") or "unknown",
        use_cases_b=_fmt_json_field(analysis_b.get("use_cases_json")),
        topics_b=_fmt_json_field(analysis_b.get("topics_json")),
    )


def assess_overlap(
    pool,
    settings: Settings,
    content_id_a: str,
    content_id_b: str,
) -> tuple[dict | None, str]:
    """Assess overlap between two content items via LLM.

    Returns (assessment_dict, reason). Reason is "ok" on success,
    or one of: "cached", "missing_analysis", "not_overlap", "llm_error",
    "parse_error", "validation_error".
    """
    # Normalize order to match content_similarity constraint
    if content_id_a > content_id_b:
        content_id_a, content_id_b = content_id_b, content_id_a

    # Check cache
    with pool.connection() as conn:
        cur = conn.execute(
            """SELECT llm_assessment, relationship_type FROM content_similarity
               WHERE content_id_a = %s AND content_id_b = %s""",
            (content_id_a, content_id_b),
        )
        row = cur.fetchone()
        if not row or row.get("relationship_type") != "overlap":
            logger.warning("not_overlap_pair", content_id_a=content_id_a, content_id_b=content_id_b)
            return None, "not_overlap"
        if row["llm_assessment"]:
            logger.debug("overlap_assessment_cached", content_id_a=content_id_a, content_id_b=content_id_b)
            return row["llm_assessment"], "cached"

    # Load analysis data
    analysis_a, analysis_b = _load_analysis_pair(pool, content_id_a, content_id_b)
    if not analysis_a or not analysis_b:
        logger.warning("missing_analysis_for_overlap_pair", content_id_a=content_id_a, content_id_b=content_id_b)
        return None, "missing_analysis"

    # Build prompt and call LLM
    prompt = _build_assessment_prompt(analysis_a, analysis_b)
    logger.info("calling_llm_for_overlap", content_id_a=content_id_a, content_id_b=content_id_b, model=settings.overlap_model)

    try:
        result = call_llm(
            settings=settings,
            model=settings.overlap_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0,
        )
    except Exception as e:
        logger.error("llm_call_failed", content_id_a=content_id_a, content_id_b=content_id_b, error=str(e))
        return None, "llm_error"

    # Parse response
    parsed = parse_analysis_response(result.text)
    if not parsed:
        logger.warning("failed_to_parse_overlap_response", content_id_a=content_id_a, content_id_b=content_id_b)
        return None, "parse_error"

    # Validate
    validated = _validate_assessment(parsed)
    if not validated:
        logger.warning("invalid_overlap_assessment", content_id_a=content_id_a, content_id_b=content_id_b, parsed=parsed)
        return None, "validation_error"

    # Attach metadata
    validated["model"] = settings.overlap_model
    validated["tokens"] = {
        "input": result.input_tokens,
        "output": result.output_tokens,
    }

    # Persist
    import json as json_module
    with pool.connection() as conn:
        conn.execute(
            """UPDATE content_similarity
               SET llm_assessment = %s::jsonb, assessed_at = NOW()
               WHERE content_id_a = %s AND content_id_b = %s""",
            (json_module.dumps(validated), content_id_a, content_id_b),
        )
        conn.commit()

    logger.info("overlap_assessed", content_id_a=content_id_a, content_id_b=content_id_b, verdict=validated["verdict"])
    return validated, "ok"


def batch_assess_overlaps(pool, settings: Settings, min_score: float = 0.95) -> dict:
    """Assess all unassessed overlap pairs above threshold.

    Returns summary: pairs_found, assessed, skipped, errors, total_tokens.
    """
    logger.info("batch_assess_start", min_score=min_score)

    # Find unassessed pairs
    with pool.connection() as conn:
        cur = conn.execute(
            """SELECT content_id_a, content_id_b
               FROM content_similarity
               WHERE relationship_type = 'overlap'
                 AND similarity_score >= %s
                 AND llm_assessment IS NULL
               ORDER BY similarity_score DESC""",
            (min_score,),
        )
        pairs = [(row["content_id_a"], row["content_id_b"]) for row in cur.fetchall()]

    pairs_found = len(pairs)
    assessed = 0
    skipped = 0
    errors = 0
    total_tokens = 0

    for content_id_a, content_id_b in pairs:
        try:
            result, reason = assess_overlap(pool, settings, content_id_a, content_id_b)
            if reason == "ok":
                assessed += 1
                total_tokens += result["tokens"]["input"] + result["tokens"]["output"]
            elif reason in {"cached", "missing_analysis", "not_overlap"}:
                skipped += 1
            else:
                errors += 1
        except Exception as e:
            logger.error("batch_assess_error", content_id_a=content_id_a, content_id_b=content_id_b, error=str(e))
            errors += 1
    logger.info("batch_assess_complete", pairs_found=pairs_found, assessed=assessed, skipped=skipped, errors=errors, total_tokens=total_tokens)

    return {
        "pairs_found": pairs_found,
        "assessed": assessed,
        "skipped": skipped,
        "errors": errors,
        "total_tokens": total_tokens,
    }
